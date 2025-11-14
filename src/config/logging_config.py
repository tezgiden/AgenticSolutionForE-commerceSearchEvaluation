"""Logging configuration and utilities for the agentic search application."""

import os
import sys
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from constants import LogLevel, Environment, FilePatterns


class LoggingManager:
    """Manages logging configuration and setup for the application."""
    
    DEFAULT_LOG_DIR = "logs"
    DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DETAILED_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s"
    
    def __init__(self):
        """Initialize the logging manager."""
        self.log_dir = Path(self.DEFAULT_LOG_DIR)
        self.formatters: Dict[str, logging.Formatter] = {}
        self.handlers: Dict[str, logging.Handler] = {}
        self._setup_formatters()
    
    def setup_application_logging(
        self,
        log_level: str = LogLevel.INFO.value,
        environment: str = Environment.DEVELOPMENT.value,
        enable_file_logging: bool = True,
        enable_detailed_logging: bool = False
    ) -> None:
        """Setup comprehensive logging for the application.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            environment: Environment (development, production, testing)
            enable_file_logging: Whether to enable file logging
            enable_detailed_logging: Whether to use detailed log format
        """
        # Convert string log level to logging constant
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        
        # Clear existing handlers
        logging.getLogger().handlers.clear()
        
        # Setup console handler
        self._setup_console_handler(numeric_level, environment, enable_detailed_logging)
        
        # Setup file handlers if enabled
        if enable_file_logging:
            self._setup_file_handlers(numeric_level, environment, enable_detailed_logging)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        
        # Configure application-specific loggers
        self._setup_application_loggers(numeric_level)
        
        # Log the logging configuration
        logger = logging.getLogger(__name__)
        logger.info(f"Logging configured: level={log_level}, environment={environment}")
    
    def setup_module_logger(
        self,
        module_name: str,
        log_level: Optional[str] = None,
        enable_debug: bool = False
    ) -> logging.Logger:
        """Setup a logger for a specific module.
        
        Args:
            module_name: Name of the module
            log_level: Optional specific log level for this module
            enable_debug: Whether to enable debug logging for this module
            
        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(module_name)
        
        if log_level:
            numeric_level = getattr(logging, log_level.upper(), logging.INFO)
            logger.setLevel(numeric_level)
        
        if enable_debug:
            logger.setLevel(logging.DEBUG)
        
        return logger
    
    def create_performance_logger(self, operation_name: str) -> 'PerformanceLogger':
        """Create a performance logger for measuring operation times.
        
        Args:
            operation_name: Name of the operation being measured
            
        Returns:
            Performance logger instance
        """
        return PerformanceLogger(operation_name)
    
    def _setup_formatters(self) -> None:
        """Setup logging formatters."""
        self.formatters['standard'] = logging.Formatter(self.DEFAULT_LOG_FORMAT)
        self.formatters['detailed'] = logging.Formatter(self.DETAILED_LOG_FORMAT)
        self.formatters['simple'] = logging.Formatter('%(levelname)s - %(message)s')
        self.formatters['timestamp'] = logging.Formatter('%(asctime)s - %(message)s')
    
    def _setup_console_handler(
        self,
        log_level: int,
        environment: str,
        enable_detailed_logging: bool
    ) -> None:
        """Setup console logging handler.
        
        Args:
            log_level: Numeric log level
            environment: Environment name
            enable_detailed_logging: Whether to use detailed format
        """
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        
        # Use detailed format in development, simple in production
        if environment == Environment.DEVELOPMENT.value or enable_detailed_logging:
            console_handler.setFormatter(self.formatters['detailed'])
        else:
            console_handler.setFormatter(self.formatters['standard'])
        
        logging.getLogger().addHandler(console_handler)
        self.handlers['console'] = console_handler
    
    def _setup_file_handlers(
        self,
        log_level: int,
        environment: str,
        enable_detailed_logging: bool
    ) -> None:
        """Setup file logging handlers.
        
        Args:
            log_level: Numeric log level
            environment: Environment name
            enable_detailed_logging: Whether to use detailed format
        """
        # Ensure log directory exists
        self.log_dir.mkdir(exist_ok=True)
        
        # Setup main application log file
        self._setup_main_log_file(log_level, enable_detailed_logging)
        
        # Setup error log file
        self._setup_error_log_file()
        
        # Setup debug log file if in development
        if environment == Environment.DEVELOPMENT.value:
            self._setup_debug_log_file()
    
    def _setup_main_log_file(self, log_level: int, enable_detailed_logging: bool) -> None:
        """Setup main application log file handler."""
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = self.log_dir / f"agentic_search_{timestamp}.log"
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(log_level)
        
        formatter = self.formatters['detailed'] if enable_detailed_logging else self.formatters['standard']
        file_handler.setFormatter(formatter)
        
        logging.getLogger().addHandler(file_handler)
        self.handlers['file'] = file_handler
    
    def _setup_error_log_file(self) -> None:
        """Setup error-specific log file handler."""
        timestamp = datetime.now().strftime("%Y%m%d")
        error_log_file = self.log_dir / f"errors_{timestamp}.log"
        
        error_handler = logging.FileHandler(error_log_file)
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(self.formatters['detailed'])
        
        logging.getLogger().addHandler(error_handler)
        self.handlers['error'] = error_handler
    
    def _setup_debug_log_file(self) -> None:
        """Setup debug-specific log file handler."""
        timestamp = datetime.now().strftime("%Y%m%d")
        debug_log_file = self.log_dir / f"debug_{timestamp}.log"
        
        debug_handler = logging.FileHandler(debug_log_file)
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(self.formatters['detailed'])
        
        # Only add to root logger if debug level is enabled
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            logging.getLogger().addHandler(debug_handler)
            self.handlers['debug'] = debug_handler
    
    def _setup_application_loggers(self, log_level: int) -> None:
        """Setup loggers for specific application modules.
        
        Args:
            log_level: Numeric log level
        """
        # Application module loggers
        app_modules = [
            'search_orchestrator',
            'search_session',
            'inventory_analyzer',
            'business_summary_generator',
            'results_manager',
            'cli_handler',
            'config_loader',
            'web_scraper'
        ]
        
        for module in app_modules:
            logger = logging.getLogger(module)
            logger.setLevel(log_level)
        
        # Third-party library loggers (reduce verbosity)
        third_party_loggers = [
            'selenium',
            'urllib3',
            'requests'
        ]
        
        for lib in third_party_loggers:
            logger = logging.getLogger(lib)
            logger.setLevel(logging.WARNING)
    
    def add_custom_handler(self, name: str, handler: logging.Handler) -> None:
        """Add a custom logging handler.
        
        Args:
            name: Name for the handler
            handler: Logging handler instance
        """
        logging.getLogger().addHandler(handler)
        self.handlers[name] = handler
    
    def remove_handler(self, name: str) -> None:
        """Remove a specific logging handler.
        
        Args:
            name: Name of the handler to remove
        """
        if name in self.handlers:
            logging.getLogger().removeHandler(self.handlers[name])
            del self.handlers[name]
    
    def get_log_file_paths(self) -> Dict[str, str]:
        """Get paths to all log files.
        
        Returns:
            Dictionary mapping log types to file paths
        """
        timestamp = datetime.now().strftime("%Y%m%d")
        
        return {
            'main': str(self.log_dir / f"agentic_search_{timestamp}.log"),
            'error': str(self.log_dir / f"errors_{timestamp}.log"),
            'debug': str(self.log_dir / f"debug_{timestamp}.log")
        }


class PerformanceLogger:
    """Logger for measuring and logging performance metrics."""
    
    def __init__(self, operation_name: str):
        """Initialize performance logger.
        
        Args:
            operation_name: Name of the operation being measured
        """
        self.operation_name = operation_name
        self.logger = logging.getLogger(f"performance.{operation_name}")
        self.start_time: Optional[float] = None
        self.metrics: Dict[str, Any] = {}
    
    def start(self) -> 'PerformanceLogger':
        """Start performance measurement.
        
        Returns:
            Self for method chaining
        """
        import time
        self.start_time = time.time()
        self.logger.debug(f"Starting performance measurement: {self.operation_name}")
        return self
    
    def end(self, success: bool = True, **kwargs) -> float:
        """End performance measurement and log results.
        
        Args:
            success: Whether the operation was successful
            **kwargs: Additional metrics to log
            
        Returns:
            Elapsed time in seconds
        """
        import time
        
        if self.start_time is None:
            self.logger.warning(f"Performance measurement not started for: {self.operation_name}")
            return 0.0
        
        elapsed_time = time.time() - self.start_time
        
        # Collect metrics
        self.metrics.update({
            'operation': self.operation_name,
            'elapsed_time_seconds': round(elapsed_time, 3),
            'success': success,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        })
        
        # Log performance metrics
        status = "completed" if success else "failed"
        self.logger.info(
            f"Performance: {self.operation_name} {status} in {elapsed_time:.3f}s"
        )
        
        # Log detailed metrics at debug level
        self.logger.debug(f"Performance metrics: {self.metrics}")
        
        return elapsed_time
    
    def add_metric(self, key: str, value: Any) -> None:
        """Add a custom metric.
        
        Args:
            key: Metric name
            value: Metric value
        """
        self.metrics[key] = value
    
    def __enter__(self) -> 'PerformanceLogger':
        """Context manager entry."""
        return self.start()
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        success = exc_type is None
        self.end(success=success)


class StructuredLogger:
    """Logger that supports structured logging with additional context."""
    
    def __init__(self, logger_name: str):
        """Initialize structured logger.
        
        Args:
            logger_name: Name for the logger
        """
        self.logger = logging.getLogger(logger_name)
        self.context: Dict[str, Any] = {}
    
    def set_context(self, **kwargs) -> None:
        """Set context information for subsequent log messages.
        
        Args:
            **kwargs: Context key-value pairs
        """
        self.context.update(kwargs)
    
    def clear_context(self) -> None:
        """Clear all context information."""
        self.context.clear()
    
    def _format_message(self, message: str, **kwargs) -> str:
        """Format message with context and additional data.
        
        Args:
            message: Base log message
            **kwargs: Additional data to include
            
        Returns:
            Formatted message
        """
        all_data = {**self.context, **kwargs}
        
        if all_data:
            context_str = " | ".join(f"{k}={v}" for k, v in all_data.items())
            return f"{message} | {context_str}"
        
        return message
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with context."""
        self.logger.debug(self._format_message(message, **kwargs))
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message with context."""
        self.logger.info(self._format_message(message, **kwargs))
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with context."""
        self.logger.warning(self._format_message(message, **kwargs))
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message with context."""
        self.logger.error(self._format_message(message, **kwargs))
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message with context."""
        self.logger.critical(self._format_message(message, **kwargs))


# Global logging manager instance
_logging_manager = LoggingManager()


def setup_logging(
    log_level: str = LogLevel.INFO.value,
    environment: str = Environment.DEVELOPMENT.value,
    enable_file_logging: bool = True,
    enable_detailed_logging: bool = False
) -> None:
    """Setup application logging (convenience function).
    
    Args:
        log_level: Logging level
        environment: Environment name
        enable_file_logging: Whether to enable file logging
        enable_detailed_logging: Whether to use detailed format
    """
    _logging_manager.setup_application_logging(
        log_level, environment, enable_file_logging, enable_detailed_logging
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance (convenience function).
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def get_structured_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance (convenience function).
    
    Args:
        name: Logger name
        
    Returns:
        Structured logger instance
    """
    return StructuredLogger(name)


def get_performance_logger(operation_name: str) -> PerformanceLogger:
    """Get a performance logger instance (convenience function).
    
    Args:
        operation_name: Name of the operation
        
    Returns:
        Performance logger instance
    """
    return _logging_manager.create_performance_logger(operation_name)