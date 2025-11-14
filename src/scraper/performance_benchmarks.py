"""Performance benchmarking utilities for the web scraper architecture."""

import time
import json
import logging
import statistics
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from scraper_factory import ScraperFactory, ScraperType
from config.config_loader import ConfigLoader
from metrics_monitor import MetricsCollector, PerformanceMonitor
from utilities import LoggingUtils, FileUtils
from testing_utilities import TestDataGenerator, MockWebDriver


logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Result of a performance benchmark."""
    
    test_name: str
    description: str
    iterations: int
    total_duration: float
    average_duration: float
    min_duration: float
    max_duration: float
    median_duration: float
    std_deviation: float
    success_rate: float
    errors: List[str]
    metadata: Dict[str, Any]
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark tests."""
    
    iterations: int = 10
    warmup_iterations: int = 2
    timeout_seconds: float = 30.0
    concurrent_threads: int = 1
    cool_down_seconds: float = 1.0
    capture_errors: bool = True
    detailed_logging: bool = False


class PerformanceBenchmark:
    """Performance benchmarking framework."""
    
    def __init__(self, config: BenchmarkConfig = None):
        """Initialize benchmark framework.
        
        Args:
            config: Benchmark configuration
        """
        self.config = config or BenchmarkConfig()
        self.results: List[BenchmarkResult] = []
        self.logger = LoggingUtils.create_logger("benchmark")
        
    def run_benchmark(
        self,
        test_name: str,
        test_function: Callable,
        description: str = "",
        **test_kwargs
    ) -> BenchmarkResult:
        """Run a performance benchmark test.
        
        Args:
            test_name: Name of the test
            test_function: Function to benchmark
            description: Test description
            **test_kwargs: Arguments to pass to test function
            
        Returns:
            Benchmark result
        """
        self.logger.info(f"Starting benchmark: {test_name}")
        
        # Warmup runs
        if self.config.warmup_iterations > 0:
            self.logger.info(f"Running {self.config.warmup_iterations} warmup iterations...")
            for _ in range(self.config.warmup_iterations):
                try:
                    test_function(**test_kwargs)
                except Exception:
                    pass  # Ignore warmup errors
                time.sleep(self.config.cool_down_seconds)
        
        # Actual benchmark runs
        durations = []
        errors = []
        successful_runs = 0
        
        start_time = datetime.now()
        
        for i in range(self.config.iterations):
            self.logger.debug(f"Iteration {i + 1}/{self.config.iterations}")
            
            iteration_start = time.time()
            try:
                test_function(**test_kwargs)
                iteration_duration = time.time() - iteration_start
                durations.append(iteration_duration)
                successful_runs += 1
                
            except Exception as e:
                iteration_duration = time.time() - iteration_start
                if self.config.capture_errors:
                    errors.append(f"Iteration {i + 1}: {str(e)}")
                
                if self.config.detailed_logging:
                    self.logger.warning(f"Iteration {i + 1} failed: {e}")
            
            # Cool down between iterations
            if i < self.config.iterations - 1:
                time.sleep(self.config.cool_down_seconds)
        
        # Calculate statistics
        if durations:
            total_duration = sum(durations)
            average_duration = statistics.mean(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            median_duration = statistics.median(durations)
            std_deviation = statistics.stdev(durations) if len(durations) > 1 else 0.0
        else:
            total_duration = average_duration = min_duration = max_duration = median_duration = std_deviation = 0.0
        
        success_rate = (successful_runs / self.config.iterations) * 100
        
        # Create result
        result = BenchmarkResult(
            test_name=test_name,
            description=description,
            iterations=self.config.iterations,
            total_duration=total_duration,
            average_duration=average_duration,
            min_duration=min_duration,
            max_duration=max_duration,
            median_duration=median_duration,
            std_deviation=std_deviation,
            success_rate=success_rate,
            errors=errors,
            metadata={
                "warmup_iterations": self.config.warmup_iterations,
                "concurrent_threads": self.config.concurrent_threads,
                "timeout_seconds": self.config.timeout_seconds,
                "successful_runs": successful_runs,
                "failed_runs": self.config.iterations - successful_runs
            },
            timestamp=start_time.isoformat()
        )
        
        self.results.append(result)
        self.logger.info(f"Benchmark completed: {test_name} - Success rate: {success_rate:.1f}%")
        
        return result
    
    def run_concurrent_benchmark(
        self,
        test_name: str,
        test_function: Callable,
        description: str = "",
        **test_kwargs
    ) -> BenchmarkResult:
        """Run a concurrent performance benchmark.
        
        Args:
            test_name: Name of the test
            test_function: Function to benchmark
            description: Test description
            **test_kwargs: Arguments to pass to test function
            
        Returns:
            Benchmark result
        """
        self.logger.info(f"Starting concurrent benchmark: {test_name} ({self.config.concurrent_threads} threads)")
        
        durations = []
        errors = []
        successful_runs = 0
        start_time = datetime.now()
        
        with ThreadPoolExecutor(max_workers=self.config.concurrent_threads) as executor:
            # Submit all tasks
            futures = []
            for i in range(self.config.iterations):
                future = executor.submit(self._run_timed_function, test_function, test_kwargs)
                futures.append(future)
            
            # Collect results
            for i, future in enumerate(as_completed(futures, timeout=self.config.timeout_seconds)):
                try:
                    duration, error = future.result()
                    if error is None:
                        durations.append(duration)
                        successful_runs += 1
                    else:
                        if self.config.capture_errors:
                            errors.append(f"Thread {i + 1}: {str(error)}")
                        
                except Exception as e:
                    if self.config.capture_errors:
                        errors.append(f"Thread {i + 1}: {str(e)}")
        
        # Calculate statistics (same as sequential)
        if durations:
            total_duration = sum(durations)
            average_duration = statistics.mean(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            median_duration = statistics.median(durations)
            std_deviation = statistics.stdev(durations) if len(durations) > 1 else 0.0
        else:
            total_duration = average_duration = min_duration = max_duration = median_duration = std_deviation = 0.0
        
        success_rate = (successful_runs / self.config.iterations) * 100
        
        result = BenchmarkResult(
            test_name=test_name,
            description=description,
            iterations=self.config.iterations,
            total_duration=total_duration,
            average_duration=average_duration,
            min_duration=min_duration,
            max_duration=max_duration,
            median_duration=median_duration,
            std_deviation=std_deviation,
            success_rate=success_rate,
            errors=errors,
            metadata={
                "concurrent_threads": self.config.concurrent_threads,
                "test_type": "concurrent",
                "successful_runs": successful_runs,
                "failed_runs": self.config.iterations - successful_runs
            },
            timestamp=start_time.isoformat()
        )
        
        self.results.append(result)
        self.logger.info(f"Concurrent benchmark completed: {test_name}")
        
        return result
    
    def _run_timed_function(self, test_function: Callable, test_kwargs: Dict) -> tuple:
        """Run function and return duration and any error."""
        start_time = time.time()
        error = None
        
        try:
            test_function(**test_kwargs)
        except Exception as e:
            error = e
        
        duration = time.time() - start_time
        return duration, error
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive benchmark report.
        
        Returns:
            Benchmark report dictionary
        """
        if not self.results:
            return {"message": "No benchmark results available"}
        
        # Overall statistics
        all_durations = []
        all_success_rates = []
        
        for result in self.results:
            if result.average_duration > 0:
                all_durations.append(result.average_duration)
            all_success_rates.append(result.success_rate)
        
        # Best and worst performing tests
        if all_durations:
            fastest_test = min(self.results, key=lambda r: r.average_duration if r.average_duration > 0 else float('inf'))
            slowest_test = max(self.results, key=lambda r: r.average_duration)
        else:
            fastest_test = slowest_test = None
        
        most_reliable = max(self.results, key=lambda r: r.success_rate)
        least_reliable = min(self.results, key=lambda r: r.success_rate)
        
        return {
            "report_timestamp": datetime.now().isoformat(),
            "total_tests": len(self.results),
            "overall_statistics": {
                "average_duration_across_tests": statistics.mean(all_durations) if all_durations else 0,
                "average_success_rate": statistics.mean(all_success_rates) if all_success_rates else 0,
                "total_iterations": sum(r.iterations for r in self.results),
                "total_successful_runs": sum(r.metadata.get("successful_runs", 0) for r in self.results)
            },
            "performance_highlights": {
                "fastest_test": {
                    "name": fastest_test.test_name if fastest_test else None,
                    "duration": fastest_test.average_duration if fastest_test else None
                },
                "slowest_test": {
                    "name": slowest_test.test_name if slowest_test else None,
                    "duration": slowest_test.average_duration if slowest_test else None
                },
                "most_reliable": {
                    "name": most_reliable.test_name,
                    "success_rate": most_reliable.success_rate
                },
                "least_reliable": {
                    "name": least_reliable.test_name,
                    "success_rate": least_reliable.success_rate
                }
            },
            "detailed_results": [result.to_dict() for result in self.results]
        }
    
    def save_report(self, filepath: Optional[str] = None) -> str:
        """Save benchmark report to file.
        
        Args:
            filepath: Optional file path
            
        Returns:
            Path to saved report
        """
        if not filepath:
            filepath = FileUtils.get_timestamped_filename("benchmark_report", "json")
        
        report = self.generate_report()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"Benchmark report saved to: {filepath}")
        return filepath


class ScraperBenchmarks:
    """Specific benchmarks for scraper components."""
    
    def __init__(self):
        """Initialize scraper benchmarks."""
        self.benchmark = PerformanceBenchmark()
        self.factory = ScraperFactory()
        
    def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run all scraper benchmarks.
        
        Returns:
            Comprehensive benchmark report
        """
        self.logger = LoggingUtils.create_logger("scraper_benchmarks")
        self.logger.info("Starting comprehensive scraper benchmarks...")
        
        # Component benchmarks
        self.benchmark_driver_creation()
        self.benchmark_element_finding()
        self.benchmark_data_extraction()
        self.benchmark_result_processing()
        
        # Integration benchmarks
        self.benchmark_basic_scraping()
        self.benchmark_monitored_scraping()
        
        # Concurrency benchmarks
        self.benchmark_concurrent_scraping()
        
        # Generate and save report
        report = self.benchmark.generate_report()
        report_file = self.benchmark.save_report()
        
        self.logger.info(f"All benchmarks completed. Report saved to: {report_file}")
        return report
    
    def benchmark_driver_creation(self):
        """Benchmark WebDriver creation and destruction."""
        from web_driver_manager import WebDriverManager
        from config.config_loader import ConfigLoader
        
        def create_and_destroy_driver():
            chrome_config = ConfigLoader.load_default_chrome_config()
            manager = WebDriverManager(chrome_config)
            driver = manager.create_driver()
            if driver:
                manager.quit_driver()
        
        config = BenchmarkConfig(iterations=5, warmup_iterations=1)
        self.benchmark.config = config
        
        self.benchmark.run_benchmark(
            "driver_creation",
            create_and_destroy_driver,
            "WebDriver creation and destruction performance"
        )
    
    def benchmark_element_finding(self):
        """Benchmark element finding performance."""
        from element_finder import ElementFinder
        from testing_utilities import MockWebDriver, TestDataGenerator
        
        def find_elements():
            mock_driver = MockWebDriver()
            elements = TestDataGenerator.create_search_page_elements()
            
            for selector, element in elements.items():
                mock_driver.add_mock_element(selector, element)
            
            finder = ElementFinder(mock_driver, default_timeout=1)
            
            # Test multiple selector strategies
            selectors = ["#searchInput", "input[type='search']", ".non-existent"]
            result = finder.find_element_with_selectors(selectors, timeout=1)
            
            return result is not None
        
        config = BenchmarkConfig(iterations=100, warmup_iterations=5, cool_down_seconds=0.01)
        self.benchmark.config = config
        
        self.benchmark.run_benchmark(
            "element_finding",
            find_elements,
            "Element finding with multiple selector fallbacks"
        )
    
    def benchmark_data_extraction(self):
        """Benchmark data extraction performance."""
        from data_extractor import DataExtractor
        from element_finder import ElementFinder
        from testing_utilities import MockWebDriver, TestDataGenerator
        from config.config_loader import ConfigLoader
        
        def extract_product_data():
            mock_driver = MockWebDriver()
            finder = ElementFinder(mock_driver)
            extractor = DataExtractor(finder)
            
            # Create mock product card
            product_card = TestDataGenerator.create_product_card_element(
                title="Performance Test Product",
                part_number="PERF123",
                price="$29.99"
            )
            
            config = ConfigLoader.create_default_truckpro_config()
            
            result = extractor.extract_product_data(
                product_card,
                config.scraping_config,
                card_index=1
            )
            
            return result.is_valid()
        
        config = BenchmarkConfig(iterations=50, warmup_iterations=3, cool_down_seconds=0.01)
        self.benchmark.config = config
        
        self.benchmark.run_benchmark(
            "data_extraction",
            extract_product_data,
            "Product data extraction from mock elements"
        )
    
    def benchmark_result_processing(self):
        """Benchmark result processing pipeline."""
        from result_processor import ResultProcessor
        
        def process_results():
            processor = ResultProcessor()
            processor.create_standard_pipeline()
            
            # Create sample results
            sample_results = {
                "test_search": [
                    {
                        "title": f"Test Product {i}",
                        "url": f"https://example.com/product-{i}",
                        "part_number": f"TEST{i:03d}",
                        "price": f"${i * 10 + 9.99:.2f}",
                        "quantity": str(i * 5)
                    }
                    for i in range(1, 21)  # 20 products
                ]
            }
            
            processed = processor.process_results(sample_results)
            return len(processed["test_search"]) > 0
        
        config = BenchmarkConfig(iterations=20, warmup_iterations=2, cool_down_seconds=0.1)
        self.benchmark.config = config
        
        self.benchmark.run_benchmark(
            "result_processing",
            process_results,
            "Result processing pipeline with 20 mock products"
        )
    
    def benchmark_basic_scraping(self):
        """Benchmark basic scraping workflow (mocked)."""
        def mock_scraping_workflow():
            # Simulate the full scraping workflow with mocks
            from testing_utilities import MockWebDriver, TestDataGenerator
            from web_scraper import WebScraper
            from config.config_loader import ConfigLoader
            
            mock_driver = MockWebDriver()
            
            # Setup mock elements
            elements = TestDataGenerator.create_search_page_elements()
            product_cards = [
                TestDataGenerator.create_product_card_element(
                    title=f"Mock Product {i}",
                    part_number=f"MOCK{i:03d}"
                ) for i in range(1, 6)
            ]
            elements["div.productlist"] = product_cards
            
            for selector, element in elements.items():
                mock_driver.add_mock_element(selector, element)
            
            # Create scraper and config
            scraper = WebScraper(mock_driver)
            config = ConfigLoader.create_default_truckpro_config()
            
            # Perform mock scraping
            results = scraper.scrape_site("mock_search", config, debug_mode=False)
            
            return len(results) > 0
        
        config = BenchmarkConfig(iterations=10, warmup_iterations=1, cool_down_seconds=0.5)
        self.benchmark.config = config
        
        self.benchmark.run_benchmark(
            "basic_scraping_workflow",
            mock_scraping_workflow,
            "Complete basic scraping workflow with mocked browser"
        )
    
    def benchmark_monitored_scraping(self):
        """Benchmark monitored scraping with metrics collection."""
        def monitored_scraping():
            from metrics_monitor import MetricsCollector
            
            collector = MetricsCollector(enable_collection=True)
            
            # Simulate multiple operations
            for i in range(5):
                operation_id = f"bench_op_{i}"
                collector.start_operation(operation_id)
                
                # Simulate work
                time.sleep(0.01)
                
                collector.end_operation(
                    operation_id=operation_id,
                    site_name="benchmark_site",
                    search_term=f"term_{i}",
                    operation="search",
                    success=True,
                    results_count=i + 1
                )
            
            stats = collector.get_stats()
            return stats.total_operations == 5
        
        config = BenchmarkConfig(iterations=15, warmup_iterations=2, cool_down_seconds=0.1)
        self.benchmark.config = config
        
        self.benchmark.run_benchmark(
            "monitored_scraping",
            monitored_scraping,
            "Scraping with metrics collection and monitoring"
        )
    
    def benchmark_concurrent_scraping(self):
        """Benchmark concurrent scraping operations."""
        def concurrent_operation():
            from threading import Lock
            from time import sleep
            
            lock = Lock()
            
            with lock:
                # Simulate thread-safe operation
                sleep(0.005)  # 5ms simulated work
                return True
        
        config = BenchmarkConfig(
            iterations=20,
            concurrent_threads=4,
            warmup_iterations=2,
            cool_down_seconds=0.01
        )
        self.benchmark.config = config
        
        self.benchmark.run_concurrent_benchmark(
            "concurrent_operations",
            concurrent_operation,
            "Concurrent scraping operations with thread safety"
        )


def run_performance_analysis():
    """Run comprehensive performance analysis."""
    print("🚀 Starting Comprehensive Performance Analysis")
    print("=" * 60)
    
    # Setup logging
    LoggingUtils.setup_logging(level="INFO", log_file="performance_benchmark.log")
    
    try:
        # Run scraper benchmarks
        scraper_benchmarks = ScraperBenchmarks()
        report = scraper_benchmarks.run_all_benchmarks()
        
        # Print summary
        print(f"\n📊 Performance Analysis Summary")
        print(f"{'=' * 40}")
        
        overall_stats = report.get("overall_statistics", {})
        print(f"Total tests run: {report.get('total_tests', 0)}")
        print(f"Average duration: {overall_stats.get('average_duration_across_tests', 0):.3f}s")
        print(f"Average success rate: {overall_stats.get('average_success_rate', 0):.1f}%")
        print(f"Total iterations: {overall_stats.get('total_iterations', 0)}")
        
        # Performance highlights
        highlights = report.get("performance_highlights", {})
        fastest = highlights.get("fastest_test", {})
        slowest = highlights.get("slowest_test", {})
        
        print(f"\n🏆 Performance Highlights:")
        if fastest.get("name"):
            print(f"  ⚡ Fastest: {fastest['name']} ({fastest['duration']:.3f}s)")
        if slowest.get("name"):
            print(f"  🐌 Slowest: {slowest['name']} ({slowest['duration']:.3f}s)")
        
        reliable = highlights.get("most_reliable", {})
        print(f"  ✅ Most Reliable: {reliable.get('name')} ({reliable.get('success_rate', 0):.1f}%)")
        
        # Detailed results
        print(f"\n📋 Detailed Test Results:")
        for result in report.get("detailed_results", []):
            status = "✅" if result['success_rate'] > 95 else "⚠️" if result['success_rate'] > 80 else "❌"
            print(f"  {status} {result['test_name']}: {result['average_duration']:.3f}s avg, {result['success_rate']:.1f}% success")
        
        # Recommendations
        print(f"\n💡 Performance Recommendations:")
        
        avg_duration = overall_stats.get('average_duration_across_tests', 0)
        if avg_duration > 1.0:
            print("  - Consider optimizing slow operations (avg > 1s)")
        if avg_duration < 0.1:
            print("  - Excellent performance across all components")
        
        avg_success = overall_stats.get('average_success_rate', 0)
        if avg_success < 95:
            print("  - Investigate reliability issues (success rate < 95%)")
        if avg_success >= 99:
            print("  - Excellent reliability across all components")
        
        print(f"\n📁 Full report available in benchmark results file")
        
        return report
        
    except Exception as e:
        print(f"❌ Performance analysis failed: {e}")
        return None


if __name__ == "__main__":
    run_performance_analysis()