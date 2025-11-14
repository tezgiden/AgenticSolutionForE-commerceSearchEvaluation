"""Shared utilities for web scraping operations."""

import re
import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path


logger = logging.getLogger(__name__)


class FileUtils:
    """File operation utilities."""
    
    @staticmethod
    def ensure_directory_exists(directory: str) -> None:
        """Ensure a directory exists, create if it doesn't.
        
        Args:
            directory: Directory path to create
        """
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def get_safe_filename(text: str, max_length: int = 50) -> str:
        """Convert text to a safe filename.
        
        Args:
            text: Text to convert
            max_length: Maximum length of filename
            
        Returns:
            Safe filename string
        """
        # Remove or replace unsafe characters
        safe_text = re.sub(r'[^A-Za-z0-9\-_\s]', '', text)
        safe_text = re.sub(r'\s+', '_', safe_text.strip())
        safe_text = safe_text.strip('_')
        
        # Truncate if too long
        if len(safe_text) > max_length:
            safe_text = safe_text[:max_length].rstrip('_')
        
        return safe_text or "unnamed"
    
    @staticmethod
    def get_timestamped_filename(base_name: str, extension: str = "json") -> str:
        """Generate a timestamped filename.
        
        Args:
            base_name: Base filename without extension
            extension: File extension (without dot)
            
        Returns:
            Timestamped filename
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_base = FileUtils.get_safe_filename(base_name)
        return f"{safe_base}_{timestamp}.{extension}"


class TextUtils:
    """Text processing utilities."""
    
    @staticmethod
    def clean_whitespace(text: str) -> str:
        """Clean and normalize whitespace in text.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        return text.strip()
    
    @staticmethod
    def extract_numbers(text: str) -> List[int]:
        """Extract all numbers from text.
        
        Args:
            text: Text to extract numbers from
            
        Returns:
            List of integers found in text
        """
        if not text:
            return []
        
        numbers = re.findall(r'\d+', text)
        return [int(num) for num in numbers]
    
    @staticmethod
    def extract_price(text: str) -> Optional[float]:
        """Extract price from text.
        
        Args:
            text: Text containing price
            
        Returns:
            Extracted price as float or None if not found
        """
        if not text:
            return None
        
        # Look for price patterns like $12.34, 12.34, $12, etc.
        price_patterns = [
            r'\$?(\d+\.\d{2})',  # $12.34 or 12.34
            r'\$?(\d+)',         # $12 or 12
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    @staticmethod
    def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
        """Truncate text to specified length with suffix.
        
        Args:
            text: Text to truncate
            max_length: Maximum length including suffix
            suffix: Suffix to add when truncating
            
        Returns:
            Truncated text
        """
        if not text or len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix


class ValidationUtils:
    """Data validation utilities."""
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if URL is valid.
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL appears valid, False otherwise
        """
        if not url:
            return False
        
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return bool(url_pattern.match(url))
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Check if email is valid.
        
        Args:
            email: Email to validate
            
        Returns:
            True if email appears valid, False otherwise
        """
        if not email:
            return False
        
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        return bool(email_pattern.match(email))
    
    @staticmethod
    def validate_scraping_result(result: Dict[str, Any]) -> List[str]:
        """Validate a scraping result and return list of issues.
        
        Args:
            result: Scraping result dictionary
            
        Returns:
            List of validation issues (empty if valid)
        """
        issues = []
        
        # Check required fields
        required_fields = ['title', 'url']
        for field in required_fields:
            if not result.get(field) or result[field] == "N/A":
                issues.append(f"Missing or invalid {field}")
        
        # Validate URL if present
        url = result.get('url')
        if url and url != "N/A" and not ValidationUtils.is_valid_url(url):
            issues.append("Invalid URL format")
        
        # Check for meaningful title
        title = result.get('title')
        if title and title != "N/A" and len(title.strip()) < 3:
            issues.append("Title too short")
        
        return issues


class LoggingUtils:
    """Logging configuration utilities."""
    
    @staticmethod
    def setup_logging(
        level: str = "INFO",
        log_file: Optional[str] = None,
        include_timestamp: bool = True
    ) -> None:
        """Setup logging configuration.
        
        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR)
            log_file: Optional log file path
            include_timestamp: Whether to include timestamp in logs
        """
        log_level = getattr(logging, level.upper(), logging.INFO)
        
        # Create formatter
        if include_timestamp:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        else:
            formatter = logging.Formatter(
                '%(name)s - %(levelname)s - %(message)s'
            )
        
        # Setup handlers
        handlers = [logging.StreamHandler()]
        
        if log_file:
            FileUtils.ensure_directory_exists(os.path.dirname(log_file) or ".")
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)
        
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            handlers=handlers,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s' if include_timestamp else '%(name)s - %(levelname)s - %(message)s'
        )
    
    @staticmethod
    def create_logger(name: str, level: Optional[str] = None) -> logging.Logger:
        """Create a logger with specified name and level.
        
        Args:
            name: Logger name
            level: Optional logging level override
            
        Returns:
            Configured logger
        """
        logger = logging.getLogger(name)
        
        if level:
            log_level = getattr(logging, level.upper(), logging.INFO)
            logger.setLevel(log_level)
        
        return logger


class PerformanceUtils:
    """Performance monitoring utilities."""
    
    @staticmethod
    def time_function(func):
        """Decorator to time function execution.
        
        Args:
            func: Function to time
            
        Returns:
            Decorated function that logs execution time
        """
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                logger.debug(f"{func.__name__} took {duration:.2f} seconds")
        
        return wrapper
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in seconds to human-readable string.
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        if seconds < 1:
            return f"{seconds*1000:.0f}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        else:
            minutes = int(seconds // 60)
            remaining_seconds = seconds % 60
            return f"{minutes}m {remaining_seconds:.1f}s"