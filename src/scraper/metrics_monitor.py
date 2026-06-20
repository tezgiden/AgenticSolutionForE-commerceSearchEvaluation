"""Metrics collection and monitoring for web scraping operations."""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import defaultdict, Counter

from exceptions import ErrorHandler


logger = logging.getLogger(__name__)


@dataclass
class ScrapingMetric:
    """Data class for individual scraping metrics."""
    
    timestamp: datetime
    site_name: str
    search_term: str
    operation: str  # 'search', 'extract', 'navigate', etc.
    duration_seconds: float
    success: bool
    results_count: int = 0
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    page_url: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScrapingMetric':
        """Create from dictionary."""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class PerformanceStats:
    """Performance statistics for a set of operations."""
    
    total_operations: int
    successful_operations: int
    failed_operations: int
    success_rate: float
    average_duration: float
    min_duration: float
    max_duration: float
    total_duration: float
    error_breakdown: Dict[str, int]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class MetricsCollector:
    """Collects and stores scraping metrics."""
    
    def __init__(self, enable_collection: bool = True, storage_path: Optional[str] = None):
        """Initialize metrics collector.
        
        Args:
            enable_collection: Whether to collect metrics
            storage_path: Optional path to store metrics (default: metrics.json)
        """
        self.enable_collection = enable_collection
        self.storage_path = storage_path or "metrics.json"
        self.metrics: List[ScrapingMetric] = []
        self.current_operations: Dict[str, float] = {}  # Track ongoing operations
        
        # Load existing metrics if file exists
        self._load_existing_metrics()
    
    def start_operation(self, operation_id: str) -> None:
        """Start timing an operation.
        
        Args:
            operation_id: Unique identifier for the operation
        """
        if not self.enable_collection:
            return
        
        self.current_operations[operation_id] = time.time()
    
    def end_operation(
        self,
        operation_id: str,
        site_name: str,
        search_term: str,
        operation: str,
        success: bool,
        results_count: int = 0,
        error: Optional[Exception] = None,
        page_url: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Optional[ScrapingMetric]:
        """End timing an operation and record metric.
        
        Args:
            operation_id: Unique identifier for the operation
            site_name: Name of the site being scraped
            search_term: Search term used
            operation: Type of operation
            success: Whether operation was successful
            results_count: Number of results obtained
            error: Exception if operation failed
            page_url: URL of the page
            additional_data: Additional metric data
            
        Returns:
            Created ScrapingMetric or None if collection disabled
        """
        if not self.enable_collection or operation_id not in self.current_operations:
            return None
        
        start_time = self.current_operations.pop(operation_id)
        duration = time.time() - start_time
        
        error_type = None
        error_message = None
        if error:
            error_type = ErrorHandler.categorize_error(error)
            error_message = str(error)
        
        metric = ScrapingMetric(
            timestamp=datetime.now(),
            site_name=site_name,
            search_term=search_term,
            operation=operation,
            duration_seconds=duration,
            success=success,
            results_count=results_count,
            error_type=error_type,
            error_message=error_message,
            page_url=page_url,
            additional_data=additional_data
        )
        
        self.metrics.append(metric)
        logger.debug(f"Recorded metric: {operation} took {duration:.2f}s, success={success}")
        
        return metric
    
    def record_simple_metric(
        self,
        site_name: str,
        search_term: str,
        operation: str,
        duration_seconds: float,
        success: bool,
        results_count: int = 0,
        error: Optional[Exception] = None,
        **kwargs
    ) -> Optional[ScrapingMetric]:
        """Record a simple metric without start/end tracking.
        
        Args:
            site_name: Name of the site
            search_term: Search term used
            operation: Type of operation
            duration_seconds: Duration in seconds
            success: Whether operation was successful
            results_count: Number of results
            error: Exception if failed
            **kwargs: Additional data
            
        Returns:
            Created ScrapingMetric or None if collection disabled
        """
        if not self.enable_collection:
            return None
        
        error_type = None
        error_message = None
        if error:
            error_type = ErrorHandler.categorize_error(error)
            error_message = str(error)
        
        metric = ScrapingMetric(
            timestamp=datetime.now(),
            site_name=site_name,
            search_term=search_term,
            operation=operation,
            duration_seconds=duration_seconds,
            success=success,
            results_count=results_count,
            error_type=error_type,
            error_message=error_message,
            additional_data=kwargs
        )
        
        self.metrics.append(metric)
        return metric
    
    def get_stats(
        self,
        site_name: Optional[str] = None,
        operation: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> PerformanceStats:
        """Get performance statistics.
        
        Args:
            site_name: Filter by site name
            operation: Filter by operation type
            since: Only include metrics since this datetime
            
        Returns:
            PerformanceStats object
        """
        filtered_metrics = self._filter_metrics(site_name, operation, since)
        
        if not filtered_metrics:
            return PerformanceStats(
                total_operations=0,
                successful_operations=0,
                failed_operations=0,
                success_rate=0.0,
                average_duration=0.0,
                min_duration=0.0,
                max_duration=0.0,
                total_duration=0.0,
                error_breakdown={}
            )
        
        durations = [m.duration_seconds for m in filtered_metrics]
        successful = [m for m in filtered_metrics if m.success]
        failed = [m for m in filtered_metrics if not m.success]
        
        error_breakdown = Counter()
        for metric in failed:
            if metric.error_type:
                error_breakdown[metric.error_type] += 1
        
        return PerformanceStats(
            total_operations=len(filtered_metrics),
            successful_operations=len(successful),
            failed_operations=len(failed),
            success_rate=len(successful) / len(filtered_metrics) * 100,
            average_duration=sum(durations) / len(durations),
            min_duration=min(durations),
            max_duration=max(durations),
            total_duration=sum(durations),
            error_breakdown=dict(error_breakdown)
        )
    
    def get_site_performance(self) -> Dict[str, PerformanceStats]:
        """Get performance stats grouped by site.
        
        Returns:
            Dictionary mapping site names to their performance stats
        """
        site_stats = {}
        sites = set(m.site_name for m in self.metrics)
        
        for site in sites:
            site_stats[site] = self.get_stats(site_name=site)
        
        return site_stats
    
    def get_operation_performance(self) -> Dict[str, PerformanceStats]:
        """Get performance stats grouped by operation type.
        
        Returns:
            Dictionary mapping operation types to their performance stats
        """
        operation_stats = {}
        operations = set(m.operation for m in self.metrics)
        
        for operation in operations:
            operation_stats[operation] = self.get_stats(operation=operation)
        
        return operation_stats
    
    def get_recent_errors(self, hours: int = 24) -> List[ScrapingMetric]:
        """Get recent error metrics.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of error metrics from the specified time period
        """
        since = datetime.now() - timedelta(hours=hours)
        return [m for m in self.metrics if not m.success and m.timestamp >= since]
    
    def save_metrics(self, filepath: Optional[str] = None) -> None:
        """Save metrics to file.
        
        Args:
            filepath: Optional file path (uses default if None)
        """
        if not self.enable_collection:
            return
        
        filepath = filepath or self.storage_path
        
        try:
            metrics_data = [metric.to_dict() for metric in self.metrics]
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(metrics_data, f, indent=2, default=str)
            
            logger.info(f"Saved {len(self.metrics)} metrics to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving metrics: {e}")
    
    def _load_existing_metrics(self) -> None:
        """Load existing metrics from file."""
        if not Path(self.storage_path).exists():
            return
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                metrics_data = json.load(f)
            
            self.metrics = [ScrapingMetric.from_dict(data) for data in metrics_data]
            logger.info(f"Loaded {len(self.metrics)} existing metrics")
            
        except Exception as e:
            logger.warning(f"Error loading existing metrics: {e}")
            self.metrics = []
    
    def _filter_metrics(
        self,
        site_name: Optional[str],
        operation: Optional[str],
        since: Optional[datetime]
    ) -> List[ScrapingMetric]:
        """Filter metrics by criteria."""
        filtered = self.metrics
        
        if site_name:
            filtered = [m for m in filtered if m.site_name == site_name]
        
        if operation:
            filtered = [m for m in filtered if m.operation == operation]
        
        if since:
            filtered = [m for m in filtered if m.timestamp >= since]
        
        return filtered


class PerformanceMonitor:
    """High-level performance monitoring and alerting."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        """Initialize performance monitor.
        
        Args:
            metrics_collector: MetricsCollector instance
        """
        self.metrics_collector = metrics_collector
        self.thresholds = {
            'min_success_rate': 80.0,  # Minimum success rate percentage
            'max_avg_duration': 30.0,  # Maximum average duration in seconds
            'max_error_rate': 20.0,    # Maximum error rate percentage
        }
    
    def set_thresholds(self, **thresholds) -> None:
        """Set performance thresholds.
        
        Args:
            **thresholds: Threshold values to update
        """
        self.thresholds.update(thresholds)
    
    def check_performance_alerts(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Check for performance issues and return alerts.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            List of alert dictionaries
        """
        alerts = []
        since = datetime.now() - timedelta(hours=hours)
        
        # Overall performance check
        overall_stats = self.metrics_collector.get_stats(since=since)
        if overall_stats.total_operations > 0:
            alerts.extend(self._check_stats_against_thresholds(overall_stats, "Overall"))
        
        # Per-site performance check
        site_stats = self.metrics_collector.get_site_performance()
        for site_name, stats in site_stats.items():
            site_filtered_stats = self.metrics_collector.get_stats(site_name=site_name, since=since)
            if site_filtered_stats.total_operations > 0:
                alerts.extend(self._check_stats_against_thresholds(
                    site_filtered_stats, f"Site: {site_name}"
                ))
        
        return alerts
    
    def generate_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate a comprehensive performance report.
        
        Args:
            hours: Number of hours to include in report
            
        Returns:
            Performance report dictionary
        """
        since = datetime.now() - timedelta(hours=hours)
        
        overall_stats = self.metrics_collector.get_stats(since=since)
        site_stats = {
            site: self.metrics_collector.get_stats(site_name=site, since=since)
            for site in set(m.site_name for m in self.metrics_collector.metrics)
        }
        operation_stats = {
            op: self.metrics_collector.get_stats(operation=op, since=since)
            for op in set(m.operation for m in self.metrics_collector.metrics)
        }
        
        recent_errors = self.metrics_collector.get_recent_errors(hours)
        alerts = self.check_performance_alerts(hours)
        
        return {
            'report_period_hours': hours,
            'generated_at': datetime.now().isoformat(),
            'overall_performance': overall_stats.to_dict(),
            'site_performance': {site: stats.to_dict() for site, stats in site_stats.items()},
            'operation_performance': {op: stats.to_dict() for op, stats in operation_stats.items()},
            'recent_errors': [error.to_dict() for error in recent_errors],
            'alerts': alerts,
            'thresholds': self.thresholds
        }
    
    def _check_stats_against_thresholds(self, stats: PerformanceStats, context: str) -> List[Dict[str, Any]]:
        """Check stats against thresholds and return alerts."""
        alerts = []
        
        # Success rate check
        if stats.success_rate < self.thresholds['min_success_rate']:
            alerts.append({
                'type': 'low_success_rate',
                'context': context,
                'message': f"Success rate ({stats.success_rate:.1f}%) below threshold ({self.thresholds['min_success_rate']:.1f}%)",
                'severity': 'warning' if stats.success_rate > 50 else 'critical',
                'value': stats.success_rate,
                'threshold': self.thresholds['min_success_rate']
            })
        
        # Average duration check
        if stats.average_duration > self.thresholds['max_avg_duration']:
            alerts.append({
                'type': 'slow_performance',
                'context': context,
                'message': f"Average duration ({stats.average_duration:.1f}s) above threshold ({self.thresholds['max_avg_duration']:.1f}s)",
                'severity': 'warning',
                'value': stats.average_duration,
                'threshold': self.thresholds['max_avg_duration']
            })
        
        # Error rate check
        error_rate = (stats.failed_operations / stats.total_operations * 100) if stats.total_operations > 0 else 0
        if error_rate > self.thresholds['max_error_rate']:
            alerts.append({
                'type': 'high_error_rate',
                'context': context,
                'message': f"Error rate ({error_rate:.1f}%) above threshold ({self.thresholds['max_error_rate']:.1f}%)",
                'severity': 'critical' if error_rate > 50 else 'warning',
                'value': error_rate,
                'threshold': self.thresholds['max_error_rate']
            })
        
        return alerts


# Decorator for automatic metric collection
def track_operation(
    metrics_collector: MetricsCollector,
    operation: str,
    site_name: Optional[str] = None,
    search_term: Optional[str] = None
):
    """Decorator to automatically track operation metrics.
    
    Args:
        metrics_collector: MetricsCollector instance
        operation: Operation type
        site_name: Site name (can be determined from function args)
        search_term: Search term (can be determined from function args)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            operation_id = f"{func.__name__}_{time.time()}"
            
            # Try to extract site_name and search_term from function arguments
            actual_site_name = site_name
            actual_search_term = search_term
            
            if not actual_site_name and len(args) > 0:
                # Try to get site name from first argument if it has site_name attribute
                if hasattr(args[0], 'site_name'):
                    actual_site_name = args[0].site_name
            
            if not actual_search_term and len(args) > 1:
                # Assume second argument might be search term
                if isinstance(args[1], str):
                    actual_search_term = args[1]
            
            # Fallback values
            actual_site_name = actual_site_name or "unknown"
            actual_search_term = actual_search_term or "unknown"
            
            metrics_collector.start_operation(operation_id)
            
            try:
                result = func(*args, **kwargs)
                
                # Try to determine results count
                results_count = 0
                if isinstance(result, list):
                    results_count = len(result)
                elif isinstance(result, dict) and 'results' in result:
                    results_count = len(result['results'])
                
                metrics_collector.end_operation(
                    operation_id=operation_id,
                    site_name=actual_site_name,
                    search_term=actual_search_term,
                    operation=operation,
                    success=True,
                    results_count=results_count
                )
                
                return result
                
            except Exception as e:
                metrics_collector.end_operation(
                    operation_id=operation_id,
                    site_name=actual_site_name,
                    search_term=actual_search_term,
                    operation=operation,
                    success=False,
                    error=e
                )
                raise
        
        return wrapper
    return decorator