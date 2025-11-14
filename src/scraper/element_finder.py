"""Element finding utilities for web scraping."""

import logging
from typing import List, Optional, Union
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


logger = logging.getLogger(__name__)


class ElementFinder:
    """Handles finding web elements using multiple selector strategies."""
    
    def __init__(self, driver: WebDriver, default_timeout: int = 10):
        """Initialize element finder.
        
        Args:
            driver: Selenium WebDriver instance
            default_timeout: Default timeout for element searches
        """
        self.driver = driver
        self.default_timeout = default_timeout
    
    def find_element_with_selectors(
        self,
        selectors: Union[str, List[str]],
        by: By = By.CSS_SELECTOR,
        timeout: Optional[int] = None,
        wait_for_clickable: bool = False,
        parent_element: Optional[WebElement] = None
    ) -> Optional[WebElement]:
        """Find element using multiple selectors as fallbacks.
        
        Args:
            selectors: Single selector string or list of selectors to try
            by: Selenium By strategy (default: CSS_SELECTOR)
            timeout: Custom timeout (uses default if None)
            wait_for_clickable: Wait for element to be clickable vs just present
            parent_element: Search within this element instead of entire page
            
        Returns:
            Found WebElement or None if not found with any selector
        """
        if isinstance(selectors, str):
            selectors = [selectors]
        
        timeout = timeout or self.default_timeout
        search_context = parent_element or self.driver
        
        for selector in selectors:
            try:
                if parent_element:
                    # For parent element searches, use direct find
                    if wait_for_clickable:
                        # Can't use WebDriverWait with parent element for clickable
                        element = search_context.find_element(by, selector)
                        if element.is_enabled() and element.is_displayed():
                            logger.debug(f"Found clickable element with selector: {selector}")
                            return element
                    else:
                        element = search_context.find_element(by, selector)
                        logger.debug(f"Found element with selector: {selector}")
                        return element
                else:
                    # For driver searches, use WebDriverWait
                    condition = (
                        EC.element_to_be_clickable((by, selector))
                        if wait_for_clickable
                        else EC.presence_of_element_located((by, selector))
                    )
                    
                    element = WebDriverWait(search_context, timeout).until(condition)
                    logger.debug(f"Found element with selector: {selector}")
                    return element
                    
            except (TimeoutException, NoSuchElementException):
                logger.debug(f"Selector failed: {selector}")
                continue
            except Exception as e:
                logger.warning(f"Error with selector {selector}: {e}")
                continue
        
        logger.warning(f"Could not find element with any of the provided selectors: {selectors}")
        return None
    
    def find_elements_with_selectors(
        self,
        selectors: Union[str, List[str]],
        by: By = By.CSS_SELECTOR,
        parent_element: Optional[WebElement] = None
    ) -> List[WebElement]:
        """Find multiple elements using selectors as fallbacks.
        
        Args:
            selectors: Single selector string or list of selectors to try
            by: Selenium By strategy (default: CSS_SELECTOR)
            parent_element: Search within this element instead of entire page
            
        Returns:
            List of found WebElements (empty if none found)
        """
        if isinstance(selectors, str):
            selectors = [selectors]
        
        search_context = parent_element or self.driver
        
        for selector in selectors:
            try:
                elements = search_context.find_elements(by, selector)
                if elements:
                    logger.debug(f"Found {len(elements)} elements with selector: {selector}")
                    return elements
            except Exception as e:
                logger.warning(f"Error with selector {selector}: {e}")
                continue
        
        logger.debug(f"Could not find elements with any selector: {selectors}")
        return []
    
    def check_element_exists(
        self,
        selectors: Union[str, List[str]],
        by: By = By.CSS_SELECTOR,
        parent_element: Optional[WebElement] = None
    ) -> bool:
        """Check if element exists without waiting.
        
        Args:
            selectors: Single selector string or list of selectors to try
            by: Selenium By strategy (default: CSS_SELECTOR)
            parent_element: Search within this element instead of entire page
            
        Returns:
            True if element exists, False otherwise
        """
        element = self.find_element_with_selectors(
            selectors=selectors,
            by=by,
            timeout=1,  # Quick check
            parent_element=parent_element
        )
        return element is not None
    
    def wait_for_element_to_disappear(
        self,
        selectors: Union[str, List[str]],
        by: By = By.CSS_SELECTOR,
        timeout: Optional[int] = None
    ) -> bool:
        """Wait for element to disappear from the page.
        
        Args:
            selectors: Single selector string or list of selectors to check
            by: Selenium By strategy (default: CSS_SELECTOR)
            timeout: Custom timeout (uses default if None)
            
        Returns:
            True if element disappeared, False if still present after timeout
        """
        if isinstance(selectors, str):
            selectors = [selectors]
        
        timeout = timeout or self.default_timeout
        
        for selector in selectors:
            try:
                WebDriverWait(self.driver, timeout).until(
                    EC.invisibility_of_element_located((by, selector))
                )
                logger.debug(f"Element disappeared: {selector}")
                return True
            except TimeoutException:
                continue
            except Exception as e:
                logger.warning(f"Error waiting for element to disappear {selector}: {e}")
                continue
        
        return False