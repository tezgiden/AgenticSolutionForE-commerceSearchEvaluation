"""Main scraper facade providing backward compatibility and easy usage."""

import json
import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

from config.config_models import SiteConfig, ChromeConfig
from config.config_loader import ConfigLoader
from .web_driver_manager import WebDriverManager
from .web_scraper import WebScraper


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ScraperFacade:
    """Main facade class for web scraping operations."""
    
    def __init__(self, chrome_config: Optional[ChromeConfig] = None):
        """Initialize scraper facade.
        
        Args:
            chrome_config: Optional Chrome configuration (uses default if None)
        """
        self.chrome_config = chrome_config or ConfigLoader.load_default_chrome_config()
        self.driver_manager = WebDriverManager(self.chrome_config)
        self._driver = None
        self._scraper = None
    
    @contextmanager
    def get_scraper(self):
        """Context manager for scraper usage.
        
        Yields:
            WebScraper instance with managed driver lifecycle
        """
        driver = None
        try:
            driver = self.driver_manager.create_driver()
            if not driver:
                raise RuntimeError("Failed to create WebDriver")
            
            scraper = WebScraper(driver)
            yield scraper
            
        finally:
            if driver:
                self.driver_manager.quit_driver()
    
    def scrape_with_config(
        self,
        search_terms: List[str],
        site_config: SiteConfig,
        debug_mode: bool = False,
        delay_between_searches: int = 2
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Scrape multiple search terms using provided configuration.
        
        Args:
            search_terms: List of search terms to scrape
            site_config: Site configuration to use
            debug_mode: Whether to enable debug mode
            delay_between_searches: Delay between searches in seconds
            
        Returns:
            Dictionary mapping search terms to their results
        """
        all_results = {}
        
        with self.get_scraper() as scraper:
            for search_term in search_terms:
                logger.info(f"Starting scrape for: {search_term}")
                
                try:
                    results = scraper.scrape_site(search_term, site_config, debug_mode)
                    all_results[search_term] = results
                    logger.info(f"Finished scrape for: {search_term}, Found {len(results)} results")
                    
                except Exception as e:
                    logger.error(f"Error scraping '{search_term}': {e}")
                    all_results[search_term] = []
                
                # Delay between searches to be respectful
                if search_term != search_terms[-1]:  # Don't delay after last search
                    time.sleep(delay_between_searches)
        
        return all_results
    
    def scrape_from_config_file(
        self,
        search_terms: List[str],
        site_name: str,
        config_path: Optional[str] = None,
        debug_mode: bool = False
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Scrape using configuration loaded from file.
        
        Args:
            search_terms: List of search terms to scrape
            site_name: Name of the site in configuration
            config_path: Optional path to config file
            debug_mode: Whether to enable debug mode
            
        Returns:
            Dictionary mapping search terms to their results
        """
        try:
            app_config = ConfigLoader.load_config_for_site(site_name, config_path)
            delay = app_config.deployment_config.delay_between_searches
            
            return self.scrape_with_config(
                search_terms, 
                app_config.site_config, 
                debug_mode,
                delay
            )
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return {}
    
    def save_results(
        self,
        results: Dict[str, List[Dict[str, Any]]],
        output_file: Optional[str] = None
    ) -> str:
        """Save scraping results to JSON file.
        
        Args:
            results: Results dictionary to save
            output_file: Optional output filename (generates default if None)
            
        Returns:
            Path to the saved file
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"scraped_results_{timestamp}.json"
        
        try:
            with open(output_file, "w", encoding='utf-8') as f:
                json.dump(results, f, indent=4, ensure_ascii=False)
            logger.info(f"Results saved to {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"Error saving results: {e}")
            raise


# Backward compatibility functions
def setup_driver_with_config(chrome_config: ChromeConfig):
    """Backward compatibility function for driver setup.
    
    Args:
        chrome_config: Chrome configuration
        
    Returns:
        WebDriver instance or None if setup failed
    """
    manager = WebDriverManager(chrome_config)
    return manager.create_driver()


def setup_driver():
    """Backward compatibility function with default config.
    
    Returns:
        WebDriver instance or None if setup failed
    """
    chrome_config = ConfigLoader.load_default_chrome_config()
    return setup_driver_with_config(chrome_config)


def scrape_site_with_config(
    driver,
    search_term: str,
    site_config: SiteConfig,
    debug_mode: bool = False
) -> List[Dict[str, Any]]:
    """Backward compatibility function for site scraping.
    
    Args:
        driver: Selenium WebDriver instance
        search_term: Search term to scrape
        site_config: Site configuration
        debug_mode: Whether to enable debug mode
        
    Returns:
        List of scraped product data
    """
    scraper = WebScraper(driver)
    return scraper.scrape_site(search_term, site_config, debug_mode)


def scrape_tundra(driver, search_term: str) -> List[Dict[str, Any]]:
    """Backward compatibility function for TruckPro scraping.
    
    Args:
        driver: Selenium WebDriver instance
        search_term: Search term to scrape
        
    Returns:
        List of scraped product data
    """
    site_config = ConfigLoader.create_default_truckpro_config()
    return scrape_site_with_config(driver, search_term, site_config)


# Main execution example
def main():
    """Main execution function demonstrating usage."""
    try:
        # Example using configuration file
        facade = ScraperFacade()
        
        search_queries = ["gasket", "BK608", "brake pads", "nonexistent_part"]
        
        # Option 1: Using configuration file
        results = facade.scrape_from_config_file(
            search_queries, 
            "truckpro",
            debug_mode=False
        )
        
        # Option 2: Using direct configuration (commented out)
        # site_config = ConfigLoader.create_default_truckpro_config()
        # results = facade.scrape_with_config(search_queries, site_config)
        
        # Save results
        output_file = facade.save_results(results)
        
        # Print summary
        print(f"\n=== SCRAPING SUMMARY ===")
        for query, query_results in results.items():
            print(f"{query}: {len(query_results)} results")
        print(f"Results saved to: {output_file}")
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")


if __name__ == "__main__":
    main()