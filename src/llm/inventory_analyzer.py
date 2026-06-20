"""Inventory analysis and management for search results."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple, Any, Optional


class InventoryStatus(Enum):
    """Enumeration of inventory status levels."""
    AVAILABLE = "Available"
    LOW_STOCK = "Low Stock"
    OUT_OF_STOCK = "Out of Stock"
    UNKNOWN = "Unknown"


@dataclass
class InventoryInfo:
    """Information about product inventory."""
    quantity: int
    status: InventoryStatus
    raw_value: str
    
    @property
    def is_available(self) -> bool:
        """Check if product is available for purchase."""
        return self.status in (InventoryStatus.AVAILABLE, InventoryStatus.LOW_STOCK)
    
    @property
    def priority_score(self) -> int:
        """Get priority score for ranking (higher is better)."""
        scores = {
            InventoryStatus.AVAILABLE: 100,
            InventoryStatus.LOW_STOCK: 50,
            InventoryStatus.OUT_OF_STOCK: 0,
            InventoryStatus.UNKNOWN: 25
        }
        return scores[self.status] + min(self.quantity, 50)  # Cap quantity bonus at 50


class InventoryParser:
    """Parses inventory information from various string formats."""
    
    def __init__(self, low_stock_threshold: int = 10, available_threshold: int = 10):
        self.low_stock_threshold = low_stock_threshold
        self.available_threshold = available_threshold
        self._numeric_pattern = re.compile(r'(\d+)')
        
    def parse(self, quantity_str: str) -> InventoryInfo:
        """
        Parse inventory quantity string and return structured information.
        
        Args:
            quantity_str: The quantity string from scraped data
            
        Returns:
            InventoryInfo object with parsed data
        """
        if not quantity_str or quantity_str.upper() in ('N/A', 'NULL', 'NONE', ''):
            return InventoryInfo(0, InventoryStatus.UNKNOWN, quantity_str or 'N/A')
        
        # Extract numeric value
        numeric_match = self._numeric_pattern.search(str(quantity_str))
        if numeric_match:
            qty = int(numeric_match.group(1))
            status = self._determine_status_from_quantity(qty)
            return InventoryInfo(qty, status, quantity_str)
        
        # Handle text-based indicators
        quantity_lower = str(quantity_str).lower()
        
        if any(term in quantity_lower for term in ['out of stock', 'unavailable', 'out-of-stock']):
            return InventoryInfo(0, InventoryStatus.OUT_OF_STOCK, quantity_str)
        elif any(term in quantity_lower for term in ['low stock', 'limited', 'few left']):
            return InventoryInfo(1, InventoryStatus.LOW_STOCK, quantity_str)
        elif any(term in quantity_lower for term in ['in stock', 'available', 'plenty']):
            return InventoryInfo(999, InventoryStatus.AVAILABLE, quantity_str)
        
        return InventoryInfo(0, InventoryStatus.UNKNOWN, quantity_str)
    
    def _determine_status_from_quantity(self, qty: int) -> InventoryStatus:
        """Determine inventory status based on quantity."""
        if qty == 0:
            return InventoryStatus.OUT_OF_STOCK
        elif qty <= self.low_stock_threshold:
            return InventoryStatus.LOW_STOCK
        else:
            return InventoryStatus.AVAILABLE


class InventoryAnalyzer:
    """Analyzes inventory impact on search results."""
    
    def __init__(self, parser: InventoryParser = None):
        self.parser = parser or InventoryParser()
    
    def analyze_results(self, results: List[Dict[str, str]]) -> List[InventoryInfo]:
        """Analyze inventory for a list of search results."""
        inventory_data = []
        for result in results:
            quantity_str = result.get('quantity', 'N/A')
            inventory_info = self.parser.parse(quantity_str)
            inventory_data.append(inventory_info)
        return inventory_data
    
    def apply_inventory_ranking(self, evaluations: List[Dict[str, Any]], 
                              inventory_data: List[InventoryInfo]) -> List[Dict[str, Any]]:
        """
        Apply inventory-aware ranking to evaluations.
        
        Args:
            evaluations: List of evaluation results
            inventory_data: Corresponding inventory information
            
        Returns:
            Reordered evaluations with inventory considerations
        """
        # Enhance evaluations with inventory data
        enhanced_evaluations = []
        for i, evaluation in enumerate(evaluations):
            if i < len(inventory_data):
                inventory = inventory_data[i]
                evaluation = evaluation.copy()  # Don't modify original
                evaluation['inventory_info'] = inventory
                evaluation['inventory_priority_score'] = inventory.priority_score
            enhanced_evaluations.append(evaluation)
        
        # Group by relevance tier and sort by inventory within each tier
        relevance_groups = self._group_by_relevance(enhanced_evaluations)
        
        # Sort each group by inventory priority
        for relevance_level in relevance_groups:
            relevance_groups[relevance_level].sort(
                key=lambda x: x.get('inventory_priority_score', 0),
                reverse=True
            )
        
        # Combine back in order: High -> Medium -> Low
        return (relevance_groups.get("High", []) + 
                relevance_groups.get("Medium", []) + 
                relevance_groups.get("Low", []))
    
    def _group_by_relevance(self, evaluations: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group evaluations by relevance level."""
        groups = {"High": [], "Medium": [], "Low": []}
        
        for evaluation in evaluations:
            relevance = evaluation.get("relevance_tier", "Low")
            if relevance in groups:
                groups[relevance].append(evaluation)
            else:
                groups["Low"].append(evaluation)  # Default to Low for unknown relevance
        
        return groups
    
    def generate_inventory_summary(self, inventory_data: List[InventoryInfo]) -> Dict[str, Any]:
        """Generate summary statistics about inventory."""
        if not inventory_data:
            return {"total": 0, "distribution": {}}
        
        total = len(inventory_data)
        distribution = {}
        total_quantity = 0
        
        for status in InventoryStatus:
            count = sum(1 for inv in inventory_data if inv.status == status)
            distribution[status.value] = {
                "count": count,
                "percentage": round((count / total) * 100, 1)
            }
        
        total_quantity = sum(inv.quantity for inv in inventory_data)
        
        return {
            "total_results": total,
            "total_quantity": total_quantity,
            "distribution": distribution,
            "average_quantity": round(total_quantity / total, 1) if total > 0 else 0
        }
