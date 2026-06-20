"""Utility functions and helpers for the agentic search application."""

import re
import json
import time
import functools
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar
from urllib.parse import urlparse, urljoin

from constants import RegexPatterns, RelevanceLevel, InventoryStatus, FilePatterns


T = TypeVar('T')


class TextProcessor:
    """Utility class for text processing and extraction."""
    
    @staticmethod
    def extract_quantity(text: str) -> int:
        """Extract quantity from text using various patterns.
        
        Args:
            text: Text to extract quantity from
            
        Returns:
            Extracted quantity or 0 if not found
        """
        if not text:
            return 0
        
        text_lower = text.lower().strip()
        
        # Handle common out-of-stock indicators
        out_of_stock_indicators = [
            'out of stock', 'unavailable', 'not available', 
            'sold out', 'back order', 'discontinued'
        ]
        
        for indicator in out_of_stock_indicators:
            if indicator in text_lower:
                return 0
        
        # Try to extract numeric quantity
        for pattern in RegexPatterns.QUANTITY_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    continue
        
        # Look for standalone numbers
        numbers = re.findall(r'\b(\d+)\b', text)
        if numbers:
            # Return the first reasonable number (not too large)
            for num_str in numbers:
                try:
                    num = int(num_str)
                    if 0 <= num <= 10000:  # Reasonable quantity range
                        return num
                except ValueError:
                    continue
        
        return 0
    
    @staticmethod
    def extract_price(text: str) -> Optional[float]:
        """Extract price from text.
        
        Args:
            text: Text to extract price from
            
        Returns:
            Extracted price or None if not found
        """
        if not text:
            return None
        
        for pattern in RegexPatterns.PRICE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except (ValueError, IndexError):
                    continue
        
        return None
    
    @staticmethod
    def extract_part_number(text: str) -> Optional[str]:
        """Extract part number from text.
        
        Args:
            text: Text to extract part number from
            
        Returns:
            Extracted part number or None if not found
        """
        if not text:
            return None
        
        for pattern in RegexPatterns.PART_NUMBER_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).upper()
        
        return None
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove special characters but keep alphanumeric and basic punctuation
        text = re.sub(r'[^\w\s\-\.\,\:\;\(\)]', '', text)
        
        return text
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
        """Truncate text to specified length.
        
        Args:
            text: Text to truncate
            max_length: Maximum length
            suffix: Suffix to add when truncating
            
        Returns:
            Truncated text
        """
        if not text or len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix


class URLValidator:
    """Utility class for URL validation and manipulation."""
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if URL is valid.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not url:
            return False
        
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize URL format.
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL
        """
        if not url:
            return ""
        
        # Add https if no scheme
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        # Remove trailing slash
        return url.rstrip('/')
    
    @staticmethod
    def build_url(base_url: str, path: str) -> str:
        """Build URL from base and path.
        
        Args:
            base_url: Base URL
            path: Path to append
            
        Returns:
            Complete URL
        """
        return urljoin(base_url, path)


class FileHelper:
    """Utility class for file operations."""
    
    @staticmethod
    def ensure_directory_exists(directory: Union[str, Path]) -> Path:
        """Ensure directory exists, create if it doesn't.
        
        Args:
            directory: Directory path
            
        Returns:
            Path object for the directory
        """
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
    
    @staticmethod
    def generate_timestamped_filename(base_name: str, extension: str = ".json") -> str:
        """Generate filename with timestamp.
        
        Args:
            base_name: Base filename
            extension: File extension
            
        Returns:
            Timestamped filename
        """
        timestamp = datetime.now().strftime(FilePatterns.TIMESTAMP_FORMAT)
        name_without_ext = base_name.replace(extension, "")
        return f"{name_without_ext}_{timestamp}{extension}"
    
    @staticmethod
    def safe_json_save(data: Any, file_path: Union[str, Path], indent: int = 4) -> bool:
        """Safely save data to JSON file.
        
        Args:
            data: Data to save
            file_path: File path
            indent: JSON indentation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)
            return True
        except Exception:
            return False
    
    @staticmethod
    def safe_json_load(file_path: Union[str, Path]) -> Optional[Any]:
        """Safely load data from JSON file.
        
        Args:
            file_path: File path
            
        Returns:
            Loaded data or None if failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    @staticmethod
    def get_file_size_mb(file_path: Union[str, Path]) -> float:
        """Get file size in megabytes.
        
        Args:
            file_path: File path
            
        Returns:
            File size in MB
        """
        try:
            size_bytes = Path(file_path).stat().st_size
            return size_bytes / (1024 * 1024)
        except Exception:
            return 0.0


class DataValidator:
    """Utility class for data validation."""
    
    @staticmethod
    def is_valid_relevance(relevance: str) -> bool:
        """Check if relevance level is valid.
        
        Args:
            relevance: Relevance level to check
            
        Returns:
            True if valid, False otherwise
        """
        return relevance in [level.value for level in RelevanceLevel]
    
    @staticmethod
    def is_valid_inventory_status(status: str) -> bool:
        """Check if inventory status is valid.
        
        Args:
            status: Inventory status to check
            
        Returns:
            True if valid, False otherwise
        """
        return status in [status.value for status in InventoryStatus]
    
    @staticmethod
    def validate_quantity(quantity: Any) -> bool:
        """Validate quantity value.
        
        Args:
            quantity: Quantity to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if isinstance(quantity, str):
                # Try to extract numeric value
                num = TextProcessor.extract_quantity(quantity)
                return 0 <= num <= 100000
            elif isinstance(quantity, (int, float)):
                return 0 <= quantity <= 100000
            else:
                return False
        except Exception:
            return False
    
    @staticmethod
    def validate_search_result(result: Dict[str, Any]) -> List[str]:
        """Validate search result structure.
        
        Args:
            result: Search result to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        required_fields = ['title', 'url']
        
        for field in required_fields:
            if field not in result or not result[field]:
                errors.append(f"Missing or empty required field: {field}")
        
        # Validate URL if present
        if 'url' in result and result['url']:
            if not URLValidator.is_valid_url(result['url']):
                errors.append(f"Invalid URL format: {result['url']}")
        
        # Validate quantity if present
        if 'quantity' in result:
            if not DataValidator.validate_quantity(result['quantity']):
                errors.append(f"Invalid quantity value: {result['quantity']}")
        
        return errors


class PerformanceMetrics:
    """Utility class for performance measurement and analysis."""
    
    @staticmethod
    def calculate_success_rate(successful: int, total: int) -> float:
        """Calculate success rate percentage.
        
        Args:
            successful: Number of successful operations
            total: Total number of operations
            
        Returns:
            Success rate as percentage (0-100)
        """
        if total == 0:
            return 0.0
        return (successful / total) * 100
    
    @staticmethod
    def calculate_average_response_time(times: List[float]) -> float:
        """Calculate average response time.
        
        Args:
            times: List of response times in seconds
            
        Returns:
            Average response time
        """
        if not times:
            return 0.0
        return sum(times) / len(times)
    
    @staticmethod
    def categorize_performance(metric_value: float, thresholds: Dict[str, float]) -> str:
        """Categorize performance based on thresholds.
        
        Args:
            metric_value: Value to categorize
            thresholds: Dictionary of threshold values
            
        Returns:
            Performance category
        """
        # Assume thresholds are ordered from best to worst
        categories = list(thresholds.keys())
        values = list(thresholds.values())
        
        for i, threshold in enumerate(values):
            if metric_value >= threshold:
                return categories[i]
        
        return categories[-1] if categories else "unknown"


class TimestampHelper:
    """Utility class for timestamp operations."""
    
    @staticmethod
    def get_current_timestamp() -> str:
        """Get current timestamp in standard format.
        
        Returns:
            Formatted timestamp string
        """
        return datetime.now().strftime(FilePatterns.READABLE_TIMESTAMP_FORMAT)
    
    @staticmethod
    def get_file_timestamp() -> str:
        """Get timestamp suitable for filenames.
        
        Returns:
            Filename-safe timestamp string
        """
        return datetime.now().strftime(FilePatterns.TIMESTAMP_FORMAT)
    
    @staticmethod
    def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp string to datetime object.
        
        Args:
            timestamp_str: Timestamp string
            
        Returns:
            Datetime object or None if parsing failed
        """
        formats = [
            FilePatterns.READABLE_TIMESTAMP_FORMAT,
            FilePatterns.TIMESTAMP_FORMAT,
            "%Y-%m-%d",
            "%Y%m%d"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        
        return None
    
    @staticmethod
    def time_ago(timestamp: datetime) -> str:
        """Get human-readable time difference.
        
        Args:
            timestamp: Past timestamp
            
        Returns:
            Human-readable time difference
        """
        now = datetime.now()
        diff = now - timestamp
        
        if diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hours ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minutes ago"
        else:
            return "Just now"


class RetryHelper:
    """Utility class for retry logic."""
    
    @staticmethod
    def retry_on_exception(
        max_retries: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        exceptions: tuple = (Exception,)
    ) -> Callable:
        """Decorator for retrying functions on exception.
        
        Args:
            max_retries: Maximum number of retries
            delay: Initial delay between retries
            backoff: Backoff multiplier for delay
            exceptions: Tuple of exceptions to catch
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> T:
                current_delay = delay
                
                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        if attempt == max_retries:
                            raise e
                        
                        time.sleep(current_delay)
                        current_delay *= backoff
                
                # This should never be reached
                raise RuntimeError("Retry logic failed unexpectedly")
            
            return wrapper
        return decorator
    
    @staticmethod
    def retry_with_condition(
        condition: Callable[[Any], bool],
        max_retries: int = 3,
        delay: float = 1.0
    ) -> Callable:
        """Decorator for retrying functions based on return value condition.
        
        Args:
            condition: Function that returns True if retry is needed
            max_retries: Maximum number of retries
            delay: Delay between retries
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> T:
                for attempt in range(max_retries + 1):
                    result = func(*args, **kwargs)
                    
                    if not condition(result) or attempt == max_retries:
                        return result
                    
                    time.sleep(delay)
                
                return result
            
            return wrapper
        return decorator


class ConfigHelper:
    """Utility class for configuration operations."""
    
    @staticmethod
    def merge_configs(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two configuration dictionaries.
        
        Args:
            base_config: Base configuration
            override_config: Override configuration
            
        Returns:
            Merged configuration
        """
        merged = base_config.copy()
        
        for key, value in override_config.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = ConfigHelper.merge_configs(merged[key], value)
            else:
                merged[key] = value
        
        return merged
    
    @staticmethod
    def validate_config_structure(config: Dict[str, Any], required_keys: List[str]) -> List[str]:
        """Validate configuration structure.
        
        Args:
            config: Configuration to validate
            required_keys: List of required keys
            
        Returns:
            List of validation errors
        """
        errors = []
        
        for key in required_keys:
            if '.' in key:
                # Nested key validation
                keys = key.split('.')
                current = config
                
                for subkey in keys:
                    if not isinstance(current, dict) or subkey not in current:
                        errors.append(f"Missing required nested key: {key}")
                        break
                    current = current[subkey]
            else:
                # Simple key validation
                if key not in config:
                    errors.append(f"Missing required key: {key}")
        
        return errors


class StringHelper:
    """Utility class for string operations."""
    
    @staticmethod
    def to_snake_case(text: str) -> str:
        """Convert text to snake_case.
        
        Args:
            text: Text to convert
            
        Returns:
            Snake case text
        """
        # Replace spaces and hyphens with underscores
        text = re.sub(r'[-\s]+', '_', text)
        # Insert underscore before uppercase letters
        text = re.sub(r'([a-z])([A-Z])', r'\1_\2', text)
        return text.lower()
    
    @staticmethod
    def to_title_case(text: str) -> str:
        """Convert text to Title Case.
        
        Args:
            text: Text to convert
            
        Returns:
            Title case text
        """
        return ' '.join(word.capitalize() for word in text.replace('_', ' ').split())
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename by removing invalid characters.
        
        Args:
            filename: Filename to sanitize
            
        Returns:
            Sanitized filename
        """
        # Remove invalid filename characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove multiple underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        return sanitized.strip('_')


# Commonly used utility functions
def safe_get(dictionary: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely get value from dictionary.
    
    Args:
        dictionary: Dictionary to get value from
        key: Key to retrieve
        default: Default value if key not found
        
    Returns:
        Value or default
    """
    return dictionary.get(key, default) if dictionary else default


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """Flatten nested dictionary.
    
    Args:
        d: Dictionary to flatten
        parent_key: Parent key prefix
        sep: Separator for nested keys
        
    Returns:
        Flattened dictionary
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def chunk_list(lst: List[T], chunk_size: int) -> List[List[T]]:
    """Split list into chunks of specified size.
    
    Args:
        lst: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]