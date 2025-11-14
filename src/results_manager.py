"""Results management and output generation module."""

import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from config.config_models import AppConfig


logger = logging.getLogger(__name__)


class ResultsManager:
    """Manages saving and organizing search campaign results."""
    
    def __init__(self, config: AppConfig):
        """Initialize the results manager.
        
        Args:
            config: Complete application configuration
        """
        self.config = config
        self.output_dir = "analysis_result"
        self._ensure_output_directory()
    
    def save_campaign_results(
        self,
        all_results: List[Dict[str, Any]],
        overall_summary: Dict[str, Any],
        total_time: float
    ) -> Dict[str, str]:
        """Save complete campaign results to files.
        
        Args:
            all_results: List of all search results
            overall_summary: Overall campaign summary
            total_time: Total execution time in seconds
            
        Returns:
            Dictionary with paths to saved files
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_paths = {}
        
        try:
            # Save main results
            main_output = self._create_main_output(all_results, overall_summary, total_time)
            main_file_path = self._get_output_file_path(
                self.config.site_config.output_config.output_file, 
                timestamp
            )
            
            self._save_json_file(main_output, main_file_path)
            output_paths['main'] = main_file_path
            logger.info(f"Main results saved to: {main_file_path}")
            
            # Save detailed analysis if enabled
            if self.config.evaluation_config.enable_detailed_analysis:
                detailed_analysis = self._extract_detailed_analysis(all_results)
                if detailed_analysis:
                    detailed_file_path = self._get_output_file_path(
                        self.config.site_config.output_config.detailed_output_file,
                        timestamp
                    )
                    
                    detailed_output = self._create_detailed_output(detailed_analysis)
                    self._save_json_file(detailed_output, detailed_file_path)
                    output_paths['detailed'] = detailed_file_path
                    logger.info(f"Detailed analysis saved to: {detailed_file_path}")
            
            return output_paths
            
        except Exception as e:
            logger.error(f"Error saving campaign results: {e}")
            raise
    
    def save_debug_results(self, results: List[Dict[str, Any]], debug_suffix: str = "debug") -> str:
        """Save results for debugging purposes.
        
        Args:
            results: Results to save
            debug_suffix: Suffix for the debug file
            
        Returns:
            Path to the saved debug file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_file = f"debug_results_{debug_suffix}_{timestamp}.json"
        debug_path = os.path.join(self.output_dir, debug_file)
        
        debug_output = {
            "debug_results": results,
            "generation_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "site_name": self.config.site_config.site_name
        }
        
        self._save_json_file(debug_output, debug_path)
        logger.info(f"Debug results saved to: {debug_path}")
        return debug_path
    
    def _ensure_output_directory(self) -> None:
        """Ensure the output directory exists."""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.debug(f"Created output directory: {self.output_dir}")
    
    def _get_output_file_path(self, base_filename: str, timestamp: str) -> str:
        """Generate timestamped output file path.
        
        Args:
            base_filename: Base filename from configuration
            timestamp: Timestamp string
            
        Returns:
            Full path to output file
        """
        # Remove .json extension if present, add timestamp, then add .json back
        name_without_ext = base_filename.replace('.json', '')
        timestamped_filename = f"{name_without_ext}_{timestamp}.json"
        return os.path.join(self.output_dir, timestamped_filename)
    
    def _create_main_output(
        self,
        all_results: List[Dict[str, Any]],
        overall_summary: Dict[str, Any],
        total_time: float
    ) -> Dict[str, Any]:
        """Create the main output structure.
        
        Args:
            all_results: All search results
            overall_summary: Overall campaign summary
            total_time: Total execution time
            
        Returns:
            Main output structure
        """
        return {
            "search_results": all_results,
            "overall_summary": overall_summary,
            "campaign_metadata": self._create_campaign_metadata(all_results, total_time),
            "configuration": self._create_configuration_summary()
        }
    
    def _create_detailed_output(self, detailed_analysis: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create the detailed analysis output structure.
        
        Args:
            detailed_analysis: Detailed analysis data
            
        Returns:
            Detailed output structure
        """
        return {
            "detailed_analysis": detailed_analysis,
            "site_name": self.config.site_config.site_name,
            "generation_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "analysis_metadata": {
                "total_queries_analyzed": len(detailed_analysis),
                "inventory_analysis_enabled": self.config.evaluation_config.enable_inventory_ranking,
                "model_used": self.config.llm_config.default_model
            }
        }
    
    def _create_campaign_metadata(
        self,
        all_results: List[Dict[str, Any]],
        total_time: float
    ) -> Dict[str, Any]:
        """Create campaign execution metadata.
        
        Args:
            all_results: All search results
            total_time: Total execution time
            
        Returns:
            Campaign metadata dictionary
        """
        successful_count = sum(1 for r in all_results if r.get('status') == 'success')
        failed_count = len(all_results) - successful_count
        
        return {
            "execution_summary": {
                "total_runtime_minutes": round(total_time / 60, 2),
                "total_queries_processed": len(all_results),
                "successful_queries": successful_count,
                "failed_queries": failed_count,
                "success_rate_percentage": round(successful_count / len(all_results) * 100, 1) if all_results else 0
            },
            "generation_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "environment": self.config.deployment_config.environment
        }
    
    def _create_configuration_summary(self) -> Dict[str, Any]:
        """Create a summary of the configuration used.
        
        Returns:
            Configuration summary dictionary
        """
        return {
            "site_configuration": {
                "site_name": self.config.site_config.site_name,
                "site_url": self.config.site_config.target_url,
                "max_results_per_query": self.config.site_config.scraping_config.max_results_per_query
            },
            "evaluation_configuration": {
                "inventory_ranking_enabled": self.config.evaluation_config.enable_inventory_ranking,
                "detailed_analysis_enabled": self.config.evaluation_config.enable_detailed_analysis,
                "inventory_weight_factor": self.config.evaluation_config.inventory_weight_factor,
                "low_stock_threshold": self.config.evaluation_config.low_stock_threshold
            },
            "llm_configuration": {
                "model_used": self.config.llm_config.default_model,
                "api_endpoint": self.config.llm_config.ollama_api_endpoint,
                "timeout": self.config.llm_config.timeout
            },
            "deployment_configuration": {
                "environment": self.config.deployment_config.environment,
                "delay_between_searches": self.config.deployment_config.delay_between_searches
            }
        }
    
    def _extract_detailed_analysis(self, all_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract detailed analysis data from results.
        
        Args:
            all_results: All search results
            
        Returns:
            List of detailed analysis data
        """
        detailed_analysis = []
        
        for result in all_results:
            if result.get('status') != 'success':
                continue
            
            analysis_item = {
                "query": result.get('query'),
                "search_type": result.get('search_type'),
                "inventory_analysis": result.get('inventory_analysis'),
                "executive_summary": result.get('executive_summary'),
                "evaluation_metadata": {
                    "total_results_evaluated": len(result.get('evaluation', [])),
                    "processing_time_seconds": result.get('processing_time_seconds'),
                    "timestamp": result.get('timestamp')
                }
            }
            
            # Add evaluation details if available
            if 'evaluation_details' in result:
                eval_details = result['evaluation_details']
                analysis_item['evaluation_metadata'].update({
                    "model_used": eval_details.get("model_used"),
                    "inventory_aware_ranking_applied": eval_details.get("inventory_aware_ranking_applied", False),
                    "ranking_summary": eval_details.get("ranking_summary", "")
                })
            
            detailed_analysis.append(analysis_item)
        
        return detailed_analysis
    
    def _save_json_file(self, data: Dict[str, Any], file_path: str) -> None:
        """Save data to a JSON file.
        
        Args:
            data: Data to save
            file_path: Path to save the file
            
        Raises:
            IOError: If file cannot be saved
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            raise IOError(f"Failed to save file {file_path}: {e}")


class ResultsValidator:
    """Validates and ensures integrity of results data."""
    
    @staticmethod
    def validate_search_result(result: Dict[str, Any]) -> bool:
        """Validate a single search result structure.
        
        Args:
            result: Search result to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['query', 'status', 'timestamp']
        
        for field in required_fields:
            if field not in result:
                logger.warning(f"Missing required field '{field}' in search result")
                return False
        
        # Validate status-specific fields
        if result['status'] == 'success':
            success_fields = ['scraped_results', 'evaluation']
            for field in success_fields:
                if field not in result:
                    logger.warning(f"Missing field '{field}' in successful search result")
                    return False
        
        return True
    
    @staticmethod
    def validate_overall_summary(summary: Dict[str, Any]) -> bool:
        """Validate overall summary structure.
        
        Args:
            summary: Summary to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['site_name', 'total_queries', 'successful_queries', 'failed_queries']
        
        for field in required_fields:
            if field not in summary:
                logger.warning(f"Missing required field '{field}' in overall summary")
                return False
        
        return True


class ResultsExporter:
    """Handles exporting results to different formats."""
    
    def __init__(self, results_manager: ResultsManager):
        """Initialize with a results manager.
        
        Args:
            results_manager: ResultsManager instance
        """
        self.results_manager = results_manager
    
    def export_to_csv(self, results: List[Dict[str, Any]], output_file: str) -> str:
        """Export results to CSV format.
        
        Args:
            results: Results to export
            output_file: Output file name
            
        Returns:
            Path to exported file
        """
        # This would implement CSV export logic
        # For now, just log the intention
        logger.info(f"CSV export requested to {output_file} (not implemented)")
        return output_file
    
    def export_summary_only(
        self,
        all_results: List[Dict[str, Any]],
        output_file: str
    ) -> str:
        """Export only summary information without full details.
        
        Args:
            all_results: All results
            output_file: Output file name
            
        Returns:
            Path to exported file
        """
        summary_data = []
        
        for result in all_results:
            summary_item = {
                'query': result.get('query'),
                'status': result.get('status'),
                'total_results': len(result.get('scraped_results', [])),
                'high_relevance_count': sum(
                    1 for eval_item in result.get('evaluation', [])
                    if eval_item.get('relevance') == 'High'
                ),
                'timestamp': result.get('timestamp')
            }
            summary_data.append(summary_item)
        
        output_path = os.path.join(self.results_manager.output_dir, output_file)
        self.results_manager._save_json_file({'summaries': summary_data}, output_path)
        
        return output_path