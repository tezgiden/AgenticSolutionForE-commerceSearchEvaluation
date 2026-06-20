"""Comprehensive example demonstrating usage of the refactored scraper architecture."""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any

# Import the refactored modules
from scraper_factory import ScraperFactory, ScraperType, create_monitored_scraper
from config.config_loader import ConfigLoader
from metrics_monitor import MetricsCollector, PerformanceMonitor
from testing_utilities import (
    TestDataGenerator, ScraperTestSuite, create_basic_scraping_test,
    MockingUtils
)
from .utilities import LoggingUtils, FileUtils, ValidationUtils
from .exceptions import ScrapingError, ConfigurationError, ErrorHandler


def setup_logging_example():
    """Example of setting up comprehensive logging."""
    print("=== Setting up logging ===")
    
    # Setup logging with file output
    LoggingUtils.setup_logging(
        level="INFO",
        log_file="scraper_example.log",
        include_timestamp=True
    )
    
    # Create component-specific loggers
    scraper_logger = LoggingUtils.create_logger("scraper_example", "DEBUG")
    scraper_logger.info("Logging configured successfully")


def basic_scraping_example():
    """Example of basic scraping using the factory pattern."""
    print("\n=== Basic Scraping Example ===")
    
    try:
        # Create a basic scraper using factory
        factory = ScraperFactory()
        scraper = factory.create_scraper(
            ScraperType.BASIC,
            site_name="truckpro"  # This would need a config file
        )
        
        # Perform scraping
        search_terms = ["brake pads", "oil filter"]
        
        # For this example, we'll use default config since we don't have config file
        site_config = ConfigLoader.create_default_truckpro_config()
        
        results = scraper.scrape_with_config(
            search_terms=search_terms,
            site_config=site_config,
            debug_mode=True
        )
        
        # Save results with timestamp
        output_file = FileUtils.get_timestamped_filename("basic_scraping_results")
        scraper.save_results(results, output_file)
        
        print(f"Basic scraping completed. Results saved to: {output_file}")
        print(f"Found results for {len(results)} search terms")
        
        return results
        
    except (ScrapingError, ConfigurationError) as e:
        print(f"Scraping error occurred: {e}")
        return {}
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {}


def monitored_scraping_example():
    """Example of scraping with performance monitoring."""
    print("\n=== Monitored Scraping Example ===")
    
    try:
        # Create monitored scraper
        monitored_scraper = create_monitored_scraper("truckpro")
        
        # Use default config for this example
        site_config = ConfigLoader.create_default_truckpro_config()
        
        search_terms = ["gasket", "brake fluid", "spark plugs"]
        
        print("Starting monitored scraping...")
        start_time = time.time()
        
        results = monitored_scraper.scrape_with_config(
            search_terms=search_terms,
            site_config=site_config,
            debug_mode=False
        )
        
        duration = time.time() - start_time
        print(f"Scraping completed in {duration:.2f} seconds")
        
        # Get performance report
        performance_report = monitored_scraper.get_performance_report(hours=1)
        
        # Check for alerts
        alerts = monitored_scraper.check_alerts()
        
        print(f"Found {len(alerts)} performance alerts")
        for alert in alerts:
            print(f"  - {alert['type']}: {alert['message']}")
        
        # Save performance report
        report_file = FileUtils.get_timestamped_filename("performance_report", "json")
        with open(report_file, 'w') as f:
            json.dump(performance_report, f, indent=2, default=str)
        
        print(f"Performance report saved to: {report_file}")
        
        return results, performance_report
        
    except Exception as e:
        print(f"Monitored scraping error: {e}")
        return {}, {}


def metrics_collection_example():
    """Example of standalone metrics collection."""
    print("\n=== Metrics Collection Example ===")
    
    # Create metrics collector
    metrics_collector = MetricsCollector(
        enable_collection=True,
        storage_path="example_metrics.json"
    )
    
    # Simulate some operations with metrics
    operations = [
        ("search", "brake pads", True, 5, 2.5),
        ("search", "oil filter", True, 3, 1.8),
        ("search", "nonexistent_part", False, 0, 0.5),
        ("extract", "brake pads", True, 5, 0.3),
        ("extract", "oil filter", True, 3, 0.2),
    ]
    
    for operation, search_term, success, results_count, duration in operations:
        error = None if success else ScrapingError("Mock error for testing")
        
        metrics_collector.record_simple_metric(
            site_name="truckpro",
            search_term=search_term,
            operation=operation,
            duration_seconds=duration,
            success=success,
            results_count=results_count,
            error=error
        )
    
    # Get statistics
    overall_stats = metrics_collector.get_stats()
    site_stats = metrics_collector.get_site_performance()
    operation_stats = metrics_collector.get_operation_performance()
    
    print(f"Overall Statistics:")
    print(f"  Total operations: {overall_stats.total_operations}")
    print(f"  Success rate: {overall_stats.success_rate:.1f}%")
    print(f"  Average duration: {overall_stats.average_duration:.2f}s")
    
    # Save metrics
    metrics_collector.save_metrics()
    print("Metrics saved to example_metrics.json")
    
    return metrics_collector


def error_handling_example():
    """Example of error handling and categorization."""
    print("\n=== Error Handling Example ===")
    
    from exceptions import (
        ElementNotFoundError, SearchError, DataExtractionError,
        NetworkError, ValidationError
    )
    
    # Simulate different types of errors
    errors = [
        ElementNotFoundError("Search input not found", selectors=["#search", ".search-input"]),
        SearchError("Search failed", search_term="test", site_name="example.com"),
        DataExtractionError("Price extraction failed", field_name="price"),
        NetworkError("Connection timeout", url="http://example.com", status_code=408),
        ValidationError("Invalid URL", field_name="product_url", field_value="invalid-url")
    ]
    
    print("Error categorization and recovery analysis:")
    for error in errors:
        category = ErrorHandler.categorize_error(error)
        recoverable = ErrorHandler.is_recoverable_error(error)
        should_retry = ErrorHandler.should_retry(error, retry_count=1, max_retries=3)
        
        print(f"  {type(error).__name__}:")
        print(f"    Category: {category}")
        print(f"    Recoverable: {recoverable}")
        print(f"    Should retry: {should_retry}")
        print(f"    Message: {error}")
        print()


def validation_example():
    """Example of data validation utilities."""
    print("\n=== Data Validation Example ===")
    
    # Sample scraping results
    test_results = [
        {
            "title": "Valid Product",
            "url": "https://example.com/product/123",
            "part_number": "ABC123",
            "price": "$19.99"
        },
        {
            "title": "AB",  # Too short
            "url": "invalid-url",  # Invalid URL
            "part_number": "N/A",  # Missing part number
            "price": "$29.99"
        },
        {
            "title": "",  # Empty title
            "url": "N/A",  # Missing URL
            "part_number": "XYZ789",
            "price": "Free"
        }
    ]
    
    print("Validating scraping results:")
    for i, result in enumerate(test_results):
        issues = ValidationUtils.validate_scraping_result(result)
        
        print(f"  Result {i+1}:")
        if issues:
            print(f"    Issues found: {', '.join(issues)}")
        else:
            print(f"    ✓ Valid result")
        
        # URL validation
        url = result.get('url')
        if url and url != "N/A":
            url_valid = ValidationUtils.is_valid_url(url)
            print(f"    URL valid: {url_valid}")
        
        print()


def testing_example():
    """Example of using testing utilities."""
    print("\n=== Testing Example ===")
    
    # Create test suite
    test_suite = ScraperTestSuite("Scraper Component Tests")
    
    # Add basic test case
    basic_test = create_basic_scraping_test()
    test_suite.add_test_case(basic_test)
    
    # Run tests
    print("Running test suite...")
    results = test_suite.run_all()
    
    print(f"Test Results:")
    print(f"  Total tests: {results['total_tests']}")
    print(f"  Passed: {results['passed_tests']}")
    print(f"  Failed: {results['failed_tests']}")
    print(f"  Success rate: {results['success_rate']:.1f}%")
    print(f"  Duration: {results['total_duration']:.2f}s")
    
    # Save test results
    test_results_file = FileUtils.get_timestamped_filename("test_results", "json")
    test_suite.save_results(results, test_results_file)
    print(f"Test results saved to: {test_results_file}")
    
    return results


def factory_pattern_example():
    """Example of using different scraper types via factory."""
    print("\n=== Factory Pattern Example ===")
    
    factory = ScraperFactory()
    
    # Show available scraper types
    available_types = factory.get_available_types()
    print(f"Available scraper types: {[t.value for t in available_types]}")
    
    # Create different types of scrapers
    scraper_types = [ScraperType.BASIC, ScraperType.TESTING]
    
    for scraper_type in scraper_types:
        try:
            print(f"\nCreating {scraper_type.value} scraper...")
            
            # For this example, we'll create with default config
            config = create_example_config()
            scraper = factory.create_scraper_with_config(scraper_type, config)
            
            print(f"  ✓ {scraper_type.value} scraper created successfully")
            print(f"  Type: {type(scraper).__name__}")
            
        except Exception as e:
            print(f"  ✗ Error creating {scraper_type.value} scraper: {e}")


def create_example_config():
    """Create example configuration for testing."""
    from config.config_models import AppConfig, DeploymentConfig, LLMConfig, EvaluationConfig
    
    # Use default configurations
    site_config = ConfigLoader.create_default_truckpro_config()
    chrome_config = ConfigLoader.load_default_chrome_config()
    
    # Create minimal other configs
    deployment_config = DeploymentConfig(
        environment="example",
        log_level="INFO",
        enable_screenshots=False,
        delay_between_searches=1,
        enable_metrics_collection=True
    )
    
    llm_config = LLMConfig(
        ollama_api_endpoint="http://localhost:11434",
        default_model="llama2",
        timeout=30,
        max_retries=3
    )
    
    evaluation_config = EvaluationConfig(
        enable_inventory_ranking=True,
        enable_detailed_analysis=False,
        inventory_weight_factor=0.3,
        apply_post_ranking=True,
        low_stock_threshold=5
    )
    
    return AppConfig(
        site_config=site_config,
        chrome_config=chrome_config,
        deployment_config=deployment_config,
        llm_config=llm_config,
        evaluation_config=evaluation_config
    )


def performance_monitoring_example():
    """Example of performance monitoring setup."""
    print("\n=== Performance Monitoring Example ===")
    
    # Create metrics collector
    metrics_collector = MetricsCollector(enable_collection=True)
    
    # Create performance monitor
    performance_monitor = PerformanceMonitor(metrics_collector)
    
    # Set custom thresholds
    performance_monitor.set_thresholds(
        min_success_rate=85.0,
        max_avg_duration=25.0,
        max_error_rate=15.0
    )
    
    print("Performance monitor configured with custom thresholds:")
    print(f"  Minimum success rate: 85%")
    print(f"  Maximum average duration: 25s")
    print(f"  Maximum error rate: 15%")
    
    # Simulate some metrics that would trigger alerts
    test_metrics = [
        ("search", "test1", False, 0, 1.0),  # Failed search
        ("search", "test2", False, 0, 1.5),  # Another failed search
        ("search", "test3", True, 2, 35.0),  # Slow but successful search
        ("search", "test4", True, 5, 2.0),   # Fast successful search
    ]
    
    for operation, term, success, count, duration in test_metrics:
        error = ScrapingError("Test error") if not success else None
        metrics_collector.record_simple_metric(
            site_name="test_site",
            search_term=term,
            operation=operation,
            duration_seconds=duration,
            success=success,
            results_count=count,
            error=error
        )
    
    # Check for alerts
    alerts = performance_monitor.check_performance_alerts(hours=1)
    
    print(f"\nPerformance alerts detected: {len(alerts)}")
    for alert in alerts:
        print(f"  - {alert['severity'].upper()}: {alert['message']}")
    
    return performance_monitor


def main():
    """Main example function demonstrating all components."""
    print("Web Scraper Architecture - Comprehensive Example")
    print("=" * 50)
    
    # Setup logging
    setup_logging_example()
    
    # Run all examples
    examples = [
        ("Basic Scraping", basic_scraping_example),
        ("Error Handling", error_handling_example),
        ("Data Validation", validation_example),
        ("Metrics Collection", metrics_collection_example),
        ("Testing Utilities", testing_example),
        ("Factory Pattern", factory_pattern_example),
        ("Performance Monitoring", performance_monitoring_example),
    ]
    
    results = {}
    
    for name, example_func in examples:
        try:
            print(f"\nRunning {name} example...")
            result = example_func()
            results[name] = {"success": True, "result": result}
            print(f"✓ {name} example completed successfully")
            
        except Exception as e:
            print(f"✗ {name} example failed: {e}")
            results[name] = {"success": False, "error": str(e)}
        
        # Small delay between examples
        time.sleep(1)
    
    # Summary
    print(f"\n" + "=" * 50)
    print("EXAMPLE EXECUTION SUMMARY")
    print("=" * 50)
    
    successful = sum(1 for r in results.values() if r["success"])
    total = len(results)
    
    print(f"Total examples: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    print(f"Success rate: {successful/total*100:.1f}%")
    
    print("\nDetailed results:")
    for name, result in results.items():
        status = "✓" if result["success"] else "✗"
        print(f"  {status} {name}")
        if not result["success"]:
            print(f"    Error: {result['error']}")
    
    # Save summary
    summary_file = FileUtils.get_timestamped_filename("example_summary", "json")
    with open(summary_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": total,
                "successful": successful,
                "failed": total - successful,
                "success_rate": successful/total*100
            },
            "details": results
        }, f, indent=2, default=str)
    
    print(f"\nExample summary saved to: {summary_file}")


if __name__ == "__main__":
    main()