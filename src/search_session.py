"""Search session management and execution module."""

import json
import logging
from typing import Dict, List, Any, Optional
from selenium.webdriver.remote.webdriver import WebDriver

from config.config_models import AppConfig
from scraper.web_scraper import WebScraper
from llm.evaluation_engine import evaluate_search_results_with_inventory
from llm.search_classifier import SearchClassifierFactory

# Import the scraper setup function - this might need to be adjusted based on actual module structure
from scraper.scraper_facade import setup_driver_with_config


logger = logging.getLogger(__name__)


class SearchSession:
    """Manages individual search sessions and WebDriver lifecycle."""
    
    def __init__(self, config: AppConfig, scraped_results_file: Optional[str] = None):
        """Initialize search session.
        
        Args:
            config: Complete application configuration
            scraped_results_file: Optional path to pre-scraped results for testing
        """
        self.config = config
        self.scraped_results_file = scraped_results_file
        self.driver: Optional[WebDriver] = None
        self.web_scraper: Optional[WebScraper] = None
        self._pre_scraped_data: Optional[List[Dict[str, Any]]] = None

         # Initialize search classifier
        self.search_classifier = SearchClassifierFactory.create_classifier("regex")
   
        
        # Initialize session based on mode
        if scraped_results_file:
            self._load_pre_scraped_data()
        else:
            self._initialize_web_driver()
    
    def execute_search(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a complete search task including scraping and evaluation.
        
        Args:
            task: Search task configuration
            
        Returns:
            Complete search result with evaluation
        """
        query = task.get("query")
        if not query:
            raise ValueError("Search task must contain a 'query' field")
        
        logger.info(f"Executing search for: '{query}'")
        
        try:
            # Step 1: Get search results (scrape or load from file)
            scraped_results = self._get_search_results(query)
            
            if not scraped_results:
                return self._create_failed_result(query, "No search results found", task)
            
            logger.info(f"Retrieved {len(scraped_results)} search results")
            self._log_scraped_results(scraped_results)
            
            # Step 2: Evaluate results with LLM
            evaluation_result = self._evaluate_search_results(query, scraped_results, task)
            
            # Step 3: Create complete result structure
            return self._create_success_result(query, scraped_results, evaluation_result, task)
            
        except Exception as e:
            logger.error(f"Error executing search for '{query}': {e}")
            return self._create_failed_result(query, str(e), task)
    
    def cleanup(self) -> None:
        """Clean up resources used by the search session."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.warning(f"Error closing WebDriver: {e}")
            finally:
                self.driver = None
                self.web_scraper = None
    
    def _load_pre_scraped_data(self) -> None:
        """Load pre-scraped data from file for testing."""
        try:
            with open(self.scraped_results_file, "r", encoding="utf-8") as f:
                self._pre_scraped_data = json.load(f)
            logger.info(f"Loaded pre-scraped data from {self.scraped_results_file}")
        except Exception as e:
            raise RuntimeError(f"Failed to load pre-scraped data: {e}")
    
    def _initialize_web_driver(self) -> None:
        """Initialize WebDriver and web scraper for live scraping."""
        try:
            self.driver = setup_driver_with_config(self.config.chrome_config)
            if not self.driver:
                raise RuntimeError("Failed to initialize WebDriver")
            
            self.web_scraper = WebScraper(self.driver)
            logger.info("WebDriver and scraper initialized successfully")
            
        except Exception as e:
            raise RuntimeError(f"Failed to initialize web driver: {e}")
    
    def _get_search_results(self, query: str) -> List[Dict[str, Any]]:
        """Get search results either by scraping or loading from file.
        
        Args:
            query: Search query
            
        Returns:
            List of search results
        """
        if self._pre_scraped_data:
            return self._get_pre_scraped_results(query)
        else:
            return self._scrape_live_results(query)
    
    def _get_pre_scraped_results(self, query: str) -> List[Dict[str, Any]]:
        """Get results from pre-scraped data file.
        
        Args:
            query: Search query to find
            
        Returns:
            List of scraped results for the query
        """
        for entry in self._pre_scraped_data:
            if entry.get("query") == query:
                results = entry.get("results", [])
                logger.info(f"Found {len(results)} pre-scraped results for query '{query}'")
                return results
        
        logger.warning(f"No pre-scraped results found for query '{query}'")
        return []
    
    def _scrape_live_results(self, query: str) -> List[Dict[str, Any]]:
        """Scrape live results from the website.
        
        Args:
            query: Search query
            
        Returns:
            List of scraped results
        """
        if not self.web_scraper:
            raise RuntimeError("Web scraper not initialized")
        
        debug_mode = self.config.deployment_config.environment == "development"
        
        scraped_results = self.web_scraper.scrape_site(
            search_term=query,
            site_config=self.config.site_config,
            debug_mode=debug_mode
        )
        
        logger.info(f"Scraped {len(scraped_results)} results for query '{query}'")
        return scraped_results
    
    def _evaluate_search_results(
        self,
        query: str,
        scraped_results: List[Dict[str, Any]],
        task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate search results using LLM.
        
        Args:
            query: Search query
            scraped_results: Results to evaluate
            task: Search task configuration
            
        Returns:
            Evaluation results from LLM
        """
        logger.info("Starting LLM evaluation of search results")
        
        # Determine search type
        search_type = task.get("search_type") or self.search_classifier.classify(query).value
        
        # Configure evaluation parameters
        evaluation_result = evaluate_search_results_with_inventory(
            query=query,
            results=scraped_results,
            search_type=search_type,
            model=self.config.llm_config.default_model,
            apply_post_ranking=self.config.evaluation_config.apply_post_ranking,
            api_endpoint=self.config.llm_config.ollama_api_endpoint,
            timeout=self.config.llm_config.timeout,
            max_retries=self.config.llm_config.max_retries
        )
        
        status = evaluation_result.get('status', 'unknown')
        logger.info(f"LLM evaluation completed with status: {status}")
        
        if status == 'success':
            evaluations = evaluation_result.get('evaluations', [])
            logger.info(f"Successfully evaluated {len(evaluations)} results")
            self._log_evaluation_results(evaluations, scraped_results)
        
        return evaluation_result
    
    def _log_scraped_results(self, scraped_results: List[Dict[str, Any]]) -> None:
        """Log summary of scraped results.
        
        Args:
            scraped_results: Results to log
        """
        logger.info("Scraped results summary:")
        for i, result in enumerate(scraped_results):
            title = result.get('title', 'N/A')
            title_short = title[:40] + '...' if len(title) > 40 else title
            quantity = result.get('quantity', 'N/A')
            part_number = result.get('part_number', 'N/A')
            logger.info(f"  {i+1}: {title_short} | Qty: {quantity} | Part: {part_number}")
    
    def _log_evaluation_results(
        self,
        evaluations: List[Dict[str, Any]],
        scraped_results: List[Dict[str, Any]]
    ) -> None:
        """Log summary of evaluation results.
        
        Args:
            evaluations: Evaluation results
            scraped_results: Original scraped results
        """
        logger.info("Final ranked results:")
        for rank, eval_item in enumerate(evaluations, 1):
            idx = eval_item.get('result_index', 0)
            if idx < len(scraped_results):
                result = scraped_results[idx]
                title = result.get('title', 'N/A')
                title_short = title[:40] + '...' if len(title) > 40 else title
                relevance = eval_item.get('relevance', 'N/A')
                quantity = result.get('quantity', 'N/A')
                logger.info(f"  {rank}: {title_short} | Relevance: {relevance} | Qty: {quantity}")
    
    def _create_success_result(
        self,
        query: str,
        scraped_results: List[Dict[str, Any]],
        evaluation_result: Dict[str, Any],
        task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a successful search result structure.
        
        Args:
            query: Search query
            scraped_results: Scraped results
            evaluation_result: LLM evaluation results
            task: Original search task
            
        Returns:
            Complete success result structure
        """
        return {
            'query': query,
            'search_type': task.get('search_type') or self.search_classifier.classify(query).value,
            'status': 'success',
            'scraped_results': scraped_results,
            'evaluation': evaluation_result.get('evaluations', []),
            'evaluation_details': evaluation_result,
            'result_count': len(scraped_results),
            'evaluation_count': len(evaluation_result.get('evaluations', []))
        }
    
    def _create_failed_result(
        self,
        query: str,
        error_message: str,
        task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a failed search result structure.
        
        Args:
            query: Search query
            error_message: Error description
            task: Original search task
            
        Returns:
            Complete failure result structure
        """
        return {
            'query': query,
            'search_type': task.get('search_type', 'unknown'),
            'status': 'failed',
            'error': error_message,
            'scraped_results': [],
            'evaluation': [],
            'evaluation_details': {},
            'result_count': 0,
            'evaluation_count': 0
        }


class SearchSessionManager:
    """Manages multiple search sessions and their lifecycle."""
    
    def __init__(self, config: AppConfig):
        """Initialize session manager.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.active_sessions: List[SearchSession] = []
    
    def create_session(self, scraped_results_file: Optional[str] = None) -> SearchSession:
        """Create a new search session.
        
        Args:
            scraped_results_file: Optional pre-scraped results file
            
        Returns:
            New search session
        """
        session = SearchSession(self.config, scraped_results_file)
        self.active_sessions.append(session)
        return session
    
    def cleanup_all_sessions(self) -> None:
        """Clean up all active sessions."""
        for session in self.active_sessions:
            try:
                session.cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up session: {e}")
        
        self.active_sessions.clear()
        logger.info("All search sessions cleaned up")
    
    def get_session_count(self) -> int:
        """Get the number of active sessions.
        
        Returns:
            Number of active sessions
        """
        return len(self.active_sessions)