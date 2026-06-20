"""Custom exceptions for the agentic search application."""

from typing import Optional, Dict, Any, List


class AgenticSearchError(Exception):
    """Base exception for all agentic search related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize the exception.
        
        Args:
            message: Error message
            details: Optional additional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        """String representation of the error."""
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class ConfigurationError(AgenticSearchError):
    """Raised when there are configuration-related errors."""
    
    def __init__(self, message: str, config_path: Optional[str] = None, site_name: Optional[str] = None):
        """Initialize configuration error.
        
        Args:
            message: Error message
            config_path: Path to the configuration file
            site_name: Name of the site being configured
        """
        details = {}
        if config_path:
            details['config_path'] = config_path
        if site_name:
            details['site_name'] = site_name
        
        super().__init__(message, details)
        self.config_path = config_path
        self.site_name = site_name


class ScrapingError(AgenticSearchError):
    """Raised when web scraping operations fail."""
    
    def __init__(
        self, 
        message: str, 
        query: Optional[str] = None, 
        url: Optional[str] = None,
        element_selector: Optional[str] = None
    ):
        """Initialize scraping error.
        
        Args:
            message: Error message
            query: Search query that failed
            url: URL being scraped
            element_selector: CSS/XPath selector that failed
        """
        details = {}
        if query:
            details['query'] = query
        if url:
            details['url'] = url
        if element_selector:
            details['element_selector'] = element_selector
        
        super().__init__(message, details)
        self.query = query
        self.url = url
        self.element_selector = element_selector


class EvaluationError(AgenticSearchError):
    """Raised when LLM evaluation operations fail."""
    
    def __init__(
        self, 
        message: str, 
        model: Optional[str] = None, 
        query: Optional[str] = None,
        api_endpoint: Optional[str] = None
    ):
        """Initialize evaluation error.
        
        Args:
            message: Error message
            model: LLM model being used
            query: Search query being evaluated
            api_endpoint: API endpoint being called
        """
        details = {}
        if model:
            details['model'] = model
        if query:
            details['query'] = query
        if api_endpoint:
            details['api_endpoint'] = api_endpoint
        
        super().__init__(message, details)
        self.model = model
        self.query = query
        self.api_endpoint = api_endpoint


class ValidationError(AgenticSearchError):
    """Raised when validation operations fail."""
    
    def __init__(self, message: str, validation_errors: Optional[List[str]] = None):
        """Initialize validation error.
        
        Args:
            message: Error message
            validation_errors: List of specific validation errors
        """
        details = {}
        if validation_errors:
            details['validation_errors'] = validation_errors
        
        super().__init__(message, details)
        self.validation_errors = validation_errors or []


class WebDriverError(AgenticSearchError):
    """Raised when WebDriver operations fail."""
    
    def __init__(
        self, 
        message: str, 
        driver_type: Optional[str] = None,
        chrome_version: Optional[str] = None
    ):
        """Initialize WebDriver error.
        
        Args:
            message: Error message
            driver_type: Type of WebDriver (e.g., 'chrome', 'firefox')
            chrome_version: Version of Chrome being used
        """
        details = {}
        if driver_type:
            details['driver_type'] = driver_type
        if chrome_version:
            details['chrome_version'] = chrome_version
        
        super().__init__(message, details)
        self.driver_type = driver_type
        self.chrome_version = chrome_version


class ResultsProcessingError(AgenticSearchError):
    """Raised when results processing operations fail."""
    
    def __init__(
        self, 
        message: str, 
        operation: Optional[str] = None,
        file_path: Optional[str] = None
    ):
        """Initialize results processing error.
        
        Args:
            message: Error message
            operation: The operation that failed (e.g., 'save', 'load', 'analyze')
            file_path: File path involved in the operation
        """
        details = {}
        if operation:
            details['operation'] = operation
        if file_path:
            details['file_path'] = file_path
        
        super().__init__(message, details)
        self.operation = operation
        self.file_path = file_path


class NetworkError(AgenticSearchError):
    """Raised when network operations fail."""
    
    def __init__(
        self, 
        message: str, 
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        timeout: Optional[int] = None
    ):
        """Initialize network error.
        
        Args:
            message: Error message
            url: URL that failed
            status_code: HTTP status code if available
            timeout: Timeout value used
        """
        details = {}
        if url:
            details['url'] = url
        if status_code:
            details['status_code'] = status_code
        if timeout:
            details['timeout'] = timeout
        
        super().__init__(message, details)
        self.url = url
        self.status_code = status_code
        self.timeout = timeout


class CLIError(AgenticSearchError):
    """Raised when command line interface operations fail."""
    
    def __init__(
        self, 
        message: str, 
        argument: Optional[str] = None,
        command: Optional[str] = None
    ):
        """Initialize CLI error.
        
        Args:
            message: Error message
            argument: Command line argument that caused the error
            command: Command being executed
        """
        details = {}
        if argument:
            details['argument'] = argument
        if command:
            details['command'] = command
        
        super().__init__(message, details)
        self.argument = argument
        self.command = command


class InventoryAnalysisError(AgenticSearchError):
    """Raised when inventory analysis operations fail."""
    
    def __init__(
        self, 
        message: str, 
        query: Optional[str] = None,
        analysis_type: Optional[str] = None
    ):
        """Initialize inventory analysis error.
        
        Args:
            message: Error message
            query: Search query being analyzed
            analysis_type: Type of analysis that failed
        """
        details = {}
        if query:
            details['query'] = query
        if analysis_type:
            details['analysis_type'] = analysis_type
        
        super().__init__(message, details)
        self.query = query
        self.analysis_type = analysis_type


class BusinessSummaryError(AgenticSearchError):
    """Raised when business summary generation fails."""
    
    def __init__(
        self, 
        message: str, 
        query: Optional[str] = None,
        summary_type: Optional[str] = None
    ):
        """Initialize business summary error.
        
        Args:
            message: Error message
            query: Search query being summarized
            summary_type: Type of summary that failed
        """
        details = {}
        if query:
            details['query'] = query
        if summary_type:
            details['summary_type'] = summary_type
        
        super().__init__(message, details)
        self.query = query
        self.summary_type = summary_type


# Exception handling utilities
class ErrorHandler:
    """Utility class for handling and logging errors consistently."""
    
    @staticmethod
    def handle_configuration_error(error: Exception, config_path: str, site_name: str) -> ConfigurationError:
        """Convert generic exceptions to ConfigurationError.
        
        Args:
            error: Original exception
            config_path: Configuration file path
            site_name: Site name
            
        Returns:
            ConfigurationError with context
        """
        message = f"Configuration error for site '{site_name}': {str(error)}"
        return ConfigurationError(message, config_path, site_name)
    
    @staticmethod
    def handle_scraping_error(error: Exception, query: str, url: str) -> ScrapingError:
        """Convert generic exceptions to ScrapingError.
        
        Args:
            error: Original exception
            query: Search query
            url: Target URL
            
        Returns:
            ScrapingError with context
        """
        message = f"Scraping failed for query '{query}' on {url}: {str(error)}"
        return ScrapingError(message, query, url)
    
    @staticmethod
    def handle_evaluation_error(error: Exception, model: str, query: str) -> EvaluationError:
        """Convert generic exceptions to EvaluationError.
        
        Args:
            error: Original exception
            model: LLM model name
            query: Search query
            
        Returns:
            EvaluationError with context
        """
        message = f"LLM evaluation failed with model '{model}' for query '{query}': {str(error)}"
        return EvaluationError(message, model, query)
    
    @staticmethod
    def handle_validation_error(errors: List[str], context: str) -> ValidationError:
        """Create ValidationError from multiple validation issues.
        
        Args:
            errors: List of validation error messages
            context: Context where validation failed
            
        Returns:
            ValidationError with all validation issues
        """
        message = f"Validation failed in {context}: {len(errors)} errors found"
        return ValidationError(message, errors)


# Context managers for error handling
class ErrorContext:
    """Context manager for consistent error handling and logging."""
    
    def __init__(self, operation: str, logger, reraise: bool = True):
        """Initialize error context.
        
        Args:
            operation: Description of the operation being performed
            logger: Logger instance for error logging
            reraise: Whether to reraise exceptions after logging
        """
        self.operation = operation
        self.logger = logger
        self.reraise = reraise
        self.error: Optional[Exception] = None
    
    def __enter__(self):
        """Enter the error context."""
        self.logger.debug(f"Starting operation: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the error context and handle any exceptions."""
        if exc_type is not None:
            self.error = exc_val
            self.logger.error(f"Operation '{self.operation}' failed: {exc_val}")
            
            if self.reraise:
                return False  # Reraise the exception
            else:
                return True  # Suppress the exception
        else:
            self.logger.debug(f"Operation completed successfully: {self.operation}")
            return False
    
    def has_error(self) -> bool:
        """Check if an error occurred during the operation.
        
        Returns:
            True if an error occurred, False otherwise
        """
        return self.error is not None
    
    def get_error(self) -> Optional[Exception]:
        """Get the error that occurred.
        
        Returns:
            The exception that occurred, or None if no error
        """
        return self.error