"""Inventory analysis and impact assessment module."""

import logging
from typing import Dict, List, Any, Optional

from config.config_models import EvaluationConfig


logger = logging.getLogger(__name__)


class InventoryAnalyzer:
    """Analyzes how inventory levels affect search result rankings."""
    
    def __init__(self, evaluation_config: EvaluationConfig):
        """Initialize the analyzer with evaluation configuration.
        
        Args:
            evaluation_config: Configuration for evaluation parameters
        """
        self.evaluation_config = evaluation_config
        self.low_stock_threshold = evaluation_config.low_stock_threshold
    
    def analyze_inventory_impact(
        self, 
        evaluation_results: Dict[str, Any], 
        original_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze how inventory affected the ranking compared to relevance-only ranking.
        
        Args:
            evaluation_results: Results from enhanced evaluation
            original_results: Original scraped results
            
        Returns:
            Dictionary with inventory impact analysis
        """
        analysis = self._initialize_analysis_structure()
        
        if evaluation_results.get('status') != 'success':
            logger.warning("Cannot analyze inventory impact: evaluation failed")
            return analysis
        
        evaluations = evaluation_results.get('evaluations', [])
        if not evaluations:
            logger.warning("Cannot analyze inventory impact: no evaluations found")
            return analysis
        
        # Analyze relevance grouping and inventory distribution
        relevance_groups = self._group_results_by_relevance(evaluations, original_results)
        analysis['inventory_summary'] = self._calculate_inventory_summary(evaluations)
        
        # Check for ranking changes within relevance tiers
        analysis['ranking_changes'] = self._detect_ranking_changes(relevance_groups)
        analysis['inventory_changes_detected'] = bool(analysis['ranking_changes'])
        
        # Generate actionable recommendations
        analysis['recommendations'] = self._generate_recommendations(analysis)
        
        logger.info(f"Inventory analysis completed. Changes detected: {analysis['inventory_changes_detected']}")
        return analysis
    
    def _initialize_analysis_structure(self) -> Dict[str, Any]:
        """Initialize the analysis result structure."""
        return {
            "inventory_changes_detected": False,
            "ranking_changes": [],
            "inventory_summary": {},
            "recommendations": []
        }
    
    def _group_results_by_relevance(
        self, 
        evaluations: List[Dict[str, Any]], 
        original_results: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group evaluation results by relevance level.
        
        Args:
            evaluations: List of evaluation results
            original_results: Original scraped results
            
        Returns:
            Dictionary grouping results by relevance level
        """
        relevance_groups = {"High": [], "Medium": [], "Low": []}
        
        for eval_item in evaluations:
            relevance = eval_item.get('relevance', 'Low')
            result_idx = eval_item.get('result_index', 0)
            
            if result_idx < len(original_results):
                original_result = original_results[result_idx]
                
                item_data = {
                    'index': result_idx,
                    'title': self._truncate_title(original_result.get('title', 'N/A')),
                    'part_number': original_result.get('part_number', 'N/A'),
                    'quantity': original_result.get('quantity', 'N/A'),
                    'relevance': relevance,
                    'evaluation': eval_item,
                    'parsed_quantity': eval_item.get('parsed_quantity', 0)
                }
                
                if relevance in relevance_groups:
                    relevance_groups[relevance].append(item_data)
                else:
                    logger.warning(f"Unknown relevance level: {relevance}")
        
        return relevance_groups
    
    def _truncate_title(self, title: str, max_length: int = 50) -> str:
        """Truncate title for display purposes."""
        if len(title) > max_length:
            return title[:max_length] + '...'
        return title
    
    def _calculate_inventory_summary(self, evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate inventory availability statistics.
        
        Args:
            evaluations: List of evaluation results
            
        Returns:
            Summary of inventory statistics
        """
        total_items = len(evaluations)
        if total_items == 0:
            return {
                'total_items': 0,
                'in_stock_items': 0,
                'out_of_stock_items': 0,
                'low_stock_items': 0,
                'stock_availability_ratio': 0
            }
        
        in_stock = 0
        out_of_stock = 0
        low_stock = 0
        
        for eval_item in evaluations:
            parsed_qty = eval_item.get('parsed_quantity', 0)
            
            if parsed_qty == 0:
                out_of_stock += 1
            elif parsed_qty < self.low_stock_threshold:
                low_stock += 1
            else:
                in_stock += 1
        
        return {
            'total_items': total_items,
            'in_stock_items': in_stock,
            'out_of_stock_items': out_of_stock,
            'low_stock_items': low_stock,
            'stock_availability_ratio': in_stock / total_items
        }
    
    def _detect_ranking_changes(
        self, 
        relevance_groups: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Detect ranking changes within relevance tiers.
        
        Args:
            relevance_groups: Results grouped by relevance level
            
        Returns:
            List of detected ranking changes
        """
        ranking_changes = []
        
        for relevance_level, items in relevance_groups.items():
            if len(items) <= 1:
                continue  # No reordering possible with 1 or fewer items
            
            # Sort by original index (scraped order) vs current order
            original_order = sorted(items, key=lambda x: x['index'])
            current_order = items  # Already in evaluation order
            
            if self._orders_differ(original_order, current_order):
                change_info = {
                    'relevance_tier': relevance_level,
                    'original_order': [item['part_number'] for item in original_order],
                    'new_order': [item['part_number'] for item in current_order],
                    'reasoning': f"Inventory-based reordering within {relevance_level} relevance tier",
                    'items_reordered': len(items)
                }
                ranking_changes.append(change_info)
                logger.debug(f"Ranking change detected in {relevance_level} tier: {len(items)} items reordered")
        
        return ranking_changes
    
    def _orders_differ(
        self, 
        original_order: List[Dict[str, Any]], 
        current_order: List[Dict[str, Any]]
    ) -> bool:
        """Check if two orderings are different."""
        if len(original_order) != len(current_order):
            return True
        
        for orig, curr in zip(original_order, current_order):
            if orig['index'] != curr['index']:
                return True
        
        return False
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on inventory analysis.
        
        Args:
            analysis: Current analysis results
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        inventory_summary = analysis['inventory_summary']
        
        # Out of stock recommendations
        out_of_stock = inventory_summary.get('out_of_stock_items', 0)
        if out_of_stock > 0:
            recommendations.append(
                f"Consider highlighting {out_of_stock} out-of-stock items differently "
                "in search results to improve customer experience"
            )
        
        # Low stock recommendations
        low_stock = inventory_summary.get('low_stock_items', 0)
        if low_stock > 0:
            recommendations.append(
                f"Monitor {low_stock} low-stock items for potential restocking needs"
            )
        
        # Ranking effectiveness recommendations
        if analysis['inventory_changes_detected']:
            recommendations.append(
                "Inventory-based ranking is actively improving result relevance"
            )
        else:
            recommendations.append(
                "No inventory-based ranking changes needed for this query"
            )
        
        # Stock ratio recommendations
        stock_ratio = inventory_summary.get('stock_availability_ratio', 0)
        if stock_ratio < 0.5:
            recommendations.append(
                "Low inventory availability may be impacting sales conversion"
            )
        elif stock_ratio > 0.8:
            recommendations.append(
                "Good inventory availability - consider promoting these search results"
            )
        
        return recommendations


class InventoryMetrics:
    """Helper class for calculating inventory-related metrics."""
    
    @staticmethod
    def calculate_availability_score(quantity: int, threshold: int = 5) -> float:
        """Calculate availability score based on quantity.
        
        Args:
            quantity: Available quantity
            threshold: Low stock threshold
            
        Returns:
            Availability score between 0 and 1
        """
        if quantity == 0:
            return 0.0
        elif quantity < threshold:
            return 0.5
        else:
            return 1.0
    
    @staticmethod
    def categorize_stock_level(quantity: int, low_threshold: int = 5) -> str:
        """Categorize stock level based on quantity.
        
        Args:
            quantity: Available quantity
            low_threshold: Threshold for low stock
            
        Returns:
            Stock level category
        """
        if quantity == 0:
            return "out_of_stock"
        elif quantity < low_threshold:
            return "low_stock"
        else:
            return "in_stock"