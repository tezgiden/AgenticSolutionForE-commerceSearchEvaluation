"""Main orchestrator for the agentic search solution."""

import time
import logging
from datetime import datetime
from typing import List, Dict, Any

from config.config_loader import ConfigLoader, AppConfig
from inventory_analyzer import InventoryAnalyzer
from business_summary_generator import BusinessSummaryGenerator
from results_manager import ResultsManager
from search_session import SearchSession
from cli_handler import CLIHandler


logger = logging.getLogger(__name__)


class SearchOrchestrator:
    """Main orchestrator that coordinates the entire search and evaluation process."""
    
    def __init__(self, config: AppConfig):
        """Initialize the orchestrator with configuration.
        
        Args:
            config: Complete application configuration
        """
        self.config = config
        self.inventory_analyzer = InventoryAnalyzer(config.evaluation_config)
        self.summary_generator = BusinessSummaryGenerator(config)
        self.results_manager = ResultsManager(config)
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Configure logging based on deployment settings."""
        logging.basicConfig(
            level=getattr(logging, self.config.deployment_config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def run_search_campaign(self, scraped_results_file: str = None) -> None:
        """Run the complete search campaign for the configured site.
        
        Args:
            scraped_results_file: Optional path to pre-scraped results for testing
        """
        start_time = time.time()
        all_results = []
        
        try:
            self._log_campaign_start()
            
            search_tasks = self._get_all_search_tasks()
            search_session = SearchSession(self.config, scraped_results_file)
            
            for task_idx, task in enumerate(search_tasks):
                try:
                    result = self._process_single_search(
                        task, task_idx, len(search_tasks), search_session
                    )
                    all_results.append(result)
                    
                    if not scraped_results_file:  # Only delay for real scraping
                        time.sleep(self.config.deployment_config.delay_between_searches)
                        
                except Exception as e:
                    logger.error(f"Failed to process search task {task_idx + 1}: {e}")
                    all_results.append(self._create_error_result(task, str(e)))
            
            # Generate final outputs
            self._finalize_campaign(all_results, time.time() - start_time)
            
        except Exception as e:
            logger.error(f"Campaign failed: {e}")
            raise
        finally:
            search_session.cleanup()
    
    def _log_campaign_start(self) -> None:
        """Log campaign initialization details."""
        logger.info(f"Starting search campaign for {self.config.site_config.site_name}")
        logger.info(f"Target URL: {self.config.site_config.target_url}")
        logger.info(f"Model: {self.config.llm_config.default_model}")
        logger.info(f"Inventory ranking: {'Enabled' if self.config.evaluation_config.enable_inventory_ranking else 'Disabled'}")
    
    def _get_all_search_tasks(self) -> List[Dict[str, Any]]:
        """Get all search tasks including regular and inventory test cases."""
        tasks = (
            self.config.site_config.search_tasks + 
            self.config.site_config.inventory_test_cases
        )
        logger.info(f"Total queries to process: {len(tasks)}")
        return tasks
    
    def _process_single_search(
        self, 
        task: Dict[str, Any], 
        task_idx: int, 
        total_tasks: int,
        search_session: SearchSession
    ) -> Dict[str, Any]:
        """Process a single search task.
        
        Args:
            task: Search task configuration
            task_idx: Current task index
            total_tasks: Total number of tasks
            search_session: Search session manager
            
        Returns:
            Complete search result dictionary
        """
        query = task.get("query")
        if not query:
            logger.warning(f"Skipping task {task_idx + 1}: No query specified")
            return self._create_error_result(task, "No query specified")
        
        logger.info(f"Processing Query {task_idx + 1}/{total_tasks}: '{query}'")
        start_time = time.time()
        
        try:
            # Execute search and evaluation
            search_result = search_session.execute_search(task)
            
            # Analyze inventory impact if successful
            if search_result['status'] == 'success':
                search_result = self._enhance_with_analysis(search_result)
            
            # Add metadata
            search_result.update({
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'processing_time_seconds': round(time.time() - start_time, 2)
            })
            
            logger.info(f"Query '{query}' processed successfully in {search_result['processing_time_seconds']}s")
            return search_result
            
        except Exception as e:
            logger.error(f"Error processing query '{query}': {e}")
            return self._create_error_result(task, str(e))
    
    def _enhance_with_analysis(self, search_result: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance search result with inventory analysis and business summary.
        
        Args:
            search_result: Basic search result
            
        Returns:
            Enhanced search result with analysis
        """
        # Add inventory analysis
        if self.config.evaluation_config.enable_detailed_analysis:
            inventory_analysis = self.inventory_analyzer.analyze_inventory_impact(
                search_result['evaluation_details'], 
                search_result['scraped_results']
            )
            search_result['inventory_analysis'] = inventory_analysis
        
        # Generate business summary
        executive_summary = self.summary_generator.generate_summary(
            search_result['query'],
            search_result['evaluation_details'],
            search_result['scraped_results'],
            search_result.get('inventory_analysis')
        )
        search_result['executive_summary'] = executive_summary
        
        return search_result
    
    def _create_error_result(self, task: Dict[str, Any], error_message: str) -> Dict[str, Any]:
        """Create a standardized error result.
        
        Args:
            task: The task that failed
            error_message: Description of the error
            
        Returns:
            Standardized error result dictionary
        """
        return {
            'query': task.get('query', 'Unknown'),
            'search_type': task.get('search_type', 'unknown'),
            'status': 'failed',
            'error': error_message,
            'scraped_results': [],
            'evaluation_details': {},
            'inventory_analysis': None,
            'executive_summary': None,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def _finalize_campaign(self, all_results: List[Dict[str, Any]], total_time: float) -> None:
        """Finalize the campaign by generating summaries and saving results.
        
        Args:
            all_results: List of all search results
            total_time: Total campaign execution time
        """
        # Generate overall summary
        overall_summary = self.summary_generator.generate_overall_summary(all_results)
        
        # Save all results
        output_paths = self.results_manager.save_campaign_results(
            all_results, overall_summary, total_time
        )
        
        # Log completion
        successful_queries = sum(1 for r in all_results if r['status'] == 'success')
        failed_queries = len(all_results) - successful_queries
        
        logger.info(f"Campaign completed in {total_time/60:.2f} minutes")
        logger.info(f"Successful queries: {successful_queries}")
        logger.info(f"Failed queries: {failed_queries}")
        logger.info(f"Results saved to: {output_paths['main']}")
        
        if output_paths.get('detailed'):
            logger.info(f"Detailed analysis saved to: {output_paths['detailed']}")


def main():
    """Main entry point."""
    cli_handler = CLIHandler()
    
    try:
        # Parse command line arguments and validate
        args = cli_handler.parse_arguments()
        
        # Handle special commands (list sites, validate config)
        if cli_handler.handle_special_commands(args):
            return
        
        # Load and validate configuration
        config = cli_handler.load_and_validate_config(args)
        
        # Create and run orchestrator
        orchestrator = SearchOrchestrator(config)
        
        # Determine if using pre-scraped results (for testing)
        scraped_results_file = None  # Can be set for testing: "llm_debug/scraped_test.json"
        
        orchestrator.run_search_campaign(scraped_results_file)
        
        logger.info("Search campaign completed successfully")
        
    except Exception as e:
        logger.error(f"Application failed: {e}")
        exit(1)


if __name__ == "__main__":
    main()