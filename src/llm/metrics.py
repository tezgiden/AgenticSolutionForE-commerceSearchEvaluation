"""
Performance metrics and monitoring system for LLM Search Result Evaluation.

Provides comprehensive metrics collection, performance monitoring, and alerting
capabilities for production deployments.
"""

import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Deque
from abc import ABC, abstractmethod
import json
import os
from pathlib import Path

from .logging_config import get_logger, LoggerMixin


@dataclass
class MetricData:
    """Individual metric data point."""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""


@dataclass
class PerformanceStats:
    """Performance statistics for operations."""
    count: int = 0
    total_duration: float = 0.0
    min_duration: float = float('inf')
    max_duration: float = 0.0
    avg_duration: float = 0.0
    p50_duration: float = 0.0
    p95_duration: float = 0.0
    p99_duration: float = 0.0
    error_count: int = 0
    success_rate: float = 100.0
    
    def update(self, duration: float, success: bool = True):
        """Update statistics with new measurement."""
        self.count += 1
        self.total_duration += duration
        self.min_duration = min(self.min_duration, duration)
        self.max_duration = max(self.max_duration, duration)
        self.avg_duration = self.total_duration / self.count
        
        if not success:
            self.error_count += 1
        
        self.success_rate = ((self.count - self.error_count) / self.count) * 100


class MetricsCollector(ABC):
    """Abstract base class for metrics collectors."""
    
    @abstractmethod
    def collect(self, metric: MetricData) -> None:
        """Collect a metric data point."""
        pass
    
    @abstractmethod
    def flush(self) -> None:
        """Flush any buffered metrics."""
        pass


class InMemoryMetricsCollector(MetricsCollector, LoggerMixin):
    """In-memory metrics collector for development and testing."""
    
    def __init__(self, max_metrics: int = 10000):
        self.max_metrics = max_metrics
        self.metrics: Deque[MetricData] = deque(maxlen=max_metrics)
        self._lock = threading.Lock()
    
    def collect(self, metric: MetricData) -> None:
        """Store metric in memory."""
        with self._lock:
            self.metrics.append(metric)
            self.logger.debug(f"Collected metric: {metric.name}={metric.value}")
    
    def flush(self) -> None:
        """No-op for in-memory collector."""
        pass
    
    def get_metrics(self, name: Optional[str] = None, 
                   since: Optional[datetime] = None) -> List[MetricData]:
        """Retrieve metrics with optional filtering."""
        with self._lock:
            filtered_metrics = []
            for metric in self.metrics:
                if name and metric.name != name:
                    continue
                if since and metric.timestamp < since:
                    continue
                filtered_metrics.append(metric)
            return filtered_metrics
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collector statistics."""
        with self._lock:
            return {
                "total_metrics": len(self.metrics),
                "max_metrics": self.max_metrics,
                "oldest_metric": self.metrics[0].timestamp if self.metrics else None,
                "newest_metric": self.metrics[-1].timestamp if self.metrics else None
            }


class FileMetricsCollector(MetricsCollector, LoggerMixin):
    """File-based metrics collector for persistent storage."""
    
    def __init__(self, file_path: str, buffer_size: int = 100):
        self.file_path = Path(file_path)
        self.buffer_size = buffer_size
        self.buffer: List[MetricData] = []
        self._lock = threading.Lock()
        
        # Ensure directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def collect(self, metric: MetricData) -> None:
        """Buffer metric for file writing."""
        with self._lock:
            self.buffer.append(metric)
            if len(self.buffer) >= self.buffer_size:
                self._flush_buffer()
    
    def flush(self) -> None:
        """Flush buffered metrics to file."""
        with self._lock:
            if self.buffer:
                self._flush_buffer()
    
    def _flush_buffer(self) -> None:
        """Internal method to write buffer to file."""
        try:
            with open(self.file_path, 'a', encoding='utf-8') as f:
                for metric in self.buffer:
                    metric_dict = {
                        'name': metric.name,
                        'value': metric.value,
                        'timestamp': metric.timestamp.isoformat(),
                        'tags': metric.tags,
                        'unit': metric.unit
                    }
                    f.write(json.dumps(metric_dict) + '\n')
            
            self.logger.debug(f"Flushed {len(self.buffer)} metrics to {self.file_path}")
            self.buffer.clear()
            
        except Exception as e:
            self.logger.error(f"Failed to flush metrics to file: {e}")


class PrometheusMetricsCollector(MetricsCollector, LoggerMixin):
    """Prometheus-compatible metrics collector."""
    
    def __init__(self, port: int = 9090, endpoint: str = "/metrics"):
        self.port = port
        self.endpoint = endpoint
        self.metrics_data: Dict[str, List[MetricData]] = defaultdict(list)
        self._lock = threading.Lock()
        self.logger.info(f"Prometheus metrics available at http://localhost:{port}{endpoint}")
    
    def collect(self, metric: MetricData) -> None:
        """Store metric for Prometheus exposition."""
        with self._lock:
            self.metrics_data[metric.name].append(metric)
            # Keep only recent metrics (last hour)
            cutoff = datetime.now() - timedelta(hours=1)
            self.metrics_data[metric.name] = [
                m for m in self.metrics_data[metric.name] 
                if m.timestamp > cutoff
            ]
    
    def flush(self) -> None:
        """No-op for Prometheus collector."""
        pass
    
    def generate_prometheus_format(self) -> str:
        """Generate metrics in Prometheus format."""
        lines = []
        
        with self._lock:
            for name, metrics in self.metrics_data.items():
                if not metrics:
                    continue
                
                # Get latest metric for each unique tag combination
                latest_metrics = {}
                for metric in metrics:
                    tag_key = tuple(sorted(metric.tags.items()))
                    if tag_key not in latest_metrics or metric.timestamp > latest_metrics[tag_key].timestamp:
                        latest_metrics[tag_key] = metric
                
                # Generate Prometheus format
                for metric in latest_metrics.values():
                    if metric.tags:
                        tags_str = ','.join(f'{k}="{v}"' for k, v in metric.tags.items())
                        lines.append(f'{name}{{{tags_str}}} {metric.value}')
                    else:
                        lines.append(f'{name} {metric.value}')
        
        return '\n'.join(lines)


class MetricsManager(LoggerMixin):
    """Central metrics management system."""
    
    def __init__(self, collectors: Optional[List[MetricsCollector]] = None):
        self.collectors = collectors or [InMemoryMetricsCollector()]
        self.performance_stats: Dict[str, PerformanceStats] = defaultdict(PerformanceStats)
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = defaultdict(float)
        self._lock = threading.Lock()
        
        # Start background flush thread
        self._flush_thread = threading.Thread(target=self._periodic_flush, daemon=True)
        self._flush_thread.start()
    
    def record_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a counter metric."""
        with self._lock:
            self.counters[name] += value
        
        metric = MetricData(
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {},
            unit="count"
        )
        self._collect_metric(metric)
    
    def record_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a gauge metric."""
        with self._lock:
            self.gauges[name] = value
        
        metric = MetricData(
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {},
            unit="gauge"
        )
        self._collect_metric(metric)
    
    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram metric."""
        metric = MetricData(
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {},
            unit="duration"
        )
        self._collect_metric(metric)
    
    def record_performance(self, operation: str, duration: float, success: bool = True, 
                          tags: Optional[Dict[str, str]] = None) -> None:
        """Record performance metrics for an operation."""
        with self._lock:
            self.performance_stats[operation].update(duration, success)
        
        # Record as histogram
        self.record_histogram(f"{operation}_duration", duration, tags)
        
        # Record success/failure counter
        status = "success" if success else "error"
        counter_tags = {**(tags or {}), "status": status}
        self.record_counter(f"{operation}_total", 1, counter_tags)
    
    def _collect_metric(self, metric: MetricData) -> None:
        """Send metric to all collectors."""
        for collector in self.collectors:
            try:
                collector.collect(metric)
            except Exception as e:
                self.logger.error(f"Failed to collect metric with {type(collector).__name__}: {e}")
    
    def _periodic_flush(self) -> None:
        """Periodically flush all collectors."""
        while True:
            try:
                time.sleep(60)  # Flush every minute
                for collector in self.collectors:
                    collector.flush()
            except Exception as e:
                self.logger.error(f"Error in periodic flush: {e}")
    
    def get_performance_stats(self) -> Dict[str, PerformanceStats]:
        """Get performance statistics for all operations."""
        with self._lock:
            return dict(self.performance_stats)
    
    def get_counter_values(self) -> Dict[str, int]:
        """Get current counter values."""
        with self._lock:
            return dict(self.counters)
    
    def get_gauge_values(self) -> Dict[str, float]:
        """Get current gauge values."""
        with self._lock:
            return dict(self.gauges)


# Global metrics manager instance
_metrics_manager: Optional[MetricsManager] = None
_metrics_lock = threading.Lock()


def get_metrics_manager() -> MetricsManager:
    """Get the global metrics manager instance."""
    global _metrics_manager
    
    if _metrics_manager is None:
        with _metrics_lock:
            if _metrics_manager is None:
                # Initialize with default collectors
                collectors = [InMemoryMetricsCollector()]
                
                # Add file collector if configured
                if os.getenv('METRICS_FILE'):
                    collectors.append(FileMetricsCollector(os.getenv('METRICS_FILE')))
                
                # Add Prometheus collector if configured
                if os.getenv('PROMETHEUS_ENABLED', '').lower() == 'true':
                    port = int(os.getenv('PROMETHEUS_PORT', 9090))
                    collectors.append(PrometheusMetricsCollector(port))
                
                _metrics_manager = MetricsManager(collectors)
    
    return _metrics_manager


def record_evaluation_metrics(query: str, results_count: int, duration: float, 
                            success: bool, model: str, search_type: str) -> None:
    """Record metrics for an evaluation operation."""
    metrics = get_metrics_manager()
    
    tags = {
        'model': model,
        'search_type': search_type,
        'results_count': str(results_count)
    }
    
    metrics.record_performance('evaluation', duration, success, tags)
    metrics.record_counter('evaluations_total', 1, tags)
    metrics.record_gauge('evaluation_results_count', results_count, tags)


def record_llm_metrics(model: str, prompt_length: int, response_length: int, 
                      duration: float, success: bool) -> None:
    """Record metrics for LLM interactions."""
    metrics = get_metrics_manager()
    
    tags = {'model': model}
    
    metrics.record_performance('llm_interaction', duration, success, tags)
    metrics.record_gauge('llm_prompt_length', prompt_length, tags)
    metrics.record_gauge('llm_response_length', response_length, tags)


def record_inventory_metrics(total_results: int, available_count: int, 
                           out_of_stock_count: int) -> None:
    """Record inventory-related metrics."""
    metrics = get_metrics_manager()
    
    metrics.record_gauge('inventory_total_results', total_results)
    metrics.record_gauge('inventory_available_count', available_count)
    metrics.record_gauge('inventory_out_of_stock_count', out_of_stock_count)
    
    if total_results > 0:
        availability_rate = (available_count / total_results) * 100
        metrics.record_gauge('inventory_availability_rate', availability_rate)


# Decorators for automatic metrics collection
def track_performance(operation_name: str = None, tags: Optional[Dict[str, str]] = None):
    """Decorator to automatically track performance metrics."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            nonlocal operation_name
            if operation_name is None:
                operation_name = f"{func.__module__}.{func.__name__}"
            
            start_time = time.time()
            success = True
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                record_performance_metric(operation_name, duration, success, tags)
        
        return wrapper
    return decorator


def count_calls(counter_name: str = None, tags: Optional[Dict[str, str]] = None):
    """Decorator to automatically count function calls."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            nonlocal counter_name
            if counter_name is None:
                counter_name = f"{func.__module__}.{func.__name__}_calls"
            
            metrics = get_metrics_manager()
            metrics.record_counter(counter_name, 1, tags)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def record_performance_metric(operation: str, duration: float, success: bool = True, 
                            tags: Optional[Dict[str, str]] = None) -> None:
    """Convenience function to record performance metrics."""
    metrics = get_metrics_manager()
    metrics.record_performance(operation, duration, success, tags)


class MetricsContext:
    """Context manager for tracking operation metrics."""
    
    def __init__(self, operation: str, tags: Optional[Dict[str, str]] = None):
        self.operation = operation
        self.tags = tags or {}
        self.start_time = None
        self.success = True
        self.metrics = get_metrics_manager()
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        success = exc_type is None
        
        self.metrics.record_performance(self.operation, duration, success, self.tags)
        
        if exc_type:
            error_tags = {**self.tags, 'error_type': exc_type.__name__}
            self.metrics.record_counter(f"{self.operation}_errors", 1, error_tags)


class AlertManager(LoggerMixin):
    """Alert management system for monitoring thresholds."""
    
    def __init__(self, metrics_manager: MetricsManager):
        self.metrics_manager = metrics_manager
        self.thresholds: Dict[str, Dict[str, float]] = {}
        self.alert_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        self.alert_history: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        
        # Start monitoring thread
        self._monitor_thread = threading.Thread(target=self._monitor_thresholds, daemon=True)
        self._monitor_thread.start()
    
    def add_threshold(self, metric_name: str, threshold_type: str, value: float) -> None:
        """Add a threshold for monitoring."""
        with self._lock:
            if metric_name not in self.thresholds:
                self.thresholds[metric_name] = {}
            self.thresholds[metric_name][threshold_type] = value
        
        self.logger.info(f"Added threshold: {metric_name} {threshold_type} {value}")
    
    def add_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """Add a callback for alert notifications."""
        self.alert_callbacks.append(callback)
    
    def _monitor_thresholds(self) -> None:
        """Monitor metrics against thresholds."""
        while True:
            try:
                time.sleep(30)  # Check every 30 seconds
                self._check_thresholds()
            except Exception as e:
                self.logger.error(f"Error in threshold monitoring: {e}")
    
    def _check_thresholds(self) -> None:
        """Check all thresholds and trigger alerts."""
        with self._lock:
            for metric_name, thresholds in self.thresholds.items():
                current_value = self._get_current_metric_value(metric_name)
                if current_value is None:
                    continue
                
                for threshold_type, threshold_value in thresholds.items():
                    if self._threshold_breached(current_value, threshold_type, threshold_value):
                        self._trigger_alert(metric_name, threshold_type, current_value, threshold_value)
    
    def _get_current_metric_value(self, metric_name: str) -> Optional[float]:
        """Get current value for a metric."""
        # Check performance stats
        perf_stats = self.metrics_manager.get_performance_stats()
        if metric_name in perf_stats:
            return perf_stats[metric_name].avg_duration
        
        # Check gauges
        gauges = self.metrics_manager.get_gauge_values()
        if metric_name in gauges:
            return gauges[metric_name]
        
        # Check counters
        counters = self.metrics_manager.get_counter_values()
        if metric_name in counters:
            return float(counters[metric_name])
        
        return None
    
    def _threshold_breached(self, value: float, threshold_type: str, threshold: float) -> bool:
        """Check if a threshold is breached."""
        if threshold_type == 'max':
            return value > threshold
        elif threshold_type == 'min':
            return value < threshold
        elif threshold_type == 'equal':
            return abs(value - threshold) < 0.001
        return False
    
    def _trigger_alert(self, metric_name: str, threshold_type: str, 
                      current_value: float, threshold_value: float) -> None:
        """Trigger an alert."""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'metric_name': metric_name,
            'threshold_type': threshold_type,
            'current_value': current_value,
            'threshold_value': threshold_value,
            'severity': 'warning' if threshold_type == 'max' else 'critical'
        }
        
        self.alert_history.append(alert)
        self.logger.warning(f"Alert triggered: {alert}")
        
        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                callback(f"Threshold breached: {metric_name}", alert)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {e}")


# Example alert callbacks
def log_alert(message: str, alert_data: Dict[str, Any]) -> None:
    """Log alert to system log."""
    logger = get_logger('llm_evaluator.alerts')
    logger.warning(f"{message}: {alert_data}")


def email_alert(message: str, alert_data: Dict[str, Any]) -> None:
    """Send email alert (placeholder implementation)."""
    # Implementation would depend on email service
    print(f"EMAIL ALERT: {message}")
    print(f"Details: {json.dumps(alert_data, indent=2)}")


# Health check functions
def get_system_health() -> Dict[str, Any]:
    """Get overall system health status."""
    metrics = get_metrics_manager()
    perf_stats = metrics.get_performance_stats()
    
    health = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'metrics': {
            'total_evaluations': metrics.get_counter_values().get('evaluations_total', 0),
            'avg_evaluation_duration': 0.0,
            'success_rate': 100.0,
            'error_count': 0
        }
    }
    
    # Calculate overall metrics
    if 'evaluation' in perf_stats:
        eval_stats = perf_stats['evaluation']
        health['metrics']['avg_evaluation_duration'] = eval_stats.avg_duration
        health['metrics']['success_rate'] = eval_stats.success_rate
        health['metrics']['error_count'] = eval_stats.error_count
        
        # Determine health status
        if eval_stats.success_rate < 90:
            health['status'] = 'degraded'
        elif eval_stats.success_rate < 50:
            health['status'] = 'unhealthy'
    
    return health
