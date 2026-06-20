"""Main web scraper orchestration module."""

import time
import logging
from typing import List, Dict, Any, Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException

from config.config_models import SiteConfig, ScrapingConfig
from .element_finder import ElementFinder
from .page_interaction_handler import PageInteractionHandler
from .data_extractor import DataExtractor, ScrapingResult


logger = logging.getLogger(__name__)


class NoResultsChecker:
    """Handles checking for 'no results' conditions."""
    
    def __init__(self, element_finder: ElementFinder):
        """Initialize with element finder.
        
        Args:
            element_finder: ElementFinder instance for element location
        """
        self.element_finder = element_finder
    
    def check_no_results(self, search_term: str, scraping_config: ScrapingConfig) -> bool:
        """Check if the search returned no results using configured selectors.
        
        Args:
            search_term: The search term that was used
            scraping_config: Configuration containing no-results selectors
            
        Returns:
            True if no results were found, False otherwise
        """
        try:
            no_results_elements = self.element_finder.find_elements_with_selectors(
                scraping_config.no_results_selectors
            )
            
            for element in no_results_elements:
                if element.is_displayed():
                    element_text = element.text.lower()
                    
                    # Check for specific no-results indicators
                    no_results_indicators = [
                        "0 results",
                        "no results",
                        "returned 0 results",
                        "no items found",
                        "no products found",
                        f"results for \"{search_term.lower()}\"" and "0" in element_text
                    ]
                    
                    for indicator in no_results_indicators:
                        if indicator and indicator in element_text:
                            logger.info(f"No results detected: {element_text.strip()}")
                            return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking for no results: {e}")
            return False


class SearchHandler:
    """Handles search operations on web pages."""
    
    def __init__(
        self,
        driver: WebDriver,
        element_finder: ElementFinder,
        page_handler: PageInteractionHandler
    ):
        """Initialize search handler.
        
        Args:
            driver: Selenium WebDriver instance
            element_finder: ElementFinder instance
            page_handler: PageInteractionHandler instance
        """
        self.driver = driver
        self.element_finder = element_finder
        self.page_handler = page_handler
    
    def perform_search(self, search_term: str, scraping_config: ScrapingConfig) -> bool:
        """Perform search operation on the current page.
        
        Args:
            search_term: Term to search for
            scraping_config: Configuration for search elements
            
        Returns:
            True if search was performed successfully, False otherwise
        """
        try:
            # Find and fill search input
            if not self._enter_search_term(search_term, scraping_config):
                return False
            
            # Find and click search button or use Enter key
            if not self._trigger_search(scraping_config):
                return False
            
            logger.info(f"Search performed successfully for: {search_term}")
            return True
            
        except Exception as e:
            logger.error(f"Error performing search for '{search_term}': {e}")
            return False
    
    def _enter_search_term(self, search_term: str, scraping_config: ScrapingConfig) -> bool:
        """Enter search term into search input field."""
        logger.debug("Looking for search input...")
        
        search_input = self.element_finder.find_element_with_selectors(
            scraping_config.search_input_selectors,
            wait_for_clickable=True,
            timeout=scraping_config.wait_timeout
        )
        
        if not search_input:
            logger.error("Could not find search input with any selector")
            self._debug_available_inputs()
            return False
        
        try:
            search_input.clear()
            search_input.send_keys(search_term)
            logger.info(f"Entered search term: {search_term}")
            return True
        except Exception as e:
            logger.error(f"Error entering search term: {e}")
            return False
    
    def _trigger_search(self, scraping_config: ScrapingConfig) -> bool:
        """Trigger search using button click or Enter key."""
        logger.debug("Looking for search button...")
        
        # Handle any modals that might interfere
        self.page_handler.handle_modal_popups()
        
        search_button = self.element_finder.find_element_with_selectors(
            scraping_config.search_button_selectors,
            by=By.XPATH,
            timeout=5
        )
        
        if search_button:
            try:
                if self.page_handler.click_element_safely(search_button):
                    logger.info("Clicked search button successfully")
                    return True
            except Exception as e:
                logger.warning(f"Error clicking search button: {e}")
        
        # Fallback: try Enter key
        return self._fallback_enter_key()
    
    def _fallback_enter_key(self) -> bool:
        """Use Enter key as fallback search method."""
        try:
            # Find search input again and press Enter
            search_input = self.driver.find_element(By.TAG_NAME, "input")
            search_input.send_keys(Keys.RETURN)
            logger.info("Used Enter key as search fallback")
            return True
        except Exception as e:
            logger.error(f"Enter key fallback failed: {e}")
            return False
    
    def _debug_available_inputs(self) -> None:
        """Debug method to show available input elements."""
        try:
            inputs = self.driver.find_elements(By.TAG_NAME, "input")
            logger.debug(f"Found {len(inputs)} input elements on page")
            for i, inp in enumerate(inputs[:5]):  # Show first 5
                input_type = inp.get_attribute('type')
                placeholder = inp.get_attribute('placeholder')
                name = inp.get_attribute('name')
                id_attr = inp.get_attribute('id')
                logger.debug(
                    f"Input {i}: type='{input_type}', placeholder='{placeholder}', "
                    f"name='{name}', id='{id_attr}'"
                )
        except Exception as e:
            logger.warning(f"Error debugging inputs: {e}")


class WebScraper:
    """Main web scraper class that orchestrates the scraping process."""
    
    def __init__(self, driver: WebDriver):
        """Initialize web scraper.
        
        Args:
            driver: Selenium WebDriver instance
        """
        self.driver = driver
        self.element_finder = ElementFinder(driver)
        self.page_handler = PageInteractionHandler(driver, self.element_finder)
        self.data_extractor = DataExtractor(self.element_finder)
        self.search_handler = SearchHandler(driver, self.element_finder, self.page_handler)
        self.no_results_checker = NoResultsChecker(self.element_finder)
    
    def scrape_site(
        self,
        search_term: str,
        site_config: SiteConfig,
        debug_mode: bool = False
    ) -> List[Dict[str, Any]]:
        """Perform a complete scraping operation for a search term.
        
        Args:
            search_term: Term to search for
            site_config: Site configuration containing all scraping parameters
            debug_mode: Whether to enable debug mode
            
        Returns:
            List of dictionaries containing scraped product data
        """
        results = []
        scraping_config = site_config.scraping_config
        
        try:
            # Setup page load timeout
            self.driver.set_page_load_timeout(scraping_config.page_load_timeout)
            
            # Navigate to the target URL
            if not self._navigate_to_site(site_config.target_url):
                return results
            
            # Handle initial page setup
            self._setup_page()
            
            # Perform search
            if not self.search_handler.perform_search(search_term, scraping_config):
                return results
            
            # Wait for results and check for no-results condition
            if not self._wait_for_search_results(search_term, scraping_config):
                return results
            
            # Take screenshot after search results are loaded
            
            safe_search_term = search_term.replace(" ", "_").replace("/", "_")
            screenshot_filename = f"search_results_{safe_search_term}"
            self.page_handler.take_screenshot(
                screenshot_filename, 
                f"Search results for '{search_term}'"
            )
                
            # Extract product data
            results = self._extract_product_data(scraping_config, debug_mode)

            self._dump_results_to_file(results, search_term, site_config.site_name)
            
            logger.info(f"Successfully extracted {len(results)} products for '{search_term}'")
            
        except TimeoutException:
            logger.error(f"Timeout during search for '{search_term}'")
        except Exception as e:
            logger.error(f"Unexpected error during scraping for '{search_term}': {e}")
            if debug_mode:
                import traceback
                traceback.print_exc()
        
        return results
    
    def _navigate_to_site(self, target_url: str) -> bool:
        """Navigate to the target URL.
        
        Args:
            target_url: URL to navigate to
            
        Returns:
            True if navigation was successful, False otherwise
        """
        try:
            logger.info(f"Navigating to {target_url}")
            self.driver.get(target_url)
            logger.info(f"Successfully navigated to {target_url}")
            logger.debug(f"Page title: {self.driver.title}")
            return True
        except Exception as e:
            logger.error(f"Error loading page: {e}")
            return False
    
    def _setup_page(self) -> None:
        """Setup page after navigation."""
        # Wait for page to load completely
        self.page_handler.wait_for_page_load(10)
        
        # Handle modal popups that might interfere
        logger.info("Checking for modal popups...")
        self.page_handler.handle_modal_popups()
        
        # Additional wait for dynamic content
        time.sleep(3)
    
    def _wait_for_search_results(self, search_term: str, scraping_config: ScrapingConfig) -> bool:
        """Wait for search results to load and check for no-results condition.
        
        Args:
            search_term: The search term used
            scraping_config: Scraping configuration
            
        Returns:
            True if results are available, False if no results or error
        """
        logger.info("Waiting for search results...")
        
        # Wait for search to process
        time.sleep(3)
        
        # Handle any new modals
        self.page_handler.handle_modal_popups()
        
        # Wait for page to finish loading
        self.page_handler.wait_for_page_load(10)
        
        # Check for no results first
        if self.no_results_checker.check_no_results(search_term, scraping_config):
            logger.info(f"Search for '{search_term}' returned no results")
            return False
        
        # Look for product cards
        product_card = self.element_finder.find_element_with_selectors(
            scraping_config.product_card_selectors,
            timeout=10
        )
        
        if not product_card:
            logger.error("Could not find product cards with any selector")
            logger.debug(f"Current URL: {self.driver.current_url}")
            
            # Double-check for no results message after waiting
            if self.no_results_checker.check_no_results(search_term, scraping_config):
                logger.info(f"Confirmed: Search for '{search_term}' returned no results")
                return False
            
            return False
        
        logger.info("Search results page loaded")
        return True
    
    def _extract_product_data(
        self,
        scraping_config: ScrapingConfig,
        debug_mode: bool
    ) -> List[Dict[str, Any]]:
        """Extract data from all product cards.
        
        Args:
            scraping_config: Scraping configuration
            debug_mode: Whether debug mode is enabled
            
        Returns:
            List of extracted product data dictionaries
        """
        results = []
        
        # Find all product cards
        logger.debug(f"Looking for product cards with selectors: {scraping_config.product_card_selectors}")
        
        product_cards = self.element_finder.find_elements_with_selectors(
            scraping_config.product_card_selectors
        )
        
        if not product_cards:
            logger.warning("No product cards found")
            return results
        
        logger.info(f"Found {len(product_cards)} product cards")
        
        # Extract data from each card
        max_results = min(len(product_cards), scraping_config.max_results_per_query)
        logger.info(f"Processing {max_results} product cards...")
        
        for i, card in enumerate(product_cards[:max_results]):
            logger.debug(f"Scraping product {i+1} of {max_results}")
            
            try:
                result = self.data_extractor.extract_product_data(
                    card, scraping_config, i+1, debug_mode
                )
                
                if result.is_valid():
                    results.append(result.to_dict())
                    title_preview = (
                        result.title[:50] + '...' if len(result.title) > 50 else result.title
                    )
                    logger.info(f"-- Scraped Product {i+1}: {title_preview}")
                else:
                    logger.debug(f"-- Skipped Product {i+1}: No meaningful data found")
                    if debug_mode:
                        logger.debug(f"   Data: {result.to_dict()}")
                        
            except Exception as e:
                logger.error(f"Error extracting data from product {i+1}: {e}")
                continue
        
        return results
    
    def _dump_results_to_file(self, results: List[Dict[str, Any]], search_term: str, site_name: str) -> None:
        """
        Dump scraping results to a timestamped file.
        
        Args:
            results: List of scraped product data
            search_term: The search term used
            site_name: Name of the site being scraped
        """
        import os
        import json
        from datetime import datetime
        
        try:
            # Create debug directory if it doesn't exist
            debug_dir = "analysis_result"
            os.makedirs(debug_dir, exist_ok=True)
            
            # Generate timestamp
            now = datetime.now().strftime("%Y%m%d-%H%M%S")
            
            # Create safe site name and search term
            safe_site_name = site_name.lower().replace(' ', '').replace('-', '')
            safe_search_term = search_term.replace(" ", "_").replace("/", "_").replace("\\", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace('"', "_").replace("<", "_").replace(">", "_").replace("|", "_")
            
            # Create filename
            filename = f"{safe_site_name}_scrape_results-{safe_search_term}-{now}.json"
            filepath = os.path.join(debug_dir, filename)
            
            # Create results data structure
            results_data = {
                "timestamp": datetime.now().isoformat(),
                "site_name": site_name,
                "search_term": search_term,
                "results_count": len(results),
                "results": results
            }
            
            # Write to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"[DEBUG] Scraping results dumped to: {filepath}")
            
        except Exception as e:
            logger.warning(f"Failed to dump results to file: {e}")