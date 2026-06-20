"""Factory pattern implementation for creating different types of scrapers."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Type, Optional, Any
from enum import Enum

from config.config_models import SiteConfig, ChromeConfig, AppConfig
from config.config_loader import ConfigLoader
from web_driver_manager import WebDriverManager
from web_scraper import WebScraper
from scraper_facade import ScraperFacade
from metrics_monitor import MetricsCollector, PerformanceMonitor
from exceptions import ConfigurationError, ScrapingError


logger = logging.getLogger(__name__)


class ScraperType(Enum):
    """Enumeration of available scraper types."""
    BASIC = "basic"
    ADVANCED = "advanced"
    MONITORED = "monitored"
    BATCH = "batch"
    TESTING = "testing"


class BaseScraperBuilder(ABC):
    """Abstract base class for scraper builders."""
    
    @abstractmethod
    def build(self, config: AppConfig) -> Any:
        """Build a scraper instance.
        
        Args:
            config: Application configuration
            
        Returns:
            Configured scraper instance
        """
        pass
    
    @abstractmethod
    def get_required_config_sections(self) -> List[str]:
        """Get required configuration sections.
        
        Returns:
            List of required configuration section names
        """
        pass


class BasicScraperBuilder(BaseScraperBuilder):
    """Builder for basic scraper instances."""
    
    def build(self, config: AppConfig) -> ScraperFacade:
        """Build a basic scraper facade.
        
        Args:
            config: Application configuration
            
        Returns:
            ScraperFacade instance
        """
        logger.info("Building basic scraper")
        return ScraperFacade(chrome_config=config.chrome_config)
    
    def get_required_config_sections(self) -> List[str]:
        """Get required configuration sections."""
        return ['chrome_config', 'site_config']


class AdvancedScraperBuilder(BaseScraperBuilder):
    """Builder for advanced scraper instances with enhanced features."""
    
    def build(self, config: AppConfig) -> 'AdvancedScraperFacade':
        """Build an advanced scraper facade.
        
        Args:
            config: Application configuration
            
        Returns:
            AdvancedScraperFacade instance
        """
        logger.info("Building advanced scraper with enhanced features")
        
        # Enable metrics collection if configured
        metrics_collector = None
        if config.deployment_config.enable_metrics_collection:
            metrics_collector = MetricsCollector(
                enable_collection=True,
                storage_path="advanced_metrics.json"
            )
        
        return AdvancedScraperFacade(
            chrome_config=config.chrome_config,
            metrics_collector=metrics_collector,
            enable_screenshots=config.deployment_config.enable_screenshots
        )
    
    def get_required_config_sections(self) -> List[str]:
        """Get required configuration sections."""
        return ['chrome_config', 'site_config', 'deployment_config']


class MonitoredScraperBuilder(BaseScraperBuilder):
    """Builder for monitored scraper instances with performance tracking."""
    
    def build(self, config: AppConfig) -> 'MonitoredScraperFacade':
        """Build a monitored scraper facade.
        
        Args:
            config: Application configuration
            
        Returns:
            MonitoredScraperFacade instance
        """
        logger.info("Building monitored scraper with performance tracking")
        
        metrics_collector = MetricsCollector(
            enable_collection=True,
            storage_path="monitored_metrics.json"
        )
        
        performance_monitor = PerformanceMonitor(metrics_collector)
        
        # Set custom thresholds if provided in config
        if hasattr(config, 'monitoring_thresholds'):
            performance_monitor.set_thresholds(**config.monitoring_thresholds)
        
        return MonitoredScraperFacade(
            chrome_config=config.chrome_config,
            metrics_collector=metrics_collector,
            performance_monitor=performance_monitor
        )
    
    def get_required_config_sections(self) -> List[str]:
        """Get required configuration sections."""
        return ['chrome_config', 'site_config', 'deployment_config']


class BatchScraperBuilder(BaseScraperBuilder):
    """Builder for batch processing scraper instances."""
    
    def build(self, config: AppConfig) -> 'BatchScraperFacade':
        """Build a batch scraper facade.
        
        Args:
            config: Application configuration
            
        Returns:
            BatchScraperFacade instance
        """
        logger.info("Building batch scraper for high-volume processing")
        
        return BatchScraperFacade(
            chrome_config=config.chrome_config,
            batch_size=getattr(config.deployment_config, 'batch_size', 10),
            max_concurrent=getattr(config.deployment_config, 'max_concurrent', 3)
        )
    
    def get_required_config_sections(self) -> List[str]:
        """Get required configuration sections."""
        return ['chrome_config', 'site_config', 'deployment_config']


class TestingScraperBuilder(BaseScraperBuilder):
    """Builder for testing scraper instances with mock capabilities."""
    
    def build(self, config: AppConfig) -> 'TestingScraperFacade':
        """Build a testing scraper facade.
        
        Args:
            config: Application configuration
            
        Returns:
            TestingScraperFacade instance
        """
        logger.info("Building testing scraper with mock capabilities")
        
        return TestingScraperFacade(
            chrome_config=config.chrome_config,
            enable_mocking=True,
            debug_mode=True
        )
    
    def get_required_config_sections(self) -> List[str]:
        """Get required configuration sections."""
        return ['chrome_config', 'site_config']


class ScraperFactory:
    """Factory class for creating different types of scrapers."""
    
    def __init__(self):
        """Initialize the scraper factory."""
        self._builders: Dict[ScraperType, BaseScraperBuilder] = {
            ScraperType.BASIC: BasicScraperBuilder(),
            ScraperType.ADVANCED: AdvancedScraperBuilder(),
            ScraperType.MONITORED: MonitoredScraperBuilder(),
            ScraperType.BATCH: BatchScraperBuilder(),
            ScraperType.TESTING: TestingScraperBuilder(),
        }
    
    def register_builder(self, scraper_type: ScraperType, builder: BaseScraperBuilder) -> None:
        """Register a custom builder.
        
        Args:
            scraper_type: Type of scraper
            builder: Builder instance
        """
        self._builders[scraper_type] = builder
        logger.info(f"Registered custom builder for {scraper_type.value}")
    
    def create_scraper(
        self,
        scraper_type: ScraperType,
        site_name: str,
        config_path: Optional[str] = None
    ) -> Any:
        """Create a scraper instance.
        
        Args:
            scraper_type: Type of scraper to create
            site_name: Name of the site configuration
            config_path: Optional path to configuration file
            
        Returns:
            Configured scraper instance
            
        Raises:
            ConfigurationError: If configuration is invalid
            ScrapingError: If scraper creation fails
        """
        if scraper_type not in self._builders:
            raise ScrapingError(f"Unknown scraper type: {scraper_type.value}")
        
        builder = self._builders[scraper_type]
        
        try:
            # Load configuration
            config = ConfigLoader.load_config_for_site(site_name, config_path)
            
            # Validate required configuration sections
            self._validate_config(config, builder.get_required_config_sections())
            
            # Build scraper
            scraper = builder.build(config)
            
            logger.info(f"Successfully created {scraper_type.value} scraper for site '{site_name}'")
            return scraper
            
        except Exception as e:
            logger.error(f"Failed to create {scraper_type.value} scraper: {e}")
            raise ScrapingError(f"Scraper creation failed: {e}")
    
    def create_scraper_with_config(self, scraper_type: ScraperType, config: AppConfig) -> Any:
        """Create a scraper instance with provided configuration.
        
        Args:
            scraper_type: Type of scraper to create
            config: Application configuration
            
        Returns:
            Configured scraper instance
        """
        if scraper_type not in self._builders:
            raise ScrapingError(f"Unknown scraper type: {scraper_type.value}")
        
        builder = self._builders[scraper_type]
        
        # Validate required configuration sections
        self._validate_config(config, builder.get_required_config_sections())
        
        return builder.build(config)
    
    def get_available_types(self) -> List[ScraperType]:
        """Get list of available scraper types.
        
        Returns:
            List of available scraper types
        """
        return list(self._builders.keys())
    
    def _validate_config(self, config: AppConfig, required_sections: List[str]) -> None:
        """Validate that required configuration sections are present.
        
        Args:
            config: Application configuration
            required_sections: List of required section names
            
        Raises:
            ConfigurationError: If required sections are missing
        """
        missing_sections = []
        
        for section in required_sections:
            if not hasattr(config, section) or getattr(config, section) is None:
                missing_sections.append(section)
        
        if missing_sections:
            raise ConfigurationError(
                f"Missing required configuration sections: {', '.join(missing_sections)}",
                invalid_keys=missing_sections
            )


# Extended facade classes for different scraper types

class AdvancedScraperFacade(ScraperFacade):
    """Advanced scraper facade with enhanced features."""
    
    def __init__(
        self,
        chrome_config: Optional[ChromeConfig] = None,
        metrics_collector: Optional[MetricsCollector] = None,
        enable_screenshots: bool = False
    ):
        """Initialize advanced scraper facade.
        
        Args:
            chrome_config: Chrome configuration
            metrics_collector: Optional metrics collector
            enable_screenshots: Whether to enable automatic screenshots
        """
        super().__init__(chrome_config)
        self.metrics_collector = metrics_collector
        self.enable_screenshots = enable_screenshots
    
    def scrape_with_retry(
        self,
        search_terms: List[str],
        site_config: SiteConfig,
        max_retries: int = 3,
        retry_delay: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Scrape with automatic retry on failures.
        
        Args:
            search_terms: List of search terms
            site_config: Site configuration
            max_retries: Maximum number of retries per search
            retry_delay: Delay between retries in seconds
            
        Returns:
            Dictionary mapping search terms to results
        """
        # Implementation would include retry logic with exponential backoff
        # This is a placeholder for the enhanced functionality
        return self.scrape_with_config(search_terms, site_config)


class MonitoredScraperFacade(ScraperFacade):
    """Monitored scraper facade with performance tracking."""
    
    def __init__(
        self,
        chrome_config: Optional[ChromeConfig] = None,
        metrics_collector: Optional[MetricsCollector] = None,
        performance_monitor: Optional[PerformanceMonitor] = None
    ):
        """Initialize monitored scraper facade.
        
        Args:
            chrome_config: Chrome configuration
            metrics_collector: Metrics collector
            performance_monitor: Performance monitor
        """
        super().__init__(chrome_config)
        self.metrics_collector = metrics_collector
        self.performance_monitor = performance_monitor
    
    def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance report.
        
        Args:
            hours: Number of hours to include in report
            
        Returns:
            Performance report dictionary
        """
        if self.performance_monitor:
            return self.performance_monitor.generate_performance_report(hours)
        return {}
    
    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for performance alerts.
        
        Returns:
            List of alert dictionaries
        """
        if self.performance_monitor:
            return self.performance_monitor.check_performance_alerts()
        return []


class BatchScraperFacade(ScraperFacade):
    """Batch scraper facade for high-volume processing."""
    
    def __init__(
        self,
        chrome_config: Optional[ChromeConfig] = None,
        batch_size: int = 10,
        max_concurrent: int = 3
    ):
        """Initialize batch scraper facade.
        
        Args:
            chrome_config: Chrome configuration
            batch_size: Number of items to process in each batch
            max_concurrent: Maximum concurrent operations
        """
        super().__init__(chrome_config)
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
    
    def scrape_batch(
        self,
        search_terms: List[str],
        site_configs: Dict[str, SiteConfig]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Scrape multiple search terms across multiple sites.
        
        Args:
            search_terms: List of search terms
            site_configs: Dictionary mapping site names to configurations
            
        Returns:
            Dictionary mapping search terms to results
        """
        # Implementation would include batch processing logic
        # This is a placeholder for the batch functionality
        results = {}
        for term in search_terms:
            results[term] = []
        return results


class TestingScraperFacade(ScraperFacade):
    """Testing scraper facade with mock capabilities."""
    
    def __init__(
        self,
        chrome_config: Optional[ChromeConfig] = None,
        enable_mocking: bool = True,
        debug_mode: bool = True
    ):
        """Initialize testing scraper facade.
        
        Args:
            chrome_config: Chrome configuration
            enable_mocking: Whether to enable mocking
            debug_mode: Whether to enable debug mode
        """
        super().__init__(chrome_config)
        self.enable_mocking = enable_mocking
        self.debug_mode = debug_mode
    
    def scrape_with_mock_data(
        self,
        search_terms: List[str],
        mock_results: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Scrape using mock data for testing.
        
        Args:
            search_terms: List of search terms
            mock_results: Mock results to return
            
        Returns:
            Mock results dictionary
        """
        if self.enable_mocking:
            return {term: mock_results.get(term, []) for term in search_terms}
        else:
            # Fall back to actual scraping
            return {}


# Convenience functions
def create_basic_scraper(site_name: str, config_path: Optional[str] = None) -> ScraperFacade:
    """Create a basic scraper instance.
    
    Args:
        site_name: Site name
        config_path: Optional configuration file path
        
    Returns:
        Basic scraper facade
    """
    factory = ScraperFactory()
    return factory.create_scraper(ScraperType.BASIC, site_name, config_path)


def create_monitored_scraper(site_name: str, config_path: Optional[str] = None) -> MonitoredScraperFacade:
    """Create a monitored scraper instance.
    
    Args:
        site_name: Site name
        config_path: Optional configuration file path
        
    Returns:
        Monitored scraper facade
    """
    factory = ScraperFactory()
    return factory.create_scraper(ScraperType.MONITORED, site_name, config_path)


def create_testing_scraper(site_name: str, config_path: Optional[str] = None) -> TestingScraperFacade:
    """Create a testing scraper instance.
    
    Args:
        site_name: Site name
        config_path: Optional configuration file path
        
    Returns:
        Testing scraper facade
    """
    factory = ScraperFactory()
    return factory.create_scraper(ScraperType.TESTING, site_name, config_path)