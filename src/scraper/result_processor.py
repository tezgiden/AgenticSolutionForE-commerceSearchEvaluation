"""Result processing pipeline for scraped data."""

import logging
import re
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

from utilities import TextUtils, ValidationUtils


logger = logging.getLogger(__name__)


class ProcessingStage(Enum):
    """Enumeration of processing stages."""
    VALIDATION = "validation"
    CLEANING = "cleaning"
    ENRICHMENT = "enrichment"
    FILTERING = "filtering"
    TRANSFORMATION = "transformation"
    AGGREGATION = "aggregation"


@dataclass
class ProcessingResult:
    """Result of a processing operation."""
    
    success: bool
    original_count: int
    processed_count: int
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]
    
    @property
    def processing_rate(self) -> float:
        """Get processing success rate."""
        if self.original_count == 0:
            return 100.0
        return (self.processed_count / self.original_count) * 100.0


class BaseProcessor(ABC):
    """Abstract base class for result processors."""
    
    def __init__(self, name: str, enabled: bool = True):
        """Initialize processor.
        
        Args:
            name: Processor name
            enabled: Whether processor is enabled
        """
        self.name = name
        self.enabled = enabled
        self.metrics = {
            'items_processed': 0,
            'items_filtered': 0,
            'errors_encountered': 0
        }
    
    @abstractmethod
    def process_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single item.
        
        Args:
            item: Item to process
            
        Returns:
            Processed item or None if filtered out
        """
        pass
    
    def process_batch(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a batch of items.
        
        Args:
            items: List of items to process
            
        Returns:
            List of processed items
        """
        if not self.enabled:
            return items
        
        processed_items = []
        
        for item in items:
            try:
                processed_item = self.process_item(item)
                if processed_item is not None:
                    processed_items.append(processed_item)
                    self.metrics['items_processed'] += 1
                else:
                    self.metrics['items_filtered'] += 1
                    
            except Exception as e:
                logger.error(f"Error in {self.name} processor: {e}")
                self.metrics['errors_encountered'] += 1
                # Optionally pass through unprocessed item
                processed_items.append(item)
        
        return processed_items
    
    def get_metrics(self) -> Dict[str, int]:
        """Get processor metrics."""
        return self.metrics.copy()
    
    def reset_metrics(self) -> None:
        """Reset processor metrics."""
        self.metrics = {
            'items_processed': 0,
            'items_filtered': 0,
            'errors_encountered': 0
        }


class ValidationProcessor(BaseProcessor):
    """Processor for validating scraped data."""
    
    def __init__(self, strict_mode: bool = False, required_fields: Optional[List[str]] = None):
        """Initialize validation processor.
        
        Args:
            strict_mode: Whether to use strict validation
            required_fields: List of required fields
        """
        super().__init__("ValidationProcessor")
        self.strict_mode = strict_mode
        self.required_fields = required_fields or ['title', 'url']
    
    def process_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate a single item."""
        issues = ValidationUtils.validate_scraping_result(item)
        
        # Check required fields
        missing_fields = []
        for field in self.required_fields:
            if not item.get(field) or item[field] == "N/A":
                missing_fields.append(field)
        
        if missing_fields:
            issues.extend([f"Missing required field: {field}" for field in missing_fields])
        
        # Add validation metadata
        item['_validation'] = {
            'issues': issues,
            'is_valid': len(issues) == 0,
            'validated_at': 'processing'
        }
        
        # In strict mode, filter out invalid items
        if self.strict_mode and issues:
            logger.debug(f"Filtered invalid item: {issues}")
            return None
        
        return item


class CleaningProcessor(BaseProcessor):
    """Processor for cleaning and normalizing data."""
    
    def __init__(self, clean_whitespace: bool = True, normalize_prices: bool = True):
        """Initialize cleaning processor.
        
        Args:
            clean_whitespace: Whether to clean whitespace
            normalize_prices: Whether to normalize price formats
        """
        super().__init__("CleaningProcessor")
        self.clean_whitespace = clean_whitespace
        self.normalize_prices = normalize_prices
    
    def process_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Clean a single item."""
        cleaned_item = item.copy()
        
        # Clean text fields
        if self.clean_whitespace:
            text_fields = ['title', 'description', 'part_number', 'vendor_part_number']
            for field in text_fields:
                if field in cleaned_item and isinstance(cleaned_item[field], str):
                    cleaned_item[field] = TextUtils.clean_whitespace(cleaned_item[field])
        
        # Normalize prices
        if self.normalize_prices and 'price' in cleaned_item:
            cleaned_item['price'] = self._normalize_price(cleaned_item['price'])
        
        # Clean URLs
        if 'url' in cleaned_item:
            cleaned_item['url'] = self._clean_url(cleaned_item['url'])
        
        # Normalize boolean fields
        boolean_fields = ['partial_match', 'cross_ref_match', 'exact_match']
        for field in boolean_fields:
            if field in cleaned_item:
                cleaned_item[field] = bool(cleaned_item[field])
        
        return cleaned_item
    
    def _normalize_price(self, price: str) -> str:
        """Normalize price format."""
        if not price or price == "N/A":
            return price
        
        # Extract numeric value
        price_value = TextUtils.extract_price(price)
        if price_value is not None:
            return f"${price_value:.2f}"
        
        return price
    
    def _clean_url(self, url: str) -> str:
        """Clean and validate URL."""
        if not url or url == "N/A":
            return url
        
        # Ensure URL has protocol
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        # Remove extra whitespace and fragments
        url = url.strip().split('#')[0]
        
        return url


class EnrichmentProcessor(BaseProcessor):
    """Processor for enriching data with additional information."""
    
    def __init__(self, add_metadata: bool = True, calculate_scores: bool = True):
        """Initialize enrichment processor.
        
        Args:
            add_metadata: Whether to add metadata
            calculate_scores: Whether to calculate relevance scores
        """
        super().__init__("EnrichmentProcessor")
        self.add_metadata = add_metadata
        self.calculate_scores = calculate_scores
    
    def process_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Enrich a single item."""
        enriched_item = item.copy()
        
        if self.add_metadata:
            enriched_item['_metadata'] = {
                'processed_at': 'enrichment_stage',
                'has_price': bool(item.get('price') and item['price'] != "N/A"),
                'has_quantity': bool(item.get('quantity') and item['quantity'] != "N/A"),
                'url_domain': self._extract_domain(item.get('url', '')),
                'title_length': len(item.get('title', '')),
            }
        
        if self.calculate_scores:
            enriched_item['_scores'] = {
                'completeness_score': self._calculate_completeness_score(item),
                'relevance_score': self._calculate_relevance_score(item),
                'quality_score': self._calculate_quality_score(item)
            }
        
        return enriched_item
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        if not url or url == "N/A":
            return ""
        
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except:
            return ""
    
    def _calculate_completeness_score(self, item: Dict[str, Any]) -> float:
        """Calculate completeness score based on available fields."""
        total_fields = ['title', 'url', 'part_number', 'price', 'quantity', 'description']
        filled_fields = sum(1 for field in total_fields 
                          if item.get(field) and item[field] != "N/A")
        return (filled_fields / len(total_fields)) * 100
    
    def _calculate_relevance_score(self, item: Dict[str, Any]) -> float:
        """Calculate relevance score based on match types."""
        score = 0.0
        
        if item.get('exact_match'):
            score += 50.0
        elif item.get('partial_match'):
            score += 30.0
        elif item.get('cross_ref_match'):
            score += 20.0
        else:
            score += 10.0  # Base score for any result
        
        # Bonus for having price and quantity
        if item.get('price') and item['price'] != "N/A":
            score += 10.0
        if item.get('quantity') and item['quantity'] != "N/A":
            score += 10.0
        
        return min(score, 100.0)
    
    def _calculate_quality_score(self, item: Dict[str, Any]) -> float:
        """Calculate quality score based on data quality indicators."""
        score = 100.0
        
        # Penalty for validation issues
        validation = item.get('_validation', {})
        if validation.get('issues'):
            score -= len(validation['issues']) * 10
        
        # Penalty for short titles
        title = item.get('title', '')
        if title and len(title) < 10:
            score -= 15
        
        # Penalty for invalid URLs
        url = item.get('url', '')
        if url and url != "N/A" and not ValidationUtils.is_valid_url(url):
            score -= 20
        
        return max(score, 0.0)


class FilterProcessor(BaseProcessor):
    """Processor for filtering items based on criteria."""
    
    def __init__(self, filters: Optional[List[Callable[[Dict[str, Any]], bool]]] = None):
        """Initialize filter processor.
        
        Args:
            filters: List of filter functions that return True to keep item
        """
        super().__init__("FilterProcessor")
        self.filters = filters or []
    
    def add_filter(self, filter_func: Callable[[Dict[str, Any]], bool]) -> None:
        """Add a filter function.
        
        Args:
            filter_func: Function that returns True to keep item
        """
        self.filters.append(filter_func)
    
    def process_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Filter a single item."""
        for filter_func in self.filters:
            try:
                if not filter_func(item):
                    return None
            except Exception as e:
                logger.warning(f"Filter function error: {e}")
                # Continue with other filters
        
        return item


class AggregationProcessor(BaseProcessor):
    """Processor for aggregating and deduplicating results."""
    
    def __init__(self, dedupe_by: Optional[List[str]] = None, group_by: Optional[str] = None):
        """Initialize aggregation processor.
        
        Args:
            dedupe_by: Fields to use for deduplication
            group_by: Field to group results by
        """
        super().__init__("AggregationProcessor")
        self.dedupe_by = dedupe_by or ['url', 'part_number']
        self.group_by = group_by
        self.seen_items = set()
        self.grouped_items = defaultdict(list)
    
    def process_batch(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process batch with deduplication and grouping."""
        if not self.enabled:
            return items
        
        # Deduplication
        deduplicated_items = []
        for item in items:
            item_key = self._generate_key(item)
            if item_key not in self.seen_items:
                self.seen_items.add(item_key)
                deduplicated_items.append(item)
                self.metrics['items_processed'] += 1
            else:
                self.metrics['items_filtered'] += 1
        
        # Grouping
        if self.group_by:
            for item in deduplicated_items:
                group_key = item.get(self.group_by, 'unknown')
                self.grouped_items[group_key].append(item)
            
            # Return items with group information
            for item in deduplicated_items:
                group_key = item.get(self.group_by, 'unknown')
                item['_group'] = {
                    'key': group_key,
                    'size': len(self.grouped_items[group_key])
                }
        
        return deduplicated_items
    
    def _generate_key(self, item: Dict[str, Any]) -> str:
        """Generate deduplication key for item."""
        key_parts = []
        for field in self.dedupe_by:
            value = item.get(field, '')
            if value and value != "N/A":
                key_parts.append(f"{field}:{value}")
        
        return "|".join(key_parts) or str(hash(str(item)))
    
    def get_grouped_results(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get grouped results."""
        return dict(self.grouped_items)


class ResultProcessor:
    """Main result processing pipeline."""
    
    def __init__(self):
        """Initialize result processor."""
        self.processors: List[BaseProcessor] = []
        self.processing_history: List[ProcessingResult] = []
    
    def add_processor(self, processor: BaseProcessor) -> None:
        """Add a processor to the pipeline.
        
        Args:
            processor: Processor to add
        """
        self.processors.append(processor)
        logger.info(f"Added processor: {processor.name}")
    
    def create_standard_pipeline(
        self,
        validate: bool = True,
        clean: bool = True,
        enrich: bool = True,
        filter_invalid: bool = False,
        deduplicate: bool = True
    ) -> None:
        """Create a standard processing pipeline.
        
        Args:
            validate: Whether to add validation processor
            clean: Whether to add cleaning processor
            enrich: Whether to add enrichment processor
            filter_invalid: Whether to filter invalid items
            deduplicate: Whether to add deduplication
        """
        if validate:
            self.add_processor(ValidationProcessor(strict_mode=filter_invalid))
        
        if clean:
            self.add_processor(CleaningProcessor())
        
        if enrich:
            self.add_processor(EnrichmentProcessor())
        
        if deduplicate:
            self.add_processor(AggregationProcessor())
    
    def process_results(
        self,
        results: Dict[str, List[Dict[str, Any]]],
        search_term_context: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Process scraping results through the pipeline.
        
        Args:
            results: Dictionary of search results
            search_term_context: Optional search term for context
            
        Returns:
            Processed results dictionary
        """
        processed_results = {}
        
        for search_term, items in results.items():
            logger.info(f"Processing {len(items)} items for search term: {search_term}")
            
            original_count = len(items)
            current_items = items.copy()
            
            # Process through pipeline
            for processor in self.processors:
                if processor.enabled:
                    processor.reset_metrics()
                    current_items = processor.process_batch(current_items)
                    metrics = processor.get_metrics()
                    
                    logger.debug(
                        f"{processor.name}: processed={metrics['items_processed']}, "
                        f"filtered={metrics['items_filtered']}, "
                        f"errors={metrics['errors_encountered']}"
                    )
            
            processed_count = len(current_items)
            processed_results[search_term] = current_items
            
            # Record processing result
            processing_result = ProcessingResult(
                success=True,
                original_count=original_count,
                processed_count=processed_count,
                errors=[],
                warnings=[],
                metadata={
                    'search_term': search_term,
                    'pipeline_stages': len(self.processors),
                    'processing_rate': (processed_count / original_count * 100) if original_count > 0 else 100.0
                }
            )
            self.processing_history.append(processing_result)
            
            logger.info(
                f"Processed {search_term}: {original_count} → {processed_count} items "
                f"({processing_result.processing_rate:.1f}%)"
            )
        
        return processed_results
    
    def get_processing_summary(self) -> Dict[str, Any]:
        """Get summary of processing operations.
        
        Returns:
            Processing summary dictionary
        """
        if not self.processing_history:
            return {"message": "No processing history available"}
        
        total_original = sum(r.original_count for r in self.processing_history)
        total_processed = sum(r.processed_count for r in self.processing_history)
        
        return {
            "total_operations": len(self.processing_history),
            "total_original_items": total_original,
            "total_processed_items": total_processed,
            "overall_processing_rate": (total_processed / total_original * 100) if total_original > 0 else 100.0,
            "processor_count": len(self.processors),
            "processors": [p.name for p in self.processors],
            "individual_results": [
                {
                    "search_term": r.metadata.get("search_term"),
                    "original_count": r.original_count,
                    "processed_count": r.processed_count,
                    "processing_rate": r.processing_rate
                }
                for r in self.processing_history
            ]
        }


# Predefined filter functions
class CommonFilters:
    """Common filter functions for use with FilterProcessor."""
    
    @staticmethod
    def has_price(item: Dict[str, Any]) -> bool:
        """Filter items that have a price."""
        return bool(item.get('price') and item['price'] != "N/A")
    
    @staticmethod
    def has_quantity(item: Dict[str, Any]) -> bool:
        """Filter items that have quantity information."""
        return bool(item.get('quantity') and item['quantity'] != "N/A")
    
    @staticmethod
    def exact_match_only(item: Dict[str, Any]) -> bool:
        """Filter to only exact matches."""
        return bool(item.get('exact_match'))
    
    @staticmethod
    def min_title_length(min_length: int = 10):
        """Create filter for minimum title length."""
        def filter_func(item: Dict[str, Any]) -> bool:
            title = item.get('title', '')
            return len(title) >= min_length
        return filter_func
    
    @staticmethod
    def price_range(min_price: float = 0.0, max_price: float = float('inf')):
        """Create filter for price range."""
        def filter_func(item: Dict[str, Any]) -> bool:
            price_str = item.get('price', '')
            if not price_str or price_str == "N/A":
                return False
            
            price_value = TextUtils.extract_price(price_str)
            if price_value is None:
                return False
            
            return min_price <= price_value <= max_price
        return filter_func