"""Enhanced configuration loading utilities with full CLI support."""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from copy import deepcopy

from config.config_models import (
    AppConfig, SiteConfig, ScrapingConfig, OutputConfig,
    LLMConfig, EvaluationConfig, ChromeConfig, DeploymentConfig
)


logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Custom exception for configuration-related errors."""
    pass


class ConfigLoader:
    """Enhanced configuration loader with CLI support and validation."""
    
    DEFAULT_CONFIG_PATH = "config.json"
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the config loader.
        
        Args:
            config_path: Optional path to configuration file
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._config_cache: Optional[Dict[str, Any]] = None
    
    def get_site_config(self, site_name: str) -> AppConfig:
        """Get configuration for a specific site.
        
        Args:
            site_name: Name of the site to load configuration for
            
        Returns:
            Complete application configuration
            
        Raises:
            ConfigurationError: If configuration cannot be loaded or parsed
        """
        return self.load_config_for_site(site_name, self.config_path)
    
    def override_config(self, site_name: str, overrides: Dict[str, Any]) -> AppConfig:
        """Load configuration with command line overrides applied.
        
        Args:
            site_name: Name of the site to load configuration for
            overrides: Dictionary of override values
            
        Returns:
            Configuration with overrides applied
            
        Raises:
            ConfigurationError: If configuration cannot be loaded or overrides applied
        """
        # Load base configuration
        base_config = self.get_site_config(site_name)
        
        # Apply overrides
        return self._apply_overrides(base_config, overrides)
    
    def get_available_sites(self, config_path: Optional[str] = None) -> List[str]:
        """Get list of available site configurations.
        
        Args:
            config_path: Optional path to config file
            
        Returns:
            List of available site names
            
        Raises:
            ConfigurationError: If configuration file cannot be read
        """
        path = config_path or self.config_path
        
        try:
            config_data = self._load_json_config(path)
            sites_config = config_data.get("sites", {})
            return list(sites_config.keys())
        except Exception as e:
            raise ConfigurationError(f"Failed to get available sites: {e}")
    
    def validate_config(self, site_name: str, config_path: Optional[str] = None) -> List[str]:
        """Validate configuration for a specific site.
        
        Args:
            site_name: Site to validate
            config_path: Optional path to config file
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        path = config_path or self.config_path
        
        try:
            # Check if config file exists
            if not Path(path).exists():
                return [f"Configuration file not found: {path}"]
            
            # Load and parse configuration
            config_data = self._load_json_config(path)
            
            # Check if site exists
            sites_config = config_data.get("sites", {})
            if site_name not in sites_config:
                available_sites = list(sites_config.keys())
                return [f"Site '{site_name}' not found. Available sites: {available_sites}"]
            
            # Validate site configuration structure
            site_errors = self._validate_site_structure(sites_config[site_name], site_name)
            errors.extend(site_errors)
            
            # Validate global configuration
            global_errors = self._validate_global_configuration(config_data)
            errors.extend(global_errors)
            
        except Exception as e:
            errors.append(f"Configuration validation failed: {e}")
        
        return errors
    
    @classmethod
    def load_config_for_site(cls, site_name: str, config_path: Optional[str] = None) -> AppConfig:
        """Load configuration for a specific site (class method for backward compatibility).
        
        Args:
            site_name: Name of the site to load configuration for
            config_path: Optional path to config file (uses default if None)
            
        Returns:
            Complete application configuration
            
        Raises:
            ConfigurationError: If configuration cannot be loaded or parsed
        """
        config_path = config_path or cls.DEFAULT_CONFIG_PATH
        print(f"Loading configuration for site '{site_name}' from {config_path}")
        try:
            config_data = cls._load_json_config(config_path)
            print(f"Configuration data loaded successfully for site '{site_name}'")
            return cls._parse_config(config_data, site_name)
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration for site '{site_name}': {e}")
    
    def _apply_overrides(self, config: AppConfig, overrides: Dict[str, Any]) -> AppConfig:
        """Apply command line overrides to configuration.
        
        Args:
            config: Base configuration
            overrides: Override values
            
        Returns:
            Configuration with overrides applied
        """
        # Create a deep copy to avoid modifying the original
        modified_config = deepcopy(config)
        
        for key, value in overrides.items():
            try:
                if key == "model":
                    modified_config.llm_config.default_model = value
                    logger.info(f"Override: LLM model set to '{value}'")
                
                elif key == "max_results":
                    modified_config.site_config.scraping_config.max_results_per_query = value
                    logger.info(f"Override: Max results per query set to {value}")
                
                elif key == "headless":
                    modified_config.chrome_config.headless = value
                    logger.info(f"Override: Headless mode set to {value}")
                
                elif key == "output_file":
                    modified_config.site_config.output_config.output_file = value
                    logger.info(f"Override: Output file set to '{value}'")
                
                elif key == "environment":
                    modified_config.deployment_config.environment = value
                    logger.info(f"Override: Environment set to '{value}'")
                
                else:
                    logger.warning(f"Unknown override key: {key}")
                    
            except Exception as e:
                logger.error(f"Failed to apply override {key}={value}: {e}")
        
        return modified_config
    
    def _validate_site_structure(self, site_data: Dict[str, Any], site_name: str) -> List[str]:
        """Validate the structure of a site configuration.
        
        Args:
            site_data: Site configuration data
            site_name: Name of the site being validated
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Required top-level fields
        required_fields = ["site_name", "target_url", "scraping"]
        for field in required_fields:
            if field not in site_data:
                errors.append(f"Missing required field '{field}' in site '{site_name}'")
        
        # Validate URL format
        target_url = site_data.get("target_url", "")
        if target_url and not (target_url.startswith("http://") or target_url.startswith("https://")):
            errors.append(f"Invalid URL format for site '{site_name}': {target_url}")
        
        # Validate scraping configuration
        scraping_config = site_data.get("scraping", {})
        scraping_errors = self._validate_scraping_config(scraping_config, site_name)
        errors.extend(scraping_errors)
        
        # Validate search tasks
        search_tasks = site_data.get("search_tasks", [])
        if not isinstance(search_tasks, list):
            errors.append(f"search_tasks must be a list in site '{site_name}'")
        
        return errors
    
    def _validate_scraping_config(self, scraping_config: Dict[str, Any], site_name: str) -> List[str]:
        """Validate scraping configuration.
        
        Args:
            scraping_config: Scraping configuration data
            site_name: Name of the site being validated
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Required scraping fields
        required_fields = [
            "search_input_selectors",
            "search_button_selectors", 
            "product_card_selectors"
        ]
        
        for field in required_fields:
            if field not in scraping_config:
                errors.append(f"Missing required scraping field '{field}' in site '{site_name}'")
            elif not isinstance(scraping_config[field], list):
                errors.append(f"Field '{field}' must be a list in site '{site_name}'")
            elif len(scraping_config[field]) == 0:
                errors.append(f"Field '{field}' cannot be empty in site '{site_name}'")
        
        # Validate numeric fields
        numeric_fields = ["max_results_per_query", "wait_timeout", "page_load_timeout"]
        for field in numeric_fields:
            value = scraping_config.get(field)
            if value is not None:
                if not isinstance(value, int) or value <= 0:
                    errors.append(f"Field '{field}' must be a positive integer in site '{site_name}'")
        
        return errors
    
    def _validate_global_configuration(self, config_data: Dict[str, Any]) -> List[str]:
        """Validate global configuration sections.
        
        Args:
            config_data: Complete configuration data
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Validate LLM configuration
        llm_config = config_data.get("llm", {})
        if "default_model" in llm_config and not llm_config["default_model"]:
            errors.append("LLM default_model cannot be empty")
        
        # Validate chrome configuration
        chrome_config = config_data.get("chrome", {})
        if "window_size" in chrome_config:
            window_size = chrome_config["window_size"]
            if not isinstance(window_size, dict) or "width" not in window_size or "height" not in window_size:
                errors.append("Chrome window_size must be a dict with 'width' and 'height' fields")
        
        return errors
    
    @classmethod
    def load_default_chrome_config(cls) -> ChromeConfig:
        """Load default Chrome configuration for backward compatibility.
        
        Returns:
            Default Chrome configuration
        """
        return ChromeConfig(
            chrome_driver_path=None,
            headless=True,
            window_size={"width": 3840, "height": 2160},
            implicit_wait=3,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        )
    
    @classmethod
    def create_default_truckpro_config(cls) -> SiteConfig:
        """Create default TruckPro configuration for backward compatibility.
        
        Returns:
            Default TruckPro site configuration
        """
        scraping_config = ScrapingConfig(
            search_input_selectors=[
                "#searchInput",
                "input[placeholder=\"Search name, sku, item #\"]",
                "input[type=\"search\"]",
                "input.search-input"
            ],
            search_button_selectors=[
                "//button[contains(@class, 'search-bar__button')]",
                "//button[normalize-space()=\"Search\"]",
                "//button[contains(@class, 'search')]",
                "//button[contains(@class, 'search-button')]"
            ],
            product_card_selectors=[
                "div.productlist",
                "div.product-card",
                "div.search-result-item"
            ],
            product_link_selector="a.link",
            product_title_selectors=["div.name.longName", "h3.name.longName"],
            product_sku_selectors=["span.sku-text", "span.vendor-value"],
            product_price_selectors=["span.formatted-price", "div.price-wrapper"],
            product_quantity_selectors=["span.inventory-available"],
            badges_selectors=["ul.product-badges li div.badges.partial-match span"],
            exact_match_selectors=["ul.product-badges li div.badges.exact-match span"],
            no_results_selectors=[
                "div.message-alert.info.p-3.message-no-item-alert",
                "div.message-no-item-alert",
                "div.message-alert"
            ],
            max_results_per_query=10,
            wait_timeout=10,
            page_load_timeout=30
        )
        
        output_config = OutputConfig(
            output_file="scraped_results.json",
            detailed_output_file="detailed_results.json"
        )
        
        return SiteConfig(
            site_name="TruckPro",
            target_url="https://www.truckpro.com/",
            search_tasks=[],
            inventory_test_cases=[],
            scraping_config=scraping_config,
            output_config=output_config
        )
    
    @classmethod
    def _load_json_config(cls, config_path: str) -> Dict[str, Any]:
        """Load JSON configuration from file.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Parsed JSON configuration data
            
        Raises:
            ConfigurationError: If file cannot be read or parsed
        """
        config_file = Path(config_path)
        
        if not config_file.exists():
            print(f"Configuration file not found: {config_path}")
            raise ConfigurationError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                print(f"Loading configuration from {config_path}")
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {config_path}: {e}")
            raise ConfigurationError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            print(f"Error reading configuration file: {e}")
            raise ConfigurationError(f"Error reading configuration file: {e}")
    
    @classmethod
    def _parse_config(cls, config_data: Dict[str, Any], site_name: str) -> AppConfig:
        """Parse configuration data into structured objects.
        
        Args:
            config_data: Raw configuration data
            site_name: Name of the site to extract configuration for
            
        Returns:
            Parsed application configuration
            
        Raises:
            ConfigurationError: If configuration is invalid or missing required fields
        """
        try:
            # Find site-specific configuration
            sites_config = config_data.get("sites", {})
            print(f"Available sites in configuration: {list(sites_config.keys())}")
            if site_name not in sites_config:
                raise ConfigurationError(f"Site '{site_name}' not found in configuration")
            
            site_data = sites_config[site_name]
            
            # Parse site configuration
            site_config = cls._parse_site_config(site_data)
            print(f"Parsed configuration for site '{site_name}': {site_config}")
            # Parse other configurations with defaults
            llm_config = cls._parse_llm_config(config_data.get("llm", {}))
            print(f"Parsed LLM configuration: {llm_config}")
            evaluation_config = cls._parse_evaluation_config(config_data.get("evaluation", {}))
            print(f"Parsed evaluation configuration: {evaluation_config}")
            chrome_config = cls._parse_chrome_config(config_data.get("chrome", {}))
            print(f"Parsed Chrome configuration: {chrome_config}")
            deployment_config = cls._parse_deployment_config(config_data.get("deployment", {}))
            print(f"Parsed deployment configuration: {deployment_config}")
            
            return AppConfig(
                site_config=site_config,
                llm_config=llm_config,
                evaluation_config=evaluation_config,
                chrome_config=chrome_config,
                deployment_config=deployment_config
            )
            
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(f"Error parsing configuration: {e}")
    
    @classmethod
    def _parse_site_config(cls, site_data: Dict[str, Any]) -> SiteConfig:
        """Parse site-specific configuration."""
        scraping_data = site_data.get("scraping", {})
        output_data = site_data.get("output", {})
        
        scraping_config = ScrapingConfig(
            search_input_selectors=scraping_data.get("search_input_selectors", []),
            search_button_selectors=scraping_data.get("search_button_selectors", []),
            product_card_selectors=scraping_data.get("product_card_selectors", []),
            product_link_selector=scraping_data.get("product_link_selector", ""),
            product_title_selectors=scraping_data.get("product_title_selectors", []),
            product_sku_selectors=scraping_data.get("product_sku_selectors", []),
            product_price_selectors=scraping_data.get("product_price_selectors", []),
            product_quantity_selectors=scraping_data.get("product_quantity_selectors", []),
            badges_selectors=scraping_data.get("badges_selectors", []),
            exact_match_selectors=scraping_data.get("exact_match_selectors", []),
            no_results_selectors=scraping_data.get("no_results_selectors", []),
            max_results_per_query=scraping_data.get("max_results_per_query", 10),
            wait_timeout=scraping_data.get("wait_timeout", 10),
            page_load_timeout=scraping_data.get("page_load_timeout", 30)
        )
        
        output_config = OutputConfig(
            output_file=output_data.get("output_file", "scraped_results.json"),
            detailed_output_file=output_data.get("detailed_output_file", "detailed_results.json")
        )
        
        return SiteConfig(
            site_name=site_data.get("site_name", ""),
            target_url=site_data.get("target_url", ""),
            search_tasks=site_data.get("search_tasks", []),
            inventory_test_cases=site_data.get("inventory_test_cases", []),
            scraping_config=scraping_config,
            output_config=output_config
        )
    
    @classmethod
    def _parse_llm_config(cls, llm_data: Dict[str, Any]) -> LLMConfig:
        """Parse LLM configuration with defaults."""
        return LLMConfig(
            ollama_api_endpoint=llm_data.get("ollama_api_endpoint", "http://localhost:11434"),
            default_model=llm_data.get("default_model", "llama2"),
            timeout=llm_data.get("timeout", 30),
            max_retries=llm_data.get("max_retries", 3)
        )
    
    @classmethod
    def _parse_evaluation_config(cls, eval_data: Dict[str, Any]) -> EvaluationConfig:
        """Parse evaluation configuration with defaults."""
        return EvaluationConfig(
            enable_inventory_ranking=eval_data.get("enable_inventory_ranking", True),
            enable_detailed_analysis=eval_data.get("enable_detailed_analysis", False),
            inventory_weight_factor=eval_data.get("inventory_weight_factor", 0.3),
            apply_post_ranking=eval_data.get("apply_post_ranking", True),
            low_stock_threshold=eval_data.get("low_stock_threshold", 5)
        )
    
    @classmethod
    def _parse_chrome_config(cls, chrome_data: Dict[str, Any]) -> ChromeConfig:
        """Parse Chrome configuration with defaults."""
        return ChromeConfig(
            chrome_driver_path=chrome_data.get("chrome_driver_path"),
            headless=chrome_data.get("headless", True),
            window_size=chrome_data.get("window_size", {"width": 1280, "height": 720}),
            implicit_wait=chrome_data.get("implicit_wait", 3),
            user_agent=chrome_data.get(
                "user_agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        )
    
    @classmethod
    def _parse_deployment_config(cls, deploy_data: Dict[str, Any]) -> DeploymentConfig:
        """Parse deployment configuration with defaults."""
        return DeploymentConfig(
            environment=deploy_data.get("environment", "development"),
            log_level=deploy_data.get("log_level", "INFO"),
            enable_screenshots=deploy_data.get("enable_screenshots", False),
            delay_between_searches=deploy_data.get("delay_between_searches", 2),
            enable_metrics_collection=deploy_data.get("enable_metrics_collection", False)
        )


# Backward compatibility functions
def load_config_for_site(site_name: str, config_path: Optional[str] = None) -> AppConfig:
    """Backward compatibility function for loading site configuration.
    
    Args:
        site_name: Name of the site to load configuration for
        config_path: Optional path to config file
        
    Returns:
        Complete application configuration
    """
    return ConfigLoader.load_config_for_site(site_name, config_path)


def get_available_sites(config_path: Optional[str] = None) -> List[str]:
    """Get available sites from configuration.
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        List of available site names
    """
    loader = ConfigLoader(config_path)
    return loader.get_available_sites()


def validate_site_config(site_name: str, config_path: Optional[str] = None) -> List[str]:
    """Validate site configuration.
    
    Args:
        site_name: Site to validate
        config_path: Optional path to config file
        
    Returns:
        List of validation errors
    """
    loader = ConfigLoader(config_path)
    return loader.validate_config(site_name)