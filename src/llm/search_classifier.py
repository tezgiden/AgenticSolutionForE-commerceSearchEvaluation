"""Search type classification for e-commerce queries."""

import re
from abc import ABC, abstractmethod
from enum import Enum
from typing import Protocol


class SearchType(Enum):
    """Enumeration of search types."""
    ENGLISH_WORD = "english_word"
    PART_NUMBER = "part_number" 
    MULTIPLE_TERMS = "multiple_terms"


class SearchClassifier(Protocol):
    """Protocol for search type classification."""
    
    def classify(self, query: str) -> SearchType:
        """Classify the search query type."""
        ...


class RegexSearchClassifier:
    """Regular expression based search type classifier."""
    
    def __init__(self):
        self._part_number_pattern = re.compile(r'[0-9\-/]')
        self._whitespace_pattern = re.compile(r'\s+')
    
    def classify(self, query: str) -> SearchType:
        """
        Determines the type of search query.
        
        Args:
            query: The search term/phrase
            
        Returns:
            SearchType indicating the query type
        """
        if not query or not query.strip():
            return SearchType.ENGLISH_WORD
        
        # Normalize whitespace
        normalized_query = self._whitespace_pattern.sub(' ', query).strip()
        words = normalized_query.split()
        
        # Multiple words/terms
        if len(words) > 1:
            return SearchType.MULTIPLE_TERMS
        
        # Check if it's likely a part number (contains digits or special characters)
        if self._part_number_pattern.search(query):
            return SearchType.PART_NUMBER
        
        # Default to english word for single-word text queries
        return SearchType.ENGLISH_WORD


class MLSearchClassifier:
    """Machine learning based search classifier (placeholder for future implementation)."""
    
    def __init__(self, model_path: str = None):
        self.model_path = model_path
        # Placeholder for ML model initialization
        
    def classify(self, query: str) -> SearchType:
        """ML-based classification (not implemented yet)."""
        # Fallback to regex classifier for now
        return RegexSearchClassifier().classify(query)


class SearchClassifierFactory:
    """Factory for creating search classifiers."""
    
    @staticmethod
    def create_classifier(classifier_type: str = "regex") -> SearchClassifier:
        """Create a search classifier instance."""
        if classifier_type == "regex":
            return RegexSearchClassifier()
        elif classifier_type == "ml":
            return MLSearchClassifier()
        else:
            raise ValueError(f"Unknown classifier type: {classifier_type}")
