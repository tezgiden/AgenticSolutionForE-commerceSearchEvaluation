# Test Cases for Agentic Search Solution

import unittest
import json
import os
from unittest.mock import patch, MagicMock
from selenium.webdriver.common.by import By # Import By
from scraper import setup_driver, scrape_tundra, PRODUCT_LINK_SELECTOR, PRODUCT_TITLE_SELECTOR, PRODUCT_SKU_SELECTOR, PRODUCT_PRICE_SELECTOR
from llm_evaluator import evaluate_search_results, classify_search_type
import main # Import the main module
from main import run_agentic_search

class TestSearchTypeClassification(unittest.TestCase):
    """Test the search type classification logic"""
    
    def test_english_word_classification(self):
        """Test that single English words are classified correctly"""
        self.assertEqual(classify_search_type("gasket"), "english_word")
        self.assertEqual(classify_search_type("alternator"), "english_word")
        self.assertEqual(classify_search_type("refrigerator"), "english_word")
    
    def test_part_number_classification(self):
        """Test that part numbers are classified correctly"""
        self.assertEqual(classify_search_type("BK608"), "part_number")
        self.assertEqual(classify_search_type("513188"), "part_number")
        self.assertEqual(classify_search_type("HB88548"), "part_number")
        self.assertEqual(classify_search_type("12-345"), "part_number")
    
    def test_multiple_terms_classification(self):
        """Test that multiple term queries are classified correctly"""
        self.assertEqual(classify_search_type("brake pads toyota camry"), "multiple_terms")
        self.assertEqual(classify_search_type("fuel pump assembly"), "multiple_terms")
        self.assertEqual(classify_search_type("commercial refrigerator parts"), "multiple_terms")

class TestScraperFunctionality(unittest.TestCase):
    """Test the web scraping functionality"""
    
    @patch("scraper.webdriver.Chrome")
    def test_scraper_setup(self, mock_chrome):
        """Test that the WebDriver setup works correctly"""
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        driver = setup_driver()
        self.assertIsNotNone(driver)
    
    @patch("scraper.webdriver.Chrome")
    def test_scraper_search(self, mock_chrome):
        """Test that the scraper can perform a search and extract results"""
        # Mock the WebDriver and its methods
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        # Mock finding elements
        mock_product_card = MagicMock(name="ProductCard")
        mock_title_element = MagicMock(name="TitleElement")
        mock_title_element.text = "Test Product"

        mock_url_ancestor_link = MagicMock(name="AncestorLink")
        mock_url_ancestor_link.get_attribute.return_value = "https://example.com/product"
        # Mock the XPath lookup relative to the title element
        mock_title_element.find_element.return_value = mock_url_ancestor_link 

        mock_sku_element = MagicMock(name="SkuElement")
        mock_sku_element.text = "SKU: 12345"

        mock_price_element = MagicMock(name="PriceElement")
        mock_price_element.text = "$99.99"

        # Define actual selectors used in scraper.py
        title_selector = PRODUCT_LINK_SELECTOR + " " + PRODUCT_TITLE_SELECTOR
        sku_selector = PRODUCT_SKU_SELECTOR
        price_selector = PRODUCT_PRICE_SELECTOR

        # Configure mock_product_card.find_element
        def card_find_element_side_effect(by, selector):
            # print(f"Mock card.find_element called with selector: {selector}") # Debug print
            if selector == title_selector:
                return mock_title_element
            elif selector == sku_selector:
                return mock_sku_element
            elif selector == price_selector:
                return mock_price_element
            else:
                # Handle fallback or other selectors if necessary
                # print(f"Unhandled selector in mock: {selector}")
                # For the URL ancestor lookup from title element, it's handled above
                # For the fallback link selector, return a basic mock link
                if selector == PRODUCT_LINK_SELECTOR:
                    mock_fallback_link = MagicMock(name="FallbackLink")
                    mock_fallback_link.get_attribute.return_value = "https://fallback.com"
                    mock_fallback_link.text = "Fallback Title"
                    return mock_fallback_link
                return MagicMock(name=f"UnhandledMock_{selector.replace('.', '_')}") # Return a default mock for unhandled cases

        mock_product_card.find_element.side_effect = card_find_element_side_effect

        # Mock driver.find_elements to return the mocked card
        mock_driver.find_elements.return_value = [mock_product_card]
        
        # Call the function with our mocked driver
        results = scrape_tundra(mock_driver, "test")
        
        # Verify the results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Test Product")
        self.assertEqual(results[0]["url"], "https://example.com/product")
        self.assertIn("12345", results[0]["part_number"])
        self.assertEqual(results[0]["price"], "$99.99")

class TestLLMEvaluation(unittest.TestCase):
    """Test the LLM evaluation functionality"""
    
    @patch("llm_evaluator.query_ollama")
    def test_evaluation_english_word(self, mock_query_ollama):
        """Test evaluation of English word search results"""
        # Mock the LLM response
        mock_query_ollama.return_value = {
            "response": """
            {
              "evaluations": [
                {
                  "result_index": 0,
                  "relevance": "High",
                  "justification": "The product is a gasket, which directly matches the search term."
                }
              ]
            }
            """
        }
        
        # Sample search results
        results = [{
            "title": "Southbend - 1187010 - Gasket",
            "part_number": "1187010",
            "url": "https://www.example.com/gasket1",
            "price": "$10.99"
        }]
        
        # Call the function
        evaluation = evaluate_search_results("gasket", results, "english_word")
        
        # Verify the evaluation
        self.assertEqual(evaluation["status"], "success")
        self.assertEqual(len(evaluation["evaluations"]), 1)
        self.assertEqual(evaluation["evaluations"][0]["relevance"], "High")

class TestEndToEndWorkflow(unittest.TestCase):
    """Test the end-to-end workflow"""
    
    @patch("main.setup_driver")
    @patch("main.scrape_tundra")
    @patch("main.evaluate_search_results")
    def test_run_agentic_search(self, mock_evaluate, mock_scrape, mock_setup):
        """Test that the main workflow runs correctly"""
        # Mock the driver setup
        mock_driver = MagicMock()
        mock_setup.return_value = mock_driver
        
        # Mock the scraper results
        mock_scrape.return_value = [{
            "title": "Test Product",
            "part_number": "12345",
            "url": "https://example.com/product",
            "price": "$99.99"
        }]
        
        # Mock the evaluation results
        mock_evaluate.return_value = {
            "status": "success",
            "evaluations": [{
                "result_index": 0,
                "relevance": "High",
                "justification": "Test justification"
            }]
        }
        
        # Run the function
        run_agentic_search()
        
        # Verify the function calls
        mock_setup.assert_called_once()
        # Use main.INPUT_SEARCH_TASKS imported from the main module
        self.assertEqual(mock_scrape.call_count, len(main.INPUT_SEARCH_TASKS))
        self.assertEqual(mock_evaluate.call_count, len(main.INPUT_SEARCH_TASKS))
        
        # Verify the output file was created
        # Use main.OUTPUT_FILE imported from the main module
        self.assertTrue(os.path.exists(main.OUTPUT_FILE))
        
        # Clean up
        if os.path.exists(main.OUTPUT_FILE):
            os.remove(main.OUTPUT_FILE)

if __name__ == "__main__":
    unittest.main()
