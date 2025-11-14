# Web Scraper Architecture

A refactored, modular web scraping framework built with Python and Selenium, following SOLID principles and software engineering best practices.

## Architecture Overview

The monolithic scraper has been refactored into focused, single-responsibility modules:

```
├── config_models.py           # Data classes for configuration
├── config_loader.py           # Configuration loading and parsing
├── web_driver_manager.py      # WebDriver lifecycle management
├── element_finder.py          # Element location with multiple selectors
├── page_interaction_handler.py # Page interactions (modals, screenshots)
├── data_extractor.py          # Data extraction from web elements
├── web_scraper.py             # Main scraping orchestration
├── scraper_facade.py          # High-level API and backward compatibility
├── scraper_factory.py         # Factory pattern for different scraper types
├── exceptions.py              # Custom exception hierarchy
├── metrics_monitor.py         # Performance monitoring and metrics
├── testing_utilities.py       # Testing framework and utilities
├── utilities.py               # Shared utilities
├── example_usage.py           # Comprehensive usage examples
└── README.md                  # This file
```

## Core Components

### 1. WebDriverManager
**Responsibility**: Chrome WebDriver setup and lifecycle management

```python
from web_driver_manager import WebDriverManager
from config_loader import ConfigLoader

chrome_config = ConfigLoader.load_default_chrome_config()
with WebDriverManager(chrome_config) as driver:
    # Use driver here
    pass
```

**Features**:
- Optimized Chrome options for stability and performance
- Support for webdriver-manager auto-installation
- Context manager support for safe cleanup
- Configurable browser settings

### 2. ElementFinder
**Responsibility**: Robust element location with multiple fallback strategies

```python
from element_finder import ElementFinder

finder = ElementFinder(driver, default_timeout=10)

# Find with multiple selectors as fallbacks
element = finder.find_element_with_selectors([
    "#search-input",
    "input[type='search']",
    ".search-box input"
])

# Find multiple elements
elements = finder.find_elements_with_selectors([
    "div.product-card",
    "article.product",
    ".product-item"
])
```

**Features**:
- Multiple selector fallback strategy
- Configurable timeouts and wait conditions
- Support for both single and multiple element finding
- Parent element scoped searches

### 3. PageInteractionHandler
**Responsibility**: Common page interactions and utilities

```python
from page_interaction_handler import PageInteractionHandler

handler = PageInteractionHandler(driver, element_finder)

# Handle modal popups automatically
handler.handle_modal_popups()

# Wait for page to fully load
handler.wait_for_page_load(timeout=15)

# Take debug screenshots
handler.take_screenshot("search_results", "After performing search")

# Safe element clicking with fallbacks
handler.click_element_safely(button_element)
```

**Features**:
- Automatic modal popup detection and closing
- Page load waiting with loading indicator handling
- Screenshot capture for debugging
- Safe element interaction methods

### 4. DataExtractor
**Responsibility**: Extract structured data from web elements

```python
from data_extractor import DataExtractor, ScrapingResult

extractor = DataExtractor(element_finder)

# Extract comprehensive product data
result: ScrapingResult = extractor.extract_product_data(
    card_element=product_card,
    scraping_config=config.scraping_config,
    card_index=1,
    debug=True
)

# Convert to dictionary
product_data = result.to_dict()
```

**Features**:
- Structured result objects with validation
- Fallback extraction strategies
- Debug mode for troubleshooting
- Support for complex HTML structures

### 5. WebScraper
**Responsibility**: Main scraping orchestration

```python
from web_scraper import WebScraper

scraper = WebScraper(driver)
results = scraper.scrape_site(
    search_term="brake pads",
    site_config=site_config,
    debug_mode=False
)
```

**Features**:
- Complete scraping workflow orchestration
- Error handling and recovery
- No-results detection
- Configurable result limits

### 7. ScraperFactory
**Responsibility**: Factory pattern for creating different types of scrapers

```python
from scraper_factory import ScraperFactory, ScraperType

# Create different types of scrapers
factory = ScraperFactory()

# Basic scraper
basic_scraper = factory.create_scraper(ScraperType.BASIC, "truckpro")

# Monitored scraper with performance tracking
monitored_scraper = factory.create_scraper(ScraperType.MONITORED, "truckpro")

# Testing scraper with mock capabilities
testing_scraper = factory.create_scraper(ScraperType.TESTING, "truckpro")
```

**Features**:
- Multiple scraper types (Basic, Advanced, Monitored, Batch, Testing)
- Configurable builder pattern
- Type-safe scraper creation
- Automatic configuration validation

### 8. Exception Hierarchy
**Responsibility**: Comprehensive error handling and categorization

```python
from exceptions import (
    ScrapingError, ElementNotFoundError, SearchError,
    DataExtractionError, ValidationError, NetworkError
)

try:
    # Scraping operations
    pass
except ElementNotFoundError as e:
    print(f"Element not found: {e.selectors}")
except SearchError as e:
    print(f"Search failed for '{e.search_term}' on {e.site_name}")
except ScrapingError as e:
    print(f"General scraping error: {e}")
```

**Features**:
- Hierarchical exception structure
- Rich error context and details
- Error categorization utilities
- Retry recommendation logic

### 9. Metrics and Monitoring
**Responsibility**: Performance tracking and alerting

```python
from metrics_monitor import MetricsCollector, PerformanceMonitor

# Collect metrics
metrics = MetricsCollector(enable_collection=True)
metrics.start_operation("search_operation")
# ... perform operation
metrics.end_operation("search_operation", "truckpro", "brake pads", "search", True, 5)

# Monitor performance
monitor = PerformanceMonitor(metrics)
alerts = monitor.check_performance_alerts()
report = monitor.generate_performance_report(hours=24)
```

**Features**:
- Automatic metric collection
- Performance statistics and reporting
- Configurable alerting thresholds
- Historical data persistence

### 10. Testing Framework
**Responsibility**: Comprehensive testing utilities and mock objects

```python
from testing_utilities import (
    TestDataGenerator, ScraperTestSuite, MockWebDriver, MockingUtils
)

# Generate test data
product_card = TestDataGenerator.create_product_card_element(
    title="Test Product",
    part_number="TEST123",
    price="$19.99"
)

# Create mock driver
mock_driver = MockWebDriver()
mock_driver.add_mock_element("div.product", product_card)

# Run test suite
test_suite = ScraperTestSuite("Component Tests")
results = test_suite.run_all()
```

**Features**:
- Mock web elements and drivers
- Test data generation utilities
- Test case and suite management
- Automated test execution and reporting

```python
from scraper_facade import ScraperFacade

facade = ScraperFacade()

# Scrape multiple terms with configuration
results = facade.scrape_from_config_file(
    search_terms=["gasket", "brake pads"],
    site_name="truckpro",
    debug_mode=False
)

# Save results
facade.save_results(results, "my_results.json")
```

## Configuration System

### Configuration Structure
```json
{
  "sites": {
    "truckpro": {
      "site_name": "TruckPro",
      "target_url": "https://www.truckpro.com/",
      "scraping": {
        "search_input_selectors": ["#searchInput", "input[type='search']"],
        "search_button_selectors": ["//button[contains(@class, 'search-button')]"],
        "product_card_selectors": ["div.productlist", "div.product-card"],
        "product_link_selector": "a.link",
        "product_title_selectors": ["div.name.longName", "h3.name.longName"],
        "product_sku_selectors": ["span.sku-text"],
        "product_price_selectors": ["span.formatted-price"],
        "product_quantity_selectors": ["span.inventory-available"],
        "no_results_selectors": ["div.message-no-item-alert"],
        "max_results_per_query": 10,
        "wait_timeout": 10,
        "page_load_timeout": 30
      }
    }
  },
  "chrome": {
    "headless": true,
    "window_size": {"width": 3840, "height": 2160},
    "implicit_wait": 3
  },
  "deployment": {
    "environment": "development",
    "log_level": "INFO",
    "delay_between_searches": 2
  }
}
```

### Loading Configuration
```python
from config_loader import ConfigLoader

# Load from file
app_config = ConfigLoader.load_config_for_site("truckpro", "config.json")

# Create default configurations
chrome_config = ConfigLoader.load_default_chrome_config()
truckpro_config = ConfigLoader.create_default_truckpro_config()
```

## Usage Examples

### Basic Usage with Facade
```python
from scraper_facade import ScraperFacade

# Simple scraping
facade = ScraperFacade()
results = facade.scrape_from_config_file(
    search_terms=["brake pads", "oil filter"],
    site_name="truckpro"
)

print(f"Found {len(results)} search results")
facade.save_results(results)
```

### Advanced Usage with Custom Configuration
```python
from scraper_facade import ScraperFacade
from config_loader import ConfigLoader

# Load custom configuration
config = ConfigLoader.load_config_for_site("custom_site", "my_config.json")

# Create facade with custom Chrome settings
facade = ScraperFacade(chrome_config=config.chrome_config)

# Scrape with specific configuration
results = facade.scrape_with_config(
    search_terms=["search term"],
    site_config=config.site_config,
    debug_mode=True,
    delay_between_searches=5
)
```

### Direct Component Usage
```python
from web_driver_manager import WebDriverManager
from web_scraper import WebScraper
from config_loader import ConfigLoader

# Manual component usage for full control
chrome_config = ConfigLoader.load_default_chrome_config()
site_config = ConfigLoader.create_default_truckpro_config()

with WebDriverManager(chrome_config) as driver:
    scraper = WebScraper(driver)
    results = scraper.scrape_site("brake pads", site_config, debug_mode=True)
```

## Backward Compatibility

The refactored code maintains backward compatibility with the original API:

```python
# Original function calls still work
from scraper_facade import setup_driver, scrape_tundra

driver = setup_driver()
results = scrape_tundra(driver, "brake pads")
driver.quit()
```

## Error Handling and Logging

### Logging Configuration
```python
from utilities import LoggingUtils

# Setup comprehensive logging
LoggingUtils.setup_logging(
    level="DEBUG",
    log_file="scraper.log",
    include_timestamp=True
)

# Create component-specific loggers
logger = LoggingUtils.create_logger("my_scraper", "INFO")
```

### Exception Handling
```python
from config_loader import ConfigurationError

try:
    config = ConfigLoader.load_config_for_site("invalid_site")
except ConfigurationError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Testing and Debugging

### Debug Mode
Enable debug mode for detailed logging and structure analysis:

```python
results = scraper.scrape_site(
    search_term="test",
    site_config=config,
    debug_mode=True  # Enables detailed element structure logging
)
```

### Screenshot Capture
Automatic screenshot capture for debugging:

```python
# Screenshots are automatically saved to debug_screenshots/
handler.take_screenshot("search_page", "After navigation")
```

### Validation
Use utilities for result validation:

```python
from utilities import ValidationUtils

issues = ValidationUtils.validate_scraping_result(result_dict)
if issues:
    print(f"Validation issues: {issues}")
```

## Performance Considerations

- **Connection Pooling**: Reuse WebDriver instances for multiple searches
- **Timeout Configuration**: Tune timeouts for site responsiveness
- **Result Limits**: Configure `max_results_per_query` to balance speed vs completeness
- **Delays**: Use `delay_between_searches` to be respectful to target sites

## Extension Points

### Adding New Sites
1. Create configuration in `config.json`
2. Add site-specific selectors
3. Test with facade or components

### Custom Data Extractors
```python
class CustomDataExtractor(DataExtractor):
    def extract_custom_field(self, element):
        # Custom extraction logic
        pass
```

### Custom Page Handlers
```python
class CustomPageHandler(PageInteractionHandler):
    def handle_custom_modal(self):
        # Site-specific modal handling
        pass
```

## Best Practices

1. **Configuration-Driven**: Use configuration files for all site-specific settings
2. **Error Resilience**: Always handle element not found scenarios
3. **Respectful Scraping**: Use appropriate delays between requests
4. **Logging**: Enable appropriate logging levels for monitoring
5. **Testing**: Use debug mode and screenshots for troubleshooting
6. **Validation**: Validate extracted data before using it

## Dependencies

```requirements.txt
selenium>=4.0.0
webdriver-manager>=3.8.0
```

## Migration from Original Code

To migrate from the original monolithic scraper:

1. **Replace imports**: Change import statements to use new modules
2. **Update configuration**: Move hardcoded selectors to configuration files  
3. **Use facade**: Start with `ScraperFacade` for simplest migration
4. **Gradual adoption**: Can mix old and new code during transition

The new architecture provides better maintainability, testability, and extensibility while preserving the existing functionality.