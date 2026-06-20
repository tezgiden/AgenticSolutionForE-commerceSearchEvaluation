"""Command-line interface for the web scraper."""

import json
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from scraper_factory import ScraperFactory, ScraperType
from config.config_loader import ConfigLoader, ConfigurationError
from result_processor import ResultProcessor, CommonFilters
from utilities import LoggingUtils, FileUtils, ValidationUtils
from exceptions import ScrapingError, ErrorHandler
from metrics_monitor import MetricsCollector, PerformanceMonitor


class CLIColors:
    """ANSI color codes for CLI output."""
    
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    
    @classmethod
    def colorize(cls, text: str, color: str) -> str:
        """Colorize text if stdout supports it."""
        if sys.stdout.isatty():
            return f"{color}{text}{cls.RESET}"
        return text


class ScraperCLI:
    """Command-line interface for the web scraper."""
    
    def __init__(self):
        """Initialize CLI."""
        self.parser = self._create_parser()
        self.logger = None
        
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser."""
        parser = argparse.ArgumentParser(
            description="Web Scraper - Extract product data from websites",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Basic scraping
  python cli_interface.py scrape --site truckpro --search "brake pads" "oil filter"
  
  # Monitored scraping with metrics
  python cli_interface.py scrape --site truckpro --type monitored --search "gasket"
  
  # Batch processing from file
  python cli_interface.py scrape --site truckpro --search-file searches.txt
  
  # Process results
  python cli_interface.py process --input results.json --output processed.json
  
  # Generate reports
  python cli_interface.py report --metrics metrics.json --format html
            """
        )
        
        # Global options
        parser.add_argument(
            '--config', '-c',
            type=str,
            help='Path to configuration file'
        )
        parser.add_argument(
            '--log-level',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
            default='INFO',
            help='Logging level'
        )
        parser.add_argument(
            '--log-file',
            type=str,
            help='Log file path'
        )
        parser.add_argument(
            '--quiet', '-q',
            action='store_true',
            help='Suppress output except errors'
        )
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Verbose output'
        )
        
        # Subcommands
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Scrape command
        self._add_scrape_command(subparsers)
        
        # Process command
        self._add_process_command(subparsers)
        
        # Report command
        self._add_report_command(subparsers)
        
        # Config command
        self._add_config_command(subparsers)
        
        # Test command
        self._add_test_command(subparsers)
        
        return parser
    
    def _add_scrape_command(self, subparsers):
        """Add scrape subcommand."""
        scrape_parser = subparsers.add_parser('scrape', help='Scrape websites for product data')
        
        scrape_parser.add_argument(
            '--site', '-s',
            required=True,
            help='Site name from configuration'
        )
        scrape_parser.add_argument(
            '--type', '-t',
            choices=['basic', 'advanced', 'monitored', 'batch', 'testing'],
            default='basic',
            help='Scraper type to use'
        )
        
        # Search terms
        search_group = scrape_parser.add_mutually_exclusive_group(required=True)
        search_group.add_argument(
            '--search',
            nargs='+',
            help='Search terms to scrape'
        )
        search_group.add_argument(
            '--search-file',
            type=str,
            help='File containing search terms (one per line)'
        )
        
        # Output options
        scrape_parser.add_argument(
            '--output', '-o',
            type=str,
            help='Output file path (default: auto-generated)'
        )
        scrape_parser.add_argument(
            '--format',
            choices=['json', 'csv', 'xlsx'],
            default='json',
            help='Output format'
        )
        
        # Scraping options
        scrape_parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug mode'
        )
        scrape_parser.add_argument(
            '--headless',
            action='store_true',
            default=True,
            help='Run browser in headless mode'
        )
        scrape_parser.add_argument(
            '--screenshots',
            action='store_true',
            help='Enable screenshots'
        )
        scrape_parser.add_argument(
            '--delay',
            type=float,
            default=2.0,
            help='Delay between searches in seconds'
        )
        scrape_parser.add_argument(
            '--max-results',
            type=int,
            default=10,
            help='Maximum results per search'
        )
        
        # Processing options
        scrape_parser.add_argument(
            '--process',
            action='store_true',
            help='Process results through pipeline'
        )
        scrape_parser.add_argument(
            '--validate',
            action='store_true',
            help='Validate results'
        )
        scrape_parser.add_argument(
            '--dedupe',
            action='store_true',
            help='Remove duplicate results'
        )
    
    def _add_process_command(self, subparsers):
        """Add process subcommand."""
        process_parser = subparsers.add_parser('process', help='Process scraped results')
        
        process_parser.add_argument(
            '--input', '-i',
            required=True,
            help='Input file with scraped results'
        )
        process_parser.add_argument(
            '--output', '-o',
            help='Output file for processed results'
        )
        process_parser.add_argument(
            '--format',
            choices=['json', 'csv', 'xlsx'],
            default='json',
            help='Output format'
        )
        
        # Processing options
        process_parser.add_argument(
            '--validate',
            action='store_true',
            default=True,
            help='Validate results'
        )
        process_parser.add_argument(
            '--clean',
            action='store_true',
            default=True,
            help='Clean and normalize data'
        )
        process_parser.add_argument(
            '--enrich',
            action='store_true',
            default=True,
            help='Enrich with additional data'
        )
        process_parser.add_argument(
            '--dedupe',
            action='store_true',
            default=True,
            help='Remove duplicates'
        )
        process_parser.add_argument(
            '--filter-invalid',
            action='store_true',
            help='Filter out invalid items'
        )
        
        # Filtering options
        process_parser.add_argument(
            '--min-price',
            type=float,
            help='Minimum price filter'
        )
        process_parser.add_argument(
            '--max-price',
            type=float,
            help='Maximum price filter'
        )
        process_parser.add_argument(
            '--has-price',
            action='store_true',
            help='Filter items with price only'
        )
        process_parser.add_argument(
            '--exact-match-only',
            action='store_true',
            help='Filter exact matches only'
        )
    
    def _add_report_command(self, subparsers):
        """Add report subcommand."""
        report_parser = subparsers.add_parser('report', help='Generate reports from data')
        
        report_group = report_parser.add_mutually_exclusive_group(required=True)
        report_group.add_argument(
            '--results',
            help='Results file to analyze'
        )
        report_group.add_argument(
            '--metrics',
            help='Metrics file to analyze'
        )
        
        report_parser.add_argument(
            '--output', '-o',
            help='Output file for report'
        )
        report_parser.add_argument(
            '--format',
            choices=['json', 'html', 'txt'],
            default='json',
            help='Report format'
        )
        report_parser.add_argument(
            '--template',
            help='Custom template file'
        )
    
    def _add_config_command(self, subparsers):
        """Add config subcommand."""
        config_parser = subparsers.add_parser('config', help='Configuration management')
        
        config_subparsers = config_parser.add_subparsers(dest='config_action')
        
        # Validate config
        validate_parser = config_subparsers.add_parser('validate', help='Validate configuration')
        validate_parser.add_argument('config_file', help='Configuration file to validate')
        
        # Generate sample config
        generate_parser = config_subparsers.add_parser('generate', help='Generate sample configuration')
        generate_parser.add_argument('--output', '-o', help='Output file path')
        generate_parser.add_argument('--site', help='Site name for configuration')
        
        # List sites
        config_subparsers.add_parser('list', help='List available sites in configuration')
    
    def _add_test_command(self, subparsers):
        """Add test subcommand."""
        test_parser = subparsers.add_parser('test', help='Run tests')
        
        test_parser.add_argument(
            '--site',
            help='Test specific site configuration'
        )
        test_parser.add_argument(
            '--component',
            choices=['element_finder', 'data_extractor', 'web_scraper', 'all'],
            default='all',
            help='Component to test'
        )
        test_parser.add_argument(
            '--output',
            help='Test results output file'
        )
    
    def run(self, args: Optional[List[str]] = None) -> int:
        """Run the CLI.
        
        Args:
            args: Command line arguments (uses sys.argv if None)
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        try:
            parsed_args = self.parser.parse_args(args)
            
            # Setup logging
            self._setup_logging(parsed_args)
            
            # Route to appropriate command handler
            if parsed_args.command == 'scrape':
                return self._handle_scrape(parsed_args)
            elif parsed_args.command == 'process':
                return self._handle_process(parsed_args)
            elif parsed_args.command == 'report':
                return self._handle_report(parsed_args)
            elif parsed_args.command == 'config':
                return self._handle_config(parsed_args)
            elif parsed_args.command == 'test':
                return self._handle_test(parsed_args)
            else:
                self.parser.print_help()
                return 1
                
        except KeyboardInterrupt:
            self._print_error("Operation cancelled by user")
            return 130
        except Exception as e:
            self._print_error(f"Unexpected error: {e}")
            if self.logger:
                self.logger.exception("CLI error")
            return 1
    
    def _setup_logging(self, args) -> None:
        """Setup logging based on arguments."""
        if args.quiet:
            log_level = 'ERROR'
        elif args.verbose:
            log_level = 'DEBUG'
        else:
            log_level = args.log_level
        
        LoggingUtils.setup_logging(
            level=log_level,
            log_file=args.log_file,
            include_timestamp=True
        )
        
        self.logger = LoggingUtils.create_logger("cli")
    
    def _handle_scrape(self, args) -> int:
        """Handle scrape command."""
        try:
            self._print_header("Web Scraper - Scraping Mode")
            
            # Load search terms
            if args.search:
                search_terms = args.search
            else:
                search_terms = self._load_search_terms_from_file(args.search_file)
            
            self._print_info(f"Search terms: {', '.join(search_terms)}")
            
            # Create scraper
            scraper_type = ScraperType(args.type)
            factory = ScraperFactory()
            
            self._print_info(f"Creating {args.type} scraper for site: {args.site}")
            scraper = factory.create_scraper(scraper_type, args.site, args.config)
            
            # Perform scraping
            self._print_info("Starting scraping operation...")
            start_time = datetime.now()
            
            # Load configuration for scraping parameters
            config = ConfigLoader.load_config_for_site(args.site, args.config)
            
            # Update configuration based on CLI args
            if args.max_results:
                config.site_config.scraping_config.max_results_per_query = args.max_results
            
            results = scraper.scrape_with_config(
                search_terms=search_terms,
                site_config=config.site_config,
                debug_mode=args.debug,
                delay_between_searches=args.delay
            )
            
            duration = datetime.now() - start_time
            self._print_success(f"Scraping completed in {duration.total_seconds():.1f} seconds")
            
            # Process results if requested
            if args.process:
                results = self._process_results(results, args)
            
            # Generate output filename if not provided
            output_file = args.output
            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_site = FileUtils.get_safe_filename(args.site)
                output_file = f"scrape_{safe_site}_{timestamp}.{args.format}"
            
            # Save results
            self._save_results(results, output_file, args.format)
            
            # Print summary
            self._print_scraping_summary(results, output_file)
            
            # Generate performance report for monitored scrapers
            if hasattr(scraper, 'get_performance_report'):
                self._print_performance_summary(scraper)
            
            return 0
            
        except (ScrapingError, ConfigurationError) as e:
            self._print_error(f"Scraping error: {e}")
            return 1
        except Exception as e:
            self._print_error(f"Unexpected error during scraping: {e}")
            return 1
    
    def _handle_process(self, args) -> int:
        """Handle process command."""
        try:
            self._print_header("Web Scraper - Processing Mode")
            
            # Load input data
            if not Path(args.input).exists():
                self._print_error(f"Input file not found: {args.input}")
                return 1
            
            with open(args.input, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            self._print_info(f"Loaded results from: {args.input}")
            
            # Process results
            processed_results = self._process_results(results, args)
            
            # Generate output filename if not provided
            output_file = args.output
            if not output_file:
                input_path = Path(args.input)
                output_file = f"{input_path.stem}_processed.{args.format}"
            
            # Save processed results
            self._save_results(processed_results, output_file, args.format)
            
            self._print_success(f"Processing completed. Results saved to: {output_file}")
            return 0
            
        except Exception as e:
            self._print_error(f"Processing error: {e}")
            return 1
    
    def _handle_report(self, args) -> int:
        """Handle report command."""
        try:
            self._print_header("Web Scraper - Report Generation")
            
            if args.results:
                return self._generate_results_report(args)
            elif args.metrics:
                return self._generate_metrics_report(args)
            else:
                self._print_error("Must specify either --results or --metrics")
                return 1
                
        except Exception as e:
            self._print_error(f"Report generation error: {e}")
            return 1
    
    def _handle_config(self, args) -> int:
        """Handle config command."""
        try:
            if args.config_action == 'validate':
                return self._validate_config(args.config_file)
            elif args.config_action == 'generate':
                return self._generate_config(args)
            elif args.config_action == 'list':
                return self._list_sites(args)
            else:
                self._print_error("Invalid config action")
                return 1
                
        except Exception as e:
            self._print_error(f"Configuration error: {e}")
            return 1
    
    def _handle_test(self, args) -> int:
        """Handle test command."""
        try:
            self._print_header("Web Scraper - Testing Mode")
            
            # Import testing utilities
            from testing_utilities import ScraperTestSuite, create_basic_scraping_test
            
            # Create and run test suite
            test_suite = ScraperTestSuite("CLI Test Suite")
            
            if args.component in ['element_finder', 'all']:
                test_suite.add_test_case(create_basic_scraping_test())
            
            # Run tests
            results = test_suite.run_all()
            
            # Print results
            self._print_test_results(results)
            
            # Save results if output specified
            if args.output:
                test_suite.save_results(results, args.output)
                self._print_info(f"Test results saved to: {args.output}")
            
            return 0 if results['failed_tests'] == 0 else 1
            
        except Exception as e:
            self._print_error(f"Testing error: {e}")
            return 1
    
    def _load_search_terms_from_file(self, filepath: str) -> List[str]:
        """Load search terms from file."""
        if not Path(filepath).exists():
            raise FileNotFoundError(f"Search file not found: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            terms = [line.strip() for line in f if line.strip()]
        
        if not terms:
            raise ValueError("No search terms found in file")
        
        return terms
    
    def _process_results(self, results: Dict[str, List[Dict[str, Any]]], args) -> Dict[str, List[Dict[str, Any]]]:
        """Process results through pipeline."""
        processor = ResultProcessor()
        
        # Create processing pipeline
        processor.create_standard_pipeline(
            validate=getattr(args, 'validate', True),
            clean=getattr(args, 'clean', True),
            enrich=getattr(args, 'enrich', True),
            filter_invalid=getattr(args, 'filter_invalid', False),
            deduplicate=getattr(args, 'dedupe', True)
        )
        
        # Add custom filters
        if hasattr(args, 'has_price') and args.has_price:
            filter_processor = processor.processors[-1] if processor.processors else None
            if hasattr(filter_processor, 'add_filter'):
                filter_processor.add_filter(CommonFilters.has_price)
        
        if hasattr(args, 'exact_match_only') and args.exact_match_only:
            filter_processor = processor.processors[-1] if processor.processors else None
            if hasattr(filter_processor, 'add_filter'):
                filter_processor.add_filter(CommonFilters.exact_match_only)
        
        if hasattr(args, 'min_price') and hasattr(args, 'max_price') and (args.min_price or args.max_price):
            min_price = args.min_price or 0.0
            max_price = args.max_price or float('inf')
            filter_processor = processor.processors[-1] if processor.processors else None
            if hasattr(filter_processor, 'add_filter'):
                filter_processor.add_filter(CommonFilters.price_range(min_price, max_price))
        
        # Process results
        processed_results = processor.process_results(results)
        
        # Print processing summary
        summary = processor.get_processing_summary()
        self._print_processing_summary(summary)
        
        return processed_results
    
    def _save_results(self, results: Dict[str, List[Dict[str, Any]]], filepath: str, format_type: str) -> None:
        """Save results in specified format."""
        if format_type == 'json':
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        elif format_type == 'csv':
            self._save_as_csv(results, filepath)
        elif format_type == 'xlsx':
            self._save_as_xlsx(results, filepath)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
    
    def _save_as_csv(self, results: Dict[str, List[Dict[str, Any]]], filepath: str) -> None:
        """Save results as CSV."""
        import csv
        
        # Flatten all results
        all_items = []
        for search_term, items in results.items():
            for item in items:
                item_copy = item.copy()
                item_copy['search_term'] = search_term
                all_items.append(item_copy)
        
        if not all_items:
            return
        
        # Get all possible fieldnames
        fieldnames = set()
        for item in all_items:
            fieldnames.update(item.keys())
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=sorted(fieldnames))
            writer.writeheader()
            writer.writerows(all_items)
    
    def _save_as_xlsx(self, results: Dict[str, List[Dict[str, Any]]], filepath: str) -> None:
        """Save results as Excel file."""
        try:
            import pandas as pd
            
            # Create sheets for each search term
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                for search_term, items in results.items():
                    if items:
                        df = pd.DataFrame(items)
                        safe_sheet_name = FileUtils.get_safe_filename(search_term)[:31]  # Excel limit
                        df.to_excel(writer, sheet_name=safe_sheet_name, index=False)
                
        except ImportError:
            self._print_error("pandas and openpyxl required for Excel output. Using JSON instead.")
            json_filepath = filepath.replace('.xlsx', '.json')
            self._save_results(results, json_filepath, 'json')
    
    def _print_scraping_summary(self, results: Dict[str, List[Dict[str, Any]]], output_file: str) -> None:
        """Print scraping summary."""
        total_results = sum(len(items) for items in results.values())
        
        print(f"\n{CLIColors.colorize('SCRAPING SUMMARY', CLIColors.BOLD)}")
        print(f"{'=' * 50}")
        print(f"Search terms processed: {len(results)}")
        print(f"Total results found: {total_results}")
        print(f"Results saved to: {output_file}")
        
        print(f"\n{CLIColors.colorize('Results by search term:', CLIColors.BOLD)}")
        for search_term, items in results.items():
            count_color = CLIColors.GREEN if items else CLIColors.YELLOW
            count_text = CLIColors.colorize(str(len(items)), count_color)
            print(f"  {search_term}: {count_text} results")
    
    def _print_processing_summary(self, summary: Dict[str, Any]) -> None:
        """Print processing summary."""
        print(f"\n{CLIColors.colorize('PROCESSING SUMMARY', CLIColors.BOLD)}")
        print(f"{'=' * 50}")
        print(f"Operations: {summary['total_operations']}")
        print(f"Original items: {summary['total_original_items']}")
        print(f"Processed items: {summary['total_processed_items']}")
        
        rate_color = CLIColors.GREEN if summary['overall_processing_rate'] > 80 else CLIColors.YELLOW
        rate_text = CLIColors.colorize(f"{summary['overall_processing_rate']:.1f}%", rate_color)
        print(f"Processing rate: {rate_text}")
        
        print(f"Pipeline stages: {summary['processor_count']}")
        print(f"Processors: {', '.join(summary['processors'])}")
    
    def _print_performance_summary(self, scraper) -> None:
        """Print performance summary for monitored scrapers."""
        try:
            alerts = scraper.check_alerts()
            if alerts:
                print(f"\n{CLIColors.colorize('PERFORMANCE ALERTS', CLIColors.YELLOW)}")
                print(f"{'=' * 50}")
                for alert in alerts:
                    severity_color = CLIColors.RED if alert['severity'] == 'critical' else CLIColors.YELLOW
                    severity_text = CLIColors.colorize(alert['severity'].upper(), severity_color)
                    print(f"  [{severity_text}] {alert['message']}")
        except Exception:
            pass  # Silently ignore if performance features not available
    
    def _print_test_results(self, results: Dict[str, Any]) -> None:
        """Print test results."""
        print(f"\n{CLIColors.colorize('TEST RESULTS', CLIColors.BOLD)}")
        print(f"{'=' * 50}")
        
        total = results['total_tests']
        passed = results['passed_tests']
        failed = results['failed_tests']
        
        status_color = CLIColors.GREEN if failed == 0 else CLIColors.RED
        status_text = "PASSED" if failed == 0 else "FAILED"
        print(f"Status: {CLIColors.colorize(status_text, status_color)}")
        print(f"Total tests: {total}")
        print(f"Passed: {CLIColors.colorize(str(passed), CLIColors.GREEN)}")
        print(f"Failed: {CLIColors.colorize(str(failed), CLIColors.RED if failed > 0 else CLIColors.GREEN)}")
        print(f"Success rate: {results['success_rate']:.1f}%")
        print(f"Duration: {results['total_duration']:.2f}s")
        
        # Show failed tests
        if failed > 0:
            print(f"\n{CLIColors.colorize('FAILED TESTS:', CLIColors.RED)}")
            for test_result in results['test_results']:
                if not test_result['passed']:
                    print(f"  ✗ {test_result['name']}")
                    for error in test_result['errors']:
                        print(f"    {error}")
    
    def _generate_results_report(self, args) -> int:
        """Generate report from results file."""
        # Implementation for results reporting
        self._print_info("Results report generation not yet implemented")
        return 0
    
    def _generate_metrics_report(self, args) -> int:
        """Generate report from metrics file."""
        # Implementation for metrics reporting
        self._print_info("Metrics report generation not yet implemented")
        return 0
    
    def _validate_config(self, config_file: str) -> int:
        """Validate configuration file."""
        try:
            if not Path(config_file).exists():
                self._print_error(f"Configuration file not found: {config_file}")
                return 1
            
            # Try to load configuration
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Basic validation
            required_sections = ['sites']
            for section in required_sections:
                if section not in config_data:
                    self._print_error(f"Missing required section: {section}")
                    return 1
            
            # Validate each site
            sites = config_data.get('sites', {})
            for site_name in sites:
                try:
                    ConfigLoader.load_config_for_site(site_name, config_file)
                    self._print_success(f"✓ Site '{site_name}' configuration valid")
                except Exception as e:
                    self._print_error(f"✗ Site '{site_name}' configuration invalid: {e}")
                    return 1
            
            self._print_success(f"Configuration file '{config_file}' is valid")
            return 0
            
        except json.JSONDecodeError as e:
            self._print_error(f"Invalid JSON in configuration file: {e}")
            return 1
        except Exception as e:
            self._print_error(f"Configuration validation error: {e}")
            return 1
    
    def _generate_config(self, args) -> int:
        """Generate sample configuration."""
        # Implementation for config generation
        self._print_info("Configuration generation not yet implemented")
        return 0
    
    def _list_sites(self, args) -> int:
        """List available sites in configuration."""
        # Implementation for listing sites
        self._print_info("Site listing not yet implemented")
        return 0
    
    def _print_header(self, text: str) -> None:
        """Print header text."""
        print(f"\n{CLIColors.colorize(text, CLIColors.BOLD + CLIColors.CYAN)}")
        print(f"{CLIColors.colorize('=' * len(text), CLIColors.CYAN)}")
    
    def _print_info(self, text: str) -> None:
        """Print info message."""
        print(f"{CLIColors.colorize('INFO:', CLIColors.BLUE)} {text}")
    
    def _print_success(self, text: str) -> None:
        """Print success message."""
        print(f"{CLIColors.colorize('SUCCESS:', CLIColors.GREEN)} {text}")
    
    def _print_warning(self, text: str) -> None:
        """Print warning message."""
        print(f"{CLIColors.colorize('WARNING:', CLIColors.YELLOW)} {text}")
    
    def _print_error(self, text: str) -> None:
        """Print error message."""
        print(f"{CLIColors.colorize('ERROR:', CLIColors.RED)} {text}", file=sys.stderr)


def main():
    """Main entry point for CLI."""
    cli = ScraperCLI()
    exit_code = cli.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()