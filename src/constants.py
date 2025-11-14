"""Constants and enumerations for the agentic search application."""

from enum import Enum, IntEnum
from typing import Dict, List


class SearchStatus(Enum):
    """Enumeration for search operation status."""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    TIMEOUT = "timeout"
    NO_RESULTS = "no_results"


class RelevanceLevel(Enum):
    """Enumeration for search result relevance levels."""
    HIGH = "High"
    MEDIUM = "Medium" 
    LOW = "Low"


class SearchType(Enum):
    """Enumeration for different types of searches."""
    PRODUCT = "product"
    PART_NUMBER = "part_number"
    CATEGORY = "category"
    BRAND = "brand"
    GENERIC = "generic"
    EXACT_MATCH = "exact_match"


class InventoryStatus(Enum):
    """Enumeration for inventory availability status."""
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    UNKNOWN = "unknown"


class Environment(Enum):
    """Enumeration for deployment environments."""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class LogLevel(Enum):
    """Enumeration for logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class FileFormat(Enum):
    """Enumeration for output file formats."""
    JSON = "json"
    CSV = "csv"
    EXCEL = "xlsx"


# Application Constants
class AppConstants:
    """Application-wide constants."""
    
    # Application metadata
    APP_NAME = "Agentic Search Solution"
    VERSION = "2.0.0"
    
    # Default configuration values
    DEFAULT_CONFIG_FILE = "config.json"
    DEFAULT_OUTPUT_DIR = "analysis_result"
    DEFAULT_DEBUG_DIR = "llm_debug"
    
    # Timeout values (in seconds)
    DEFAULT_PAGE_LOAD_TIMEOUT = 30
    DEFAULT_ELEMENT_WAIT_TIMEOUT = 10
    DEFAULT_LLM_TIMEOUT = 30
    DEFAULT_NETWORK_TIMEOUT = 15
    
    # Retry configuration
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 2
    
    # Search configuration
    DEFAULT_MAX_RESULTS_PER_QUERY = 10
    DEFAULT_SEARCH_DELAY = 2
    MIN_RESULTS_FOR_ANALYSIS = 1
    MAX_RESULTS_FOR_ANALYSIS = 100
    
    # Inventory thresholds
    DEFAULT_LOW_STOCK_THRESHOLD = 5
    ZERO_STOCK_THRESHOLD = 0
    
    # Relevance scoring
    RELEVANCE_SCORES = {
        RelevanceLevel.HIGH: 3,
        RelevanceLevel.MEDIUM: 2, 
        RelevanceLevel.LOW: 1
    }
    
    # Performance thresholds
    EXCELLENT_RELEVANCE_THRESHOLD = 60  # Percentage
    GOOD_RELEVANCE_THRESHOLD = 40
    MODERATE_RELEVANCE_THRESHOLD = 20
    
    STRONG_INVENTORY_THRESHOLD = 70  # Percentage
    MODERATE_INVENTORY_THRESHOLD = 40


class WebDriverConstants:
    """Constants related to WebDriver configuration."""
    
    # Default window size
    DEFAULT_WINDOW_WIDTH = 1280
    DEFAULT_WINDOW_HEIGHT = 720
    
    # User agent strings
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    
    # WebDriver timeouts
    DEFAULT_IMPLICIT_WAIT = 3
    DEFAULT_PAGE_LOAD_TIMEOUT = 30
    DEFAULT_SCRIPT_TIMEOUT = 30
    
    # Common CSS selectors
    COMMON_SEARCH_INPUT_SELECTORS = [
        "input[type='search']",
        "input[placeholder*='search']",
        "input[name*='search']",
        "#search",
        ".search-input",
        "[data-testid*='search']"
    ]
    
    COMMON_SEARCH_BUTTON_SELECTORS = [
        "button[type='submit']",
        "button:contains('Search')",
        "input[type='submit']",
        ".search-button",
        "[data-testid*='search-button']"
    ]


class LLMConstants:
    """Constants related to LLM operations."""
    
    # Default API configuration
    DEFAULT_OLLAMA_ENDPOINT = "http://localhost:11434"
    DEFAULT_MODEL = "llama2"
    
    # Prompt templates and limits
    MAX_PROMPT_LENGTH = 4000
    MAX_CONTEXT_RESULTS = 20
    
    # Evaluation criteria
    EVALUATION_CRITERIA = [
        "relevance_to_query",
        "product_match_accuracy",
        "category_appropriateness",
        "brand_consistency",
        "specifications_alignment"
    ]


class ErrorMessages:
    """Standardized error messages."""
    
    # Configuration errors
    CONFIG_FILE_NOT_FOUND = "Configuration file not found: {path}"
    INVALID_JSON_CONFIG = "Invalid JSON in configuration file: {error}"
    SITE_NOT_FOUND = "Site '{site}' not found in configuration"
    MISSING_REQUIRED_FIELD = "Missing required field '{field}' in {context}"
    
    # Scraping errors
    WEBDRIVER_INIT_FAILED = "Failed to initialize WebDriver: {error}"
    PAGE_LOAD_FAILED = "Failed to load page: {url}"
    ELEMENT_NOT_FOUND = "Element not found with selector: {selector}"
    SEARCH_FAILED = "Search operation failed for query: {query}"
    NO_RESULTS_FOUND = "No search results found for query: {query}"
    
    # Evaluation errors
    LLM_EVALUATION_FAILED = "LLM evaluation failed: {error}"
    MODEL_NOT_AVAILABLE = "Model '{model}' is not available"
    API_CONNECTION_FAILED = "Failed to connect to LLM API: {endpoint}"
    
    # File operation errors
    FILE_SAVE_FAILED = "Failed to save file: {path}"
    FILE_LOAD_FAILED = "Failed to load file: {path}"
    DIRECTORY_CREATE_FAILED = "Failed to create directory: {path}"
    
    # Validation errors
    INVALID_URL_FORMAT = "Invalid URL format: {url}"
    INVALID_THRESHOLD_VALUE = "Invalid threshold value: {value}"
    EMPTY_SELECTOR_LIST = "Selector list cannot be empty for: {field}"


class SuccessMessages:
    """Standardized success messages."""
    
    WEBDRIVER_INITIALIZED = "WebDriver initialized successfully"
    PAGE_LOADED = "Page loaded successfully: {url}"
    SEARCH_COMPLETED = "Search completed for query: {query}"
    EVALUATION_COMPLETED = "LLM evaluation completed successfully"
    RESULTS_SAVED = "Results saved to: {path}"
    CONFIGURATION_LOADED = "Configuration loaded successfully for site: {site}"


class FilePatterns:
    """File naming patterns and extensions."""
    
    # Output file patterns
    MAIN_RESULTS_PATTERN = "{base_name}_{timestamp}.json"
    DETAILED_RESULTS_PATTERN = "detailed_{base_name}_{timestamp}.json"
    DEBUG_RESULTS_PATTERN = "debug_{base_name}_{timestamp}.json"
    
    # Timestamp format
    TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"
    READABLE_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    # File extensions
    JSON_EXTENSION = ".json"
    CSV_EXTENSION = ".csv"
    EXCEL_EXTENSION = ".xlsx"
    LOG_EXTENSION = ".log"


class HTMLSelectors:
    """Common HTML selectors and patterns."""
    
    # Input elements
    SEARCH_INPUTS = [
        "input[type='search']",
        "input[placeholder*='search' i]",
        "input[name*='search' i]",
        "input[id*='search' i]",
        ".search-input",
        ".search-field"
    ]
    
    # Button elements
    SEARCH_BUTTONS = [
        "button[type='submit']",
        "input[type='submit']",
        "button:contains('Search')",
        ".search-button",
        ".search-btn",
        "[data-testid*='search']"
    ]
    
    # Common no-results indicators
    NO_RESULTS_INDICATORS = [
        ".no-results",
        ".empty-results",
        ".search-empty",
        "[data-testid*='no-results']",
        "*:contains('No results')",
        "*:contains('0 results')",
        "*:contains('No items found')"
    ]
    
    # Product card selectors
    PRODUCT_CARDS = [
        ".product-card",
        ".product-item",
        ".search-result",
        ".product-tile",
        "[data-testid*='product']"
    ]


class MetricThresholds:
    """Performance and quality metric thresholds."""
    
    # Success rate thresholds
    EXCELLENT_SUCCESS_RATE = 95.0  # Percentage
    GOOD_SUCCESS_RATE = 85.0
    ACCEPTABLE_SUCCESS_RATE = 70.0
    
    # Response time thresholds (seconds)
    FAST_RESPONSE_TIME = 5.0
    ACCEPTABLE_RESPONSE_TIME = 15.0
    SLOW_RESPONSE_TIME = 30.0
    
    # Relevance quality thresholds
    HIGH_QUALITY_RELEVANCE = 80.0  # Percentage of high relevance results
    MEDIUM_QUALITY_RELEVANCE = 60.0
    LOW_QUALITY_RELEVANCE = 40.0
    
    # Inventory availability thresholds  
    EXCELLENT_AVAILABILITY = 90.0  # Percentage
    GOOD_AVAILABILITY = 75.0
    POOR_AVAILABILITY = 50.0


class ConfigDefaults:
    """Default configuration values."""
    
    # Chrome configuration
    CHROME_DEFAULTS = {
        "headless": True,
        "window_size": {"width": 3840, "height": 2160},
        "implicit_wait": 3,
        "page_load_timeout": 30
    }
    
    # LLM configuration
    LLM_DEFAULTS = {
        "timeout": 30,
        "max_retries": 3,
        "api_endpoint": "http://localhost:11434",
        "default_model": "llama2"
    }
    
    # Evaluation configuration
    EVALUATION_DEFAULTS = {
        "enable_inventory_ranking": True,
        "enable_detailed_analysis": False,
        "inventory_weight_factor": 0.3,
        "apply_post_ranking": True,
        "low_stock_threshold": 5
    }
    
    # Deployment configuration
    DEPLOYMENT_DEFAULTS = {
        "environment": "development",
        "log_level": "INFO",
        "enable_screenshots": False,
        "delay_between_searches": 2,
        "enable_metrics_collection": False
    }


class RegexPatterns:
    """Common regex patterns for data extraction and validation."""
    
    # Quantity extraction patterns
    QUANTITY_PATTERNS = [
        r'(\d+)\s*(?:in stock|available|qty)',
        r'quantity[:\s]*(\d+)',
        r'stock[:\s]*(\d+)',
        r'available[:\s]*(\d+)',
        r'(\d+)\s*(?:pcs?|pieces?|units?)'
    ]
    
    # Price patterns
    PRICE_PATTERNS = [
        r'\$\s*(\d+(?:\.\d{2})?)',
        r'USD\s*(\d+(?:\.\d{2})?)',
        r'(\d+(?:\.\d{2})?)\s*USD',
        r'Price[:\s]*\$?(\d+(?:\.\d{2})?)'
    ]
    
    # Part number patterns
    PART_NUMBER_PATTERNS = [
        r'[A-Z0-9]{3,}-[A-Z0-9]{3,}',
        r'[A-Z]{2,}\d{4,}',
        r'\d{4,}[A-Z]{2,}',
        r'[A-Z0-9]{6,}'
    ]
    
    # URL validation
    URL_PATTERN = r'^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$'