"""Prompt template management for LLM evaluation system."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from .search_classifier import SearchType


class PromptTemplate(ABC):
    """Abstract base class for prompt templates."""
    
    @abstractmethod
    def generate(self, query: str, results_text: str, result_count: int, **kwargs) -> str:
        """Generate prompt from template."""
        pass


class BasePromptTemplate(PromptTemplate):
    """Base implementation for prompt templates."""
    
    def __init__(self, template: str):
        self.template = template
    
    def generate(self, query: str, results_text: str, result_count: int, **kwargs) -> str:
        """Generate prompt by substituting placeholders."""
        return self.template.format(
            query=query,
            results_text=results_text,
            search_result_count=result_count,
            search_result_count_minus_one=result_count - 1,
            **kwargs
        )


class EnglishWordPromptTemplate(BasePromptTemplate):
    """Prompt template for English word queries."""
    
    def __init__(self):
        template = """
E-commerce Search Relevance Evaluation: English Word Query

You are an expert e-commerce product relevance analyst specializing in automotive and industrial parts.

SEARCH QUERY: "{query}"  
SEARCH TYPE: english_word  
BUSINESS CONTEXT: E-commerce search optimization for conversion and customer satisfaction

CRITICAL INSTRUCTION: COMPLETE EVALUATION REQUIRED

🚨 MANDATORY: You MUST evaluate EVERY SINGLE result provided in the "RESULTS TO EVALUATE" section.
🚨 COUNT VERIFICATION: The evaluation array must contain exactly {search_result_count} entries (Results 0-{search_result_count_minus_one}).
🚨 NO SHORTCUTS: Do not use "..." or skip any results. Each result requires a complete evaluation.
🚨 VALIDATION: Before finishing, verify your "evaluations" array has {search_result_count} entries matching the {search_result_count} input results.

RELEVANCE EVALUATION FRAMEWORK

🎯 HIGH RELEVANCE (Score: 9-10)
- Direct Product Match: Product directly matches the search term (e.g., searching "gasket" returns gaskets).
- Primary Function: Product's main purpose aligns with search term
- Category Match: Product belongs to the exact category implied by search term

🎯 MEDIUM RELEVANCE (Score: 6-8) 
- Related Items: Accessories or complementary products for the search term
- Similar Function: Products that serve a similar but not identical purpose
- Secondary Use: Products that can be used for the searched purpose but aren't primary

🎯 LOW RELEVANCE (Score: 1-5)
- Unrelated Items: Products that don't logically connect to the search term
- Different Category: Products from completely different automotive/industrial categories
- Keyword Coincidence: Products that only share words but different context

OUTPUT FORMAT IS FOLLOWING JSON STRUCTURE:

CRITICAL: 
- Your response must include exactly {search_result_count} evaluation entries in the "evaluations" array, one for each Result (0-{search_result_count_minus_one}).
- Your response must include "ranking_summary", quality_score" and "conversion_likelihood" sections in the JSON
- Validate the JSON structure before submitting.

json
{{
  "search_analysis": {{
    "query": "{query}",
    "total_results": {search_result_count},
    "category_matches_found": 0,
    "inventory_considerations_applied": true
  }},
  "evaluations": [
    // {search_result_count} evaluation entries here
  ],
  "ranking_summary": "Overall assessment of search result quality and inventory impact",    
  "quality_score": "Overall search result quality (1-10)",
  "conversion_likelihood": "High|Medium|Low based on result relevance and availability"
}}


RESULTS TO EVALUATE:
{results_text}
"""
        super().__init__(template)


class PartNumberPromptTemplate(BasePromptTemplate):
    """Prompt template for part number queries."""
    
    def __init__(self):
        template = """
E-commerce Search Relevance Evaluation: Part Number Query

You are an expert e-commerce product relevance analyst specializing in automotive and industrial parts.

SEARCH QUERY: "{query}"  
SEARCH TYPE: part_number  
BUSINESS CONTEXT: E-commerce part number search optimization for conversion and customer satisfaction

🚨 CRITICAL INSTRUCTIONS - READ CAREFULLY
MANDATORY REQUIREMENTS:

You MUST evaluate ALL {search_result_count} results (indices 0-{search_result_count_minus_one}) provided below
Your response MUST be valid JSON format only - no additional text
NO shortcuts, ellipsis (...), or incomplete entries allowed
Each evaluation must include ALL required fields

COUNT VERIFICATION:

Input: {search_result_count} results (Result 0 through Result {search_result_count_minus_one})
Output: Exactly {search_result_count} evaluations in JSON array
Before finishing: Count your evaluations = {search_result_count}

RELEVANCE EVALUATION FRAMEWORK

🎯 HIGH RELEVANCE (Score: 9-10)
Exact Match Criteria (Prioritized Order):
1. exact_match=Yes indicates an Exact Match for the search term. This product MUST BE the First one in the search results.      
2. Primary Part Number: Complete character-for-character match in 'Part Number' field
3. Vendor Part Number: Complete character-for-character match in 'Vendor Part Number' field  
4. Manufacturer Part Number: Complete character-for-character match in manufacturer-specific fields
5. Title Exact Match: Query appears as standalone complete part number in product title

🎯 MEDIUM RELEVANCE (Score: 6-8)
Partial Match Criteria:
1. cross_ref_match=Yes or partial_match=Yes indicates a Partial Match to the search term.
2. Substring Match: Query is contained within part number (e.g., "4707Q" in "SDNS-4707Q")
3. Reverse Substring: Part number is contained within query (longer query, shorter part)
4. Cross-Reference Match: Explicitly labeled as "Compatible with", "Replaces", "Alternative for"
5. Model/Series Match: Part of same product series or model family

### 🎯 LOW RELEVANCE (Score: 1-5)
Weak or No Match:
1. Category Only: Same product type but no part number relationship
2. Keyword Overlap: Only shares common words but different context
3. Unrelated: Different product category or no logical connection
4. False Positive: Incidental number matches in unrelated fields

OUTPUT FORMAT  IS FOLLOWING JSON STRUCTURE:

json
{{
  "search_analysis": {{
    "query": "{query}",
    "total_results": {search_result_count},
    "exact_matches_found": 0,
    "partial_matches_found": 0,
    "inventory_considerations_applied": true
  }},
  "evaluations": [
    // {search_result_count} evaluation entries here
  ],
  "ranking_summary": "Overall assessment of how inventory and relevance combined to create final ranking",  
  "quality_score": "Overall search result quality (1-10)",
  "conversion_likelihood": "High|Medium|Low based on result relevance and availability"
}}


RESULTS TO EVALUATE:
{results_text}
"""
        super().__init__(template)


class MultipleTermsPromptTemplate(BasePromptTemplate):
    """Prompt template for multiple terms queries."""
    
    def __init__(self):
        template = """
E-commerce Search Relevance Evaluation: Multiple Terms Query

You are a JSON generation specialist. Your ONLY task is to output valid JSON evaluating search results.

SEARCH QUERY: "{query}"

CRITICAL RULES:
1. Output ONLY valid JSON - no other text
2. Must have exactly {search_result_count} evaluations (indices 0-{search_result_count_minus_one})
3. Use EXACT field names from template
4. Copy titles and part numbers EXACTLY from input data
5. Find query terms in part numbers or title for relevance scoring

OUTPUT FORMAT IS FOLLOWING JSON STRUCTURE:

json
{{
  "search_analysis": {{
    "query": "{query}",
    "total_results": {search_result_count},
    "inventory_considerations_applied": true
  }},
  "evaluations": [
    // {search_result_count} evaluation entries here
  ],
  "ranking_summary": "Overall assessment of search result quality",
  "quality_score": "Overall search result quality (1-10)",
  "conversion_likelihood": "High|Medium|Low based on result relevance and availability"
}}


RESULTS TO EVALUATE:
{results_text}
"""
        super().__init__(template)


class ExecutiveSummaryPromptTemplate(BasePromptTemplate):
    """Prompt template for executive summary generation."""
    
    def __init__(self):
        template = """
Executive Summary Generation for E-commerce Search Analysis

You are an expert e-commerce analyst tasked with creating a concise executive summary based on the search relevance analysis below.

SEARCH QUERY ANALYZED: "{query}"
INITIAL ANALYSIS RESULTS:
{initial_analysis}

INSTRUCTIONS

Generate a comprehensive business recommendations summary in the EXACT JSON format specified below. Focus on:

1. Relevancy Assessment: Evaluate overall match quality
2. Inventory Impact: Analyze how stock levels affect customer experience and conversion
3. Customer Satisfaction Risk: Assess potential frustration or dissatisfaction
4. Key Insights: Highlight the most important findings
5. Recommended Actions: Provide specific, actionable recommendations

REQUIRED OUTPUT FORMAT IS FOLLOWING JSON STRUCTURE:

json
{{
  "business_recommendations": {{
    "relevancy_assessment": "High|Medium|Low - Explain why based on match quality and inventory.",
    "inventory_impact": "Detailed analysis of how inventory affected ranking within relevance tiers.",
    "customer_satisfaction_risk": "Low|Medium|High - Based on result quality, availability, and likelihood of customer finding what they need.",
    "key_insights": "2-3 bullet points summarizing the most critical findings from the evaluation that impact business performance.",
    "recommended_actions": {{
      "promote": "Specific results to promote based on high relevance and good stock levels.",
      "maintain": "Results that are performing adequately and should remain in current positions.",
      "demote": "Results to lower in ranking due to low relevance, poor stock or customer satisfaction risks.",
      "remove": "Results that should be removed entirely due to very poor relevance or zero business value.",
      "urgent_action": "Immediate critical actions needed to improve search performance, inventory management, or customer experience."
    }}
  }},
  "quality_score": "1-10 overall search result quality score",
  "conversion_likelihood": "High|Medium|Low based on result relevance, availability, and customer intent match"
}}

"""
        super().__init__(template)


class PromptTemplateManager:
    """Manages prompt templates for different search types."""
    
    def __init__(self):
        self._templates = {
            SearchType.ENGLISH_WORD: EnglishWordPromptTemplate(),
            SearchType.PART_NUMBER: PartNumberPromptTemplate(),
            SearchType.MULTIPLE_TERMS: MultipleTermsPromptTemplate(),
        }
        self._executive_summary_template = ExecutiveSummaryPromptTemplate()
    
    def get_template(self, search_type: SearchType) -> PromptTemplate:
        """Get template for specific search type."""
        return self._templates.get(search_type, self._templates[SearchType.ENGLISH_WORD])
    
    def get_executive_summary_template(self) -> PromptTemplate:
        """Get executive summary template."""
        return self._executive_summary_template
    
    def generate_prompt(self, search_type: SearchType, query: str, 
                       results_text: str, result_count: int, **kwargs) -> str:
        """Generate prompt for given search type and parameters."""
        template = self.get_template(search_type)
        return template.generate(query, results_text, result_count, **kwargs)
    
    def generate_executive_summary_prompt(self, query: str, initial_analysis: str, **kwargs) -> str:
        """Generate executive summary prompt."""
        return self._executive_summary_template.generate(
            query=query,
            results_text="",  # Not used in executive summary
            result_count=0,   # Not used in executive summary
            initial_analysis=initial_analysis,
            **kwargs
        )


class PromptValidator:
    """Validates prompt templates for common issues."""
    
    @staticmethod
    def validate_template(template_content: str, search_type: SearchType) -> Dict[str, Any]:
        """Validate template for required elements and best practices."""
        validation_result = {
            "is_valid": True,
            "warnings": [],
            "errors": [],
            "suggestions": []
        }
        
        # Check for required placeholders
        required_placeholders = ["{query}", "{results_text}", "{search_result_count}"]
        for placeholder in required_placeholders:
            if placeholder not in template_content:
                validation_result["errors"].append(f"Missing required placeholder: {placeholder}")
                validation_result["is_valid"] = False
        
        # Check for JSON format specification
        if "json" not in template_content.lower():
            validation_result["warnings"].append("Template should specify JSON output format")
        
        # Check template length
        if len(template_content) < 500:
            validation_result["warnings"].append("Template might be too short for comprehensive evaluation")
        elif len(template_content) > 10000:
            validation_result["warnings"].append("Template might be too long, consider reducing verbosity")
        
        return validation_result
