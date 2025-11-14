"""Business summary and insights generation module."""

import logging
from typing import Dict, List, Any, Optional, Tuple

from config.config_models import AppConfig


logger = logging.getLogger(__name__)


class BusinessSummaryGenerator:
    """Generates business-focused summaries and recommendations."""
    
    def __init__(self, config: AppConfig):
        """Initialize the generator with configuration.
        
        Args:
            config: Complete application configuration
        """
        self.config = config
        self.site_name = config.site_config.site_name
        self.low_stock_threshold = config.evaluation_config.low_stock_threshold
    
    def generate_summary(
        self,
        query: str,
        evaluation: Dict[str, Any],
        scraped_results: List[Dict[str, Any]],
        inventory_analysis: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate a comprehensive business summary for a search query.
        
        Args:
            query: The search query
            evaluation: Evaluation results from LLM
            scraped_results: Original scraped results
            inventory_analysis: Optional inventory impact analysis
            
        Returns:
            Dictionary containing business summary and recommendations
        """
        summary = self._initialize_summary_structure()
        
        if evaluation.get('status') != 'success' or not scraped_results:
            return self._generate_failure_summary(query, summary)
        
        evaluations = evaluation.get('evaluations', [])
        if not evaluations:
            return self._generate_empty_results_summary(query, summary)
        
        # Analyze search performance
        performance_metrics = self._analyze_search_performance(evaluations)
        inventory_metrics = self._analyze_inventory_performance(evaluations)
        
        # Generate core summary components
        summary['relevancy_assessment'] = self._generate_relevancy_assessment(
            query, performance_metrics, inventory_metrics, len(evaluations)
        )
        
        summary['product_movement_recommendations'] = self._generate_product_recommendations(
            performance_metrics, inventory_metrics, inventory_analysis
        )
        
        summary['key_insights'] = self._generate_key_insights(
            evaluations, scraped_results, performance_metrics, inventory_metrics
        )
        
        summary['action_items'] = self._generate_action_items(
            performance_metrics, inventory_metrics
        )
        
        logger.info(f"Generated business summary for query: '{query}'")
        return summary
    
    def generate_overall_summary(self, all_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate an overall summary across all search queries.
        
        Args:
            all_results: List of all search result evaluations
            
        Returns:
            Dictionary containing overall performance summary
        """
        summary = self._initialize_overall_summary()
        
        successful_results = [r for r in all_results if r.get('status') == 'success']
        summary.update({
            'total_queries': len(all_results),
            'successful_queries': len(successful_results),
            'failed_queries': len(all_results) - len(successful_results)
        })
        
        if not successful_results:
            summary['critical_issues'].append(
                f"All searches failed on {self.site_name} - major system issue"
            )
            return summary
        
        # Aggregate performance metrics
        aggregated_metrics = self._aggregate_performance_metrics(successful_results)
        summary.update(aggregated_metrics)
        
        # Generate top-level recommendations and issues
        summary['top_recommendations'] = self._generate_overall_recommendations(aggregated_metrics)
        summary['critical_issues'] = self._identify_critical_issues(aggregated_metrics)
        
        logger.info(f"Generated overall summary for {len(all_results)} queries")
        return summary
    
    def _initialize_summary_structure(self) -> Dict[str, Any]:
        """Initialize the summary structure."""
        return {
            'relevancy_assessment': '',
            'product_movement_recommendations': [],
            'key_insights': [],
            'action_items': []
        }
    
    def _initialize_overall_summary(self) -> Dict[str, Any]:
        """Initialize the overall summary structure."""
        return {
            'site_name': self.site_name,
            'site_url': self.config.site_config.target_url,
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'average_relevancy_score': 0,
            'inventory_performance': {},
            'top_recommendations': [],
            'critical_issues': [],
            'configuration_summary': {
                'inventory_ranking_enabled': self.config.evaluation_config.enable_inventory_ranking,
                'model_used': self.config.llm_config.default_model,
                'max_results_per_query': self.config.site_config.scraping_config.max_results_per_query
            }
        }
    
    def _generate_failure_summary(self, query: str, summary: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary for failed searches."""
        summary['relevancy_assessment'] = (
            f"Search for '{query}' failed to return evaluable results. "
            f"Consider investigating search functionality or product catalog coverage for {self.site_name}."
        )
        summary['action_items'].append("Investigate why search failed to return results")
        return summary
    
    def _generate_empty_results_summary(self, query: str, summary: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary for searches with no results."""
        summary['relevancy_assessment'] = (
            f"Search for '{query}' on {self.site_name} returned no evaluable results."
        )
        summary['action_items'].append("Review search algorithm and product catalog coverage")
        return summary
    
    def _analyze_search_performance(self, evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze search performance metrics."""
        relevancy_counts = {'High': 0, 'Medium': 0, 'Low': 0}
        
        for eval_item in evaluations:
            relevance = eval_item.get('relevance', 'Low')
            if relevance in relevancy_counts:
                relevancy_counts[relevance] += 1
        
        total_results = len(evaluations)
        high_relevance_pct = (relevancy_counts['High'] / total_results * 100) if total_results > 0 else 0
        
        # Determine relevancy quality level
        if high_relevance_pct >= 60:
            quality_level = 'excellent'
        elif high_relevance_pct >= 40:
            quality_level = 'good'
        elif high_relevance_pct >= 20:
            quality_level = 'moderate'
        else:
            quality_level = 'poor'
        
        return {
            'relevancy_counts': relevancy_counts,
            'total_results': total_results,
            'high_relevance_percentage': high_relevance_pct,
            'quality_level': quality_level
        }
    
    def _analyze_inventory_performance(self, evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze inventory performance metrics."""
        inventory_stats = {'in_stock': 0, 'out_of_stock': 0, 'low_stock': 0}
        
        for eval_item in evaluations:
            parsed_qty = eval_item.get('parsed_quantity', 0)
            
            if parsed_qty == 0:
                inventory_stats['out_of_stock'] += 1
            elif parsed_qty < self.low_stock_threshold:
                inventory_stats['low_stock'] += 1
            else:
                inventory_stats['in_stock'] += 1
        
        total_results = len(evaluations)
        in_stock_pct = (inventory_stats['in_stock'] / total_results * 100) if total_results > 0 else 0
        
        # Determine inventory availability level
        if in_stock_pct >= 70:
            availability_level = 'strong'
        elif in_stock_pct >= 40:
            availability_level = 'moderate'
        else:
            availability_level = 'concerning'
        
        return {
            'inventory_stats': inventory_stats,
            'in_stock_percentage': in_stock_pct,
            'availability_level': availability_level
        }
    
    def _generate_relevancy_assessment(
        self,
        query: str,
        performance_metrics: Dict[str, Any],
        inventory_metrics: Dict[str, Any],
        total_results: int
    ) -> str:
        """Generate the main relevancy assessment text."""
        relevancy_counts = performance_metrics['relevancy_counts']
        quality_level = performance_metrics['quality_level']
        availability_level = inventory_metrics['availability_level']
        inventory_stats = inventory_metrics['inventory_stats']
        
        return (
            f"Search for '{query}' on {self.site_name} returned {total_results} results with {quality_level} relevancy "
            f"({relevancy_counts['High']} high, {relevancy_counts['Medium']} medium, {relevancy_counts['Low']} low relevance). "
            f"Inventory availability is {availability_level} "
            f"with {inventory_stats['in_stock']} items in stock, {inventory_stats['out_of_stock']} out of stock."
        )
    
    def _generate_product_recommendations(
        self,
        performance_metrics: Dict[str, Any],
        inventory_metrics: Dict[str, Any],
        inventory_analysis: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Generate product movement recommendations."""
        recommendations = []
        inventory_stats = inventory_metrics['inventory_stats']
        relevancy_counts = performance_metrics['relevancy_counts']
        
        # Inventory recommendations
        if inventory_stats['out_of_stock'] > 0:
            recommendations.append(
                f"Restock {inventory_stats['out_of_stock']} out-of-stock items or consider "
                "removing them from search results to improve customer experience"
            )
        
        # Relevancy recommendations
        if relevancy_counts['Low'] > relevancy_counts['High']:
            recommendations.append(
                f"Improve search algorithm or product tagging on {self.site_name} "
                "to surface more relevant results higher in rankings"
            )
        
        # Inventory-aware ranking recommendations
        if inventory_analysis and inventory_analysis.get('inventory_changes_detected'):
            recommendations.append(
                "Continue using inventory-aware ranking as it's successfully prioritizing available products"
            )
        
        return recommendations
    
    def _generate_key_insights(
        self,
        evaluations: List[Dict[str, Any]],
        scraped_results: List[Dict[str, Any]],
        performance_metrics: Dict[str, Any],
        inventory_metrics: Dict[str, Any]
    ) -> List[str]:
        """Generate key business insights."""
        insights = []
        
        # Identify top performers and problem products
        top_products, problem_products = self._identify_key_products(evaluations, scraped_results)
        
        if top_products:
            insights.append(f"Top performing products: {', '.join(top_products[:2])}")
        
        if problem_products:
            insights.append(f"Products needing attention: {', '.join(problem_products[:2])}")
        
        # Performance insights
        high_relevance_pct = performance_metrics['high_relevance_percentage']
        if high_relevance_pct < 30:
            insights.append(
                f"Search relevancy on {self.site_name} is below optimal - "
                "consider improving product metadata or search algorithm"
            )
        
        # Inventory insights
        in_stock_pct = inventory_metrics['in_stock_percentage']
        if in_stock_pct < 50:
            insights.append("Low inventory availability may be impacting sales conversion")
        
        return insights
    
    def _generate_action_items(
        self,
        performance_metrics: Dict[str, Any],
        inventory_metrics: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable items based on performance."""
        action_items = []
        
        # Critical relevancy issues
        if performance_metrics['relevancy_counts']['High'] == 0:
            action_items.append(
                f"URGENT: No highly relevant results found on {self.site_name} - "
                "review product catalog and search functionality"
            )
        
        # Critical inventory issues
        inventory_stats = inventory_metrics['inventory_stats']
        if inventory_stats['out_of_stock'] > inventory_stats['in_stock']:
            action_items.append(
                "PRIORITY: More items out of stock than in stock - review inventory management"
            )
        
        # Optimization opportunities
        high_relevance_pct = performance_metrics['high_relevance_percentage']
        in_stock_pct = inventory_metrics['in_stock_percentage']
        
        if high_relevance_pct > 70 and in_stock_pct > 70:
            action_items.append(
                "OPTIMIZE: Strong performance - consider promoting these search results in marketing"
            )
        
        return action_items
    
    def _identify_key_products(
        self,
        evaluations: List[Dict[str, Any]],
        scraped_results: List[Dict[str, Any]]
    ) -> Tuple[List[str], List[str]]:
        """Identify top performing and problematic products."""
        top_products = []
        problem_products = []
        
        # Analyze top 3 results
        for eval_item in evaluations[:3]:
            idx = eval_item.get('result_index', 0)
            if idx < len(scraped_results):
                result = scraped_results[idx]
                relevance = eval_item.get('relevance')
                qty = eval_item.get('parsed_quantity', 0)
                part_number = result.get('part_number', f'Product {idx}')
                
                if relevance == "High" and qty > 0:
                    top_products.append(part_number)
                elif relevance == "Low" or qty == 0:
                    problem_products.append(part_number)
        
        return top_products, problem_products
    
    def _aggregate_performance_metrics(self, successful_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate performance metrics across all successful results."""
        total_relevancy_score = 0
        total_products = 0
        total_in_stock = 0
        total_out_of_stock = 0
        
        for result in successful_results:
            evaluations = result.get('evaluation', [])
            for eval_item in evaluations:
                total_products += 1
                
                # Convert relevance to numeric score
                relevance = eval_item.get('relevance', 'Low')
                score_map = {'High': 3, 'Medium': 2, 'Low': 1}
                total_relevancy_score += score_map.get(relevance, 1)
                
                # Count inventory
                if eval_item.get('parsed_quantity', 0) > 0:
                    total_in_stock += 1
                else:
                    total_out_of_stock += 1
        
        if total_products == 0:
            return {
                'average_relevancy_score': 0,
                'inventory_performance': {
                    'in_stock_percentage': 0,
                    'out_of_stock_percentage': 0,
                    'total_products_analyzed': 0
                }
            }
        
        return {
            'average_relevancy_score': round(total_relevancy_score / total_products, 2),
            'inventory_performance': {
                'in_stock_percentage': round(total_in_stock / total_products * 100, 1),
                'out_of_stock_percentage': round(total_out_of_stock / total_products * 100, 1),
                'total_products_analyzed': total_products
            }
        }
    
    def _generate_overall_recommendations(self, aggregated_metrics: Dict[str, Any]) -> List[str]:
        """Generate top-level recommendations for overall performance."""
        recommendations = []
        
        avg_relevancy = aggregated_metrics.get('average_relevancy_score', 0)
        if avg_relevancy < 2.0:
            recommendations.append(
                f"Improve search relevancy algorithms on {self.site_name} - average score below target"
            )
        
        inventory_perf = aggregated_metrics.get('inventory_performance', {})
        in_stock_pct = inventory_perf.get('in_stock_percentage', 0)
        
        if in_stock_pct < 60:
            recommendations.append(
                f"Address inventory issues on {self.site_name} - only {in_stock_pct}% of products in stock"
            )
        
        return recommendations
    
    def _identify_critical_issues(self, aggregated_metrics: Dict[str, Any]) -> List[str]:
        """Identify critical issues requiring immediate attention."""
        issues = []
        
        inventory_perf = aggregated_metrics.get('inventory_performance', {})
        in_stock_pct = inventory_perf.get('in_stock_percentage', 0)
        
        if in_stock_pct < 30:
            issues.append(
                f"Critical inventory shortage across most products on {self.site_name}"
            )
        
        return issues