"""
Custom exception classes for the LLM Search Result Evaluation System.

Provides specific exception types for different error conditions to enable
better error handling and debugging throughout the system.
"""

from typing import Optional, Dict, Any


class LLMEvaluatorError(Exception):
    """Base exception class for all LLM evaluator errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


class ConfigurationError(LLMEvaluatorError):
    """Raised when there are configuration issues."""
    
    def __init__(self, message: str, config_key: Optional[str] = None, 
                 config_value: Optional[str] = None):
        details = {}
        if config_key:
            details["config_key"] = config_key
        if config_value:
            details["config_value"] = config_value
        
        super().__init__(message, details)
        self.config_key = config_key
        self.config_value = config_value


class ServiceUnavailableError(LLMEvaluatorError):
    """Raised when the LLM service is not available."""
    
    def __init__(self, message: str, endpoint: Optional[str] = None, 
                 status_code: Optional[int] = None):
        details = {}
        if endpoint:
            details["endpoint"] = endpoint
        if status_code:
            details["status_code"] = status_code
        
        super().__init__(message, details)
        self.endpoint = endpoint
        self.status_code = status_code


class ModelNotFoundError(LLMEvaluatorError):
    """Raised when the specified model is not available."""
    
    def __init__(self, model_name: str, available_models: Optional[list] = None):
        message = f"Model '{model_name}' not found"
        details = {"requested_model": model_name}
        if available_models:
            details["available_models"] = available_models
            message += f". Available models: {', '.join(available_models)}"
        
        super().__init__(message, details)
        self.model_name = model_name
        self.available_models = available_models or []


class PromptGenerationError(LLMEvaluatorError):
    """Raised when prompt generation fails."""
    
    def __init__(self, message: str, search_type: Optional[str] = None, 
                 query: Optional[str] = None):
        details = {}
        if search_type:
            details["search_type"] = search_type
        if query:
            details["query"] = query
        
        super().__init__(message, details)
        self.search_type = search_type
        self.query = query


class ResponseParsingError(LLMEvaluatorError):
    """Raised when LLM response parsing fails."""
    
    def __init__(self, message: str, response_content: Optional[str] = None, 
                 parse_error: Optional[str] = None):
        details = {}
        if response_content:
            # Truncate long responses for readability
            content_preview = response_content[:200] + "..." if len(response_content) > 200 else response_content
            details["response_preview"] = content_preview
        if parse_error:
            details["parse_error"] = parse_error
        
        super().__init__(message, details)
        self.response_content = response_content
        self.parse_error = parse_error


class ValidationError(LLMEvaluatorError):
    """Raised when data validation fails."""
    
    def __init__(self, message: str, validation_type: Optional[str] = None, 
                 invalid_data: Optional[Any] = None):
        details = {}
        if validation_type:
            details["validation_type"] = validation_type
        if invalid_data is not None:
            details["invalid_data"] = str(invalid_data)
        
        super().__init__(message, details)
        self.validation_type = validation_type
        self.invalid_data = invalid_data


class InventoryAnalysisError(LLMEvaluatorError):
    """Raised when inventory analysis fails."""
    
    def __init__(self, message: str, inventory_data: Optional[str] = None, 
                 analysis_step: Optional[str] = None):
        details = {}
        if inventory_data:
            details["inventory_data"] = inventory_data
        if analysis_step:
            details["analysis_step"] = analysis_step
        
        super().__init__(message, details)
        self.inventory_data = inventory_data
        self.analysis_step = analysis_step


class SearchClassificationError(LLMEvaluatorError):
    """Raised when search type classification fails."""
    
    def __init__(self, message: str, query: Optional[str] = None, 
                 classifier_type: Optional[str] = None):
        details = {}
        if query:
            details["query"] = query
        if classifier_type:
            details["classifier_type"] = classifier_type
        
        super().__init__(message, details)
        self.query = query
        self.classifier_type = classifier_type


class EvaluationError(LLMEvaluatorError):
    """Raised when the evaluation process fails."""
    
    def __init__(self, message: str, query: Optional[str] = None, 
                 results_count: Optional[int] = None, stage: Optional[str] = None):
        details = {}
        if query:
            details["query"] = query
        if results_count is not None:
            details["results_count"] = results_count
        if stage:
            details["evaluation_stage"] = stage
        
        super().__init__(message, details)
        self.query = query
        self.results_count = results_count
        self.stage = stage


class ResultFormattingError(LLMEvaluatorError):
    """Raised when result formatting fails."""
    
    def __init__(self, message: str, formatter_type: Optional[str] = None, 
                 results_count: Optional[int] = None):
        details = {}
        if formatter_type:
            details["formatter_type"] = formatter_type
        if results_count is not None:
            details["results_count"] = results_count
        
        super().__init__(message, details)
        self.formatter_type = formatter_type
        self.results_count = results_count


class TestingError(LLMEvaluatorError):
    """Raised when testing operations fail."""
    
    def __init__(self, message: str, test_name: Optional[str] = None, 
                 test_category: Optional[str] = None):
        details = {}
        if test_name:
            details["test_name"] = test_name
        if test_category:
            details["test_category"] = test_category
        
        super().__init__(message, details)
        self.test_name = test_name
        self.test_category = test_category


class TimeoutError(LLMEvaluatorError):
    """Raised when operations timeout."""
    
    def __init__(self, message: str, timeout_duration: Optional[float] = None, 
                 operation: Optional[str] = None):
        details = {}
        if timeout_duration is not None:
            details["timeout_duration"] = timeout_duration
        if operation:
            details["operation"] = operation
        
        super().__init__(message, details)
        self.timeout_duration = timeout_duration
        self.operation = operation


class RetryExhaustedError(LLMEvaluatorError):
    """Raised when retry attempts are exhausted."""
    
    def __init__(self, message: str, max_retries: Optional[int] = None, 
                 last_error: Optional[str] = None):
        details = {}
        if max_retries is not None:
            details["max_retries"] = max_retries
        if last_error:
            details["last_error"] = last_error
        
        super().__init__(message, details)
        self.max_retries = max_retries
        self.last_error = last_error


class DataIntegrityError(LLMEvaluatorError):
    """Raised when data integrity checks fail."""
    
    def __init__(self, message: str, expected_count: Optional[int] = None, 
                 actual_count: Optional[int] = None, data_type: Optional[str] = None):
        details = {}
        if expected_count is not None:
            details["expected_count"] = expected_count
        if actual_count is not None:
            details["actual_count"] = actual_count
        if data_type:
            details["data_type"] = data_type
        
        super().__init__(message, details)
        self.expected_count = expected_count
        self.actual_count = actual_count
        self.data_type = data_type


# Exception context managers for better error handling
class EvaluationContext:
    """Context manager for evaluation operations."""
    
    def __init__(self, query: str, results_count: int, stage: str = "unknown"):
        self.query = query
        self.results_count = results_count
        self.stage = stage
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type and not issubclass(exc_type, LLMEvaluatorError):
            # Wrap unexpected exceptions in EvaluationError
            raise EvaluationError(
                f"Unexpected error during {self.stage}: {exc_val}",
                query=self.query,
                results_count=self.results_count,
                stage=self.stage
            ) from exc_val


class ServiceContext:
    """Context manager for service operations."""
    
    def __init__(self, endpoint: str, operation: str = "unknown"):
        self.endpoint = endpoint
        self.operation = operation
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type and not issubclass(exc_type, LLMEvaluatorError):
            # Wrap service-related exceptions
            if "timeout" in str(exc_val).lower():
                raise TimeoutError(
                    f"Operation '{self.operation}' timed out",
                    operation=self.operation
                ) from exc_val
            else:
                raise ServiceUnavailableError(
                    f"Service error during {self.operation}: {exc_val}",
                    endpoint=self.endpoint
                ) from exc_val


# Error handler decorators
def handle_configuration_errors(func):
    """Decorator to handle configuration-related errors."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            if "config" in str(e).lower():
                raise ConfigurationError(str(e)) from e
            raise
        except KeyError as e:
            raise ConfigurationError(f"Missing configuration key: {e}") from e
    
    return wrapper


def handle_service_errors(func):
    """Decorator to handle service-related errors."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ConnectionError as e:
            raise ServiceUnavailableError(f"Connection failed: {e}") from e
        except Exception as e:
            if "timeout" in str(e).lower():
                raise TimeoutError(f"Operation timed out: {e}") from e
            elif "connection" in str(e).lower():
                raise ServiceUnavailableError(f"Service connection error: {e}") from e
            raise
    
    return wrapper


def handle_parsing_errors(func):
    """Decorator to handle parsing-related errors."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ValueError, TypeError) as e:
            if "json" in str(e).lower():
                raise ResponseParsingError(f"JSON parsing failed: {e}") from e
            raise ValidationError(f"Data validation failed: {e}") from e
    
    return wrapper


# Utility functions for error handling
def format_error_details(error: LLMEvaluatorError) -> str:
    """Format error details for logging or display."""
    lines = [f"Error: {error.message}"]
    
    if error.details:
        lines.append("Details:")
        for key, value in error.details.items():
            lines.append(f"  {key}: {value}")
    
    return "\n".join(lines)


def is_retryable_error(error: Exception) -> bool:
    """Determine if an error is retryable."""
    retryable_errors = (
        ServiceUnavailableError,
        TimeoutError,
        ConnectionError,
    )
    
    # Configuration and validation errors are not retryable
    non_retryable_errors = (
        ConfigurationError,
        ValidationError,
        ModelNotFoundError,
    )
    
    if isinstance(error, non_retryable_errors):
        return False
    
    if isinstance(error, retryable_errors):
        return True
    
    # Check for specific error messages that indicate retryable conditions
    error_msg = str(error).lower()
    retryable_keywords = ["timeout", "connection", "network", "temporary", "unavailable"]
    
    return any(keyword in error_msg for keyword in retryable_keywords)


def get_error_category(error: Exception) -> str:
    """Get the category of an error for logging and monitoring."""
    if isinstance(error, ConfigurationError):
        return "configuration"
    elif isinstance(error, ServiceUnavailableError):
        return "service"
    elif isinstance(error, ModelNotFoundError):
        return "model"
    elif isinstance(error, ResponseParsingError):
        return "parsing"
    elif isinstance(error, ValidationError):
        return "validation"
    elif isinstance(error, InventoryAnalysisError):
        return "inventory"
    elif isinstance(error, SearchClassificationError):
        return "classification"
    elif isinstance(error, EvaluationError):
        return "evaluation"
    elif isinstance(error, TimeoutError):
        return "timeout"
    elif isinstance(error, RetryExhaustedError):
        return "retry_exhausted"
    else:
        return "unknown"


# Error recovery strategies
class ErrorRecoveryStrategy:
    """Base class for error recovery strategies."""
    
    def can_recover(self, error: Exception) -> bool:
        """Check if this strategy can recover from the given error."""
        return False
    
    def recover(self, error: Exception, context: Dict[str, Any]) -> Any:
        """Attempt to recover from the error."""
        raise NotImplementedError


class FallbackModelRecovery(ErrorRecoveryStrategy):
    """Recovery strategy that falls back to a different model."""
    
    def __init__(self, fallback_models: list):
        self.fallback_models = fallback_models
    
    def can_recover(self, error: Exception) -> bool:
        return isinstance(error, ModelNotFoundError) and self.fallback_models
    
    def recover(self, error: Exception, context: Dict[str, Any]) -> str:
        """Return the first available fallback model."""
        if self.fallback_models:
            return self.fallback_models[0]
        raise error


class SimplifiedPromptRecovery(ErrorRecoveryStrategy):
    """Recovery strategy that uses a simplified prompt on parsing failures."""
    
    def can_recover(self, error: Exception) -> bool:
        return isinstance(error, ResponseParsingError)
    
    def recover(self, error: Exception, context: Dict[str, Any]) -> str:
        """Return a simplified prompt for retry."""
        query = context.get('query', 'unknown')
        results_count = context.get('results_count', 0)
        
        return f"""
        Evaluate {results_count} search results for query: "{query}"
        
        Return ONLY a JSON object with this structure:
        {{
            "evaluations": [
                {{"result_index": 0, "relevance_tier": "High|Medium|Low", "justification": "brief reason"}}
            ]
        }}
        """
