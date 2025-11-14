#!/usr/bin/env python3
"""
Debug Scraper Test Script

This script helps debug scraping issues by:
1. Testing with a single query
2. Enabling detailed debug output
3. Taking screenshots at key steps
4. Showing detailed element inspection

Usage:
    python debug_scraper.py --site truckpro --query "4707Q"
    python debug_scraper.py --site truckpro --query "brake pad" --take-screenshots
"""

import os
import sys
import argparse
import time
from config_loader import load_config_for_site, get_available_sites
from scraper import setup_driver_with_config, scrape_site_with_config

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

def debug_page_elements(driver, description: str = ""):
    """Debug current page elements"""
    try:
        print(f"\n=== DEBUG: {description} ===")
        print(f"Current URL: {driver.current_url}")
        print(f"Page Title: {driver.title}")
        
        # Check for common elements
        element_checks = [
            ("input", "Input elements"),
            ("button", "Button elements"), 
            ("a", "Link elements"),
            ("div[class*='product']", "Product-like divs"),
            ("div[class*='result']", "Result-like divs"),
            (".modal", "Modal elements"),
            (".popup", "Popup elements")
        ]
        
        for selector, desc in element_checks:
            try:
                elements = driver.find_elements("css selector", selector) if selector.startswith(('.', '#', '[')) else driver.find_elements("tag name", selector)
                print(f"{desc}: {len(elements)} found")
                
                if len(elements) > 0 and len(elements) <= 5:  # Show details for small numbers
                    for i, elem in enumerate(elements):
                        try:
                            tag = elem.tag_name
                            classes = elem.get_attribute("class") or ""
                            id_attr = elem.get_attribute("id") or ""
                            text = elem.text.strip()[:50] if elem.text else ""
                            
                            if selector == "input":
                                input_type = elem.get_attribute("type") or ""
                                placeholder = elem.get_attribute("placeholder") or ""
                                name = elem.get_attribute("name") or ""
                                print(f"  [{i}] <{tag}> type='{input_type}' name='{name}' placeholder='{placeholder}' class='{classes}' id='{id_attr}'")
                            elif selector == "button":
                                print(f"  [{i}] <{tag}> text='{text}' class='{classes}' id='{id_attr}'")
                            elif selector == "a":
                                href = elem.get_attribute("href") or ""
                                print(f"  [{i}] <{tag}> href='{href[:50]}' text='{text}' class='{classes}'")
                            else:
                                print(f"  [{i}] <{tag}> text='{text}' class='{classes}' id='{id_attr}'")
                        except:
                            print(f"  [{i}] <{tag}> (error getting details)")
                            
            except Exception as e:
                print(f"{desc}: Error - {e}")
        
        print(f"=== END DEBUG ===\n")
        
    except Exception as e:
        print(f"Debug error: {e}")

def run_debug_scraping(site_key: str, query: str, take_screenshots: bool = False, config_path: str = "config.json"):
    """Run debug scraping for a single query"""
    
    try:
        # Load configuration
        print(f"Loading configuration for site: {site_key}")
        config = load_config_for_site(site_key, config_path)
        
        print(f"Site: {config.site_config.site_name}")
        print(f"URL: {config.site_config.target_url}")
        print(f"Debug Query: '{query}'")
        print(f"Screenshots: {'Enabled' if take_screenshots else 'Disabled'}")
        
        # Setup WebDriver
        print("\nSetting up WebDriver...")
        driver = setup_driver_with_config(config.chrome_config)
        
        if not driver:
            print("❌ Failed to setup WebDriver")
            return False
        
        try:
            print("✅ WebDriver setup successful")
            
            # Initial page load
            print(f"\n📍 STEP 1: Loading initial page")
            driver.get(config.site_config.target_url)
            
            if take_screenshots:
                take_screenshot(driver, "01_initial_page", "Initial page load")
            
            debug_page_elements(driver, "After initial page load")
            
            # Wait and handle modals
            print(f"\n📍 STEP 2: Handling modals and popups")
            time.sleep(3)
            
            # Import the modal handler
            from scraper import handle_modal_popups
            handle_modal_popups(driver)
            
            if take_screenshots:
                take_screenshot(driver, "02_after_modal_handling", "After modal handling")
            
            debug_page_elements(driver, "After modal handling")
            
            # Search input
            print(f"\n📍 STEP 3: Finding search input")
            search_selectors = config.site_config.scraping_config.search_input_selectors
            print(f"Trying selectors: {search_selectors}")
            
            search_input = None
            from scraper import find_element_with_multiple_selectors
            from selenium.webdriver.common.by import By
            
            search_input = find_element_with_multiple_selectors(
                driver, search_selectors, wait_for_interactable=True, timeout=10
            )
            
            if search_input:
                print("✅ Found search input")
                search_input.clear()
                search_input.send_keys(query)
                print(f"✅ Entered query: '{query}'")
                
                if take_screenshots:
                    take_screenshot(driver, "03_search_entered", "After entering search query")
            else:
                print("❌ Could not find search input")
                debug_page_elements(driver, "Search input not found")
                return False
            
            # Search button
            print(f"\n📍 STEP 4: Finding and clicking search button")
            button_selectors = config.site_config.scraping_config.search_button_selectors
            print(f"Trying selectors: {button_selectors}")
            
            search_button = find_element_with_multiple_selectors(
                driver, button_selectors, by=By.XPATH, timeout=5
            )
            
            if search_button:
                print("✅ Found search button")
                try:
                    # Try direct click first
                    search_button.click()
                    print("✅ Clicked search button")
                except Exception as click_error:
                    print(f"⚠️ Direct click failed: {click_error}")
                    try:
                        # Try JavaScript click
                        driver.execute_script("arguments[0].click();", search_button)
                        print("✅ Used JavaScript click")
                    except Exception as js_error:
                        print(f"⚠️ JavaScript click failed: {js_error}")
                        # Use Enter key
                        from selenium.webdriver.common.keys import Keys
                        search_input.send_keys(Keys.RETURN)
                        print("✅ Used Enter key")
            else:
                print("⚠️ Search button not found, using Enter key")
                from selenium.webdriver.common.keys import Keys
                search_input.send_keys(Keys.RETURN)
            
            if take_screenshots:
                take_screenshot(driver, "04_search_submitted", "After submitting search")
            
            # Wait for results
            print(f"\n📍 STEP 5: Waiting for search results")
            time.sleep(5)  # Wait longer for debug
            
            debug_page_elements(driver, "After search submission")
            
            if take_screenshots:
                take_screenshot(driver, "05_search_results", "Search results page")
            
            # Look for product cards
            print(f"\n📍 STEP 6: Looking for product cards")
            card_selectors = config.site_config.scraping_config.product_card_selectors
            print(f"Trying selectors: {card_selectors}")
            
            found_cards = False
            product_cards = []
            
            for selector in card_selectors:
                try:
                    cards = driver.find_elements(By.CSS_SELECTOR, selector)
                    if cards:
                        product_cards = cards
                        print(f"✅ Found {len(cards)} product cards with selector: {selector}")
                        found_cards = True
                        break
                except Exception as e:
                    print(f"❌ Selector '{selector}' failed: {e}")
            
            if not found_cards:
                print("❌ No product cards found with configured selectors")
                
                # Try some common alternatives
                alternative_selectors = [
                    "div[class*='product']",
                    "div[class*='item']",
                    "div[class*='result']",
                    "article",
                    "li[class*='product']"
                ]
                
                print("Trying alternative selectors...")
                for alt_selector in alternative_selectors:
                    try:
                        alt_cards = driver.find_elements(By.CSS_SELECTOR, alt_selector)
                        if alt_cards:
                            print(f"🔍 Found {len(alt_cards)} elements with '{alt_selector}'")
                    except:
                        continue
                
                return False
            
            # Test data extraction on first few cards
            print(f"\n📍 STEP 7: Testing data extraction")
            
            from scraper import extract_product_data_enhanced
            
            for i, card in enumerate(product_cards[:3]):  # Test first 3 cards
                print(f"\nTesting card {i+1}:")
                
                try:
                    product_data = extract_product_data_enhanced(
                        card, i+1, config.site_config.scraping_config, debug=True
                    )
                    
                    print(f"Extracted data:")
                    for key, value in product_data.items():
                        print(f"  {key}: {value}")
                        
                except Exception as e:
                    print(f"❌ Error extracting data from card {i+1}: {e}")
            
            # Full scraping test
            print(f"\n📍 STEP 8: Running full scraping function")
            
            # Reset to initial page for clean test
            driver.get(config.site_config.target_url)
            time.sleep(2)
            
            results = scrape_site_with_config(driver, query, config.site_config, debug_mode=True)
            
            print(f"\n🎯 FINAL RESULTS:")
            print(f"Total results extracted: {len(results)}")
            
            for i, result in enumerate(results):
                print(f"\nResult {i+1}:")
                for key, value in result.items():
                    if key == "title" and len(str(value)) > 50:
                        value = str(value)[:50] + "..."
                    print(f"  {key}: {value}")
            
            if take_screenshots:
                take_screenshot(driver, "06_final_results", "Final results")
            
            return len(results) > 0
            
        finally:
            print("\n🔚 Closing WebDriver...")
            driver.quit()
            
    except Exception as e:
        print(f"❌ Debug scraping failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description="Debug Scraper Test Script")
    parser.add_argument("--site", type=str, required=True, help="Site configuration key")
    parser.add_argument("--query", type=str, required=True, help="Search query to test")
    parser.add_argument("--config", type=str, default="config.json", help="Configuration file path")
    parser.add_argument("--take-screenshots", action="store_true", help="Take screenshots at each step")
    
    args = parser.parse_args()
    
    # Validate site
    available_sites = get_available_sites(args.config)
    if args.site not in available_sites:
        print(f"❌ Site '{args.site}' not found. Available sites: {available_sites}")
        sys.exit(1)
    
    print("🐛 DEBUG SCRAPER TEST SCRIPT")
    print("=" * 50)
    
    success = run_debug_scraping(
        args.site, 
        args.query, 
        args.take_screenshots, 
        args.config
    )
    
    if success:
        print("\n✅ Debug scraping completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Debug scraping failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()