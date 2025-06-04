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
TARGET_URL = "https://www.tundrafmp.com/"
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
PRODUCT_TITLE_SELECTOR = "div.name.longName" # Specific element for title text
PRODUCT_SKU_SELECTOR = "span.sku-text" # Contains SKU, need to parse text
PRODUCT_PRICE_SELECTOR = "span.formatted-price" # Contains prices
MAX_RESULTS_PER_QUERY = 10 # Limit the number of results to scrape per search
WAIT_TIMEOUT = 60 # Increased timeout to 20 seconds
PAGE_LOAD_TIMEOUT = 90 # Timeout for initial page load

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
    chrome_options.add_argument("--disable-images")  # Optional: disable images for faster loading
    chrome_options.add_argument("--disable-javascript")  # Remove this if site needs JS
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
        driver.set_window_size(1920, 1080)  # Set window size for consistency
        driver.implicitly_wait(10)  # Set implicit wait
        
        print("WebDriver setup successful")
        return driver
        
    except Exception as e:
        print(f"Error setting up WebDriver: {e}")
        return None

def find_element_with_multiple_selectors(driver, selectors, by=By.CSS_SELECTOR, wait_for_interactable=False):
    """Try multiple selectors to find an element."""
    for selector in selectors:
        try:
            if wait_for_interactable:
                element = WebDriverWait(driver, WAIT_TIMEOUT).until(
                    EC.element_to_be_clickable((by, selector))
                )
            else:
                element = WebDriverWait(driver, WAIT_TIMEOUT).until(
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
            search_input = find_element_with_multiple_selectors(driver, SEARCH_INPUT_SELECTORS, wait_for_interactable=True)
            if not search_input:
                print("Error: Could not find search input with any selector")
                # Debug: print available input elements
                inputs = driver.find_elements(By.TAG_NAME, "input")
                print(f"Found {len(inputs)} input elements on page")
                for i, inp in enumerate(inputs[:5]):  # Show first 5
                    print(f"Input {i}: type='{inp.get_attribute('type')}', placeholder='{inp.get_attribute('placeholder')}', class='{inp.get_attribute('class')}'")
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
            search_button = find_element_with_multiple_selectors(driver, SEARCH_BUTTON_SELECTORS, by=By.XPATH)
            if not search_button:
                print("Error: Could not find search button with any selector")
                # Debug: print available button elements
                buttons = driver.find_elements(By.TAG_NAME, "button")
                print(f"Found {len(buttons)} button elements on page")
                for i, btn in enumerate(buttons[:5]):  # Show first 5
                    print(f"Button {i}: text='{btn.text}', class='{btn.get_attribute('class')}'")
                
                # Try pressing Enter instead
                try:
                    from selenium.webdriver.common.keys import Keys
                    search_input.send_keys(Keys.RETURN)
                    print("Pressed Enter to search instead of clicking button")
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
            # Wait longer for results to load
            time.sleep(5)
            
            product_card = find_element_with_multiple_selectors(driver, PRODUCT_CARD_SELECTORS)
            if not product_card:
                print("Error: Could not find product cards with any selector")
                # Print current URL to see if we're on the right page
                print(f"Current URL: {driver.current_url}")
                # Print partial page source for debugging
                page_source = driver.page_source
                print(f"Page source length: {len(page_source)}")
                if "no results" in page_source.lower() or "not found" in page_source.lower():
                    print("No search results found for this query")
                return results
                
            print("Search results page loaded")
            time.sleep(2)  # Allow dynamic content to load
            
        except Exception as e:
            print(f"Error waiting for results: {e}")
            return results

        # Find all product cards
        product_cards = driver.find_elements(By.CSS_SELECTOR, PRODUCT_CARD_SELECTORS[0])
        print(f"Found {len(product_cards)} potential product cards.")

        # Extract data from each card
        for i, card in enumerate(product_cards):
            if i >= MAX_RESULTS_PER_QUERY:
                break
            
            product_data = {
                "title": "N/A",
                "part_number": "N/A",
                "url": "N/A",
                "price": "N/A",
                "description": "N/A"
            }

            try:
                # Extract Title and URL from the main product link
                link_element = card.find_element(By.CSS_SELECTOR, PRODUCT_LINK_SELECTOR + " " + PRODUCT_TITLE_SELECTOR)
                product_data["title"] = link_element.text.strip()
                # Get URL from the parent 'a' tag
                url_element = link_element.find_element(By.XPATH, "./ancestor::a")
                product_data["url"] = url_element.get_attribute("href")
                
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
                # Extract SKU (Part Number)
                sku_element = card.find_element(By.CSS_SELECTOR, PRODUCT_SKU_SELECTOR)
                sku_text = sku_element.text.strip()
                if "SKU:" in sku_text:
                    product_data["part_number"] = sku_text.split("SKU:")[-1].strip()
                else:
                    product_data["part_number"] = sku_text
            except NoSuchElementException:
                print(f"Warning: Could not find SKU for product {i+1}")

            try:
                # Extract Price
                price_element = card.find_element(By.CSS_SELECTOR, PRODUCT_PRICE_SELECTOR)
                product_data["price"] = price_element.text.strip()
            except NoSuchElementException:
                print(f"Warning: Could not find price for product {i+1}")

            # Only add if we found at least a title or URL
            if product_data["title"] != "N/A" or product_data["url"] != "N/A":
                results.append(product_data)
                print(f"-- Scraped Product {i+1}: Title: {product_data['title']}")
            else:
                print(f"-- Skipped Product {i+1} due to missing title and URL.")

    except TimeoutException:
        print(f"Error: Timed out waiting for elements during search for {search_term}")
    except Exception as e:
        print(f"An unexpected error occurred during scraping for {search_term}: {e}")

    return results

if __name__ == "__main__":
    search_queries = ["gasket", "BK608", "brake pads toyota camry"]
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
                time.sleep(2)  # Delay between searches

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