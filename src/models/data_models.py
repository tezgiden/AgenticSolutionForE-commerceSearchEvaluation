"""Data models for the e-commerce search evaluation system."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class SearchType(Enum):
    """Enumeration of search types."""
    ENGLISH_WORD = "english_word"
    PART_NUMBER = "part_number"
    MULTIPLE_TERMS = "multiple_terms"


class RelevanceTier(Enum):
    """Enumeration of relevance tiers."""
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class InventoryStatus(Enum):
    """Enumeration of inventory statuses."""
    AVAILABLE = "Available"
    LOW_STOCK = "Low Stock"
    OUT_OF_STOCK = "Out of Stock"
    UNKNOWN = "Unknown"


class MatchType(Enum):
    """Enumeration of match types."""
    EXACT = "Exact"
    PARTIAL = "Partial"
    CROSS_REFERENCE = "Cross-reference"
    CATEGORY = "Category"
    NONE = "None"


@dataclass
class ProductData:
    """Data model for scraped product information."""
    title: str = "N/A"
    part_number: str = "N/A"
    vendor_part_number: str = "N/A"
    manufacturer_part_number: str = "N/A"
    description: str = "N/A"
    price: str = "N/A"
    quantity: str = "N/A"
    url: str = "N/A"
    partial_match: bool = False
    cross_ref_match: bool = False
    exact_match: bool = False

    def get_parsed_quantity(self) -> int:
        """Parse quantity string to integer."""
        import re
        if not self.quantity or self.quantity == 'N/A':
            return 0
        numeric_match = re.search(r'(\d+)', str(self.quantity))
        return int(numeric_match.group(1)) if numeric_match else 0


@dataclass
class EvaluationResult:
    """Data model for product evaluation results."""
    result_index: int
    title: str
    relevance_tier: RelevanceTier
    relevance_score: int
    match_type: MatchType
    inventory_status: InventoryStatus
    inventory_quantity: str
    part_number: str
    vendor_part_number: str
    justification: str
    inventory_impact: str
    business_impact: str
    recommended_action: str
    parsed_quantity: int = 0
    inventory_status_parsed: str = "Unknown"


@dataclass
class SearchAnalysis:
    """Data model for search analysis results."""
    query: str
    total_results: int
    category_matches_found: int = 0
    exact_matches_found: int = 0
    partial_matches_found: int = 0
    inventory_considerations_applied: bool = True


@dataclass
class ExecutiveSummary:
    """Data model for executive summary."""
    relevancy_assessment: str
    inventory_impact: str
    customer_satisfaction_risk: str
    key_insights: str
    recommended_actions: Dict[str, str]


@dataclass
class EvaluationResponse:
    """Data model for complete evaluation response."""
    query: str
    search_type: SearchType
    model_used: str
    evaluations: List[EvaluationResult]
    ranking_summary: str
    inventory_aware_ranking_applied: bool
    status: str
    executive_summary: Optional[ExecutiveSummary] = None
    error: Optional[str] = None
    quality_score: Optional[int] = None
    conversion_likelihood: Optional[str] = None