"""Testing utilities for web scraping components."""

import json
import time
import logging
from typing import Dict, List, Any, Optional, Callable
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass
from pathlib import Path

from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.webdriver import WebDriver

from config.config_models import SiteConfig, ScrapingConfig, ChromeConfig, OutputConfig
from data_extractor import ScrapingResult
from exceptions import ScrapingError


logger = logging.getLogger(__name__)


@dataclass
class MockElementData:
    """Data class for mock web element configuration."""
    
    tag_name: str = "div"
    text: str = ""
    attributes: Dict[str, str] = None
    is_displayed: bool = True
    is_enabled: bool = True
    children: List['MockElementData'] = None
    
    def __post_init__(self):
        """Post initialization setup."""
        if self.attributes is None:
            self.attributes = {}
        if self.children is None:
            self.children = []


class MockWebElement:
    """Mock WebElement for testing."""
    
    def __init__(self, mock_data: MockElementData):
        """Initialize mock web element.
        
        Args:
            mock_data: Configuration for the mock element
        """
        self.mock_data = mock_data
        self._children = [MockWebElement(child) for child in mock_data.children]
    
    @property
    def tag_name(self) -> str:
        """Get tag name."""
        return self.mock_data.tag_name
    
    @property
    def text(self) -> str:
        """Get element text."""
        return self.mock_data.text
    
    def get_attribute(self, name: str) -> Optional[str]:
        """Get attribute value.
        
        Args:
            name: Attribute name
            
        Returns:
            Attribute value or None
        """
        return self.mock_data.attributes.get(name)
    
    def is_displayed(self) -> bool:
        """Check if element is displayed."""
        return self.mock_data.is_displayed
    
    def is_enabled(self) -> bool:
        """Check if element is enabled."""
        return self.mock_data.is_enabled
    
    def find_element(self, by, value) -> 'MockWebElement':
        """Find child element."""
        # Simple implementation - return first child if any
        if self._children:
            return self._children[0]
        raise Exception("Element not found")
    
    def find_elements(self, by, value) -> List['MockWebElement']:
        """Find child elements."""
        return self._children
    
    def click(self) -> None:
        """Mock click action."""
        pass
    
    def clear(self) -> None:
        """Mock clear action."""
        pass
    
    def send_keys(self, keys) -> None:
        """Mock send keys action."""
        pass


class MockWebDriver:
    """Mock WebDriver for testing."""
    
    def __init__(self, mock_page_source: str = "", mock_url: str = "http://example.com"):
        """Initialize mock driver.
        
        Args:
            mock_page_source: Mock page source HTML
            mock_url: Mock current URL
        """
        self.page_source = mock_page_source
        self.current_url = mock_url
        self.title = "Mock Page Title"
        self._elements = {}
        self._quit_called = False
    
    def get(self, url: str) -> None:
        """Mock navigation."""
        self.current_url = url
    
    def quit(self) -> None:
        """Mock quit."""
        self._quit_called = True
    
    def find_element(self, by, value) -> MockWebElement:
        """Mock find element."""
        if value in self._elements:
            return self._elements[value]
        raise Exception("Element not found")
    
    def find_elements(self, by, value) -> List[MockWebElement]:
        """Mock find elements."""
        if value in self._elements:
            element = self._elements[value]
            return [element] if isinstance(element, MockWebElement) else element
        return []
    
    def execute_script(self, script: str, *args) -> Any:
        """Mock script execution."""
        if "document.readyState" in script:
            return "complete"
        return None
    
    def save_screenshot(self, filename: str) -> bool:
        """Mock screenshot."""
        return True
    
    def set_page_load_timeout(self, timeout: int) -> None:
        """Mock timeout setting."""
        pass
    
    def set_window_size(self, width: int, height: int) -> None:
        """Mock window size setting."""
        pass
    
    def implicitly_wait(self, timeout: int) -> None:
        """Mock implicit wait."""
        pass
    
    def add_mock_element(self, selector: str, element: MockWebElement) -> None:
        """Add a mock element for a specific selector.
        
        Args:
            selector: CSS selector or XPath
            element: Mock element to return
        """
        self._elements[selector] = element
    
    def add_mock_elements(self, selector: str, elements: List[MockWebElement]) -> None:
        """Add mock elements for a specific selector.
        
        Args:
            selector: CSS selector or XPath
            elements: List of mock elements to return
        """
        self._elements[selector] = elements


class TestDataGenerator:
    """Generates test data for scraping tests."""
    
    @staticmethod
    def create_product_card_element(
        title: str = "Test Product",
        part_number: str = "TEST123",
        price: str = "$19.99",
        url: str = "http://example.com/product/test123",
        quantity: str = "5",
        **kwargs
    ) -> MockWebElement:
        """Create a mock product card element.
        
        Args:
            title: Product title
            part_number: Product part number
            price: Product price
            url: Product URL
            quantity: Product quantity
            **kwargs: Additional attributes
            
        Returns:
            Mock product card element
        """
        # Create child elements
        title_element = MockElementData(
            tag_name="div",
            text=title,
            attributes={"class": "name longName"}
        )
        
        sku_element = MockElementData(
            tag_name="span",
            text=part_number,
            attributes={"class": "sku-text"}
        )
        
        price_element = MockElementData(
            tag_name="span",
            text=price,
            attributes={"class": "formatted-price"}
        )
        
        quantity_element = MockElementData(
            tag_name="span",
            text=quantity,
            attributes={"class": "inventory-available"}
        )
        
        link_element = MockElementData(
            tag_name="a",
            text=title,
            attributes={"href": url, "class": "link"},
            children=[title_element]
        )
        
        # Create main product card
        card_data = MockElementData(
            tag_name="div",
            attributes={"class": "productlist"},
            children=[link_element, sku_element, price_element, quantity_element]
        )
        
        return MockWebElement(card_data)
    
    @staticmethod
    def create_search_page_elements(
        search_input_selector: str = "#searchInput",
        search_button_selector: str = "//button[contains(@class, 'search-button')]",
        product_cards: List[MockWebElement] = None
    ) -> Dict[str, MockWebElement]:
        """Create mock elements for a search page.
        
        Args:
            search_input_selector: Selector for search input
            search_button_selector: Selector for search button
            product_cards: List of product card elements
            
        Returns:
            Dictionary mapping selectors to mock elements
        """
        elements = {}
        
        # Search input
        search_input = MockWebElement(MockElementData(
            tag_name="input",
            attributes={"id": "searchInput", "type": "search", "placeholder": "Search products"}
        ))
        elements[search_input_selector] = search_input
        
        # Search button
        search_button = MockWebElement(MockElementData(
            tag_name="button",
            text="Search",
            attributes={"class": "search-button btn-primary"}
        ))
        elements[search_button_selector] = search_button
        
        # Product cards
        if product_cards:
            elements["div.productlist"] = product_cards
        
        return elements
    
    @staticmethod
    def create_test_config(
        site_name: str = "test_site",
        target_url: str = "http://example.com"
    ) -> SiteConfig:
        """Create a test site configuration.
        
        Args:
            site_name: Name of the test site
            target_url: Target URL for the test site
            
        Returns:
            Test site configuration
        """
        scraping_config = ScrapingConfig(
            search_input_selectors=["#searchInput", "input[type='search']"],
            search_button_selectors=["//button[contains(@class, 'search-button')]"],
            product_card_selectors=["div.productlist", "div.product-card"],
            product_link_selector="a.link",
            product_title_selectors=["div.name.longName", "h3.name.longName"],
            product_sku_selectors=["span.sku-text"],
            product_price_selectors=["span.formatted-price"],
            product_quantity_selectors=["span.inventory-available"],
            badges_selectors=["span.badge"],
            exact_match_selectors=["span.exact-match"],
            no_results_selectors=["div.no-results"],
            max_results_per_query=10,
            wait_timeout=5,
            page_load_timeout=15
        )
        
        output_config = OutputConfig(
            output_file="test_results.json",
            detailed_output_file="test_detailed_results.json"
        )
        
        return SiteConfig(
            site_name=site_name,
            target_url=target_url,
            search_tasks=[],
            inventory_test_cases=[],
            scraping_config=scraping_config,
            output_config=output_config
        )
    
    @staticmethod
    def create_expected_results(
        search_term: str = "test_search",
        num_results: int = 3
    ) -> List[Dict[str, Any]]:
        """Create expected test results.
        
        Args:
            search_term: Search term used
            num_results: Number of results to generate
            
        Returns:
            List of expected result dictionaries
        """
        results = []
        
        for i in range(num_results):
            result = {
                "title": f"Test Product {i+1}",
                "part_number": f"TEST{i+1:03d}",
                "vendor_part_number": f"VENDOR{i+1:03d}",
                "url": f"http://example.com/product/test{i+1:03d}",
                "price": f"${(i+1) * 10 + 9.99:.2f}",
                "quantity": str((i+1) * 5),
                "description": f"Description for test product {i+1}",
                "partial_match": i % 3 == 0,
                "cross_ref_match": i % 2 == 0,
                "exact_match": i == 0
            }
            results.append(result)
        
        return results


class ScraperTestCase:
    """Base class for scraper test cases."""
    
    def __init__(self, name: str, description: str = ""):
        """Initialize test case.
        
        Args:
            name: Test case name
            description: Test case description
        """
        self.name = name
        self.description = description
        self.setup_callbacks: List[Callable] = []
        self.teardown_callbacks: List[Callable] = []
        self.assertions: List[Callable] = []
    
    def add_setup(self, callback: Callable) -> None:
        """Add setup callback.
        
        Args:
            callback: Setup function to call
        """
        self.setup_callbacks.append(callback)
    
    def add_teardown(self, callback: Callable) -> None:
        """Add teardown callback.
        
        Args:
            callback: Teardown function to call
        """
        self.teardown_callbacks.append(callback)
    
    def add_assertion(self, assertion: Callable) -> None:
        """Add assertion to test.
        
        Args:
            assertion: Assertion function to call
        """
        self.assertions.append(assertion)
    
    def run(self) -> Dict[str, Any]:
        """Run the test case.
        
        Returns:
            Test result dictionary
        """
        result = {
            "name": self.name,
            "description": self.description,
            "passed": False,
            "errors": [],
            "duration": 0.0,
            "timestamp": time.time()
        }
        
        start_time = time.time()
        
        try:
            # Setup
            for setup_fn in self.setup_callbacks:
                setup_fn()
            
            # Run assertions
            for assertion in self.assertions:
                assertion()
            
            result["passed"] = True
            
        except Exception as e:
            result["errors"].append(str(e))
            logger.error(f"Test case '{self.name}' failed: {e}")
        
        finally:
            # Teardown
            for teardown_fn in self.teardown_callbacks:
                try:
                    teardown_fn()
                except Exception as e:
                    result["errors"].append(f"Teardown error: {e}")
            
            result["duration"] = time.time() - start_time
        
        return result


class ScraperTestSuite:
    """Test suite for running multiple scraper tests."""
    
    def __init__(self, name: str):
        """Initialize test suite.
        
        Args:
            name: Test suite name
        """
        self.name = name
        self.test_cases: List[ScraperTestCase] = []
    
    def add_test_case(self, test_case: ScraperTestCase) -> None:
        """Add test case to suite.
        
        Args:
            test_case: Test case to add
        """
        self.test_cases.append(test_case)
    
    def run_all(self) -> Dict[str, Any]:
        """Run all test cases in the suite.
        
        Returns:
            Test suite results
        """
        results = {
            "suite_name": self.name,
            "total_tests": len(self.test_cases),
            "passed_tests": 0,
            "failed_tests": 0,
            "total_duration": 0.0,
            "test_results": []
        }
        
        start_time = time.time()
        
        for test_case in self.test_cases:
            logger.info(f"Running test case: {test_case.name}")
            test_result = test_case.run()
            
            results["test_results"].append(test_result)
            
            if test_result["passed"]:
                results["passed_tests"] += 1
            else:
                results["failed_tests"] += 1
        
        results["total_duration"] = time.time() - start_time
        results["success_rate"] = (results["passed_tests"] / results["total_tests"] * 100) if results["total_tests"] > 0 else 0
        
        return results
    
    def save_results(self, results: Dict[str, Any], filepath: str = "test_results.json") -> None:
        """Save test results to file.
        
        Args:
            results: Test results dictionary
            filepath: Path to save results
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"Test results saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving test results: {e}")


class MockingUtils:
    """Utilities for mocking scraper components."""
    
    @staticmethod
    def mock_web_driver_manager(return_driver: MockWebDriver = None):
        """Mock WebDriverManager.
        
        Args:
            return_driver: Driver to return from create_driver()
            
        Returns:
            Mock WebDriverManager
        """
        mock_manager = Mock()
        mock_manager.create_driver.return_value = return_driver or MockWebDriver()
        mock_manager.quit_driver.return_value = None
        return mock_manager
    
    @staticmethod
    def mock_element_finder(mock_elements: Dict[str, Any] = None):
        """Mock ElementFinder.
        
        Args:
            mock_elements: Dictionary mapping selectors to elements
            
        Returns:
            Mock ElementFinder
        """
        mock_finder = Mock()
        
        def find_element_side_effect(selectors, **kwargs):
            if isinstance(selectors, list):
                for selector in selectors:
                    if mock_elements and selector in mock_elements:
                        return mock_elements[selector]
            else:
                if mock_elements and selectors in mock_elements:
                    return mock_elements[selectors]
            return None
        
        def find_elements_side_effect(selectors, **kwargs):
            if isinstance(selectors, list):
                for selector in selectors:
                    if mock_elements and selector in mock_elements:
                        elements = mock_elements[selector]
                        return elements if isinstance(elements, list) else [elements]
            else:
                if mock_elements and selectors in mock_elements:
                    elements = mock_elements[selectors]
                    return elements if isinstance(elements, list) else [elements]
            return []
        
        mock_finder.find_element_with_selectors.side_effect = find_element_side_effect
        mock_finder.find_elements_with_selectors.side_effect = find_elements_side_effect
        
        return mock_finder
    
    @staticmethod
    def mock_data_extractor(expected_results: List[ScrapingResult] = None):
        """Mock DataExtractor.
        
        Args:
            expected_results: List of results to return
            
        Returns:
            Mock DataExtractor
        """
        mock_extractor = Mock()
        
        if expected_results:
            mock_extractor.extract_product_data.side_effect = expected_results
        else:
            # Default result
            default_result = ScrapingResult()
            default_result.title = "Mock Product"
            default_result.part_number = "MOCK123"
            default_result.url = "http://example.com/mock"
            mock_extractor.extract_product_data.return_value = default_result
        
        return mock_extractor


# Example test case functions
def create_basic_scraping_test() -> ScraperTestCase:
    """Create a basic scraping test case.
    
    Returns:
        Configured test case
    """
    test_case = ScraperTestCase(
        name="basic_scraping_test",
        description="Test basic scraping functionality"
    )
    
    # Mock data
    mock_driver = MockWebDriver()
    mock_elements = TestDataGenerator.create_search_page_elements()
    product_cards = [
        TestDataGenerator.create_product_card_element(
            title=f"Product {i}",
            part_number=f"PART{i:03d}"
        ) for i in range(1, 4)
    ]
    mock_elements["div.productlist"] = product_cards
    
    # Add elements to mock driver
    for selector, element in mock_elements.items():
        mock_driver.add_mock_element(selector, element)
    
    def setup():
        """Test setup."""
        logger.info("Setting up basic scraping test")
    
    def test_element_finding():
        """Test element finding."""
        search_input = mock_driver.find_element("css", "#searchInput")
        assert search_input is not None, "Search input should be found"
        assert search_input.get_attribute("type") == "search", "Input should be search type"
    
    def test_product_extraction():
        """Test product data extraction."""
        cards = mock_driver.find_elements("css", "div.productlist")
        assert len(cards) == 3, f"Should find 3 product cards, found {len(cards)}"
    
    def teardown():
        """Test teardown."""
        logger.info("Tearing down basic scraping test")
    
    test_case.add_setup(setup)
    test_case.add_assertion(test_element_finding)
    test_case.add_assertion(test_product_extraction)
    test_case.add_teardown(teardown)
    
    return test_case