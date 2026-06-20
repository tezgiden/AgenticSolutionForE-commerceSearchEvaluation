"""Page interaction utilities for web scraping."""

import os
import time
import logging
from datetime import datetime
from typing import List, Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .element_finder import ElementFinder


logger = logging.getLogger(__name__)


class PageInteractionHandler:
    """Handles common page interactions and utilities."""
    
    # Modal selectors for common popup patterns
    MODAL_SELECTORS = [
        "div.modal.show",
        "div.modal-wrapper.show", 
        "div[role='dialog'][aria-modal='true']",
        ".newsletter-modal.show",
        ".popup-modal.show",
        "#cookie-banner",
        ".cookie-consent",
        ".gdpr-banner",
        ".overlay.show",
        ".modal-overlay.show"
    ]
    
    # Close button selectors for modals
    CLOSE_BUTTON_SELECTORS = [
        "button.close",
        "button[aria-label='Close']",
        "button[data-dismiss='modal']",
        ".modal-close",
        ".close-button",
        "[data-close-modal]",
        "button.btn-close",
        "span.close",
        ".fa-times",
        ".fa-close"
    ]
    
    # Loading indicator selectors
    LOADING_SELECTORS = [
        ".loading",
        ".spinner", 
        ".loader",
        "[data-loading='true']",
        ".loading-overlay"
    ]
    
    def __init__(self, driver: WebDriver, element_finder: ElementFinder):
        """Initialize page interaction handler.
        
        Args:
            driver: Selenium WebDriver instance
            element_finder: ElementFinder instance for element location
        """
        self.driver = driver
        self.element_finder = element_finder
    
    def wait_for_page_load(self, timeout: int = 10) -> None:
        """Wait for page to fully load and handle loading states.
        
        Args:
            timeout: Maximum time to wait for page load
        """
        try:
            # Wait for document ready state
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # Wait for loading indicators to disappear
            for selector in self.LOADING_SELECTORS:
                self.element_finder.wait_for_element_to_disappear(
                    selector, timeout=3
                )
            
            logger.debug("Page load completed")
            
        except Exception as e:
            logger.warning(f"Page load wait issue: {e}")
    
    def handle_modal_popups(self) -> bool:
        """Handle common modal popups that might interfere with scraping.
        
        Returns:
            True if any modal was handled, False otherwise
        """
        try:
            # Find visible modals
            for modal_selector in self.MODAL_SELECTORS:
                modals = self.element_finder.find_elements_with_selectors(modal_selector)
                
                for modal in modals:
                    if not modal.is_displayed():
                        continue
                    
                    logger.info(f"Found visible modal: {modal_selector}")
                    
                    # Try to find and click close button within modal
                    if self._close_modal_with_button(modal):
                        return True
                    
                    # Try to hide modal with JavaScript
                    if self._hide_modal_with_js(modal):
                        return True
            
            # Try pressing Escape key as fallback
            self._try_escape_key()
            return False
            
        except Exception as e:
            logger.error(f"Error handling modals: {e}")
            return False
    
    def take_screenshot(self, filename: str, description: str = "") -> Optional[str]:
        """Take a screenshot for debugging.
        
        Args:
            filename: Base filename (without extension)
            description: Optional description for logging
            
        Returns:
            Path to saved screenshot or None if failed
        """
        try:
            screenshot_dir = "debug_screenshots"
            os.makedirs(screenshot_dir, exist_ok=True)
            
            # Add timestamp to filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(screenshot_dir, f"{filename}_{timestamp}.png")
            
            self.driver.save_screenshot(filepath)
            logger.info(f"Screenshot saved: {filepath} ({description})")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return None
    
    def scroll_to_element(self, element) -> None:
        """Scroll element into view.
        
        Args:
            element: WebElement to scroll to
        """
        try:
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)  # Brief pause for scroll to complete
        except Exception as e:
            logger.warning(f"Error scrolling to element: {e}")
    
    def click_element_safely(self, element) -> bool:
        """Safely click an element with multiple fallback strategies.
        
        Args:
            element: WebElement to click
            
        Returns:
            True if click was successful, False otherwise
        """
        try:
            # Try normal click first
            if element.is_enabled() and element.is_displayed():
                element.click()
                return True
        except Exception:
            pass
        
        try:
            # Try JavaScript click as fallback
            self.driver.execute_script("arguments[0].click();", element)
            return True
        except Exception as e:
            logger.warning(f"Failed to click element: {e}")
            return False
    
    def _close_modal_with_button(self, modal) -> bool:
        """Try to close modal using close buttons.
        
        Args:
            modal: Modal WebElement
            
        Returns:
            True if modal was closed, False otherwise
        """
        for close_selector in self.CLOSE_BUTTON_SELECTORS:
            try:
                # Handle special case for text-based selectors
                if "contains" in close_selector:
                    close_buttons = modal.find_elements(By.TAG_NAME, "button")
                    for btn in close_buttons:
                        if any(x in btn.text for x in ["×", "X", "Close"]):
                            if self.click_element_safely(btn):
                                logger.info("Closed modal using X button")
                                time.sleep(1)
                                return True
                else:
                    close_button = self.element_finder.find_element_with_selectors(
                        close_selector, parent_element=modal
                    )
                    if close_button and close_button.is_displayed():
                        if self.click_element_safely(close_button):
                            logger.info(f"Closed modal using: {close_selector}")
                            time.sleep(1)
                            return True
                            
            except Exception:
                continue
        
        return False
    
    def _hide_modal_with_js(self, modal) -> bool:
        """Try to hide modal using JavaScript.
        
        Args:
            modal: Modal WebElement
            
        Returns:
            True if modal was hidden, False otherwise
        """
        try:
            self.driver.execute_script("arguments[0].style.display = 'none';", modal)
            logger.info("Hid modal using JavaScript")
            time.sleep(1)
            return True
        except Exception:
            return False
    
    def _try_escape_key(self) -> None:
        """Try pressing Escape key to close modals."""
        try:
            body = self.driver.find_element(By.TAG_NAME, 'body')
            body.send_keys(Keys.ESCAPE)
            logger.debug("Attempted to close modals with Escape key")
            time.sleep(1)
        except Exception:
            pass