"""Data extraction utilities for web scraping."""

import re
import logging
from typing import Dict, Any, Optional, List
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from .element_finder import ElementFinder
from config.config_models import ScrapingConfig


logger = logging.getLogger(__name__)


class ScrapingResult:
    """Data class for scraping results."""
    
    def __init__(self):
        """Initialize with default values."""
        self.title: str = "N/A"
        self.part_number: str = "N/A"
        self.vendor_part_number: str = "N/A"
        self.url: str = "N/A"
        self.price: str = "N/A"
        self.quantity: str = "N/A"
        self.description: str = "N/A"
        self.partial_match: bool = False
        self.cross_ref_match: bool = False
        self.exact_match: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format.
        
        Returns:
            Dictionary representation of the result
        """
        return {
            "title": self.title,
            "part_number": self.part_number,
            "vendor_part_number": self.vendor_part_number,
            "url": self.url,
            "price": self.price,
            "quantity": self.quantity,
            "description": self.description,
            "partial_match": self.partial_match,
            "cross_ref_match": self.cross_ref_match,
            "exact_match": self.exact_match
        }
    
    def is_valid(self) -> bool:
        """Check if result has meaningful data.
        
        Returns:
            True if result has at least title or URL
        """
        return (
            (self.title != "N/A" and self.title.strip()) or
            (self.url != "N/A" and self.url.strip())
        )


class DataExtractor:
    """Handles extraction of product data from web elements."""
    
    def __init__(self, element_finder: ElementFinder):
        """Initialize data extractor.
        
        Args:
            element_finder: ElementFinder instance for element location
        """
        self.element_finder = element_finder
    
    def extract_product_data(
        self,
        card_element: WebElement,
        scraping_config: ScrapingConfig,
        card_index: int = 0,
        debug: bool = False
    ) -> ScrapingResult:
        """Extract comprehensive product data from a product card element.
        
        Args:
            card_element: WebElement representing the product card
            scraping_config: Configuration for scraping selectors
            card_index: Index of the card for debugging
            debug: Whether to enable debug logging
            
        Returns:
            ScrapingResult with extracted data
        """
        result = ScrapingResult()
        
        if debug:
            self._debug_product_structure(card_element, card_index)
        
        try:
            self._extract_title_and_url(card_element, scraping_config, result)
            self._extract_part_numbers(card_element, scraping_config, result, card_index)
            self._extract_price(card_element, scraping_config, result)
            self._extract_quantity(card_element, scraping_config, result)
            self._extract_badges(card_element, scraping_config, result)
            
        except Exception as e:
            logger.error(f"Error extracting data from product {card_index}: {e}")
        
        return result
    
    def _extract_title_and_url(
        self,
        card_element: WebElement,
        scraping_config: ScrapingConfig,
        result: ScrapingResult
    ) -> None:
        """Extract title and URL from product card."""
        title_found = False
        url_found = False
        
        # Try configured title selectors
        for title_selector in scraping_config.product_title_selectors:
            title_element = self.element_finder.find_element_with_selectors(
                title_selector, parent_element=card_element
            )
            if title_element and title_element.text.strip():
                result.title = title_element.text.strip()
                title_found = True
                logger.debug(f"Found title with selector '{title_selector}': {result.title[:50]}...")
                break
        
        # Try to find URL using configured link selector
        link_element = self.element_finder.find_element_with_selectors(
            scraping_config.product_link_selector, parent_element=card_element
        )
        if link_element:
            href = link_element.get_attribute("href")
            if href:
                result.url = href
                url_found = True
                logger.debug(f"Found URL: {href}")
                
                # If title not found yet, try to get it from the link
                if not title_found and link_element.text.strip():
                    result.title = link_element.text.strip()
                    title_found = True
                    logger.debug(f"Got title from link text: {result.title[:50]}...")
        
        # Fallback methods if configured selectors don't work
        if not title_found or not url_found:
            self._fallback_title_url_extraction(card_element, result, title_found, url_found)
    
    def _extract_part_numbers(
        self,
        card_element: WebElement,
        scraping_config: ScrapingConfig,
        result: ScrapingResult,
        card_index: int
    ) -> None:
        """Extract part numbers (SKU) from product card."""
        try:
            sku_elements = self.element_finder.find_elements_with_selectors(
                scraping_config.product_sku_selectors, parent_element=card_element
            )
            
            logger.debug(f"Found {len(sku_elements)} SKU elements")
            
            if len(sku_elements) > 0:
                # Extract Part Number from the first element
                part_number = self._extract_sku_from_html(sku_elements[0])
                if part_number and part_number.strip():
                    result.part_number = self._clean_sku_text(part_number)
                    logger.debug(f"Extracted part_number: {result.part_number}")
            
            if len(sku_elements) > 1:
                # Extract Vendor Part Number from the second element
                vendor_part_number = self._extract_sku_from_html(sku_elements[1])
                if vendor_part_number and vendor_part_number.strip():
                    result.vendor_part_number = self._clean_sku_text(vendor_part_number)
                    logger.debug(f"Extracted vendor_part_number: {result.vendor_part_number}")
            
            # Fallback: look for common SKU patterns in text
            if result.part_number == "N/A":
                self._fallback_sku_extraction(card_element, result)
                
        except Exception as e:
            logger.error(f"Error extracting part numbers for product {card_index}: {e}")
    
    def _extract_price(
        self,
        card_element: WebElement,
        scraping_config: ScrapingConfig,
        result: ScrapingResult
    ) -> None:
        """Extract price from product card."""
        for price_selector in scraping_config.product_price_selectors:
            price_element = self.element_finder.find_element_with_selectors(
                price_selector, parent_element=card_element
            )
            if price_element:
                extracted_price = self._extract_price_from_html(price_element)
                if extracted_price and extracted_price.strip():
                    result.price = extracted_price
                    logger.debug(f"Found price: {extracted_price}")
                    break
    
    def _extract_quantity(
        self,
        card_element: WebElement,
        scraping_config: ScrapingConfig,
        result: ScrapingResult
    ) -> None:
        """Extract quantity from product card."""
        try:
            total_quantity = 0
            quantity_elements = self.element_finder.find_elements_with_selectors(
                scraping_config.product_quantity_selectors, parent_element=card_element
            )
            
            for idx, quantity_element in enumerate(quantity_elements):
                extracted_quantity = self._extract_quantity_from_html(quantity_element)
                if extracted_quantity is not None:
                    total_quantity += extracted_quantity
                    logger.debug(f"Added quantity from element {idx}: {extracted_quantity}")
            
            if total_quantity > 0:
                result.quantity = str(total_quantity)
                logger.debug(f"Total quantity found: {total_quantity}")
                
        except Exception as e:
            logger.error(f"Error extracting quantity: {e}")
    
    def _extract_badges(
        self,
        card_element: WebElement,
        scraping_config: ScrapingConfig,
        result: ScrapingResult
    ) -> None:
        """Extract badge information from product card."""
        try:
            # Extract general badges
            badge_elements = self.element_finder.find_elements_with_selectors(
                scraping_config.badges_selectors, parent_element=card_element
            )
            for badge in badge_elements:
                text = badge.text.strip().lower()
                logger.debug(f"Found badge text: '{text}'")
                if text == "partial match":
                    result.partial_match = True
                elif text == "cross ref match":
                    result.cross_ref_match = True
            
            # Extract exact match badges
            exact_match_elements = self.element_finder.find_elements_with_selectors(
                scraping_config.exact_match_selectors, parent_element=card_element
            )
            for badge in exact_match_elements:
                text = badge.text.strip().lower()
                if text == "exact match":
                    result.exact_match = True
                    
        except Exception as e:
            logger.error(f"Error extracting badges: {e}")
    
    def _extract_sku_from_html(self, sku_element: WebElement) -> str:
        """Extract SKU from complex HTML structures with nested spans."""
        try:
            # Method 1: Check for hidden input with SKU value
            try:
                hidden_input = sku_element.find_element(By.CSS_SELECTOR, "input[name='sku-id']")
                return hidden_input.get_attribute("value")
            except NoSuchElementException:
                pass
            
            # Method 2: Extract from vendor-value spans
            try:
                vendor_value = sku_element.find_element(By.CSS_SELECTOR, "span.vendor-value")
                spans = vendor_value.find_elements(By.CSS_SELECTOR, "span:not(.d-none)")
                sku_parts = []
                
                for span in spans:
                    text = span.text.strip()
                    if text and not any(char in text for char in ['✓', '☑', '✔']):
                        sku_parts.append(text)
                
                if sku_parts:
                    return ''.join(sku_parts)
            except NoSuchElementException:
                pass
            
            # Method 3: Fallback to getting all text and cleaning it
            full_text = sku_element.text.strip()
            full_text = full_text.replace('✓', '').replace('☑', '').replace('✔', '').strip()
            return full_text
            
        except Exception:
            return sku_element.text.strip()
    
    def _extract_price_from_html(self, price_element: WebElement) -> str:
        """Extract price from complex HTML structures."""
        try:
            # Method 1: Check if it's a price-wrapper with separate dollar and cents
            if "price-wrapper" in price_element.get_attribute("class"):
                spans = price_element.find_elements(By.TAG_NAME, "span")
                price_parts = []
                
                for span in spans:
                    text = span.text.strip()
                    # Skip "(each)" and similar text
                    if text and not text.startswith("(") and not text.endswith(")"):
                        price_parts.append(text)
                
                if price_parts:
                    dollars = price_parts[0].replace("$", "")
                    cents = price_parts[1]
                    return f"{dollars}.{cents}"
            
            # Method 2: Simple text extraction
            return price_element.text.strip()
            
        except Exception:
            return price_element.text.strip()
    
    def _extract_quantity_from_html(self, quantity_element: WebElement) -> Optional[int]:
        """Extract quantity from a Selenium WebElement."""
        try:
            logger.debug(f"Processing quantity element: {quantity_element}")
            
            if quantity_element:
                quantity_text = quantity_element.text.strip()
                logger.debug(f"Quantity text: '{quantity_text}'")
                
                digits = ''.join(filter(str.isdigit, quantity_text))
                logger.debug(f"Extracted digits: '{digits}'")
                
                return int(digits) if digits else None
            
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting quantity: {e}")
            return None
    
    def _clean_sku_text(self, part_number: str) -> str:
        """Clean SKU text by removing unwanted characters and whitespace."""
        if not part_number:
            return "N/A"
        
        # Clean up the SKU text
        prefixes = ["Vendor Part #:", "SKU:", "Part #:"]
        for prefix in prefixes:
            if prefix in part_number:
                part_number = part_number.split(prefix)[-1].strip()
                break
        
        return part_number.strip()
    
    def _fallback_title_url_extraction(
        self,
        card_element: WebElement,
        result: ScrapingResult,
        title_found: bool,
        url_found: bool
    ) -> None:
        """Fallback method for title and URL extraction."""
        all_links = card_element.find_elements(By.TAG_NAME, "a")
        
        for link in all_links:
            href = link.get_attribute("href")
            link_text = link.text.strip()
            
            # Skip invalid links
            if not href or any(skip in href.lower() for skip in ['mailto:', 'tel:', 'javascript:', '#']):
                continue
            
            # Priority for product-like links
            if any(indicator in href.lower() for indicator in ['/product/', '/item/', '/p/', '/details/']):
                if not url_found:
                    result.url = href
                    url_found = True
                if not title_found and link_text:
                    result.title = link_text
                    title_found = True
                if title_found and url_found:
                    break
        
        # Last resort: use first meaningful link
        if not title_found or not url_found:
            for link in all_links:
                href = link.get_attribute("href")
                link_text = link.text.strip()
                
                if href and link_text and len(link_text) > 5:
                    if not url_found:
                        result.url = href
                    if not title_found:
                        result.title = link_text
                    break
    
    def _fallback_sku_extraction(self, card_element: WebElement, result: ScrapingResult) -> None:
        """Fallback method for SKU extraction using regex patterns."""
        all_text = card_element.text
        sku_patterns = [
            r'SKU:?\s*([A-Za-z0-9\-]+)',
            r'Part\s*#:?\s*([A-Za-z0-9\-]+)',
            r'Item\s*#:?\s*([A-Za-z0-9\-]+)',
            r'Model:?\s*([A-Za-z0-9\-]+)'
        ]
        
        for pattern in sku_patterns:
            match = re.search(pattern, all_text, re.IGNORECASE)
            if match:
                result.part_number = match.group(1)
                logger.debug(f"Found SKU with pattern '{pattern}': {result.part_number}")
                break
    
    def _debug_product_structure(self, card_element: WebElement, card_index: int) -> None:
        """Debug function to understand product card structure."""
        try:
            logger.debug(f"\n=== DEBUGGING PRODUCT CARD {card_index} ===")
            
            # Get outer HTML for inspection
            outer_html = card_element.get_attribute("outerHTML")
            logger.debug(f"Card HTML (first 300 chars): {outer_html[:300]}...")
            
            # Find all links in the card
            links = card_element.find_elements(By.TAG_NAME, "a")
            logger.debug(f"Found {len(links)} links in card:")
            for i, link in enumerate(links):
                href = link.get_attribute("href")
                text = link.text.strip()
                classes = link.get_attribute("class")
                logger.debug(f"  Link {i}: href='{href}', text='{text[:50]}', classes='{classes}'")
            
            logger.debug(f"=== END DEBUG CARD {card_index} ===\n")
            
        except Exception as e:
            logger.error(f"Debug error for card {card_index}: {e}")