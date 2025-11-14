# inventory_utils.py

import re
from typing import Tuple


class InventoryParser:
    """
    Provides utilities for parsing and interpreting inventory quantity data.
    """

    @staticmethod
    def parse_quantity(quantity_str: str) -> Tuple[int, str]:
        """
        Parse inventory quantity string and return numeric value and status.

        Args:
            quantity_str (str): Raw quantity string from scraped data.

        Returns:
            Tuple[int, str]: (parsed numeric quantity, status string)
        """
        if not quantity_str or quantity_str.strip().upper() == 'N/A':
            return 0, "Unknown"

        try:
            numeric_match = re.search(r'(\d+)', str(quantity_str))
            if numeric_match:
                qty = int(numeric_match.group(1))
                if qty == 0:
                    return 0, "Out of Stock"
                elif qty < 5:
                    return qty, "Low Stock"
                else:
                    return qty, "Available"
        except Exception:
            pass

        lower_val = quantity_str.lower()
        if any(term in lower_val for term in ['out of stock', 'unavailable', '0', 'n/a']):
            return 0, "Out of Stock"
        if any(term in lower_val for term in ['low stock', 'limited']):
            return 1, "Low Stock"
        if any(term in lower_val for term in ['in stock', 'available']):
            return 999, "Available"

        return 0, "Unknown"
