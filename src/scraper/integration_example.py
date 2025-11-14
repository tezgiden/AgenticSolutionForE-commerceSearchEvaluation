"""Comprehensive integration example demonstrating the complete scraper architecture."""

import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any

# Import all components
from scraper_factory import ScraperFactory, ScraperType
from config.config_loader import ConfigLoader, ConfigurationError
from result_processor import ResultProcessor, CommonFilters
from rate_limiter import RateLimitConfig, TokenBucketRateLimiter, DomainBasedRateLimiter
from metrics_monitor import MetricsCollector, PerformanceMonitor
from testing_utilities import TestDataGenerator, ScraperTestSuite, create_basic_scraping_test
from utilities import LoggingUtils, FileUtils, ValidationUtils
from exceptions import ScrapingError, ErrorHandler
from cli_interface import ScraperCLI


class EnterpriseScraper:
    """Enterprise-grade scraper with all features integrated."""
    
    def __init__(self, config_path: str = None):
        """Initialize enterprise scraper.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.factory = ScraperFactory()
        self.metrics_collector = MetricsCollector(enable_collection=True)
        self.performance_monitor = PerformanceMonitor(self.metrics_collector)
        self.rate_limiter = self._setup_rate_limiting()
        self.result_processor = ResultProcessor()
        self.logger = LoggingUtils.create_logger("enterprise_scraper")
        
        # Setup result processing pipeline
        self._setup_processing_pipeline()
        
        # Configure performance thresholds
        self.performance_monitor.set_thresholds(
            min_success_rate=85.0,
            max_avg_duration=20.0,
            max_error_rate=10.0
        )
    
    def _setup_rate_limiting(self) -> DomainBasedRateLimiter:
        """Setup domain-based rate limiting."""
        default_config = RateLimitConfig(
            requests_per_second=0.5,  # Conservative default
            requests_per_minute=30,
            burst_allowance=3
        )
        
        rate_limiter = DomainBasedRateLimiter(default_config)
        
        # Configure specific domains
        truckpro_config = RateLimitConfig(
            requests_per_second=1.0,
            requests_per_minute=50,
            burst_allowance=5
        )
        rate_limiter.set_domain_config("truckpro.com", truckpro_config)
        
        return rate_limiter
    
    def _setup_processing_pipeline(self) -> None:
        """Setup comprehensive result processing pipeline."""
        self.result_processor.create_standard_pipeline(
            validate=True,
            clean=True,
            enrich=True,
            filter_invalid=False,  # Keep invalid items but mark them
            deduplicate=True
        )
        
        # Add custom filters
        from result_processor import FilterProcessor
        filter_processor = FilterProcessor()
        
        # Add price filter (items with price information preferred)
        filter_processor.add_filter(
            lambda item: item.get('price', 'N/A') != 'N/A' or 
                        item.get('quantity', 'N/A') != 'N/A'
        )
        
        self.result_processor.add_processor(filter_processor)
    
    def scrape_with_enterprise_features(
        self,
        search_terms: List[str],
        site_name: str,
        scraper_type: ScraperType = ScraperType.MONITORED
    ) -> Dict[str, Any]:
        """Perform enterprise-grade scraping with all features.
        
        Args:
            search_terms: Terms to search for
            site_name: Name of the site to scrape
            scraper_type: Type of scraper to use
            
        Returns:
            Comprehensive results with metadata
        """
        operation_start = time.time()
        operation_id = f"enterprise_scrape_{int(operation_start)}"
        
        try:
            self.logger.info(f"Starting enterprise scraping operation: {operation_id}")
            
            # Pre-flight checks
            self._perform_pre_flight_checks(site_name)
            
            # Create scraper
            scraper = self.factory.create_scraper(scraper_type, site_name, self.config_path)
            
            # Load configuration
            config = ConfigLoader.load_config_for_site(site_name, self.config_path)
            
            # Perform rate-limited scraping
            raw_results = self._perform_rate_limited_scraping(
                scraper, search_terms, config, operation_id
            )
            
            # Process results
            processed_results = self.result_processor.process_results(raw_results)
            
            # Generate comprehensive metrics
            operation_duration = time.time() - operation_start
            metrics = self._generate_operation_metrics(
                operation_id, search_terms, raw_results, processed_results, operation_duration
            )
            
            # Check for performance issues
            alerts = self.performance_monitor.check_performance_alerts(hours=1)
            
            # Prepare final results
            final_results = {
                'operation_id': operation_id,
                'timestamp': datetime.now().isoformat(),
                'configuration': {
                    'site_name': site_name,
                    'scraper_type': scraper_type.value,
                    'search_terms': search_terms
                },
                'raw_results': raw_results,
                'processed_results': processed_results,
                'metrics': metrics,
                'performance_alerts': alerts,
                'processing_summary': self.result_processor.get_processing_summary(),
                'rate_limiting_stats': self.rate_limiter.get_domain_stats()
            }
            
            self.logger.info(f"Enterprise scraping operation completed: {operation_id}")
            return final_results
            
        except Exception as e:
            self.logger.error(f"Enterprise scraping operation failed: {e}")
            
            # Record failure metrics
            self.metrics_collector.record_simple_metric(
                site_name=site_name,
                search_term=",".join(search_terms),
                operation="enterprise_scrape",
                duration_seconds=time.time() - operation_start,
                success=False,
                error=e
            )
            
            raise ScrapingError(f"Enterprise scraping failed: {e}")
    
    def _perform_pre_flight_checks(self, site_name: str) -> None:
        """Perform pre-flight checks before scraping."""
        self.logger.info("Performing pre-flight checks...")
        
        # Check configuration
        try:
            config = ConfigLoader.load_config_for_site(site_name, self.config_path)
            self.logger.info(f"✓ Configuration loaded for site: {site_name}")
        except ConfigurationError as e:
            raise ScrapingError(f"Configuration check failed: {e}")
        
        # Check recent performance
        recent_alerts = self.performance_monitor.check_performance_alerts(hours=1)
        critical_alerts = [a for a in recent_alerts if a['severity'] == 'critical']
        
        if critical_alerts:
            self.logger.warning(f"Found {len(critical_alerts)} critical performance alerts")
            for alert in critical_alerts[:3]:  # Show first 3
                self.logger.warning(f"  - {alert['message']}")
        
        # Check rate limiting status
        target_url = config.site_config.target_url
        if not self.rate_limiter.can_proceed_for_url(target_url):
            self.logger.warning("Rate limiting active - operations may be slower")
        
        self.logger.info("Pre-flight checks completed")
    
    def _perform_rate_limited_scraping(
        self,
        scraper,
        search_terms: List[str],
        config,
        operation_id: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Perform scraping with rate limiting."""
        results = {}
        target_url = config.site_config.target_url
        
        for i, search_term in enumerate(search_terms):
            # Rate limiting
            if not self.rate_limiter.acquire_for_url(target_url, timeout=30):
                raise ScrapingError(f"Rate limit timeout for search term: {search_term}")
            
            self.logger.info(f"Scraping term {i+1}/{len(search_terms)}: {search_term}")
            
            # Track operation
            term_operation_id = f"{operation_id}_term_{i}"
            self.metrics_collector.start_operation(term_operation_id)
            
            try:
                term_results = scraper.scrape_with_config(
                    search_terms=[search_term],
                    site_config=config.site_config,
                    debug_mode=False
                )
                
                results.update(term_results)
                
                self.metrics_collector.end_operation(
                    operation_id=term_operation_id,
                    site_name=config.site_config.site_name,
                    search_term=search_term,
                    operation="search",
                    success=True,
                    results_count=len(term_results.get(search_term, []))
                )
                
            except Exception as e:
                self.metrics_collector.end_operation(
                    operation_id=term_operation_id,
                    site_name=config.site_config.site_name,
                    search_term=search_term,
                    operation="search",
                    success=False,
                    error=e
                )
                raise
        
        return results
    
    def _generate_operation_metrics(
        self,
        operation_id: str,
        search_terms: List[str],
        raw_results: Dict[str, List[Dict[str, Any]]],
        processed_results: Dict[str, List[Dict[str, Any]]],
        operation_duration: float
    ) -> Dict[str, Any]:
        """Generate comprehensive operation metrics."""
        total_raw = sum(len(items) for items in raw_results.values())
        total_processed = sum(len(items) for items in processed_results.values())
        
        # Calculate quality metrics
        quality_scores = []
        for items in processed_results.values():
            for item in items:
                if '_scores' in item:
                    quality_scores.append(item['_scores'].get('quality_score', 0))
        
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # Validation statistics
        validation_issues = 0
        for items in processed_results.values():
            for item in items:
                if '_validation' in item and item['_validation'].get('issues'):
                    validation_issues += len(item['_validation']['issues'])
        
        return {
            'operation_id': operation_id,
            'duration_seconds': operation_duration,
            'search_terms_count': len(search_terms),
            'results_summary': {
                'raw_total': total_raw,
                'processed_total': total_processed,
                'processing_efficiency': (total_processed / total_raw * 100) if total_raw > 0 else 100,
                'average_quality_score': avg_quality,
                'validation_issues': validation_issues
            },
            'per_term_breakdown': {
                term: {
                    'raw_count': len(raw_results.get(term, [])),
                    'processed_count': len(processed_results.get(term, [])),
                    'has_results': len(processed_results.get(term, [])) > 0
                }
                for term in search_terms
            }
        }
    
    def generate_comprehensive_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive operational report.
        
        Args:
            hours: Number of hours to include in report
            
        Returns:
            Comprehensive report dictionary
        """
        performance_report = self.performance_monitor.generate_performance_report(hours)
        processing_summary = self.result_processor.get_processing_summary()
        rate_limiting_stats = self.rate_limiter.get_domain_stats()
        
        return {
            'report_type': 'comprehensive_operational_report',
            'generated_at': datetime.now().isoformat(),
            'time_period_hours': hours,
            'performance': performance_report,
            'processing': processing_summary,
            'rate_limiting': rate_limiting_stats,
            'system_health': {
                'total_operations': performance_report.get('overall_performance', {}).get('total_operations', 0),
                'overall_success_rate': performance_report.get('overall_performance', {}).get('success_rate', 0),
                'critical_alerts': len([
                    a for a in performance_report.get('alerts', [])
                    if a.get('severity') == 'critical'
                ])
            }
        }
    
    def run_system_tests(self) -> Dict[str, Any]:
        """Run comprehensive system tests.
        
        Returns:
            Test results dictionary
        """
        self.logger.info("Running comprehensive system tests...")
        
        test_suite = ScraperTestSuite("Enterprise System Tests")
        
        # Add component tests
        test_suite.add_test_case(create_basic_scraping_test())
        
        # Add integration tests
        integration_test = self._create_integration_test()
        test_suite.add_test_case(integration_test)
        
        # Run tests
        results = test_suite.run_all()
        
        self.logger.info(f"System tests completed: {results['success_rate']:.1f}% success rate")
        
        return results
    
    def _create_integration_test(self):
        """Create integration test case."""
        from testing_utilities import ScraperTestCase
        
        test_case = ScraperTestCase(
            name="enterprise_integration_test",
            description="Test enterprise scraper integration"
        )
        
        def test_rate_limiter():
            """Test rate limiter functionality."""
            assert self.rate_limiter is not None, "Rate limiter should be initialized"
            assert self.rate_limiter.can_proceed_for_url("https://example.com"), "Should allow requests initially"
        
        def test_metrics_collection():
            """Test metrics collection."""
            initial_count = len(self.metrics_collector.metrics)
            
            self.metrics_collector.record_simple_metric(
                site_name="test",
                search_term="test",
                operation="test",
                duration_seconds=1.0,
                success=True
            )
            
            assert len(self.metrics_collector.metrics) == initial_count + 1, "Metrics should be recorded"
        
        def test_result_processor():
            """Test result processor."""
            test_results = {"test": [{"title": "Test Product", "url": "https://example.com/test"}]}
            processed = self.result_processor.process_results(test_results)
            
            assert "test" in processed, "Results should be processed"
            assert len(processed["test"]) > 0, "Should have processed items"
        
        test_case.add_assertion(test_rate_limiter)
        test_case.add_assertion(test_metrics_collection)
        test_case.add_assertion(test_result_processor)
        
        return test_case


def demonstration_workflow():
    """Comprehensive demonstration of the enterprise scraper."""
    print("🚀 Enterprise Web Scraper - Comprehensive Demonstration")
    print("=" * 60)
    
    # Setup logging
    LoggingUtils.setup_logging(level="INFO", log_file="enterprise_demo.log")
    logger = LoggingUtils.create_logger("demo")
    
    try:
        # Initialize enterprise scraper
        print("\n📊 Initializing Enterprise Scraper...")
        scraper = EnterpriseScraper()
        
        # Run system tests
        print("\n🧪 Running System Tests...")
        test_results = scraper.run_system_tests()
        
        print(f"Test Results:")
        print(f"  ✅ Passed: {test_results['passed_tests']}")
        print(f"  ❌ Failed: {test_results['failed_tests']}")
        print(f"  📈 Success Rate: {test_results['success_rate']:.1f}%")
        
        # Demonstrate configuration loading
        print("\n⚙️ Testing Configuration System...")
        try:
            # Use default TruckPro configuration for demo
            config = ConfigLoader.create_default_truckpro_config()
            print(f"  ✅ Configuration loaded: {config.site_name}")
            print(f"  🎯 Target URL: {config.target_url}")
            print(f"  🔍 Search selectors: {len(config.scraping_config.search_input_selectors)}")
        except Exception as e:
            print(f"  ❌ Configuration error: {e}")
        
        # Demonstrate rate limiting
        print("\n🚦 Testing Rate Limiting...")
        test_url = "https://truckpro.com"
        can_proceed = scraper.rate_limiter.can_proceed_for_url(test_url)
        print(f"  📊 Can proceed to {test_url}: {can_proceed}")
        
        # Demonstrate result processing
        print("\n🔄 Testing Result Processing...")
        sample_results = {
            "brake pads": [
                {
                    "title": "Premium Brake Pads",
                    "url": "https://example.com/brake-pads-1",
                    "part_number": "BP001",
                    "price": "$49.99",
                    "quantity": "5"
                },
                {
                    "title": "Economy Brake Pads",
                    "url": "https://example.com/brake-pads-2", 
                    "part_number": "BP002",
                    "price": "N/A",
                    "quantity": "10"
                }
            ]
        }
        
        processed_results = scraper.result_processor.process_results(sample_results)
        processing_summary = scraper.result_processor.get_processing_summary()
        
        print(f"  📥 Original items: {processing_summary['total_original_items']}")
        print(f"  📤 Processed items: {processing_summary['total_processed_items']}")
        print(f"  📈 Processing rate: {processing_summary['overall_processing_rate']:.1f}%")
        
        # Demonstrate metrics and monitoring
        print("\n📈 Testing Metrics and Monitoring...")
        
        # Simulate some operations
        for i in range(5):
            scraper.metrics_collector.record_simple_metric(
                site_name="demo_site",
                search_term=f"test_term_{i}",
                operation="demo_search",
                duration_seconds=1.0 + i * 0.5,
                success=i < 4,  # 4 successes, 1 failure
                results_count=i * 2
            )
        
        # Generate performance report
        performance_report = scraper.performance_monitor.generate_performance_report(hours=1)
        overall_stats = performance_report.get('overall_performance', {})
        
        print(f"  📊 Total operations: {overall_stats.get('total_operations', 0)}")
        print(f"  ✅ Success rate: {overall_stats.get('success_rate', 0):.1f}%")
        print(f"  ⏱️ Average duration: {overall_stats.get('average_duration', 0):.2f}s")
        
        # Check for alerts
        alerts = scraper.performance_monitor.check_performance_alerts()
        print(f"  🚨 Performance alerts: {len(alerts)}")
        
        # Generate comprehensive report
        print("\n📋 Generating Comprehensive Report...")
        comprehensive_report = scraper.generate_comprehensive_report(hours=1)
        
        # Save report
        report_file = FileUtils.get_timestamped_filename("enterprise_demo_report", "json")
        with open(report_file, 'w') as f:
            json.dump(comprehensive_report, f, indent=2, default=str)
        
        print(f"  💾 Report saved: {report_file}")
        
        # Demonstrate CLI interface
        print("\n💻 Testing CLI Interface...")
        try:
            cli = ScraperCLI()
            print("  ✅ CLI interface initialized successfully")
            print("  💡 Try: python cli_interface.py --help")
        except Exception as e:
            print(f"  ❌ CLI error: {e}")
        
        # Final summary
        print(f"\n🎉 Enterprise Demonstration Completed Successfully!")
        print("=" * 60)
        print("Key Features Demonstrated:")
        print("  ✅ Modular architecture with SOLID principles")
        print("  ✅ Factory pattern for different scraper types")
        print("  ✅ Comprehensive exception handling")
        print("  ✅ Performance monitoring and alerting")
        print("  ✅ Rate limiting for respectful scraping")
        print("  ✅ Result processing pipeline")
        print("  ✅ Metrics collection and reporting")
        print("  ✅ Testing framework integration")
        print("  ✅ Command-line interface")
        print("  ✅ Configuration management")
        
        return True
        
    except Exception as e:
        logger.error(f"Enterprise demonstration failed: {e}")
        print(f"\n❌ Demonstration failed: {e}")
        return False


if __name__ == "__main__":
    demonstration_workflow()