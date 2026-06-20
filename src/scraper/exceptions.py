"""Custom exception classes for web scraping operations."""

from typing import Optional, List, Any


class ScrapingError(Exception):
    """Base exception class for all scraping-related errors."""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        """Initialize scraping error.
        
        Args:
            message: Error message
            details: Optional additional details about the error
        """
        super().__init__(message)
        self.message = message
        self.details = details
    
    def __str__(self) -> str:
        """String representation of the error."""
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class ConfigurationError(ScrapingError):
    """Raised when there are configuration-related issues."""
    
    def __init__(self, message: str, config_section: Optional[str] = None, invalid_keys: Optional[List[str]] = None):
        """Initialize configuration error.
        
        Args:
            message: Error message
            config_section: The configuration section that caused the error
            invalid_keys: List of invalid configuration keys
        """
        super().__init__(message)
        self.config_section = config_section
        self.invalid_keys = invalid_keys or []
    
    def __str__(self) -> str:
        """String representation of the configuration error."""
        details = []
        if self.config_section:
            details.append(f"Section: {self.config_section}")
        if self.invalid_keys:
            details.append(f"Invalid keys: {', '.join(self.invalid_keys)}")
        
        if details:
            return f"{self.message} ({'; '.join(details)})"
        return self.message


class WebDriverError(ScrapingError):
    """Raised when there are WebDriver-related issues."""
    
    def __init__(self, message: str, driver_type: Optional[str] = None, browser_version: Optional[str] = None):
        """Initialize WebDriver error.
        
        Args:
            message: Error message
            driver_type: Type of WebDriver (e.g., 'Chrome', 'Firefox')
            browser_version: Browser version if available
        """
        super().__init__(message)
        self.driver_type = driver_type
        self.browser_version = browser_version


class ElementNotFoundError(ScrapingError):
    """Raised when required elements cannot be found on the page."""
    
    def __init__(self, message: str, selectors: Optional[List[str]] = None, page_url: Optional[str] = None):
        """Initialize element not found error.
        
        Args:
            message: Error message
            selectors: List of selectors that were tried
            page_url: URL of the page where element was not found
        """
        super().__init__(message)
        self.selectors = selectors or []
        self.page_url = page_url
    
    def __str__(self) -> str:
        """String representation of the element not found error."""
        details = []
        if self.selectors:
            details.append(f"Tried selectors: {', '.join(self.selectors)}")
        if self.page_url:
            details.append(f"URL: {self.page_url}")
        
        if details:
            return f"{self.message} ({'; '.join(details)})"
        return self.message


class SearchError(ScrapingError):
    """Raised when search operations fail."""
    
    def __init__(self, message: str, search_term: Optional[str] = None, site_name: Optional[str] = None):
        """Initialize search error.
        
        Args:
            message: Error message
            search_term: The search term that caused the error
            site_name: Name of the site where search failed
        """
        super().__init__(message)
        self.search_term = search_term
        self.site_name = site_name
    
    def __str__(self) -> str:
        """String representation of the search error."""
        details = []
        if self.search_term:
            details.append(f"Search term: '{self.search_term}'")
        if self.site_name:
            details.append(f"Site: {self.site_name}")
        
        if details:
            return f"{self.message} ({'; '.join(details)})"
        return self.message


class DataExtractionError(ScrapingError):
    """Raised when data extraction operations fail."""
    
    def __init__(self, message: str, field_name: Optional[str] = None, element_html: Optional[str] = None):
        """Initialize data extraction error.
        
        Args:
            message: Error message
            field_name: Name of the field that failed to extract
            element_html: HTML of the element (first 200 chars for debugging)
        """
        super().__init__(message)
        self.field_name = field_name
        self.element_html = element_html[:200] if element_html else None
    
    def __str__(self) -> str:
        """String representation of the data extraction error."""
        details = []
        if self.field_name:
            details.append(f"Field: {self.field_name}")
        if self.element_html:
            details.append(f"Element HTML: {self.element_html}...")
        
        if details:
            return f"{self.message} ({'; '.join(details)})"
        return self.message


class ValidationError(ScrapingError):
    """Raised when data validation fails."""
    
    def __init__(self, message: str, field_name: Optional[str] = None, field_value: Optional[Any] = None, 
                 validation_rules: Optional[List[str]] = None):
        """Initialize validation error.
        
        Args:
            message: Error message
            field_name: Name of the field that failed validation
            field_value: Value that failed validation
            validation_rules: List of validation rules that failed
        """
        super().__init__(message)
        self.field_name = field_name
        self.field_value = field_value
        self.validation_rules = validation_rules or []
    
    def __str__(self) -> str:
        """String representation of the validation error."""
        details = []
        if self.field_name:
            details.append(f"Field: {self.field_name}")
        if self.field_value is not None:
            details.append(f"Value: '{self.field_value}'")
        if self.validation_rules:
            details.append(f"Failed rules: {', '.join(self.validation_rules)}")
        
        if details:
            return f"{self.message} ({'; '.join(details)})"
        return self.message


class NetworkError(ScrapingError):
    """Raised when network-related issues occur."""
    
    def __init__(self, message: str, url: Optional[str] = None, status_code: Optional[int] = None, 
                 retry_count: Optional[int] = None):
        """Initialize network error.
        
        Args:
            message: Error message
            url: URL that caused the network error
            status_code: HTTP status code if available
            retry_count: Number of retries attempted
        """
        super().__init__(message)
        self.url = url
        self.status_code = status_code
        self.retry_count = retry_count
    
    def __str__(self) -> str:
        """String representation of the network error."""
        details = []
        if self.url:
            details.append(f"URL: {self.url}")
        if self.status_code:
            details.append(f"Status: {self.status_code}")
        if self.retry_count is not None:
            details.append(f"Retries: {self.retry_count}")
        
        if details:
            return f"{self.message} ({'; '.join(details)})"
        return self.message


class TimeoutError(ScrapingError):
    """Raised when operations timeout."""
    
    def __init__(self, message: str, timeout_duration: Optional[float] = None, operation: Optional[str] = None):
        """Initialize timeout error.
        
        Args:
            message: Error message
            timeout_duration: Duration of the timeout in seconds
            operation: Name of the operation that timed out
        """
        super().__init__(message)
        self.timeout_duration = timeout_duration
        self.operation = operation
    
    def __str__(self) -> str:
        """String representation of the timeout error."""
        details = []
        if self.timeout_duration:
            details.append(f"Timeout: {self.timeout_duration}s")
        if self.operation:
            details.append(f"Operation: {self.operation}")
        
        if details:
            return f"{self.message} ({'; '.join(details)})"
        return self.message


class NoResultsError(ScrapingError):
    """Raised when search returns no results."""
    
    def __init__(self, message: str, search_term: Optional[str] = None, site_name: Optional[str] = None):
        """Initialize no results error.
        
        Args:
            message: Error message
            search_term: The search term that returned no results
            site_name: Name of the site where no results were found
        """
        super().__init__(message)
        self.search_term = search_term
        self.site_name = site_name
    
    def __str__(self) -> str:
        """String representation of the no results error."""
        details = []
        if self.search_term:
            details.append(f"Search term: '{self.search_term}'")
        if self.site_name:
            details.append(f"Site: {self.site_name}")
        
        if details:
            return f"{self.message} ({'; '.join(details)})"
        return self.message


class ParsingError(ScrapingError):
    """Raised when parsing operations fail."""
    
    def __init__(self, message: str, parser_type: Optional[str] = None, content_preview: Optional[str] = None):
        """Initialize parsing error.
        
        Args:
            message: Error message
            parser_type: Type of parser that failed (e.g., 'JSON', 'HTML', 'CSS')
            content_preview: Preview of content that failed to parse
        """
        super().__init__(message)
        self.parser_type = parser_type
        self.content_preview = content_preview[:100] if content_preview else None
    
    def __str__(self) -> str:
        """String representation of the parsing error."""
        details = []
        if self.parser_type:
            details.append(f"Parser: {self.parser_type}")
        if self.content_preview:
            details.append(f"Content: {self.content_preview}...")
        
        if details:
            return f"{self.message} ({'; '.join(details)})"
        return self.message


# Error handler utility class
class ErrorHandler:
    """Utility class for handling and categorizing errors."""
    
    @staticmethod
    def is_recoverable_error(error: Exception) -> bool:
        """Determine if an error is potentially recoverable.
        
        Args:
            error: Exception to check
            
        Returns:
            True if error might be recoverable with retry, False otherwise
        """
        recoverable_errors = (
            NetworkError,
            TimeoutError,
            ElementNotFoundError
        )
        return isinstance(error, recoverable_errors)
    
    @staticmethod
    def should_retry(error: Exception, retry_count: int, max_retries: int = 3) -> bool:
        """Determine if an operation should be retried.
        
        Args:
            error: Exception that occurred
            retry_count: Current retry count
            max_retries: Maximum number of retries allowed
            
        Returns:
            True if should retry, False otherwise
        """
        if retry_count >= max_retries:
            return False
        
        return ErrorHandler.is_recoverable_error(error)
    
    @staticmethod
    def categorize_error(error: Exception) -> str:
        """Categorize an error for reporting purposes.
        
        Args:
            error: Exception to categorize
            
        Returns:
            Error category string
        """
        if isinstance(error, ConfigurationError):
            return "Configuration"
        elif isinstance(error, WebDriverError):
            return "WebDriver"
        elif isinstance(error, ElementNotFoundError):
            return "Element Not Found"
        elif isinstance(error, SearchError):
            return "Search"
        elif isinstance(error, DataExtractionError):
            return "Data Extraction"
        elif isinstance(error, ValidationError):
            return "Validation"
        elif isinstance(error, NetworkError):
            return "Network"
        elif isinstance(error, TimeoutError):
            return "Timeout"
        elif isinstance(error, NoResultsError):
            return "No Results"
        elif isinstance(error, ParsingError):
            return "Parsing"
        elif isinstance(error, ScrapingError):
            return "General Scraping"
        else:
            return "Unknown"