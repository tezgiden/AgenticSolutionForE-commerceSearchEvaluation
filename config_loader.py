# Configuration Loader Module for Multi-Site Deployment

import json
import os
import sys
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class ScrapingConfig:
    """Configuration for web scraping parameters"""
    search_input_selectors: List[str]
    search_button_selectors: List[str] 
    product_card_selectors: List[str]
    product_link_selector: str
    product_title_selectors: List[str]
    product_sku_selectors: List[str]
    product_price_selectors: List[str]
    product_quantity_selectors: List[str]
    no_results_selectors: List[str]
    max_results_per_query: int
    wait_timeout: int
    page_load_timeout: int

@dataclass
class OutputConfig:
    """Configuration for output files"""
    output_file: str
    detailed_output_file: str

@dataclass
class SiteConfig:
    """Configuration for a specific site"""
    site_name: str
    target_url: str
    search_tasks: List[Dict[str, str]]
    inventory_test_cases: List[Dict[str, str]]
    scraping_config: ScrapingConfig
    output_config: OutputConfig

@dataclass
class LLMConfig:
    """Configuration for LLM/Ollama settings"""
    ollama_api_endpoint: str
    default_model: str
    timeout: int
    max_retries: int

@dataclass
class EvaluationConfig:
    """Configuration for evaluation parameters"""
    enable_inventory_ranking: bool
    enable_detailed_analysis: bool
    inventory_weight_factor: float
    apply_post_ranking: bool
    low_stock_threshold: int

@dataclass
class ChromeConfig:
    """Configuration for Chrome browser settings"""
    chrome_driver_path: Optional[str]
    headless: bool
    window_size: Dict[str, int]
    implicit_wait: int
    user_agent: str

@dataclass
class DeploymentConfig:
    """Configuration for deployment settings"""
    environment: str
    log_level: str
    enable_screenshots: bool
    delay_between_searches: int
    enable_metrics_collection: bool

@dataclass
class AppConfig:
    """Main application configuration"""
    site_config: SiteConfig
    llm_config: LLMConfig
    evaluation_config: EvaluationConfig
    chrome_config: ChromeConfig
    deployment_config: DeploymentConfig

class ConfigLoader:
    """Loads and manages application configuration"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self._raw_config = None
        self.load_config()
    
    def load_config(self) -> None:
        """Load configuration from JSON file"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r') as f:
                self._raw_config = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise Exception(f"Error loading configuration: {e}")
    
    def get_available_sites(self) -> List[str]:
        """Get list of available site configurations"""
        return list(self._raw_config.get("site_configs", {}).keys())
    
    def get_site_config(self, site_key: str) -> AppConfig:
        """
        Get complete configuration for a specific site
        
        Args:
            site_key: The site configuration key (e.g., 'truckpro', 'tundrafmp')
            
        Returns:
            AppConfig object with all configuration settings
        """
        if site_key not in self._raw_config.get("site_configs", {}):
            available_sites = self.get_available_sites()
            raise ValueError(f"Site '{site_key}' not found. Available sites: {available_sites}")
        
        site_data = self._raw_config["site_configs"][site_key]
        
        # Create ScrapingConfig
        scraping_data = site_data["scraping_config"]
        scraping_config = ScrapingConfig(
            search_input_selectors=scraping_data["search_input_selectors"],
            search_button_selectors=scraping_data["search_button_selectors"],
            product_card_selectors=scraping_data["product_card_selectors"],
            product_link_selector=scraping_data["product_link_selector"],
            product_title_selectors=scraping_data["product_title_selectors"],
            product_sku_selectors=scraping_data["product_sku_selectors"],
            product_price_selectors=scraping_data["product_price_selectors"],
            product_quantity_selectors=scraping_data["product_quantity_selectors"],
            no_results_selectors=scraping_data["no_results_selectors"],
            max_results_per_query=scraping_data["max_results_per_query"],
            wait_timeout=scraping_data["wait_timeout"],
            page_load_timeout=scraping_data["page_load_timeout"]
        )
        
        # Create OutputConfig
        output_data = site_data["output_config"]
        output_config = OutputConfig(
            output_file=output_data["output_file"],
            detailed_output_file=output_data["detailed_output_file"]
        )
        
        # Create SiteConfig
        site_config = SiteConfig(
            site_name=site_data["site_name"],
            target_url=site_data["target_url"],
            search_tasks=site_data["search_tasks"],
            inventory_test_cases=site_data["inventory_test_cases"],
            scraping_config=scraping_config,
            output_config=output_config
        )
        
        # Create LLMConfig
        llm_data = self._raw_config["llm_config"]
        llm_config = LLMConfig(
            ollama_api_endpoint=llm_data["ollama_api_endpoint"],
            default_model=llm_data["default_model"],
            timeout=llm_data["timeout"],
            max_retries=llm_data["max_retries"]
        )
        
        # Create EvaluationConfig
        eval_data = self._raw_config["evaluation_config"]
        evaluation_config = EvaluationConfig(
            enable_inventory_ranking=eval_data["enable_inventory_ranking"],
            enable_detailed_analysis=eval_data["enable_detailed_analysis"],
            inventory_weight_factor=eval_data["inventory_weight_factor"],
            apply_post_ranking=eval_data["apply_post_ranking"],
            low_stock_threshold=eval_data["low_stock_threshold"]
        )
        
        # Create ChromeConfig
        chrome_data = self._raw_config["chrome_config"]
        chrome_config = ChromeConfig(
            chrome_driver_path=chrome_data["chrome_driver_path"],
            headless=chrome_data["headless"],
            window_size=chrome_data["window_size"],
            implicit_wait=chrome_data["implicit_wait"],
            user_agent=chrome_data["user_agent"]
        )
        
        # Create DeploymentConfig
        deploy_data = self._raw_config["deployment_config"]
        deployment_config = DeploymentConfig(
            environment=deploy_data["environment"],
            log_level=deploy_data["log_level"],
            enable_screenshots=deploy_data["enable_screenshots"],
            delay_between_searches=deploy_data["delay_between_searches"],
            enable_metrics_collection=deploy_data["enable_metrics_collection"]
        )
        
        return AppConfig(
            site_config=site_config,
            llm_config=llm_config,
            evaluation_config=evaluation_config,
            chrome_config=chrome_config,
            deployment_config=deployment_config
        )
    
    def override_config(self, site_key: str, overrides: Dict[str, Any]) -> AppConfig:
        """
        Get configuration with runtime overrides
        
        Args:
            site_key: The site configuration key
            overrides: Dictionary of configuration overrides
            
        Returns:
            AppConfig with applied overrides
        """
        config = self.get_site_config(site_key)
        
        # Apply overrides (simple implementation, can be enhanced)
        if "model" in overrides:
            config.llm_config.default_model = overrides["model"]
        
        if "enable_inventory_ranking" in overrides:
            config.evaluation_config.enable_inventory_ranking = overrides["enable_inventory_ranking"]
        
        if "max_results" in overrides:
            config.site_config.scraping_config.max_results_per_query = overrides["max_results"]
        
        if "headless" in overrides:
            config.chrome_config.headless = overrides["headless"]
        
        if "output_file" in overrides:
            config.site_config.output_config.output_file = overrides["output_file"]
            
        return config
    
    def validate_config(self, site_key: str) -> List[str]:
        """
        Validate configuration for a site
        
        Args:
            site_key: The site configuration key
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        try:
            config = self.get_site_config(site_key)
            
            # Validate required fields
            if not config.site_config.target_url:
                errors.append("target_url is required")
            
            if not config.site_config.search_tasks:
                errors.append("search_tasks cannot be empty")
            
            if not config.site_config.scraping_config.search_input_selectors:
                errors.append("search_input_selectors cannot be empty")
            
            if not config.llm_config.default_model:
                errors.append("default_model is required")
            
            # Validate ranges
            if config.evaluation_config.inventory_weight_factor < 0 or config.evaluation_config.inventory_weight_factor > 1:
                errors.append("inventory_weight_factor must be between 0.0 and 1.0")
            
            if config.site_config.scraping_config.max_results_per_query <= 0:
                errors.append("max_results_per_query must be positive")
            
            if config.site_config.scraping_config.wait_timeout <= 0:
                errors.append("wait_timeout must be positive")
                
        except Exception as e:
            errors.append(f"Configuration validation error: {e}")
        
        return errors

# Convenience functions for backward compatibility and easy usage
def load_config_for_site(site_key: str, config_path: str = "config.json") -> AppConfig:
    """
    Load configuration for a specific site
    
    Args:
        site_key: Site configuration key
        config_path: Path to configuration file
        
    Returns:
        AppConfig object
    """
    loader = ConfigLoader(config_path)
    return loader.get_site_config(site_key)

def get_available_sites(config_path: str = "config.json") -> List[str]:
    """
    Get list of available site configurations
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        List of available site keys
    """
    loader = ConfigLoader(config_path)
    return loader.get_available_sites()

def validate_site_config(site_key: str, config_path: str = "config.json") -> List[str]:
    """
    Validate configuration for a site
    
    Args:
        site_key: Site configuration key
        config_path: Path to configuration file
        
    Returns:
        List of validation errors
    """
    loader = ConfigLoader(config_path)
    return loader.validate_config(site_key)

# Example usage and testing
if __name__ == "__main__":
    # Example usage
    try:
        # Load configuration
        loader = ConfigLoader("config.json")
        
        # Show available sites
        sites = loader.get_available_sites()
        print(f"Available sites: {sites}")
        
        # Load configuration for a specific site
        if sites:
            site_key = sites[0]  # Use first available site
            print(f"\nLoading configuration for: {site_key}")
            
            config = loader.get_site_config(site_key)
            print(f"Site: {config.site_config.site_name}")
            print(f"URL: {config.site_config.target_url}")
            print(f"Search tasks: {len(config.site_config.search_tasks)}")
            print(f"Model: {config.llm_config.default_model}")
            print(f"Inventory ranking: {config.evaluation_config.enable_inventory_ranking}")
            print(f"Max results: {config.site_config.scraping_config.max_results_per_query}")
            
            # Validate configuration
            errors = loader.validate_config(site_key)
            if errors:
                print(f"Configuration errors: {errors}")
            else:
                print("Configuration is valid!")
                
            # Test overrides
            print(f"\nTesting configuration overrides...")
            overridden_config = loader.override_config(site_key, {
                "model": "llama3",
                "max_results": 20,
                "headless": False
            })
            print(f"Overridden model: {overridden_config.llm_config.default_model}")
            print(f"Overridden max results: {overridden_config.site_config.scraping_config.max_results_per_query}")
            print(f"Overridden headless: {overridden_config.chrome_config.headless}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)