# Web Scraping Module (Python + Selenium) - FIXED VERSION

import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# --- Configuration ---
# Assuming chromedriver is installed and in PATH or specify path
# service = Service("/path/to/chromedriver")
CHROME_DRIVER_PATH = None # Set to None to use webdriver-manager or specify path
TARGET_URL = "https://www.truckpro.com/" #"https://www.tundrafmp.com/"
# Updated selectors with multiple options
SEARCH_INPUT_SELECTORS = [
    "#searchInput",
    "input[placeholder=\"Search name, sku, item #\"]",
    "input[type=\"search\"]",
    "input.search-input"
]
SEARCH_BUTTON_SELECTORS = [
    "//button[contains(@class, 'search-bar__button')]",
    "//button[normalize-space()=\"Search\"]",
    "//button[contains(@class, 'search')]",
    "//button[contains(@class, 'search-button')]"
]
PRODUCT_CARD_SELECTORS = [
    "div.productlist",
    "div.product-card",
    "div.search-result-item"
]
PRODUCT_LINK_SELECTOR = "a.link" # Contains title and href
PRODUCT_TITLE_SELECTOR = ["div.name.longName", "h3.name.longName"] # Specific element for title text
PRODUCT_SKU_SELECTOR = ["span.sku-text", "span.vendor-value"] # Contains SKU, need to parse text
PRODUCT_PRICE_SELECTOR = ["span.formatted-price", "div.price-wrapper"] # Contains prices
PRODUCT_QUANTITY_SELECTOR = ["span.inventory-available"] # Contains available quantity
NO_RESULTS_SELECTORS = [
    "div.message-alert.info.p-3.message-no-item-alert",
    "div.message-no-item-alert",
    "div.message-alert"
] # Elements that indicate no search results found
MAX_RESULTS_PER_QUERY = 10 # Limit the number of results to scrape per search
WAIT_TIMEOUT = 10 # Reduced from 60 seconds
PAGE_LOAD_TIMEOUT = 30 # Reduced from 90 seconds

def setup_driver():
    """Sets up the Selenium WebDriver with improved Chrome options."""
    chrome_options = Options()
    
    # Basic headless configuration
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # GPU and rendering fixes - MAIN FIX FOR YOUR ERRORS
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-gpu-sandbox")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-3d-apis")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-features=TranslateUI")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("--disable-features=VizServiceDisplayCompositor")
    chrome_options.add_argument("--use-gl=disabled")  # Disable OpenGL
    chrome_options.add_argument("--disable-gl-drawing-for-tests")
    
    # Proxy resolver fix - FIXES THE V8 PROXY RESOLVER ERROR
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
    chrome_options.add_argument("--disable-images")  # Disable images for faster loading
    chrome_options.add_argument("--disable-javascript")  # Remove this line - site likely needs JS
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--no-default-browser-check")
    chrome_options.add_argument("--disable-default-apps")
    
    # Memory and process management
    chrome_options.add_argument("--memory-pressure-off")
    chrome_options.add_argument("--max_old_space_size=4096")
    
    # User agent
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
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
        if CHROME_DRIVER_PATH is None:
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                print("Using webdriver-manager to install Chrome driver")
            except ImportError:
                print("webdriver-manager not installed. Please install it (`pip install webdriver-manager`) or specify CHROME_DRIVER_PATH.")
                return None
        else:
            service = Service(CHROME_DRIVER_PATH)
        
        # Add service arguments to reduce logging
        service.creation_flags = 0x08000000  # CREATE_NO_WINDOW flag for Windows
        
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Additional driver configuration
        driver.set_window_size(1280, 720)  # Smaller window size for better performance
        driver.implicitly_wait(3)  # Reduced implicit wait
        
        print("WebDriver setup successful")
        return driver
        
    except Exception as e:
        print(f"Error setting up WebDriver: {e}")
        return None

def check_for_no_results(driver, search_term):
    """Check if the search returned no results using multiple selectors."""
    try:
        for no_results_selector in NO_RESULTS_SELECTORS:
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
        
        # Method 3: Fallback to getting all text and cleaning it
        full_text = vendor_value.text.strip()
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
                return ''.join(price_parts[:2])  # Usually $XX and .YY
        
        # Method 2: Simple text extraction
        return price_element.text.strip()
        
    except Exception:
        return price_element.text.strip()

def extract_quantity_from_html(quantity_element):
    """Extract quantity from inventory HTML."""
    try:
        # Get the numeric value from inventory-available span
        return quantity_element.text.strip()
    except Exception:
        return "N/A"
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

def scrape_tundra(driver, search_term):
    """Performs a search and scrapes results from tundrafmp.com."""
    results = []
    try:
        # Set page load timeout
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        
        # Navigate to the page with error handling
        try:
            print(f"Navigating to {TARGET_URL}")
            driver.get(TARGET_URL)
            print(f"Successfully navigated to {TARGET_URL}")
            
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
            search_input = find_element_with_multiple_selectors(driver, SEARCH_INPUT_SELECTORS, wait_for_interactable=True, timeout=10)
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
            search_button = find_element_with_multiple_selectors(driver, SEARCH_BUTTON_SELECTORS, by=By.XPATH, timeout=5)
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
            if check_for_no_results(driver, search_term):
                print(f"Search for '{search_term}' returned no results.")
                return results  # Return empty results list
            
            product_card = find_element_with_multiple_selectors(driver, PRODUCT_CARD_SELECTORS, timeout=8)
            if not product_card:
                print("Error: Could not find product cards with any selector")
                print(f"Current URL: {driver.current_url}")
                
                # Double-check for no results message after waiting
                if check_for_no_results(driver, search_term):
                    print(f"Confirmed: Search for '{search_term}' returned no results.")
                    return results
                    
                return results
                
            print("Search results page loaded")
            
        except Exception as e:
            print(f"Error waiting for results: {e}")
            return results

        # Find all product cards
        product_cards = driver.find_elements(By.CSS_SELECTOR, PRODUCT_CARD_SELECTORS[0])
        print(f"Found {len(product_cards)} potential product cards.")
        
        # If no product cards found, do final check for no results message
        if len(product_cards) == 0:
            if check_for_no_results(driver, search_term):
                print(f"Final confirmation: No results found for '{search_term}'")
                return results
            else:
                print("No product cards found, but no 'no results' message detected either.")
                return results

        # Extract data from each card
        for i, card in enumerate(product_cards):
            if i >= MAX_RESULTS_PER_QUERY:
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
                # First try to find the title element using multiple selectors
                title_element = None
                for title_selector in PRODUCT_TITLE_SELECTOR:
                    try:
                        title_element = card.find_element(By.CSS_SELECTOR, PRODUCT_LINK_SELECTOR + " " + title_selector)
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
                    link_element = card.find_element(By.CSS_SELECTOR, PRODUCT_LINK_SELECTOR)
                    product_data["url"] = link_element.get_attribute("href")
                    
                    # Try each title selector directly in the link
                    for title_selector in PRODUCT_TITLE_SELECTOR:
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
                    link_element = card.find_element(By.CSS_SELECTOR, PRODUCT_LINK_SELECTOR)
                    product_data["url"] = link_element.get_attribute("href")
                    product_data["title"] = link_element.text.strip()
                except NoSuchElementException:
                    print(f"Warning: Could not find any link for product {i+1}")

            try:
                # Extract SKU (Part Number) with enhanced parsing
                sku_element = None
                for sku_selector in PRODUCT_SKU_SELECTOR:
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
                for price_selector in PRODUCT_PRICE_SELECTOR:
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
                # Extract Quantity (New field)
                quantity_element = None
                for quantity_selector in PRODUCT_QUANTITY_SELECTOR:
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

if __name__ == "__main__":
    # Include a test case with no results to verify the detection works
    search_queries = ["gasket", "BK608", "brake pads toyota camry", "asdsadasdsad"]
    all_results = {}

    print("Setting up WebDriver...")
    driver = setup_driver()

    if driver:
        try:
            for query in search_queries:
                print(f"\n--- Starting scrape for: {query} ---")
                scraped_data = scrape_tundra(driver, query)
                all_results[query] = scraped_data
                print(f"--- Finished scrape for: {query}, Found {len(scraped_data)} results ---")
                time.sleep(1)  # Reduced delay between searches

        finally:
            print("\nClosing WebDriver...")
            driver.quit()
            print("--- All scraping finished ---\n")

        # Save results to a JSON file
        output_file = "scraped_results.json"
        try:
            with open(output_file, "w") as f:
                json.dump(all_results, f, indent=4)
            print(f"Results saved to {output_file}")
        except Exception as e:
            print(f"Error saving results: {e}")
    else:
        print("Could not start WebDriver. Scraping aborted.")