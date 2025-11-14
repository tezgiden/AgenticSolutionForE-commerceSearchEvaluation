# Migration Guide: From Monolithic to Modular Architecture

This guide helps you migrate from the original monolithic `scraper.py` to the new modular enterprise web scraper architecture.

## Overview of Changes

The original single-file scraper has been refactored into a modular architecture with the following benefits:

- **Better maintainability** through single-responsibility modules
- **Enhanced testability** with comprehensive testing framework
- **Improved scalability** with factory patterns and monitoring
- **Better error handling** with custom exception hierarchy
- **Performance monitoring** and metrics collection
- **Rate limiting** for respectful scraping
- **Result processing pipeline** for data quality
- **CLI interface** for operational use

## Migration Steps

### Step 1: Update Dependencies

**Old requirements:**
```
selenium>=4.0.0
webdriver-manager>=3.8.0
```

**New requirements:**
```bash
pip install -r requirements.txt
# Or for basic installation:
pip install selenium>=4.15.0 webdriver-manager>=4.0.0 pandas>=2.0.0
```

### Step 2: Replace Direct Function Calls

#### Old Code Pattern:
```python
# Original monolithic approach
from scraper import setup_driver, scrape_tundra

driver = setup_driver()
results = scrape_tundra(driver, "brake pads")
driver.quit()
```

#### New Code Pattern:
```python
# New modular approach - Option 1: Simple migration
from scraper_facade import setup_driver, scrape_tundra

driver = setup_driver()
results = scrape_tundra(driver, "brake pads")
driver.quit()

# New modular approach - Option 2: Recommended
from scraper_facade import ScraperFacade

facade = ScraperFacade()
results = facade.scrape_from_config_file(
    search_terms=["brake pads"],
    site_name="truckpro"
)
```

### Step 3: Update Configuration

#### Old Configuration (Hardcoded):
```python
# Configuration was hardcoded in the original scraper
search_selectors = ["#searchInput", "input[type='search']"]
```

#### New Configuration (JSON file):
```json
{
  "sites": {
    "truckpro": {
      "site_name": "TruckPro",
      "target_url": "https://www.truckpro.com/",
      "scraping": {
        "search_input_selectors": [
          "#searchInput",
          "input[placeholder=\"Search name, sku, item #\"]"
        ],
        "search_button_selectors": [
          "//button[contains(@class, 'search-bar__button')]"
        ],
        "product_card_selectors": ["div.productlist"],
        "max_results_per_query": 10
      }
    }
  }
}
```

### Step 4: Migrate Custom Configurations

#### If you had custom selector configurations:

**Old approach:**
```python
# Custom selectors were passed as parameters
def scrape_custom_site(driver, search_term, custom_selectors):
    # Custom scraping logic
    pass
```

**New approach:**
```python
# Create custom configuration
from config_models import SiteConfig, ScrapingConfig, OutputConfig

custom_scraping_config = ScrapingConfig(
    search_input_selectors=["#custom-search"],
    search_button_selectors=["//button[@id='search-btn']"],
    product_card_selectors=[".custom-product"],
    product_link_selector="a.custom-link",
    product_title_selectors=[".custom-title"],
    product_sku_selectors=[".custom-sku"],
    product_price_selectors=[".custom-price"],
    product_quantity_selectors=[".custom-quantity"],
    no_results_selectors=[".no-results"],
    max_results_per_query=10,
    wait_timeout=10,
    page_load_timeout=30
)

site_config = SiteConfig(
    site_name="CustomSite",
    target_url="https://custom-site.com",
    search_tasks=[],
    inventory_test_cases=[],
    scraping_config=custom_scraping_config,
    output_config=OutputConfig(
        output_file="custom_results.json",
        detailed_output_file="custom_detailed.json"
    )
)

# Use with facade
facade = ScraperFacade()
results = facade.scrape_with_config(
    search_terms=["search term"],
    site_config=site_config
)
```

## Feature Migration Guide

### Error Handling

#### Old Error Handling:
```python
try:
    results = scrape_tundra(driver, "brake pads")
except Exception as e:
    print(f"Error: {e}")
```

#### New Error Handling:
```python
from exceptions import ScrapingError, ElementNotFoundError, SearchError

try:
    results = facade.scrape_from_config_file(["brake pads"], "truckpro")
except ElementNotFoundError as e:
    print(f"Element not found: {e.selectors}")
except SearchError as e:
    print(f"Search failed for '{e.search_term}' on {e.site_name}")
except ScrapingError as e:
    print(f"Scraping error: {e}")
```

### Adding Monitoring

#### Old Code (No monitoring):
```python
results = scrape_tundra(driver, "brake pads")
# No performance tracking
```

#### New Code (With monitoring):
```python
from scraper_factory import create_monitored_scraper

# Create monitored scraper
scraper = create_monitored_scraper("truckpro")

# Perform scraping with monitoring
results = scraper.scrape_from_config_file(["brake pads"], "truckpro")

# Get performance insights
performance_report = scraper.get_performance_report()
alerts = scraper.check_alerts()

print(f"Success rate: {performance_report['overall_performance']['success_rate']:.1f}%")
for alert in alerts:
    print(f"Alert: {alert['message']}")
```

### Result Processing

#### Old Code (Manual processing):
```python
results = scrape_tundra(driver, "brake pads")

# Manual result filtering
filtered_results = []
for result in results:
    if result.get('price') != 'N/A':
        filtered_results.append(result)
```

#### New Code (Automated pipeline):
```python
from result_processor import ResultProcessor, CommonFilters

# Create processor with pipeline
processor = ResultProcessor()
processor.create_standard_pipeline(
    validate=True,
    clean=True,
    enrich=True,
    deduplicate=True
)

# Add custom filters
from result_processor import FilterProcessor
filter_processor = FilterProcessor()
filter_processor.add_filter(CommonFilters.has_price)
processor.add_processor(filter_processor)

# Process results
raw_results = {"brake pads": scraping_results}
processed_results = processor.process_results(raw_results)

# Get processing summary
summary = processor.get_processing_summary()
print(f"Processing rate: {summary['overall_processing_rate']:.1f}%")
```

### Rate Limiting

#### Old Code (No rate limiting):
```python
for search_term in search_terms:
    results = scrape_tundra(driver, search_term)
    # Potentially too fast, could overwhelm server
```

#### New Code (With rate limiting):
```python
from rate_limiter import RateLimitConfig, TokenBucketRateLimiter

# Configure rate limiting
rate_config = RateLimitConfig(
    requests_per_second=1.0,
    burst_allowance=3
)
rate_limiter = TokenBucketRateLimiter(rate_config)

# Use with scraper (automatic in ScraperFacade)
facade = ScraperFacade()
results = facade.scrape_from_config_file(
    search_terms=["brake pads", "oil filter"],
    site_name="truckpro",
    delay_between_searches=2  # Respectful delays
)
```

## Command Line Interface Migration

### Old Usage (Script execution):
```bash
python scraper.py
# Had to modify script for different searches
```

### New Usage (CLI):
```bash
# Basic scraping
web-scraper scrape --site truckpro --search "brake pads" "oil filter"

# With monitoring
web-scraper scrape --site truckpro --type monitored --search "gasket"

# Process existing results
web-scraper process --input results.json --output processed.json

# Generate reports
web-scraper report --metrics metrics.json --format html

# Run tests
web-scraper test --site truckpro
```

## Testing Migration

### Old Testing (Manual):
```python
# No systematic testing framework
if __name__ == "__main__":
    # Manual testing code
    driver = setup_driver()
    results = scrape_tundra(driver, "test")
    print(f"Found {len(results)} results")
```

### New Testing (Comprehensive):
```python
from testing_utilities import ScraperTestSuite, create_basic_scraping_test

# Create test suite
test_suite = ScraperTestSuite("Migration Tests")
test_suite.add_test_case(create_basic_scraping_test())

# Run tests
results = test_suite.run_all()
print(f"Tests: {results['passed_tests']}/{results['total_tests']} passed")

# Save test results
test_suite.save_results(results, "test_results.json")
```

## Performance Optimization

### Memory Management

#### Old Code:
```python
# Manual driver management
driver = setup_driver()
try:
    # Multiple operations
    for term in search_terms:
        results = scrape_tundra(driver, term)
finally:
    driver.quit()  # Manual cleanup
```

#### New Code:
```python
# Automatic resource management
from scraper_facade import ScraperFacade

facade = ScraperFacade()
with facade.get_scraper() as scraper:
    # Automatic cleanup when context exits
    for term in search_terms:
        results = scraper.scrape_site(term, site_config)
```

### Batch Processing

#### Old Code (Sequential):
```python
all_results = {}
for search_term in search_terms:
    results = scrape_tundra(driver, search_term)
    all_results[search_term] = results
    time.sleep(2)  # Manual delay
```

#### New Code (Optimized batch):
```python
from scraper_factory import ScraperFactory, ScraperType

# Use batch scraper for high-volume processing
factory = ScraperFactory()
batch_scraper = factory.create_scraper(ScraperType.BATCH, "truckpro")

# Efficient batch processing with automatic optimization
results = batch_scraper.scrape_batch(
    search_terms=search_terms,
    site_configs={"truckpro": site_config}
)
```

## Common Migration Issues

### Issue 1: Import Errors

**Problem:**
```python
from scraper import setup_driver  # ModuleNotFoundError
```

**Solution:**
```python
# Install new package
pip install -e .

# Update imports
from scraper_facade import setup_driver
# Or use new approach
from scraper_facade import ScraperFacade
```

### Issue 2: Configuration Not Found

**Problem:**
```python
# Error: Site 'custom_site' not found in configuration
scraper = factory.create_scraper(ScraperType.BASIC, "custom_site")
```

**Solution:**
```python
# Option 1: Create configuration file
# See configuration examples above

# Option 2: Use default configuration
from config_loader import ConfigLoader
site_config = ConfigLoader.create_default_truckpro_config()
site_config.site_name = "custom_site"
site_config.target_url = "https://custom-site.com"

# Use with factory
scraper = factory.create_scraper_with_config(ScraperType.BASIC, app_config)
```

### Issue 3: Different Result Format

**Problem:**
```python
# Old results were simple list
# New results are nested dictionary
results = scraper.scrape_site("brake pads", site_config)
# Returns: {"brake pads": [list of results]}
```

**Solution:**
```python
# Access results correctly
results = scraper.scrape_site("brake pads", site_config)
brake_pad_results = results.get("brake pads", [])

# Or flatten if needed
all_items = []
for search_term, items in results.items():
    all_items.extend(items)
```

## Gradual Migration Strategy

### Phase 1: Drop-in Replacement
```python
# Minimal changes - just update imports
from scraper_facade import setup_driver, scrape_tundra

# Rest of code remains the same
driver = setup_driver()
results = scrape_tundra(driver, "brake pads")
driver.quit()
```

### Phase 2: Adopt Configuration
```python
# Move to configuration-based approach
from scraper_facade import ScraperFacade

facade = ScraperFacade()
results = facade.scrape_from_config_file(["brake pads"], "truckpro")
```

### Phase 3: Add Monitoring
```python
# Enable performance tracking
from scraper_factory import create_monitored_scraper

scraper = create_monitored_scraper("truckpro")
results = scraper.scrape_from_config_file(["brake pads"], "truckpro")

# Review performance
performance_report = scraper.get_performance_report()
```

### Phase 4: Full Enterprise Features
```python
# Complete migration to enterprise features
from integration_example import EnterpriseScraper

enterprise_scraper = EnterpriseScraper("config.json")
comprehensive_results = enterprise_scraper.scrape_with_enterprise_features(
    search_terms=["brake pads", "oil filter"],
    site_name="truckpro",
    scraper_type=ScraperType.MONITORED
)

# Full reporting and monitoring
report = enterprise_scraper.generate_comprehensive_report()
```

## Validation and Testing

After migration, validate your setup:

```bash
# Run system tests
python -m pytest tests/

# Run integration tests
web-scraper test --component all

# Validate configuration
web-scraper config validate config.json

# Test basic functionality
web-scraper scrape --site truckpro --search "test" --debug
```

## Getting Help

- **Documentation**: See README.md for comprehensive examples
- **CLI Help**: `web-scraper --help`
- **Example Code**: Check `example_usage.py` and `integration_example.py`
- **Testing**: Use `testing_utilities.py` for creating custom tests

## Benefits After Migration

✅ **Improved Reliability**: Better error handling and recovery  
✅ **Enhanced Performance**: Monitoring and optimization  
✅ **Better Testing**: Comprehensive test framework  
✅ **Easier Maintenance**: Modular, single-responsibility code  
✅ **Operational Insights**: Metrics and alerting  
✅ **Respectful Scraping**: Built-in rate limiting  
✅ **Data Quality**: Automated result processing  
✅ **Scalability**: Factory patterns and batch processing  
✅ **CLI Operations**: Command-line interface for automation  
✅ **Future-Proof**: Extensible architecture for new requirements