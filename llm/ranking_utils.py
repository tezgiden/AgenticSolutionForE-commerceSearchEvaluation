# ranking_utils.py

from typing import List, Dict, Any
from inventory_utils import InventoryParser


class InventoryAwareRanker:
    """
    Applies post-processing to reorder results within relevance tiers based on inventory levels.
    """

    def __init__(self, original_results: List[Dict[str, str]]):
        self.original_results = original_results

    def apply(self, evaluations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Reorder evaluations based on inventory levels within each relevance tier.

        Args:
            evaluations (List[Dict]): LLM evaluation output.

        Returns:
            List[Dict]: Reordered evaluations.
        """
        relevance_buckets = {"High": [], "Medium": [], "Low": []}

        for eval_item in evaluations:
            relevance = eval_item.get("relevance_tier", "Low")
            result_index = eval_item.get("result_index", 0)

            if result_index < len(self.original_results):
                quantity_str = self.original_results[result_index].get('quantity', 'N/A')
                qty, status = InventoryParser.parse_quantity(quantity_str)
                eval_item["parsed_quantity"] = qty
                eval_item["inventory_status_parsed"] = status
            else:
                eval_item["parsed_quantity"] = 0
                eval_item["inventory_status_parsed"] = "Unknown"

            relevance_buckets.get(relevance, relevance_buckets["Low"]).append(eval_item)

        # Sort within each bucket
        for tier in relevance_buckets:
            relevance_buckets[tier].sort(key=lambda x: x["parsed_quantity"], reverse=True)

        return relevance_buckets["High"] + relevance_buckets["Medium"] + relevance_buckets["Low"]
