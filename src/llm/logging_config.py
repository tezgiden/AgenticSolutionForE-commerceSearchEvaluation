"""
Logging configuration for the LLM Search Result Evaluation System.

Provides structured logging with appropriate levels, formatters, and handlers
for different environments (development, testing, production).
"""

import logging
import logging.config
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from .config import LLMConfig


class ContextFilter(logging.Filter):
    """Custom filter to add context information to log records."""
    
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.context = context or {}
    
    def filter(self, record):
        # Add context information to the log record
        for key, value in self.context.items():
            setattr(record, key, value)
        
        # Add some standard context
        if not hasattr(record, 'component'):
            # Try to determine component from logger name
            name_parts = record.name.split('.')
            if len(name_parts) >= 2:
                record.component = name_parts[-1]
            else:
                record.component = 'unknown'
        
        return True


class TimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """Custom timed rotating file handler with better error handling."""
    
    def __init__(self, filename, when='midnight', interval=1, backupCount=7, **kwargs):
        # Ensure log directory exists
        log_path = Path(filename)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        super().__init__(filename, when, interval, backupCount, **kwargs)


def get_log_level_from_env() -> int:
    """Get log level from environment variable."""
    level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
    return getattr(logging, level_str, logging.INFO)


def create_formatter(format_type: str = 'detailed') -> logging.Formatter:
    """Create a logging formatter based on type."""
    
    formatters = {
        'simple': logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ),
        'detailed': logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(component)s - %(funcName)s:%(lineno)d - %(message)s'
        ),
        'json': JsonFormatter(),
        'development': logging.Formatter(
            '%(asctime)s [%(levelname)8s] %(component)s:%(funcName)s:%(lineno)d - %(message)s',
            datefmt='%H:%M:%S'
        ),
        'production': logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s.%(component)s - %(message)s - '
            'function=%(funcName)s line=%(lineno)d',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    }
    
    return formatters.get(format_type, formatters['detailed'])


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record):
        import json
        
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'component': getattr(record, 'component', 'unknown'),
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
        }
        
        # Add any extra context
        for key, value in record.__dict__.items():
            if key not in ('name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'stack_info', 'exc_info', 'exc_text'):
                log_entry[key] = value
        
        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, default=str)


def get_logging_config(config: LLMConfig, environment: str = 'development') -> Dict[str, Any]:
    """Get logging configuration dictionary."""
    
    log_level = get_log_level_from_env()
    log_dir = Path(config.debug_dir) / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Base configuration
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'filters': {
            'context_filter': {
                '()': ContextFilter,
            },
        },
        'formatters': {
            'simple': {
                '()': create_formatter,
                'format_type': 'simple'
            },
            'detailed': {
                '()': create_formatter,
                'format_type': 'detailed'
            },
            'development': {
                '()': create_formatter,
                'format_type': 'development'
            },
            'production': {
                '()': create_formatter,
                'format_type': 'production'
            },
            'json': {
                '()': create_formatter,
                'format_type': 'json'
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'development' if environment == 'development' else 'production',
                'filters': ['context_filter'],
                'stream': sys.stdout,
            },
            'file': {
                '()': TimedRotatingFileHandler,
                'level': 'DEBUG',
                'formatter': 'detailed',
                'filters': ['context_filter'],
                'filename': str(log_dir / 'llm_evaluator.log'),
                'when': 'midnight',
                'interval': 1,
                'backupCount': 7,
                'encoding': 'utf-8',
            },
            'error_file': {
                '()': TimedRotatingFileHandler,
                'level': 'ERROR',
                'formatter': 'detailed',
                'filters': ['context_filter'],
                'filename': str(log_dir / 'errors.log'),
                'when': 'midnight',
                'interval': 1,
                'backupCount': 30,
                'encoding': 'utf-8',
            },
        },
        'loggers': {
            'llm_evaluator': {
                'level': 'DEBUG',
                'handlers': ['console', 'file', 'error_file'],
                'propagate': False,
            },
            'llm_evaluator.evaluation_engine': {
                'level': 'DEBUG',
                'handlers': ['console', 'file'],
                'propagate': False,
            },
            'llm_evaluator.llm_client': {
                'level': 'DEBUG',
                'handlers': ['console', 'file'],
                'propagate': False,
            },
            'llm_evaluator.response_parser': {
                'level': 'DEBUG',
                'handlers': ['console', 'file'],
                'propagate': False,
            },
        },
        'root': {
            'level': 'WARNING',
            'handlers': ['console'],
        }
    }
    
    # Environment-specific adjustments
    if environment == 'production':
        # In production, use JSON logging for better parsing
        logging_config['handlers']['file']['formatter'] = 'json'
        logging_config['handlers']['console']['level'] = 'INFO'
        
        # Add metrics logging
        logging_config['handlers']['metrics'] = {
            '()': TimedRotatingFileHandler,
            'level': 'INFO',
            'formatter': 'json',
            'filename': str(log_dir / 'metrics.log'),
            'when': 'midnight',
            'interval': 1,
            'backupCount': 30,
            'encoding': 'utf-8',
        }
        
        # Add performance logging
        logging_config['loggers']['llm_evaluator.performance'] = {
            'level': 'INFO',
            'handlers': ['metrics'],
            'propagate': False,
        }
    
    elif environment == 'testing':
        # In testing, reduce logging noise
        logging_config['handlers']['console']['level'] = 'WARNING'
        logging_config['loggers']['llm_evaluator']['level'] = 'INFO'
        
        # Add test-specific handler
        logging_config['handlers']['test'] = {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'simple',
            'stream': sys.stderr,
        }
    
    return logging_config


def setup_logging(config: LLMConfig = None, environment: str = None) -> None:
    """Set up logging for the application."""
    
    if config is None:
        config = LLMConfig.from_environment()
    
    if environment is None:
        environment = os.getenv('ENVIRONMENT', 'development')
    
    logging_config = get_logging_config(config, environment)
    logging.config.dictConfig(logging_config)
    
    # Log the setup
    logger = logging.getLogger('llm_evaluator.logging')
    logger.info(f"Logging configured for {environment} environment")
    logger.debug(f"Log level: {logging.getLevelName(get_log_level_from_env())}")
    logger.debug(f"Log directory: {Path(config.debug_dir) / 'logs'}")


def get_logger(name: str, component: str = None) -> logging.Logger:
    """Get a logger with optional component context."""
    
    logger = logging.getLogger(name)
    
    if component:
        # Add context filter for this component
        context_filter = ContextFilter({'component': component})
        logger.addFilter(context_filter)
    
    return logger


class LoggerMixin:
    """Mixin class to add logging capability to any class."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        if not hasattr(self, '_logger'):
            class_name = self.__class__.__name__
            module_name = self.__class__.__module__
            
            # Create logger name from module and class
            if module_name.startswith('llm_evaluator'):
                logger_name = f"{module_name}.{class_name}"
            else:
                logger_name = f"llm_evaluator.{class_name}"
            
            self._logger = get_logger(logger_name, class_name.lower())
        
        return self._logger
    
    def log_method_call(self, method_name: str, **kwargs):
        """Log a method call with parameters."""
        if kwargs:
            params = ", ".join(f"{k}={v}" for k, v in kwargs.items())
            self.logger.debug(f"Calling {method_name}({params})")
        else:
            self.logger.debug(f"Calling {method_name}()")
    
    def log_performance(self, operation: str, duration: float, **context):
        """Log performance metrics."""
        metrics_logger = logging.getLogger('llm_evaluator.performance')
        metrics_logger.info(
            f"Performance metric",
            extra={
                'operation': operation,
                'duration_seconds': duration,
                'component': self.__class__.__name__.lower(),
                **context
            }
        )


def log_evaluation_metrics(query: str, results_count: int, duration: float, 
                          status: str, **additional_metrics):
    """Log evaluation performance metrics."""
    metrics_logger = logging.getLogger('llm_evaluator.performance')
    
    metrics_logger.info(
        f"Evaluation completed",
        extra={
            'operation': 'evaluation',
            'query': query,
            'results_count': results_count,
            'duration_seconds': duration,
            'status': status,
            **additional_metrics
        }
    )


def log_llm_interaction(model: str, prompt_length: int, response_length: int, 
                       duration: float, success: bool):
    """Log LLM interaction metrics."""
    metrics_logger = logging.getLogger('llm_evaluator.performance')
    
    metrics_logger.info(
        f"LLM interaction",
        extra={
            'operation': 'llm_interaction',
            'model': model,
            'prompt_length': prompt_length,
            'response_length': response_length,
            'duration_seconds': duration,
            'success': success
        }
    )


def log_error_with_context(logger: logging.Logger, error: Exception, 
                          context: Dict[str, Any] = None):
    """Log an error with additional context information."""
    
    context = context or {}
    
    # Extract error information
    error_info = {
        'error_type': type(error).__name__,
        'error_message': str(error),
    }
    
    # Add custom error details if available
    if hasattr(error, 'details'):
        error_info.update(error.details)
    
    # Combine with context
    log_context = {**context, **error_info}
    
    logger.error(
        f"Error occurred: {error}",
        extra=log_context,
        exc_info=True
    )


# Decorators for automatic logging
def log_function_call(logger_name: str = None):
    """Decorator to automatically log function calls."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            nonlocal logger_name
            if logger_name is None:
                logger_name = f"llm_evaluator.{func.__module__}.{func.__name__}"
            
            logger = logging.getLogger(logger_name)
            
            # Log function entry
            logger.debug(f"Entering {func.__name__}")
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log successful completion
                logger.debug(f"Completed {func.__name__} in {duration:.3f}s")
                
                return result
            
            except Exception as e:
                duration = time.time() - start_time
                
                # Log error
                logger.error(
                    f"Error in {func.__name__} after {duration:.3f}s: {e}",
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator


def log_performance_metrics(operation_name: str = None):
    """Decorator to automatically log performance metrics."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            nonlocal operation_name
            if operation_name is None:
                operation_name = func.__name__
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log performance metrics
                metrics_logger = logging.getLogger('llm_evaluator.performance')
                metrics_logger.info(
                    f"Operation completed",
                    extra={
                        'operation': operation_name,
                        'function': func.__name__,
                        'duration_seconds': duration,
                        'success': True
                    }
                )
                
                return result
            
            except Exception as e:
                duration = time.time() - start_time
                
                # Log failed operation
                metrics_logger = logging.getLogger('llm_evaluator.performance')
                metrics_logger.warning(
                    f"Operation failed",
                    extra={
                        'operation': operation_name,
                        'function': func.__name__,
                        'duration_seconds': duration,
                        'success': False,
                        'error': str(e)
                    }
                )
                raise
        
        return wrapper
    return decorator


# Contextual logging
class LoggingContext:
    """Context manager for adding context to all log messages within a block."""
    
    def __init__(self, **context):
        self.context = context
        self.filter = None
    
    def __enter__(self):
        # Add context filter to root logger
        self.filter = ContextFilter(self.context)
        logging.getLogger().addFilter(self.filter)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Remove context filter
        if self.filter:
            logging.getLogger().removeFilter(self.filter)


# Example usage functions
def setup_development_logging():
    """Set up logging for development environment."""
    setup_logging(environment='development')


def setup_production_logging():
    """Set up logging for production environment."""
    setup_logging(environment='production')


def setup_testing_logging():
    """Set up logging for testing environment."""
    setup_logging(environment='testing')


# Import time module for decorators
import time
