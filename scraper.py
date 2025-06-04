# Web Scraping Module (Python + Selenium)

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
    ".search-bar__button",
    "//button[normalize-space()=\"Search\"]",
    "//button[contains(@class, 'search')]",
    "button.search-button"
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
    """Sets up the Selenium WebDriver."""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--ignore-ssl-errors")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--dns-prefetch-disable")
    chrome_options.add_argument("--disable-features=NetworkService")
    chrome_options.add_argument("--disable-gpu-sandbox")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--no-zygote")
    chrome_options.add_argument("--single-process")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Add experimental options
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    try:
        # Try using webdriver_manager if path is not specified
        if CHROME_DRIVER_PATH is None:
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
            except ImportError:
                print("webdriver-manager not installed. Please install it (`pip install webdriver-manager`) or specify CHROME_DRIVER_PATH.")
                return None
        else:
            service = Service(CHROME_DRIVER_PATH)
        
        driver = webdriver.Chrome(service=service, options=chrome_options)
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
    return None

def scrape_tundra(driver, search_term):
    """Performs a search and scrapes results from tundrafmp.com."""
    results = []
    try:
        # Set page load timeout
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        
        # Navigate to the page with error handling
        try:
            driver.get(TARGET_URL)
            print(f"Navigated to {TARGET_URL}")
            # Print page title for debugging
            print(f"Page title: {driver.title}")
            # Add a small delay to ensure page is fully loaded
            time.sleep(3)
        except Exception as e:
            print(f"Error loading page: {e}")
            return results

        # Wait for search input and enter search term with better error handling
        try:
            search_input = find_element_with_multiple_selectors(driver, SEARCH_INPUT_SELECTORS, wait_for_interactable=True)
            if not search_input:
                print("Error: Could not find search input with any selector")
                return results
                
            search_input.clear()
            search_input.send_keys(search_term)
            print(f"Entered search term: {search_term}")
        except Exception as e:
            print(f"Error entering search term: {e}")
            return results

        # Find and click search button with better error handling
        try:
            search_button = find_element_with_multiple_selectors(driver, SEARCH_BUTTON_SELECTORS, by=By.XPATH)
            if not search_button:
                print("Error: Could not find search button with any selector")
                return results
                
            search_button.click()
            print("Clicked search button")
        except Exception as e:
            print(f"Error clicking search button: {e}")
            return results

        # Wait for results with better error handling
        try:
            product_card = find_element_with_multiple_selectors(driver, PRODUCT_CARD_SELECTORS)
            if not product_card:
                print("Error: Could not find product cards with any selector")
                # Print page source for debugging
                print("Current page source:")
                print(driver.page_source[:500] + "...")  # Print first 500 chars
                return results
                
            print("Search results page loaded")
            time.sleep(2) # Allow dynamic content to potentially load
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
                "description": "N/A" # Description not readily available in card, maybe on product page
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
                    # Title might be inside this link directly or nested differently
                    # This part might need refinement based on more examples
                    product_data["title"] = link_element.text.strip() # Fallback title
                except NoSuchElementException:
                     print(f"Warning: Could not find any link for product {i+1}")


            try:
                # Extract SKU (Part Number)
                sku_element = card.find_element(By.CSS_SELECTOR, PRODUCT_SKU_SELECTOR)
                sku_text = sku_element.text.strip()
                # Assuming format "SKU: XXXXXX"
                if "SKU:" in sku_text:
                    product_data["part_number"] = sku_text.split("SKU:")[-1].strip()
                else:
                    product_data["part_number"] = sku_text # Use raw text if format differs
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
        print(f"Error: Timed out waiting for elements during search for 	{search_term}")
    except Exception as e:
        print(f"An unexpected error occurred during scraping for 	{search_term}	: {e}")

    return results

if __name__ == "__main__":
    search_queries = ["gasket", "BK608", "brake pads toyota camry"]
    all_results = {}

    driver = setup_driver()

    if driver:
        for query in search_queries:
            print(f"\n--- Starting scrape for: {query} ---")
            scraped_data = scrape_tundra(driver, query)
            all_results[query] = scraped_data
            print(f"--- Finished scrape for: {query}, Found {len(scraped_data)} results ---")
            time.sleep(1) # Small delay between searches

        driver.quit()
        print("\n--- All scraping finished --- \n")

        # Save results to a JSON file
        output_file = "scraped_results.json"
        with open(output_file, "w") as f:
            json.dump(all_results, f, indent=4)
        print(f"Results saved to {output_file}")
    else:
        print("Could not start WebDriver. Scraping aborted.")


