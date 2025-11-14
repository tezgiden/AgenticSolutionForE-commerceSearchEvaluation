"""Result formatting utilities for LLM evaluation system."""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import json


class ResultFormatter(ABC):
    """Abstract base class for result formatters."""
    
    @abstractmethod
    def format(self, results: List[Dict[str, str]]) -> str:
        """Format results for LLM consumption."""
        pass


class StandardResultFormatter(ResultFormatter):
    """Standard formatter for search results with inventory emphasis."""
    
    def __init__(self, include_inventory: bool = True, include_metadata: bool = True):
        self.include_inventory = include_inventory
        self.include_metadata = include_metadata
    
    def format(self, results: List[Dict[str, str]]) -> str:
        """
        Formats the scraped results into a text format suitable for LLM prompts.
        Includes inventory/quantity information prominently.
        
        Args:
            results: List of dictionaries containing scraped product data
            
        Returns:
            Formatted string of results with inventory emphasis
        """
        if not results:
            return "No results to evaluate."
        
        formatted_text = ""
        for i, result in enumerate(results):
            formatted_text += f"Result {i}:\n"
            formatted_text += f"Title: {result.get('title', 'N/A')}\n"
            formatted_text += f"Part Number: {result.get('part_number', 'N/A')}\n"
            formatted_text += f"Vendor Part Number: {result.get('vendor_part_number', 'N/A')}\n"
            
            if self.include_metadata:
                formatted_text += f"Manufacturer Part Number: {result.get('manufacturer_part_number', 'N/A')}\n"
                formatted_text += f"Description: {result.get('description', 'N/A')}\n"
                formatted_text += f"Price: {result.get('price', 'N/A')}\n"
                formatted_text += f"exact_match: {result.get('exact_match', 'N/A')}\n"
                formatted_text += f"partial_match: {result.get('partial_match', 'N/A')}\n"
                formatted_text += f"cross_ref_match: {result.get('cross_ref_match', 'N/A')}\n"
            
            # Emphasize inventory information
            if self.include_inventory:
                quantity = result.get('quantity', 'N/A')
                formatted_text += f"INVENTORY/QUANTITY: {quantity}\n"
            
            if self.include_metadata:
                formatted_text += f"URL: {result.get('url', 'N/A')}\n"
            
            formatted_text += "---\n"
        
        return formatted_text


class JSONResultFormatter(ResultFormatter):
    """JSON formatter for structured result representation."""
    
    def __init__(self, pretty_print: bool = True):
        self.pretty_print = pretty_print
    
    def format(self, results: List[Dict[str, str]]) -> str:
        """Format results as JSON string."""
        if self.pretty_print:
            return json.dumps(results, indent=2, ensure_ascii=False)
        return json.dumps(results, ensure_ascii=False)


class CompactResultFormatter(ResultFormatter):
    """Compact formatter for minimal result representation."""
    
    def format(self, results: List[Dict[str, str]]) -> str:
        """Format results in compact format."""
        if not results:
            return "No results to evaluate."
        
        formatted_text = ""
        for i, result in enumerate(results):
            title = result.get('title', 'N/A')[:50]  # Truncate long titles
            part_num = result.get('part_number', 'N/A')
            quantity = result.get('quantity', 'N/A')
            formatted_text += f"[{i}] {title} | Part: {part_num} | Qty: {quantity}\n"
        
        return formatted_text


class CustomFieldResultFormatter(ResultFormatter):
    """Formatter that allows custom field selection and ordering."""
    
    def __init__(self, fields: List[str], separator: str = " | "):
        self.fields = fields
        self.separator = separator
    
    def format(self, results: List[Dict[str, str]]) -> str:
        """Format results with custom field selection."""
        if not results:
            return "No results to evaluate."
        
        formatted_text = ""
        for i, result in enumerate(results):
            values = [f"{field}: {result.get(field, 'N/A')}" for field in self.fields]
            formatted_text += f"Result {i}: {self.separator.join(values)}\n"
        
        return formatted_text


class ResultFormatterFactory:
    """Factory for creating result formatters."""
    
    @staticmethod
    def create_formatter(formatter_type: str = "standard", **kwargs) -> ResultFormatter:
        """Create a result formatter instance."""
        if formatter_type == "standard":
            return StandardResultFormatter(**kwargs)
        elif formatter_type == "json":
            return JSONResultFormatter(**kwargs)
        elif formatter_type == "compact":
            return CompactResultFormatter(**kwargs)
        elif formatter_type == "custom":
            return CustomFieldResultFormatter(**kwargs)
        else:
            raise ValueError(f"Unknown formatter type: {formatter_type}")


class ResultProcessor:
    """Processes and enhances search results before formatting."""
    
    def __init__(self, formatter: ResultFormatter = None):
        self.formatter = formatter or StandardResultFormatter()
    
    def process_and_format(self, results: List[Dict[str, str]], 
                          enhance_data: bool = True) -> str:
        """Process results and format them for LLM consumption."""
        if enhance_data:
            results = self._enhance_results(results)
        
        return self.formatter.format(results)
    
    def _enhance_results(self, results: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Enhance results with additional computed fields."""
        enhanced_results = []
        
        for result in results:
            enhanced_result = result.copy()
            
            # Add computed fields
            enhanced_result['has_part_number'] = bool(result.get('part_number') and 
                                                    result.get('part_number') != 'N/A')
            enhanced_result['has_inventory'] = bool(result.get('quantity') and 
                                                  result.get('quantity') != 'N/A')
            enhanced_result['price_available'] = bool(result.get('price') and 
                                                    result.get('price') != 'N/A')
            
            # Normalize quantity field
            quantity = result.get('quantity', 'N/A')
            if isinstance(quantity, str) and quantity.isdigit():
                enhanced_result['quantity_numeric'] = int(quantity)
            else:
                enhanced_result['quantity_numeric'] = 0
            
            enhanced_results.append(enhanced_result)
        
        return enhanced_results
