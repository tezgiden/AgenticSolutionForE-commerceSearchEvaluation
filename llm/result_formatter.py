# result_formatter.py

from typing import List, Dict


class ResultFormatter:
    """
    Formats product results for prompt input to LLMs.
    """

    @staticmethod
    def format_results(results: List[Dict[str, str]]) -> str:
        """
        Convert product result list into a text format for prompt inclusion.

        Args:
            results (List[Dict[str, str]]): List of product dictionaries.

        Returns:
            str: Formatted text block of results.
        """
        lines = []
        for idx, result in enumerate(results):
            lines.append(f"Result {idx}:")
            lines.append(f"Title: {result.get('title', 'N/A')}")
            lines.append(f"Part Number: {result.get('part_number', 'N/A')}")
            lines.append(f"Vendor Part Number: {result.get('vendor_part_number', 'N/A')}")
            lines.append(f"Manufacturer Part Number: {result.get('manufacturer_part_number', 'N/A')}")
            lines.append(f"Description: {result.get('description', 'N/A')}")
            lines.append(f"Price: {result.get('price', 'N/A')}")
            lines.append(f"exact_match: {result.get('exact_match', 'N/A')}")
            lines.append(f"partial_match: {result.get('partial_match', 'N/A')}")
            lines.append(f"cross_ref_match: {result.get('cross_ref_match', 'N/A')}")
            lines.append(f"INVENTORY/QUANTITY: {result.get('quantity', 'N/A')}")
            lines.append(f"URL: {result.get('url', 'N/A')}")
            lines.append("---")
        return "\n".join(lines)
