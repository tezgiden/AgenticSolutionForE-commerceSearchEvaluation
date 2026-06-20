"""Search query classification service."""

import re
from models.data_models import SearchType


class SearchTypeClassifier:
    """Classifies search queries by type."""
    
    @staticmethod
    def classify(query: str) -> SearchType:
        """
        Determines the type of search query.
        
        Args:
            query: The search term/phrase
            
        Returns:
            SearchType indicating the query type
        """
        # Check if query contains multiple words
        normalized_query = re.sub(r'\s+', ' ', query).strip()
        words = normalized_query.split()
        
        if len(words) > 1:
            return SearchType.MULTIPLE_TERMS
        
        # Check if it's likely a part number
        if re.search(r'[0-9\-/]', query):
            return SearchType.PART_NUMBER
        
        # Default to english_word for single-word text queries
        return SearchType.ENGLISH_WORD

