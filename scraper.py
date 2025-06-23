# Configurable Web Scraping Module (Python + Selenium)

import os
import sys
import argparse
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from typing import List, Dict, Any, Optional

# Import configuration types
from config_loader import SiteConfig, ChromeConfig, ScrapingConfig

def setup_driver_with_config(chrome_config: ChromeConfig):
    """Sets up the Selenium WebDriver using configuration."""
    chrome_options = Options()
    
    # Basic headless configuration
    if chrome_config.headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # GPU and rendering fixes
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-gpu-sandbox")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-3d-apis")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-features=TranslateUI")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("--disable-features=VizServiceDisplayCompositor")
    chrome_options.add_argument("--use-gl=disabled")
    chrome_options.add_argument("--disable-gl-drawing-for-tests")
    
    # Proxy resolver fix
    chrome_options.add_argument("--no-proxy-server")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-features=NetworkService")
    
    # Security and certificate handling
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--ignore-ssl-errors")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--ignore-certificate-errors-spki-list")
    chrome_options.add_argument("--ignore-urlfetcher-cert-requests")
    
    # Performance optimizations
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--no-default-browser-check")
    chrome_options.add_argument("--disable-default-apps")
    
    # Memory and process management
    chrome_options.add_argument("--memory-pressure-off")
    chrome_options.add_argument("--max_old_space_size=4096")
    
    # User agent from config
    chrome_options.add_argument(f"user-agent={chrome_config.user_agent}")
    
    # Experimental options to reduce errors
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Logging preferences to reduce console noise
    chrome_options.add_experimental_option('prefs', {
        'profile.default_content_setting_values.notifications': 2,
        'profile.default_content_settings.popups': 0,
        'profile.managed_default_content_settings.images': 2
    })

    try:
        # Try using webdriver_manager if path is not specified
        if chrome_config.chrome_driver_path is None:
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                print("Using webdriver-manager to install Chrome driver")
            except ImportError:
                print("webdriver-manager not installed. Please install it (`pip install webdriver-manager`) or specify chrome_driver_path in config.")
                return None
        else:
            service = Service(chrome_config.chrome_driver_path)
        
        # Add service arguments to reduce logging
        service.creation_flags = 0x08000000  # CREATE_NO_WINDOW flag for Windows
        
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Additional driver configuration from config
        driver.set_window_size(chrome_config.window_size["width"], chrome_config.window_size["height"])
        driver.implicitly_wait(chrome_config.implicit_wait)
        
        print("WebDriver setup successful")
        return driver
        
    except Exception as e:
        print(f"Error setting up WebDriver: {e}")
        return None

def check_for_no_results_with_config(driver, search_term: str, scraping_config: ScrapingConfig) -> bool:
    """Check if the search returned no results using configured selectors."""
    try:
        for no_results_selector in scraping_config.no_results_selectors:
            try:
                no_results_element = driver.find_element(By.CSS_SELECTOR, no_results_selector)
                if no_results_element.is_displayed():
                    # Check if the text contains indicators of no results
                    element_text = no_results_element.text.lower()
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
                            print(f"No results detected: {element_text.strip()}")
                            return True
                            
            except NoSuchElementException:
                continue
                
        return False
        
    except Exception as e:
        print(f"Error checking for no results: {e}")
        return False

def extract_sku_from_complex_html(sku_element):
    """Extract SKU from complex HTML structures with nested spans."""
    try:
        # Method 1: Check for hidden input with SKU value
        try:
            hidden_input = sku_element.find_element(By.CSS_SELECTOR, "input[name='sku-id']")
            return hidden_input.get_attribute("value")
        except NoSuchElementException:
            pass
        
        # Method 2: Extract from vendor-value spans (concatenate all text from spans)
        try:
            vendor_value = sku_element.find_element(By.CSS_SELECTOR, "span.vendor-value")
            
            # Get all direct child spans that contain text (exclude hidden elements)
            spans = vendor_value.find_elements(By.CSS_SELECTOR, "span:not(.d-none)")
            sku_parts = []
            
            for span in spans:
                text = span.text.strip()
                if text and not any(char in text for char in ['✓', '☑', '✔']):  # Exclude checkmark text
                    sku_parts.append(text)
            
            if sku_parts:
                return ''.join(sku_parts)
        except NoSuchElementException:
            pass
        
        # Method 3: Fallback to getting all text and cleaning it
        full_text = sku_element.text.strip()
        # Remove common non-SKU text
        full_text = full_text.replace('✓', '').replace('☑', '').replace('✔', '').strip()
        return full_text
        
    except NoSuchElementException:
        # Method 4: Simple text extraction
        return sku_element.text.strip()

def extract_price_from_complex_html(price_element):
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
                # Join dollar and cents parts
                #return ''.join(price_parts[:2])  # Usually $XX and .YY
                dollars = price_parts[0].replace("$", "")
                cents = price_parts[1]
                return f"{dollars}.{cents}"
        
        # Method 2: Simple text extraction
        return price_element.text.strip()
        
    except Exception:
        return price_element.text.strip()

def handle_modal_popups(driver) -> None:
    """Handle common modal popups that might interfere with scraping"""
    modal_selectors = [
        # Newsletter modals
        "div.modal.show",
        "div.modal-wrapper.show", 
        "div[role='dialog'][aria-modal='true']",
        ".newsletter-modal.show",
        ".popup-modal.show",
        
        # Cookie banners
        "#cookie-banner",
        ".cookie-consent",
        ".gdpr-banner",
        
        # General overlay modals
        ".overlay.show",
        ".modal-overlay.show"
    ]
    
    close_button_selectors = [
        # Common close button patterns
        "button.close",
        "button[aria-label='Close']",
        "button[data-dismiss='modal']",
        ".modal-close",
        ".close-button",
        "[data-close-modal]",
        "button.btn-close",
        
        # X button patterns
        "button:contains('×')",
        "span.close",
        ".fa-times",
        ".fa-close"
    ]
    
    try:
        # First, try to find and close any visible modals
        for modal_selector in modal_selectors:
            try:
                modals = driver.find_elements(By.CSS_SELECTOR, modal_selector)
                for modal in modals:
                    if modal.is_displayed():
                        print(f"Found visible modal: {modal_selector}")
                        
                        # Try to find close button within the modal
                        for close_selector in close_button_selectors:
                            try:
                                if close_selector.startswith("button:contains"):
                                    # Handle jQuery-style selector manually
                                    close_buttons = modal.find_elements(By.TAG_NAME, "button")
                                    for btn in close_buttons:
                                        if "×" in btn.text or "X" in btn.text:
                                            btn.click()
                                            print(f"Closed modal using X button")
                                            time.sleep(1)
                                            return
                                else:
                                    close_button = modal.find_element(By.CSS_SELECTOR, close_selector)
                                    if close_button.is_displayed():
                                        close_button.click()
                                        print(f"Closed modal using: {close_selector}")
                                        time.sleep(1)
                                        return
                            except NoSuchElementException:
                                continue
                        
                        # If no close button found, try clicking outside the modal
                        try:
                            driver.execute_script("arguments[0].style.display = 'none';", modal)
                            print("Hid modal using JavaScript")
                            time.sleep(1)
                            return
                        except:
                            pass
                            
            except NoSuchElementException:
                continue
                
        # Try pressing Escape key as fallback
        try:
            from selenium.webdriver.common.keys import Keys
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            print("Attempted to close modals with Escape key")
            time.sleep(1)
        except:
            pass
            
    except Exception as e:
        print(f"Error handling modals: {e}")

def wait_for_page_load(driver, timeout: int = 10) -> None:
    """Wait for page to fully load and handle any loading states"""
    try:
        # Wait for basic page load
        WebDriverWait(driver, timeout).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )
        
        # Wait for any loading indicators to disappear
        loading_selectors = [
            ".loading",
            ".spinner", 
            ".loader",
            "[data-loading='true']",
            ".loading-overlay"
        ]
        
        for selector in loading_selectors:
            try:
                WebDriverWait(driver, 3).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, selector))
                )
            except TimeoutException:
                continue
                
    except Exception as e:
        print(f"Warning: Page load wait issue: {e}")

def debug_product_structure(driver, card_element, card_index: int) -> None:
    """Debug function to understand product card structure"""
    try:
        print(f"\n=== DEBUGGING PRODUCT CARD {card_index} ===")
        
        # Get outer HTML for inspection
        outer_html = card_element.get_attribute("outerHTML")
        print(f"Card HTML (first 300 chars): {outer_html[:300]}...")
        
        # Find all links in the card
        links = card_element.find_elements(By.TAG_NAME, "a")
        print(f"Found {len(links)} links in card:")
        for i, link in enumerate(links):
            href = link.get_attribute("href")
            text = link.text.strip()
            classes = link.get_attribute("class")
            print(f"  Link {i}: href='{href}', text='{text[:50]}', classes='{classes}'")
        
        # Find all text elements
        all_text_elements = card_element.find_elements(By.XPATH, ".//*[text()]")
        print(f"Found {len(all_text_elements)} text elements:")
        for i, elem in enumerate(all_text_elements[:5]):  # Limit to first 5
            tag = elem.tag_name
            text = elem.text.strip()
            classes = elem.get_attribute("class")
            if text:
                print(f"  Element {i}: <{tag}> '{text[:30]}' classes='{classes}'")
        
        print(f"=== END DEBUG CARD {card_index} ===\n")
        
    except Exception as e:
        print(f"Debug error for card {card_index}: {e}")

def extract_product_data_enhanced(card_element, card_index: int, scraping_config: ScrapingConfig, debug: bool = False) -> Dict[str, str]:
    """Enhanced product data extraction with better error handling and debugging"""
    
    product_data = {
        "title": "N/A",
        "part_number": "N/A", 
        "vendor_part_number": "N/A",
        "url": "N/A",
        "price": "N/A",
        "quantity": "N/A",
        "description": "N/A"
    }
    
    if debug:
        debug_product_structure(None, card_element, card_index)
    
    # Enhanced title and URL extraction
    try:
        # Method 1: Try configured selectors first
        title_found = False
        url_found = False
        
        # Try to find title using multiple approaches
        for title_selector in scraping_config.product_title_selectors:
            try:
                # Try direct selector on card
                title_element = card_element.find_element(By.CSS_SELECTOR, title_selector)
                if title_element.text.strip():
                    product_data["title"] = title_element.text.strip()
                    title_found = True
                    print(f"Found title with selector '{title_selector}': {product_data['title'][:50]}...")
                    break
            except NoSuchElementException:
                continue
        
        # Try to find URL using configured link selector
        try:
            link_element = card_element.find_element(By.CSS_SELECTOR, scraping_config.product_link_selector)
            href = link_element.get_attribute("href")
            if href:
                product_data["url"] = href
                url_found = True
                print(f"Found URL with selector '{scraping_config.product_link_selector}': {href}")
                
                # If title not found yet, try to get it from the link
                if not title_found and link_element.text.strip():
                    product_data["title"] = link_element.text.strip()
                    title_found = True
                    print(f"Got title from link text: {product_data['title'][:50]}...")
                    
        except NoSuchElementException:
            pass
        
        # Fallback methods if configured selectors don't work
        if not title_found or not url_found:
            print(f"Fallback: searching for any links in card {card_index}")
            
            # Find all links and try to identify the main product link
            all_links = card_element.find_elements(By.TAG_NAME, "a")
            
            for link in all_links:
                href = link.get_attribute("href")
                link_text = link.text.strip()
                
                # Skip empty links or non-product links
                if not href or any(skip in href.lower() for skip in ['mailto:', 'tel:', 'javascript:', '#']):
                    continue
                
                # Priority for links that look like product links
                if any(indicator in href.lower() for indicator in ['/product/', '/item/', '/p/', '/details/']):
                    if not url_found:
                        product_data["url"] = href
                        url_found = True
                        print(f"Found product URL (fallback): {href}")
                    
                    if not title_found and link_text:
                        product_data["title"] = link_text
                        title_found = True
                        print(f"Found title (fallback): {link_text[:50]}...")
                    
                    if title_found and url_found:
                        break
            
            # Last resort: use the first meaningful link
            if not title_found or not url_found:
                for link in all_links:
                    href = link.get_attribute("href")
                    link_text = link.text.strip()
                    
                    if href and link_text and len(link_text) > 5:  # Meaningful text
                        if not url_found:
                            product_data["url"] = href
                            url_found = True
                        if not title_found:
                            product_data["title"] = link_text
                            title_found = True
                        break
        
    except Exception as e:
        print(f"Error extracting title/URL for product {card_index}: {e}")
    
    # Enhanced SKU/Part Number extraction
    try:
        sku_found = False
        for sku_selector in scraping_config.product_sku_selectors:
            # ...existing code...
            try:
                # Find all span.sku-text elements
                sku_elements = card_element.find_elements(By.CSS_SELECTOR, sku_selector)
                print(f"[DEBUG] Found {len(sku_elements)} span.sku-text elements")
                if len(sku_elements) > 0:
                    # Extract Part Number from the first
                    part_number = extract_sku_from_complex_html(sku_elements[0])
                    if part_number and part_number.strip():
                         # Clean up the SKU text                        
                        product_data["part_number"] = clean_sku_text(part_number)
                        print(f"[DEBUG] Extracted part_number: {product_data['part_number']}")
                        sku_found =True 
                if len(sku_elements) > 1:
                    # Extract Vendor Part Number from the second
                    vendor_part_number = extract_sku_from_complex_html(sku_elements[1])
                    if vendor_part_number and vendor_part_number.strip():
                        product_data["vendor_part_number"] = clean_sku_text(vendor_part_number.strip())
                        print(f"[DEBUG] Extracted vendor_part_number: {product_data['vendor_part_number']}")
            except Exception as e:
                print(f"Error extracting part numbers for product {card_index}: {e}")

            # ...existing code...
        
        # Fallback: look for common SKU patterns in any text
        if not sku_found:
            all_text = card_element.text
            import re
            # Look for patterns like "SKU: ABC123", "Part #: ABC123", etc.
            sku_patterns = [
                r'SKU:?\s*([A-Za-z0-9\-]+)',
                r'Part\s*#:?\s*([A-Za-z0-9\-]+)',
                r'Item\s*#:?\s*([A-Za-z0-9\-]+)',
                r'Model:?\s*([A-Za-z0-9\-]+)'
            ]
            
            for pattern in sku_patterns:
                match = re.search(pattern, all_text, re.IGNORECASE)
                if match:
                    product_data["part_number"] = match.group(1)
                    print(f"Found SKU with pattern '{pattern}': {product_data['part_number']}")
                    break
                    
    except Exception as e:
        print(f"Error extracting SKU for product {card_index}: {e}")
    
    # Enhanced Price extraction
    try:
        for price_selector in scraping_config.product_price_selectors:
            try:
                price_element = card_element.find_element(By.CSS_SELECTOR, price_selector)
                extracted_price = extract_price_from_complex_html(price_element)
                
                if extracted_price and extracted_price.strip():
                    product_data["price"] = extracted_price
                    print(f"Found price with selector '{price_selector}': {extracted_price}")
                    break
                    
            except NoSuchElementException:
                continue
                
    except Exception as e:
        print(f"Error extracting price for product {card_index}: {e}")
    
    # Enhanced Quantity extraction
    try:
        total_quantity = 0
        for quantity_selector in scraping_config.product_quantity_selectors:
            try:
                # Use find_elements to get all matching spans
                quantity_elements = card_element.find_elements(By.CSS_SELECTOR, quantity_selector)
                print(f"[DEBUG] Found {len(quantity_elements)} elements with selector '{quantity_selector}'")
                for idx, quantity_element in enumerate(quantity_elements):
                    print(f"[DEBUG] [{idx}] quantity_element: {quantity_element}")
                    extracted_quantity = extract_quantity_from_html(quantity_element)
                    print(f"[DEBUG] [{idx}] extracted_quantity: {extracted_quantity}")
                    if extracted_quantity is not None:
                        total_quantity += extracted_quantity
                        print(f"[DEBUG] Added quantity from element {idx}: {extracted_quantity}")
            except NoSuchElementException:
                continue

        if total_quantity > 0:
            product_data["quantity"] = total_quantity
            print(f"Total quantity found: {total_quantity}")

    except Exception as e:
        print(f"Error extracting quantity for product {card_index}: {e}")
    
    return product_data

def clean_sku_text(part_number: str):
    """Clean SKU text by removing unwanted characters and whitespace."""
    if not part_number:
        return "N/A"
    
    # Clean up the SKU text
    if "Vendor Part #:" in part_number:
        part_number = part_number.split("Vendor Part #:")[-1].strip()
    elif "SKU:" in part_number:
        part_number = part_number.split("SKU:")[-1].strip()
    elif "Part #:" in part_number:
        ppart_number = part_number.split("Part #:")[-1].strip()
    else:
        part_number = part_number.strip()

    return part_number

def extract_quantity_from_html(quantity_element):
    """Extract quantity from a Selenium WebElement with debug."""
    try:
        print(f"[DEBUG] Received quantity_element: {quantity_element} (type: {type(quantity_element)})")
        if quantity_element:
            try:
                outer_html = quantity_element.get_attribute('outerHTML')
                print(f"[DEBUG] quantity_element outerHTML: {outer_html}")
            except Exception as e:
                print(f"[DEBUG] Could not get outerHTML: {e}")

            try:
                text = quantity_element.text
                print(f"[DEBUG] quantity_element .text: '{text}'")
            except Exception as e:
                print(f"[DEBUG] Could not get .text: {e}")

            try:
                value = quantity_element.get_attribute('value')
                print(f"[DEBUG] quantity_element value attribute: '{value}'")
            except Exception as e:
                print(f"[DEBUG] Could not get value attribute: {e}")

            # Extract and clean text
            quantity_text = quantity_element.text.strip()
            print(f"[DEBUG] Stripped quantity_text: '{quantity_text}'")
            digits = ''.join(filter(str.isdigit, quantity_text))
            print(f"[DEBUG] Extracted digits from quantity_text: '{digits}'")
            return int(digits) if digits else None
        print("[DEBUG] quantity_element is None or empty")
        return None
    except Exception as e:
        print(f"Warning: Error extracting quantity: {e}")
        return None
    
def find_element_in_parent(parent_element, selectors):
    """Try multiple selectors to find an element within a parent element."""
    if isinstance(selectors, str):
        selectors = [selectors]  # Convert string to list for consistency
    
    for selector in selectors:
        try:
            element = parent_element.find_element(By.CSS_SELECTOR, selector)
            return element
        except NoSuchElementException:
            continue
    return None

def find_element_with_multiple_selectors(driver, selectors, by=By.CSS_SELECTOR, wait_for_interactable=False, timeout=5):
    """Try multiple selectors to find an element with shorter timeout for faster performance."""
    if isinstance(selectors, str):
        selectors = [selectors]  # Convert string to list for consistency
        
    for selector in selectors:
        try:
            if wait_for_interactable:
                element = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((by, selector))
                )
            else:
                element = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((by, selector))
                )
            print(f"Found element with selector: {selector}")
            return element
        except TimeoutException:
            continue
        except Exception as e:
            print(f"Error with selector {selector}: {e}")
            continue
    return None

def scrape_site_with_config(driver, search_term: str, site_config: SiteConfig, debug_mode: bool = False) -> List[Dict[str, Any]]:
    """Performs a search and scrapes results using site configuration."""
    results = []
    scraping_config = site_config.scraping_config
    
    try:
        # Set page load timeout
        driver.set_page_load_timeout(scraping_config.page_load_timeout)
        
        # Navigate to the page with error handling
        try:
            print(f"Navigating to {site_config.target_url}")
            driver.get(site_config.target_url)
            print(f"Successfully navigated to {site_config.target_url}")
            
            # Wait for page to load completely
            wait_for_page_load(driver, 10)
            
            print(f"Page title: {driver.title}")
            
            # Handle modal popups that might interfere
            print("Checking for modal popups...")
            handle_modal_popups(driver)
            
            # Additional wait for dynamic content
            time.sleep(3)
            
        except Exception as e:
            print(f"Error loading page: {e}")
            return results

        # Wait for search input and enter search term with better error handling
        try:
            print("Looking for search input...")
            search_input = find_element_with_multiple_selectors(
                driver, 
                scraping_config.search_input_selectors, 
                wait_for_interactable=True, 
                timeout=scraping_config.wait_timeout
            )
            if not search_input:
                print("Error: Could not find search input with any selector")
                # Debug: print available input elements
                inputs = driver.find_elements(By.TAG_NAME, "input")
                print(f"Found {len(inputs)} input elements on page")
                for i, inp in enumerate(inputs[:5]):  # Show first 5
                    input_type = inp.get_attribute('type')
                    placeholder = inp.get_attribute('placeholder')
                    name = inp.get_attribute('name')
                    id_attr = inp.get_attribute('id')
                    print(f"Input {i}: type='{input_type}', placeholder='{placeholder}', name='{name}', id='{id_attr}'")
                return results
                
            search_input.clear()
            search_input.send_keys(search_term)
            print(f"Entered search term: {search_term}")
            
        except Exception as e:
            print(f"Error entering search term: {e}")
            return results

        # Find and click search button with enhanced error handling
        try:
            print("Looking for search button...")
            
            # Handle any modals that might have appeared
            handle_modal_popups(driver)
            
            search_button = find_element_with_multiple_selectors(
                driver, 
                scraping_config.search_button_selectors, 
                by=By.XPATH, 
                timeout=5
            )
            
            if search_button:
                try:
                    # Check if button is clickable
                    WebDriverWait(driver, 5).until(EC.element_to_be_clickable(search_button))
                    search_button.click()
                    print("Clicked search button successfully")
                except Exception as click_error:
                    print(f"Error clicking search button: {click_error}")
                    # Try JavaScript click as fallback
                    try:
                        driver.execute_script("arguments[0].click();", search_button)
                        print("Used JavaScript click as fallback")
                    except Exception as js_error:
                        print(f"JavaScript click also failed: {js_error}")
                        # Try Enter key as final fallback
                        from selenium.webdriver.common.keys import Keys
                        search_input.send_keys(Keys.RETURN)
                        print("Used Enter key as final fallback")
            else:
                print("Search button not found, using Enter key...")
                from selenium.webdriver.common.keys import Keys
                search_input.send_keys(Keys.RETURN)
                print("Used Enter key")
                
        except Exception as e:
            print(f"Error with search button: {e}")
            # Final fallback: try pressing Enter
            try:
                from selenium.webdriver.common.keys import Keys
                search_input.send_keys(Keys.RETURN)
                print("Used Enter key as final fallback")
            except Exception as fallback_error:
                print(f"All search methods failed: {fallback_error}")
                return results

        # Wait for results with better error handling
        try:
            print("Waiting for search results...")
            
            # Wait a bit for the search to process
            time.sleep(3)
            
            # Handle any new modals that might appear
            handle_modal_popups(driver)
            
            # Wait for page to finish loading
            wait_for_page_load(driver, 10)
            # Wait a bit more for the quantity to process
            time.sleep(8)
           
            # First check if we got a "no results" message
            if check_for_no_results_with_config(driver, search_term, scraping_config):
                print(f"Search for '{search_term}' returned no results.")
                return results  # Return empty results list
            
            # Look for product cards
            product_card = find_element_with_multiple_selectors(
                driver, 
                scraping_config.product_card_selectors, 
                timeout=10
            )
            
            if not product_card:
                print("Error: Could not find product cards with any selector")
                print(f"Current URL: {driver.current_url}")
                
                # Debug: Show what's on the page
                page_source_sample = driver.page_source[:1000]
                print(f"Page source sample: {page_source_sample}")
                
                # Double-check for no results message after waiting
                if check_for_no_results_with_config(driver, search_term, scraping_config):
                    print(f"Confirmed: Search for '{search_term}' returned no results.")
                    return results
                    
                return results
                
            print("Search results page loaded")
            # take_screenshots = config.deployment_config.enable_screenshots
            # if take_screenshots:
            take_screenshot(driver, "05_after_searchReulstLoaded", "After Search Results are loaded")

        except Exception as e:
            print(f"Error waiting for results: {e}")
            return results

        # Find all product cards with enhanced detection
        print(f"Looking for product cards with selectors: {scraping_config.product_card_selectors}")
        
        product_cards = []
        for selector in scraping_config.product_card_selectors:
            try:
                cards = driver.find_elements(By.CSS_SELECTOR, selector)
                if cards:
                    product_cards = cards
                    print(f"Found {len(cards)} product cards using selector: {selector}")
                    break
            except Exception as e:
                print(f"Error with selector '{selector}': {e}")
                continue
        
        if len(product_cards) == 0:
            if check_for_no_results_with_config(driver, search_term, scraping_config):
                print(f"Final confirmation: No results found for '{search_term}'")
                return results
            else:
                print("No product cards found, but no 'no results' message detected either.")
                
                # Debug: try to find any elements that might be product cards
                potential_selectors = [
                    "div[class*='product']",
                    "div[class*='item']", 
                    "div[class*='result']",
                    "article",
                    "li[class*='product']",
                    ".product",
                    ".item",
                    ".result"
                ]
                
                for debug_selector in potential_selectors:
                    try:
                        debug_cards = driver.find_elements(By.CSS_SELECTOR, debug_selector)
                        if debug_cards:
                            print(f"DEBUG: Found {len(debug_cards)} elements with selector '{debug_selector}'")
                    except:
                        continue
                        
                return results

        # Extract data from each card using enhanced method
        print(f"Starting to extract data from {len(product_cards)} product cards...")
        
        for i, card in enumerate(product_cards):
            if i >= scraping_config.max_results_per_query:
                print(f"Reached max results limit ({scraping_config.max_results_per_query})")
                break
            
            print(f"Scraping product {i+1} of {min(len(product_cards), scraping_config.max_results_per_query)}")
            
            try:
                product_data = extract_product_data_enhanced(
                    card, i+1, scraping_config, debug=debug_mode
                )
                
                # Only add if we found meaningful data
                if (product_data["title"] != "N/A" and product_data["title"]) or \
                   (product_data["url"] != "N/A" and product_data["url"]):
                    results.append(product_data)
                    title_preview = product_data['title'][:50] + '...' if len(product_data['title']) > 50 else product_data['title']
                    print(f"-- Scraped Product {i+1}: Title: {title_preview}")
                else:
                    print(f"-- Skipped Product {i+1}: No meaningful data found")
                    if debug_mode:
                        print(f"   Data: {product_data}")
                        
            except Exception as e:
                print(f"Error extracting data from product {i+1}: {e}")
                continue

        print(f"Successfully extracted data from {len(results)} products")

    except TimeoutException:
        print(f"Error: Timed out waiting for elements during search for {search_term}")
    except Exception as e:
        print(f"An unexpected error occurred during scraping for {search_term}: {e}")
        import traceback
        traceback.print_exc()

    return results
    """Performs a search and scrapes results using site configuration."""
    results = []
    scraping_config = site_config.scraping_config
    
    try:
        # Set page load timeout
        driver.set_page_load_timeout(scraping_config.page_load_timeout)
        
        # Navigate to the page with error handling
        try:
            print(f"Navigating to {site_config.target_url}")
            driver.get(site_config.target_url)
            print(f"Successfully navigated to {site_config.target_url}")
            
            # Wait for page to load completely
            WebDriverWait(driver, 10).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            print(f"Page title: {driver.title}")
            time.sleep(3)  # Additional wait for dynamic content
            
        except Exception as e:
            print(f"Error loading page: {e}")
            return results

        # Wait for search input and enter search term with better error handling
        try:
            print("Looking for search input...")
            search_input = find_element_with_multiple_selectors(
                driver, 
                scraping_config.search_input_selectors, 
                wait_for_interactable=True, 
                timeout=scraping_config.wait_timeout
            )
            if not search_input:
                print("Error: Could not find search input with any selector")
                # Debug: print available input elements
                inputs = driver.find_elements(By.TAG_NAME, "input")
                print(f"Found {len(inputs)} input elements on page")
                for i, inp in enumerate(inputs[:3]):  # Show first 3 only
                    print(f"Input {i}: type='{inp.get_attribute('type')}', placeholder='{inp.get_attribute('placeholder')}'")
                return results
                
            search_input.clear()
            search_input.send_keys(search_term)
            print(f"Entered search term: {search_term}")
            
        except Exception as e:
            print(f"Error entering search term: {e}")
            return results

        # Find and click search button with better error handling
        try:
            print("Looking for search button...")
            search_button = find_element_with_multiple_selectors(
                driver, 
                scraping_config.search_button_selectors, 
                by=By.XPATH, 
                timeout=5
            )
            if not search_button:
                print("Search button not found, trying Enter key...")
                # Try pressing Enter instead
                try:
                    from selenium.webdriver.common.keys import Keys
                    search_input.send_keys(Keys.RETURN)
                    print("Used Enter key as fallback")
                except:
                    return results
            else:
                search_button.click()
                print("Clicked search button")
                
        except Exception as e:
            print(f"Error clicking search button: {e}")
            # Fallback: try pressing Enter
            try:
                from selenium.webdriver.common.keys import Keys
                search_input.send_keys(Keys.RETURN)
                print("Used Enter key as fallback")
            except Exception as fallback_error:
                print(f"Fallback also failed: {fallback_error}")
                return results

        # Wait for results with better error handling
        try:
            print("Waiting for search results...")
            # Shorter wait time and immediate check
            time.sleep(2)
            
            # First check if we got a "no results" message
            if check_for_no_results_with_config(driver, search_term, scraping_config):
                print(f"Search for '{search_term}' returned no results.")
                return results  # Return empty results list
            
            product_card = find_element_with_multiple_selectors(
                driver, 
                scraping_config.product_card_selectors, 
                timeout=8
            )
            if not product_card:
                print("Error: Could not find product cards with any selector")
                print(f"Current URL: {driver.current_url}")
                
                # Double-check for no results message after waiting
                if check_for_no_results_with_config(driver, search_term, scraping_config):
                    print(f"Confirmed: Search for '{search_term}' returned no results.")
                    return results
                    
                return results
                
            print("Search results page loaded")
            
        except Exception as e:
            print(f"Error waiting for results: {e}")
            return results

        # Find all product cards
        product_cards = driver.find_elements(By.CSS_SELECTOR, scraping_config.product_card_selectors[0])
        print(f"Found {len(product_cards)} potential product cards.")
        
        # If no product cards found, do final check for no results message
        if len(product_cards) == 0:
            if check_for_no_results_with_config(driver, search_term, scraping_config):
                print(f"Final confirmation: No results found for '{search_term}'")
                return results
            else:
                print("No product cards found, but no 'no results' message detected either.")
                return results

        # Extract data from each card
        for i, card in enumerate(product_cards):
            if i >= scraping_config.max_results_per_query:
                break
            
            product_data = {
                "title": "N/A",
                "part_number": "N/A",
                "url": "N/A",
                "price": "N/A",
                "quantity": "N/A",
                "description": "N/A"
            }

            try:
                # Extract Title and URL from the main product link
                title_element = None
                for title_selector in scraping_config.product_title_selectors:
                    try:
                        title_element = card.find_element(By.CSS_SELECTOR, scraping_config.product_link_selector + " " + title_selector)
                        break
                    except NoSuchElementException:
                        continue
                
                if title_element:
                    product_data["title"] = title_element.text.strip()
                    # Get URL from the parent 'a' tag
                    url_element = title_element.find_element(By.XPATH, "./ancestor::a")
                    product_data["url"] = url_element.get_attribute("href")
                else:
                    # Fallback: try to find title in different structure
                    link_element = card.find_element(By.CSS_SELECTOR, scraping_config.product_link_selector)
                    product_data["url"] = link_element.get_attribute("href")
                    
                    # Try each title selector directly in the link
                    for title_selector in scraping_config.product_title_selectors:
                        try:
                            title_element = link_element.find_element(By.CSS_SELECTOR, title_selector)
                            product_data["title"] = title_element.text.strip()
                            break
                        except NoSuchElementException:
                            continue
                    
                    # Final fallback: use link text
                    if product_data["title"] == "N/A":
                        product_data["title"] = link_element.text.strip()
                
            except NoSuchElementException:
                print(f"Warning: Could not find title/URL for product {i+1}")
                # Try alternative if structure varies
                try:
                    link_element = card.find_element(By.CSS_SELECTOR, scraping_config.product_link_selector)
                    product_data["url"] = link_element.get_attribute("href")
                    product_data["title"] = link_element.text.strip()
                except NoSuchElementException:
                    print(f"Warning: Could not find any link for product {i+1}")

            try:
                # Extract SKU (Part Number) with enhanced parsing
                sku_element = None
                for sku_selector in scraping_config.product_sku_selectors:
                    try:
                        sku_element = card.find_element(By.CSS_SELECTOR, sku_selector)
                        break
                    except NoSuchElementException:
                        continue
                
                if sku_element:
                    extracted_sku = extract_sku_from_complex_html(sku_element)
                    
                    # Clean up the SKU text
                    if "Vendor Part #:" in extracted_sku:
                        product_data["part_number"] = extracted_sku.split("Vendor Part #:")[-1].strip()
                    elif "SKU:" in extracted_sku:
                        product_data["part_number"] = extracted_sku.split("SKU:")[-1].strip()
                    else:
                        product_data["part_number"] = extracted_sku
                else:
                    print(f"Warning: Could not find SKU for product {i+1}")
                    
            except Exception as e:
                print(f"Warning: Error extracting SKU for product {i+1}: {e}")

            try:
                # Extract Price using multiple selectors with enhanced parsing
                price_element = None
                for price_selector in scraping_config.product_price_selectors:
                    try:
                        price_element = card.find_element(By.CSS_SELECTOR, price_selector)
                        break
                    except NoSuchElementException:
                        continue
                
                if price_element:
                    extracted_price = extract_price_from_complex_html(price_element)
                    product_data["price"] = extracted_price
                else:
                    print(f"Warning: Could not find price for product {i+1}")
                    
            except Exception as e:
                print(f"Warning: Error extracting price for product {i+1}: {e}")

            try:
                # Extract Quantity using configured selectors
                quantity_element = None
                for quantity_selector in scraping_config.product_quantity_selectors:
                    try:
                        quantity_element = card.find_element(By.CSS_SELECTOR, quantity_selector)
                        break
                    except NoSuchElementException:
                        continue
                
                if quantity_element:
                    extracted_quantity = extract_quantity_from_html(quantity_element)
                    product_data["quantity"] = extracted_quantity
                else:
                    # Quantity might not always be available, so this is not an error
                    pass
                    
            except Exception as e:
                print(f"Warning: Error extracting quantity for product {i+1}: {e}")

            # Only add if we found at least a title or URL
            if product_data["title"] != "N/A" or product_data["url"] != "N/A":
                results.append(product_data)
                print(f"-- Scraped Product {i+1}: Title: {product_data['title'][:50]}{'...' if len(product_data['title']) > 50 else ''}")  # Truncate long titles
            else:
                print(f"-- Skipped Product {i+1} due to missing title and URL.")

    except TimeoutException:
        print(f"Error: Timed out waiting for elements during search for {search_term}")
    except Exception as e:
        print(f"An unexpected error occurred during scraping for {search_term}: {e}")

    return results

# Backward compatibility functions
def setup_driver():
    """Backward compatibility function - uses default Chrome config"""
    from config_loader import ChromeConfig
    
    default_chrome_config = ChromeConfig(
        chrome_driver_path=None,
        headless=True,
        window_size={"width": 1280, "height": 720},
        implicit_wait=3,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    
    return setup_driver_with_config(default_chrome_config)


def take_screenshot(driver, filename: str, description: str = ""):
    """Take a screenshot for debugging"""
    try:
        screenshot_dir = "debug_screenshots"
        os.makedirs(screenshot_dir, exist_ok=True)
        
        filepath = os.path.join(screenshot_dir, f"{filename}.png")
        driver.save_screenshot(filepath)
        print(f"📸 Screenshot saved: {filepath} ({description})")
        return filepath
    except Exception as e:
        print(f"Failed to take screenshot: {e}")
        return None


def scrape_tundra(driver, search_term: str) -> List[Dict[str, Any]]:
    """Backward compatibility function for existing code"""
    # Create a default TruckPro configuration for backward compatibility
    from config_loader import SiteConfig, ScrapingConfig, OutputConfig
    
    default_scraping_config = ScrapingConfig(
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
        no_results_selectors=[
            "div.message-alert.info.p-3.message-no-item-alert",
            "div.message-no-item-alert",
            "div.message-alert"
        ],
        max_results_per_query=10,
        wait_timeout=10,
        page_load_timeout=30
    )
    
    default_output_config = OutputConfig(
        output_file="scraped_results.json",
        detailed_output_file="detailed_results.json"
    )
    
    default_site_config = SiteConfig(
        site_name="TruckPro",
        target_url="https://www.truckpro.com/",
        search_tasks=[],
        inventory_test_cases=[],
        scraping_config=default_scraping_config,
        output_config=default_output_config
    )
    
    return scrape_site_with_config(driver, search_term, default_site_config)

if __name__ == "__main__":
    # Test the configurable scraper
    from config_loader import load_config_for_site
    
    try:
        # Load configuration for a specific site
        config = load_config_for_site("truckpro")
        
        search_queries = ["gasket", "BK608", "brake pads", "nonexistent_part"]
        all_results = {}

        print("Setting up WebDriver with configuration...")
        driver = setup_driver_with_config(config.chrome_config)

        if driver:
            try:
                for query in search_queries:
                    print(f"\n--- Starting scrape for: {query} ---")
                    scraped_data = scrape_site_with_config(driver, query, config.site_config)
                    all_results[query] = scraped_data
                    print(f"--- Finished scrape for: {query}, Found {len(scraped_data)} results ---")
                    time.sleep(config.deployment_config.delay_between_searches)

            finally:
                print("\nClosing WebDriver...")
                driver.quit()
                print("--- All scraping finished ---\n")

            # Save results to a JSON file
            output_file = "configurable_scraped_results.json"
            try:
                with open(output_file, "w") as f:
                    json.dump(all_results, f, indent=4)
                print(f"Results saved to {output_file}")
            except Exception as e:
                print(f"Error saving results: {e}")
        else:
            print("Could not start WebDriver. Scraping aborted.")
            
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure config.json exists and contains valid configuration.")