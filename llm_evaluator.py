# Enhanced LLM Evaluation Module with Inventory-Aware Ranking

from datetime import datetime
import json
import requests
import time
import re
from typing import Dict, List, Any, Optional, Union, Tuple
import os

# --- Configuration ---
OLLAMA_API_ENDPOINT = "http://localhost:11434/api/generate"
DEFAULT_MODEL =  "gemma3" #"gemma3"  # Change to your preferred model
TIMEOUT = 600  # Seconds to wait for Ollama response
MAX_RETRIES = 3  # Number of retries for API calls

# --- Search Type Classification ---
def classify_search_type(query: str) -> str:
    """
    Determines the type of search query.
    
    Args:
        query: The search term/phrase
        
    Returns:
        String indicating search type: "english_word", "part_number", or "multiple_terms"
    """
    # Check if query contains multiple words (excluding common separators in part numbers)
    normalized_query = re.sub(r'\s+', ' ', query).strip()
    words = normalized_query.split()
    
    if len(words) > 1:
        return "multiple_terms"
    
    # Check if it's likely a part number (contains digits or special characters typical in part numbers)
    if re.search(r'[0-9\-/]', query):
        return "part_number"
    
    # Default to english_word for single-word text queries
    return "english_word"

# --- Enhanced Prompt Templates with Inventory Awareness ---


def get_enhanced_prompt_template(search_type: str, initial_llm_response=None, Query=None) -> str:
    """
    Returns the enhanced prompt template with inventory consideration based on search type.
    
    Args:
        search_type: "english_word", "part_number", or "multiple_terms"
        
    Returns:
        String containing the enhanced prompt template
    """
    
    # Common inventory analysis section
    base_inventory_instruction = """
## INVENTORY IMPACT ANALYSIS

### 📦 Inventory Priority Rules
1. **Zero Inventory Penalty**: Products with 0 stock automatically drop one relevance tier unless no alternatives exist
2. **Stock Availability Boost**: Within same relevance tier, rank by inventory descending
3. **Low Stock Warning**: Flag items with <5 inventory_quantity as "Low Stock Risk"
4. **Business Impact**: Consider conversion probability based on stock levels

### 📊 Inventory Status Classification
- **Available**: >10 inventory_quantity in stock
- **Low Stock**: 1-10 inventory_quantity in stock  
- **Out of Stock**: If `inventory_quantity` = "N/A" or 0, `inventory_status` MUST be "Out of Stock" — NO EXCEPTIONS. 
- **Unknown**:  Only used if inventory data field is literally absent or null or not parsable
"""

    # Enhanced evaluation criteria section
    enhanced_evaluation_criteria = """
## ENHANCED EVALUATION CRITERIA

### 🔍 Match Quality Assessment
For each result, evaluate:
1. **Match Type**: Exact, Partial, Cross-reference, Category, None
2. **Match Location**: Part Number field, Vendor field, Title, Description
3. **Match Confidence**: How certain are you this is the intended product?
4. **Customer Intent**: Would a customer searching for "{query}" want this result?

### 💼 Business Impact Scoring
Consider:
- **Conversion Likelihood**: Will customer purchase this result?
- **Customer Satisfaction**: Does this meet search expectations?
- **Inventory Efficiency**: Does ranking optimize available stock?
- **Brand Trust**: Does result quality maintain platform credibility?

### recommended_action  scoring
- "Promote" → High relevance + In Stock  
- "Maintain" → Medium relevance or Low stock  
- "Demote" → Low stock + Medium/Low relevance  
- "Remove" → Out of Stock + Low relevance
- "Urgent Action" → Critical issues like no stock or poor relevance
"""

    # Critical evaluation guidelines
    critical_evaluation_guidelines = """
## CRITICAL EVALUATION GUIDELINES

Before submitting your response, verify:

✅ Evaluated exactly {search_result_count} results (indices 0-{search_result_count_minus_one})
✅ Each evaluation has all required fields
✅ No "..." or incomplete entries
✅ "total_results" in search_analysis equals {search_result_count}
✅ Length of "evaluations" array equals {search_result_count}
✅ If inventory_quantity is "N/A" or 0, then inventory_status MUST BE "Out of Stock" NO EXCEPTIONS
✅ Once you are done, review and validate the JSON structure before submitting. JSON MUST be valid and complete.
✅ VALIDATION REMINDER: Ensure JSON output conforms to schema. Use a validator if needed. No trailing commas or extra fields.



IMPORTANT REMINDERS

COMPLETE ALL {search_result_count}: Do not stop early or use shortcuts
BRIEF BUT COMPLETE: Keep justifications concise but ensure every result is evaluated
CONSISTENT FORMAT: Use exact same JSON structure for all {search_result_count} entries
VERIFY COUNT: Double-check you have exactly {search_result_count} evaluations before finishing

### ⚡ Key Priorities
1. **Exact Matches**: Always prioritize exact part number matches over partial
2. **Stock Availability**: Never rank out-of-stock items higher than in-stock within same relevance
3. **Customer Intent**: Ask "Would a customer searching '{query}' be satisfied with this result?"
4. **Business Value**: Consider both immediate conversion and long-term customer trust

### 🚫 Common Pitfalls to Avoid
- Don't confuse partial matches with exact matches
- Don't ignore inventory when ranking within same relevance tier
- Don't rank based on price or brand preference over relevance
- Don't give high relevance to products just because they're in stock

### 🎯 Quality Assurance
- If no exact matches exist, clearly state this in ranking_summary
- Explain any inventory-based ranking changes
- Highlight any potential customer satisfaction risks
- Provide specific, actionable business recommendations
"""

    # Define templates for each search type
    templates = {
        "english_word": f"""
# E-commerce Search Relevance Evaluation: English Word Query

You are an expert e-commerce product relevance analyst specializing in automotive and industrial parts.

**SEARCH QUERY**: "{{query}}"  
**SEARCH TYPE**: english_word  
**BUSINESS CONTEXT**: E-commerce search optimization for conversion and customer satisfaction


## CRITICAL INSTRUCTION: COMPLETE EVALUATION REQUIRED

🚨 **MANDATORY**: You MUST evaluate EVERY SINGLE result provided in the "RESULTS TO EVALUATE" section.
🚨 **COUNT VERIFICATION**: The evaluation array must contain exactly {{search_result_count}} entries (Results 0-{{search_result_count_minus_one}}).
🚨 **NO SHORTCUTS**: Do not use "..." or skip any results. Each result requires a complete evaluation.
🚨 **VALIDATION**: Before finishing, verify your "evaluations" array has {{search_result_count}} entries matching the {{search_result_count}} input results.


## RELEVANCE EVALUATION FRAMEWORK

### 🎯 **HIGH RELEVANCE (Score: 9-10)**
- **Direct Product Match**: Product directly matches the search term (e.g., searching "gasket" returns gaskets).
- **Primary Function**: Product's main purpose aligns with search term
- **Category Match**: Product belongs to the exact category implied by search term

### 🎯 **MEDIUM RELEVANCE (Score: 6-8)**  
- **Related Items**: Accessories or complementary products for the search term
- **Similar Function**: Products that serve a similar but not identical purpose
- **Secondary Use**: Products that can be used for the searched purpose but aren't primary

### 🎯 **LOW RELEVANCE (Score: 1-5)**
- **Unrelated Items**: Products that don't logically connect to the search term
- **Different Category**: Products from completely different automotive/industrial categories
- **Keyword Coincidence**: Products that only share words but different context

{base_inventory_instruction}

{enhanced_evaluation_criteria}

## OUTPUT FORMAT

**CRITICAL**: 
- Your response must include exactly {{search_result_count}} evaluation entries in the "evaluations" array, one for each Result (0-{{search_result_count_minus_one}}).
- Your response must include "ranking_summary", quality_score" and "conversion_likelihood" sections in the JSON
- Validate the JSON structure before submitting.
```json
{{{{
  "search_analysis": {{{{
    "query": "{{query}}",
    "total_results": 0,
    "category_matches_found": 0,
    "inventory_considerations_applied": true
  }}}},  ← **IMPORTANT: COMMA HERE**
  "evaluations": [
    {{{{
      "result_index": 0,
      "title": "Product Title",
      "relevance_tier": "High|Medium|Low",
      "relevance_score": "1-10",
      "match_type": "Direct|Related|Category|Unrelated",
      "inventory_status": "Available|Low Stock|Out of Stock|Unknown. Use the following strict rules:  - If inventory_quantity > 10 → Available     - If inventory_quantity between 1-10 → Low Stock     - If inventory_quantity = 0 or inventory_quantity = 'N/A' → Out of Stock    - If inventory_quantity is missing or unparseable → Unknown. If inventory_quantity is "N/A" or 0, then inventory_status MUST be "Out of Stock"—NO EXCEPTIONS.'",
      "inventory_quantity": "actual number or N/A",
      "part_number": "actual part number or N/A",
      "vendor_part_number": "actual vendor part number or N/A",
      "justification": "Detailed explanation of why this relevance tier was assigned",
      "inventory_impact": "How inventory affected ranking within relevance tier",
      "business_impact": "Excellent|Good|Fair|Poor",
      "recommended_action": "Promote|Maintain|Demote|Remove"
    }}}}... [CONTINUE FOR ALL {{search_result_count}} RESULTS - DO NOT USE "..." IN ACTUAL RESPONSE]
  ],
  "ranking_summary": "Overall assessment of search result quality and inventory impact",    
  "quality_score": "Overall search result quality (1-10)",
  "conversion_likelihood": "High|Medium|Low based on result relevance and availability"
}}}}
```

{critical_evaluation_guidelines}

**RESULTS TO EVALUATE:**
{{results_text}}
""",

        "part_number": f"""
# E-commerce Search Relevance Evaluation: Part Number Query

You are an expert e-commerce product relevance analyst specializing in automotive and industrial parts.

**SEARCH QUERY**: "{{query}}"  
**SEARCH TYPE**: part_number  
**BUSINESS CONTEXT**: E-commerce part number search optimization for conversion and customer satisfaction


🚨 CRITICAL INSTRUCTIONS - READ CAREFULLY
MANDATORY REQUIREMENTS:

You MUST evaluate ALL {{search_result_count}} results (indices 0-{{search_result_count_minus_one}}) provided below
Your response MUST be valid JSON format only - no additional text
NO shortcuts, ellipsis (...), or incomplete entries allowed
Each evaluation must include ALL required fields

COUNT VERIFICATION:

Input: {{search_result_count}} results (Result 0 through Result {{search_result_count_minus_one}})
Output: Exactly {{search_result_count}} evaluations in JSON array
Before finishing: Count your evaluations = {{search_result_count}}

## RELEVANCE EVALUATION FRAMEWORK

### 🎯 **HIGH RELEVANCE (Score: 9-10)**
**Exact Match Criteria (Prioritized Order):**
1. **exact_match=Yes indicates an Exact Match for the search term. This product MUST BE the First one in the search results.      
2. **Primary Part Number**: Complete character-for-character match in 'Part Number' field
3. **Vendor Part Number**: Complete character-for-character match in 'Vendor Part Number' field  
4. **Manufacturer Part Number**: Complete character-for-character match in manufacturer-specific fields
5. **Title Exact Match**: Query appears as standalone complete part number in product title

**Examples:**
- ✅ Search: "4707Q" → Part Number: "4707Q" (EXACT)
- ❌ Search: "4707Q" → Part Number: "SDNS-4707Q" (PARTIAL - not exact)
- ✅ Search: "BK608" → Title: "Vulcan BK608 Bearing Kit" (EXACT in title)

### 🎯 **MEDIUM RELEVANCE (Score: 6-8)**
**Partial Match Criteria:**
1. **cross_ref_match=Yes or partial_match=Yes indicates a Partial Match to the serch term.
2. **Substring Match**: Query is contained within part number (e.g., "4707Q" in "SDNS-4707Q")
3. **Reverse Substring**: Part number is contained within query (longer query, shorter part)
4. **Cross-Reference Match**: Explicitly labeled as "Compatible with", "Replaces", "Alternative for"
5. **Model/Series Match**: Part of same product series or model family
Functional Equivalent**: Same function but different manufacturer designation


### 🎯 **LOW RELEVANCE (Score: 1-5)**
**Weak or No Match:**
1. **Category Only**: Same product type but no part number relationship
2. **Keyword Overlap**: Only shares common words but different context
3. **Unrelated**: Different product category or no logical connection
4. **False Positive**: Incidental number matches in unrelated fields

{base_inventory_instruction}

{enhanced_evaluation_criteria}

## OUTPUT FORMAT - MANDATORY STRUCTURE

**CRITICAL**: Your response must include exactly {{search_result_count}} evaluation entries in the "evaluations" array, one for each Result (0-{{search_result_count_minus_one}}).

```json
{{{{
     "search_analysis": {{{{
    "query": "{{query}}",
    "total_results": 0,
    "exact_matches_found": 0,
    "partial_matches_found": 0,
    "inventory_considerations_applied": true
  }}}},  ← **IMPORTANT: COMMA HERE**
  "evaluations": [
    {{{{
      "result_index": 0,
      "title": "Product Title",
      "relevance_score": "1-10",
      "relevance_tier": "High|Medium|Low",
      "match_type": "Exact|Partial|Cross-reference|Category|None",
      "match_location": "Part Number|Vendor Part Number|Title|Description|Multiple",
      "match_confidence": "Very High|High|Medium|Low|Very Low",
      "inventory_status": "Available|Low Stock|Out of Stock|Unknown. Use the following strict rules:  - If inventory_quantity > 10 → Available     - If inventory_quantity between 1-10 → Low Stock     - If inventory_quantity = 0 or inventory_quantity = 'N/A' → Out of Stock    - If inventory_quantity is missing or unparseable → Unknown. If inventory_quantity is "N/A" or 0, then inventory_status MUST be "Out of Stock"—NO EXCEPTIONS",
      "inventory_quantity": "actual number or N/A",
      "part_number": "actual part number or N/A",
      "vendor_part_number": "actual vendor part number or N/A",
      "business_impact": "Excellent|Good|Fair|Poor",
      "justification": "Detailed explanation of match quality, location, and why this relevance tier was assigned",
      "inventory_impact": "How inventory affected ranking within relevance tier",
      "customer_satisfaction_risk": "Low|Medium|High",
      "recommended_action": "Promote|Maintain|Demote|Remove"
    }}}} ... [CONTINUE FOR ALL {{search_result_count}} RESULTS - DO NOT USE "..." IN ACTUAL RESPONSE]
  ],
  "ranking_summary": "Overall assessment of how inventory and relevance combined to create final ranking",  
  "quality_score": "Overall search result quality (1-10)",
  "conversion_likelihood": "High|Medium|Low based on result relevance and availability"
}}}}
```

FINAL REMINDER:

Response must be ONLY the JSON above
Must contain exactly {{search_result_count}} evaluations (indices 0-{{search_result_count_minus_one}})
No additional text before or after JSON
Each justification: maximum 10 words

{critical_evaluation_guidelines}

**RESULTS TO EVALUATE:**
{{results_text}}

""",

        "multiple_terms": f"""
# E-commerce Search Relevance Evaluation: Multi-Term Query

You are an expert e-commerce product relevance analyst specializing in automotive and industrial parts.

**SEARCH QUERY**: "{{query}}"  
**SEARCH TYPE**: multiple_terms  
**BUSINESS CONTEXT**: E-commerce multi-term search optimization for conversion and customer satisfaction


## OUTPUT FORMATMANDATORY STRUCTURE

**CRITICAL**: 
- Your response must include exactly {{search_result_count}} evaluation entries in the "evaluations" array, one for each Result (0-{{search_result_count_minus_one}}).
- Your response must include "ranking_summary", quality_score" and "conversion_likelihood" sections in the JSON
- Validate the JSON structure before submitting.
- If a field is EMPTY or "N/A", treat it as MISSING. DO NOT ASSUME MEANING OR MATCH FROM IT.

🧠 TIP: If you are truncating results or evaluations, STOP and retry with fewer tokens. DO NOT SKIP ENTRIES.



```json
{{{{
  "search_analysis": {{{{
    "query": "{{query}}",
    "query_terms": ["term1", "term2", "term3"],
    "total_results": 0,
    "full_matches_found": 0,
    "partial_matches_found": 0,
    "inventory_considerations_applied": true
  }}}},  ← **IMPORTANT: COMMA HERE**
  "evaluations": [
    {{{{
      "result_index": 0,
      "title": "Product Title",
      "relevance_tier": "High|Medium|Low",
      "relevance_score": "1-10",
      "terms_matched": ["List only the query terms that matched any of: title, part_number, vendor_part_number, manufacturer_part_number"],
      "terms_missing": ["missing_term1"],
      "match_quality": "All Key Terms|Most Terms|Some Terms|Few Terms",
      "contextual_accuracy": "Excellent|Good|Fair|Poor",
      "inventory_status": "Available|Low Stock|Out of Stock|Unknown. Use the following strict rules:  - If inventory_quantity > 10 → Available     - If inventory_quantity between 1-10 → Low Stock     - If inventory_quantity = 0 or inventory_quantity = 'N/A' → Out of Stock    - If inventory_quantity is missing or unparseable → Unknown. If inventory_quantity is "N/A" or 0, then inventory_status MUST be "Out of Stock"—NO EXCEPTIONS'",
      "inventory_quantity": "actual number or N/A",
      "part_number": "actual part number or N/A",
      "vendor_part_number": "actual vendor part number or N/A",
      "justification": "Detailed explanation of which terms matched, context quality, and relevance reasoning. ",
      "inventory_impact": "How inventory affected ranking within relevance tier",
      "business_impact": "Excellent|Good|Fair|Poor",
      "recommended_action": "Promote|Maintain|Demote|Remove|Urgent Action"
    }}}}... [CONTINUE FOR ALL {{search_result_count}} RESULTS - DO NOT USE "..." IN ACTUAL RESPONSE]
  ],
  "ranking_summary": "Overall assessment of multi-term matching quality and inventory impact",
  "quality_score": "Overall search result quality (1-10)",
  "conversion_likelihood": "High|Medium|Low based on result relevance and availability"
}}}} ← **IMPORTANT: MUST evaluate upto HERE. Make sure the JSON is VALID **
```

🚨 CRITICAL INSTRUCTIONS - READ CAREFULLY
MANDATORY REQUIREMENTS:

🚨 You MUST evaluate ALL {{search_result_count}} results (indices 0-{{search_result_count_minus_one}}) provided below
🚨 Your response MUST be valid JSON format only - no additional text
🚨 NO shortcuts, ellipsis (...), or incomplete entries allowed
🚨 Each evaluation must include ALL required fields
🚨 IMPORTANT: If `inventory_quantity` = "N/A" or 0, `inventory_status` MUST be "Out of Stock" — NO EXCEPTIONS.


COUNT VERIFICATION:

Input: {{search_result_count}} results (Result 0 through Result {{search_result_count_minus_one}})
Output: Exactly {{search_result_count}} evaluations in JSON array
Before finishing: Count your evaluations = {{search_result_count}}

## RELEVANCE EVALUATION FRAMEWORK

### 🎯 **HIGH RELEVANCE (Score: 9-10)**
**Exact Match Criteria (Prioritized Order):**
1. **exact_match=Yes indicates an Exact Match for the search term. This product MUST BE the First one in the search results.      
2. **Primary Part Number**: Complete character-for-character match in 'Part Number' field
3. **Vendor Part Number**: Complete character-for-character match in 'Vendor Part Number' field  
4. **Manufacturer Part Number**: Complete character-for-character match in manufacturer-specific fields
5. **Title Exact Match**: Query appears as standalone complete part number in product title

**Examples:**
- ✅ Search: "4707Q" → Part Number: "4707Q" (EXACT MATCH)
- ❌ Search: "4707Q" → Part Number: "SDNS-4707Q" (PARTIAL  MATCH- not exact)
- ✅ Search: "BK608" → Title: "Vulcan BK608 Bearing Kit" (EXACT MATCH in title)

### 🎯 **MEDIUM RELEVANCE (Score: 6-8)**
**Partial Match Criteria:**
1. **cross_ref_match=Yes or partial_match=Yes indicates a Partial Match to the serch term.
2. **Substring Match**: Query is contained within part number (e.g., "4707Q" in "SDNS-4707Q" or "4707Q-AK" in "Armada Brake pad WWAK4707Q-AK12")
3. **Reverse Substring**: Part number is contained within query (longer query, shorter part)
4. **Cross-Reference Match**: Explicitly labeled as "Compatible with", "Replaces", "Alternative for"
5. **Model/Series Match**: Part of same product series or model family
6. **Functional Equivalent**: Same function but different manufacturer designation

**Examples:**
- ✅ Search: "4707Q" → Part Number: "AK4707Q-AK" (PARTIAL MATCH "4707Q" in "AK4707Q-AK")
- ✅ Search: "BK608" → Title: "Vulcan 12BK608ABC Bearing Kit" (PARTIAL MATCH to "BK608" in title)


### 🎯 **LOW RELEVANCE (Score: 1-5)**
**Weak or No Match:**
1. **Category Only**: Same product type but no part number relationship
2. **Keyword Overlap**: Only shares common words but different context
3. **Unrelated**: Different product category or no logical connection
4. **False Positive**: Incidental number matches in unrelated fields

{base_inventory_instruction}

{enhanced_evaluation_criteria}


FINAL REMINDER:

Response must be ONLY the JSON above
Must contain exactly {{search_result_count}} evaluations (indices 0-{{search_result_count_minus_one}}). Count evaluations array length = {{search_result_count}}
No additional text before or after JSON
Each justification: MUST be 20 words or less

{critical_evaluation_guidelines}



### HERE IS A SAMPLE OUTPUT:
```json
{{{{
  "search_analysis":{{{{
    "query": "armada 4707q",
    "query_terms": ["armada", "4707q"],
    "total_results": 10,
    "full_matches_found": 0,
    "partial_matches_found": 0,
    "inventory_considerations_applied": true
  }}}},
  "evaluations": [
    {{{{
      "result_index": 0,
      "title": "Armada Brake Shoe Kit New",
      "relevance_tier": "High",
      "relevance_score": "9",
      "terms_matched": ["armada", "4707q"],
      "terms_missing": [],
      "match_quality": "All Key Terms",
      "contextual_accuracy": "Excellent",
      "inventory_status": "Available",
      "inventory_quantity": "44",
      "part_number": "NK4707QPAR2",
      "vendor_part_number": "4707QPAR2",
      "justification": "Both terms match exactly, strong title alignment.",
      "inventory_impact": "Boosted due to high stock availability",
      "business_impact": "Excellent",
      "recommended_action": "Promote"
    }}}},
    {{{{
      "result_index": 1,
      "title": "Product Title",
      ...
    }}}}
  ],
  "ranking_summary": "Summarize ranking and inventory impact.",
  "quality_score": "8",
  "conversion_likelihood": "High"
}}}}
```


**RESULTS TO EVALUATE:**
{{results_text}}
""",

        "executive_summary": f"""

# Executive Summary Generation for E-commerce Search Analysis

You are an expert e-commerce analyst tasked with creating a concise executive summary based on the search relevance analysis below.

**SEARCH QUERY ANALYZED**: "{Query}"
**INITIAL ANALYSIS RESULTS**:
{json.dumps(initial_llm_response, indent=2)}

## INSTRUCTIONS

Generate a comprehensive business recommendations summary in the EXACT JSON format specified below. Focus on:

1. **Relevancy Assessment**: Evaluate overall match quality (High if exact matches exist, Medium for good partial matches, Low for poor matches)
2. **Inventory Impact**: Analyze how stock levels affect customer experience and conversion. Quantiy 'N/A' means no stock, 'Low Stock' means limited availability, 'Medium Stock' means some availability, and 'High Stock' means good availability.
3. **Customer Satisfaction Risk**: Assess potential frustration or dissatisfaction
4. **Key Insights**: Highlight the most important findings
5. **Recommended Actions**: Provide specific, actionable recommendations

## REQUIRED OUTPUT FORMAT

Your response must be ONLY valid JSON in this exact structure:

```json
{{
  "business_recommendations": {{
    "relevancy_assessment": "High|Medium|Low - Explain why based on match quality and inventory. Having 1+ exact matches = HIGH relevancy assessment.",
    "inventory_impact": "Detailed analysis of how inventory affected ranking within relevance tiers. Include percentages of No Stock/Low Stock/Medium Stock/High Stock products and their impact on customer experience.",
    "customer_satisfaction_risk": "Low|Medium|High - Based on result quality, availability, and likelihood of customer finding what they need.",
    "key_insights": "2-3 bullet points summarizing the most critical findings from the evaluation that impact business performance.",
    "recommended_actions": {{
      "promote": "REVIEW EACH and EVERY ONE OF THE results. Specific results (by index or part number) to promote based on high relevance and good stock levels.",
      "maintain": "REVIEW EACH and EVERY ONE OF THE results. Results that are performing adequately and should remain in current positions.",
      "demote": "REVIEW EACH and EVERY ONE OF THE results. Results to lower in ranking due to low relevance, poor stock or No Stock  or customer satisfaction risks.",
      "remove": "REVIEW EACH and EVERY ONE OF THE results. Results that should be removed entirely due to very poor relevance or with 'N/A' or 0 quantity or No Inventory or zero business value.",
      "urgent_action": "Immediate critical actions needed to improve search performance, inventory management, or customer experience. Flag if top results have no inventory or poor relevance."
    }}
  }},
  "quality_score": "1-10 overall search result quality score",
  "conversion_likelihood": "High|Medium|Low based on result relevance, availability, and customer intent match"
}}
```

## BASE INVENTORY INSTRUCTION
{base_inventory_instruction}

## ANALYSIS GUIDELINES

- **High Relevancy**: Exact matches found with good inventory
- **Medium Relevancy**: Good partial matches or exact matches with poor inventory  
- **Low Relevancy**: Only weak matches or category-level results
- **Inventory Impact**: Consider how stock levels within each relevance tier affect final rankings
- **Customer Risk**: High risk if top results are irrelevant or out of stock
- **Actions**: Be specific about which results (by index) need attention

## CRITICAL REQUIREMENTS

1. Response must be ONLY the JSON structure above
2. No additional text before or after the JSON
3. All fields must be completed with specific, actionable content
4. Reference specific result indices where applicable
5. Provide clear business justification for all recommendations
6. For BUSINESS RECOMMENDATIONS, REVIEW EACH and EVERY ONE OF THE results before summarizing the data.

Generate the executive summary now:
"""
    }
    
    return templates.get(search_type, templates["english_word"])

# --- Enhanced Result Formatting ---
def format_results_for_enhanced_prompt(results: List[Dict[str, str]]) -> str:
    """
    Formats the scraped results into a text format suitable for the enhanced prompt.
    Includes inventory/quantity information prominently.
    
    Args:
        results: List of dictionaries containing scraped product data
        
    Returns:
        Formatted string of results with inventory emphasis
    """
    formatted_text = ""
    for i, result in enumerate(results):
        formatted_text += f"Result {i}:\n"
        formatted_text += f"Title: {result.get('title', 'N/A')}\n"
        formatted_text += f"Part Number: {result.get('part_number', 'N/A')}\n"
        formatted_text += f"Vendor Part Number: {result.get('vendor_part_number', 'N/A')}\n"
        formatted_text += f"Manufacturer Part Number: {result.get('manufacturer_part_number', 'N/A')}\n"
        formatted_text += f"Description: {result.get('description', 'N/A')}\n"
        formatted_text += f"Price: {result.get('price', 'N/A')}\n"
        formatted_text += f"exact_match: {result.get('exact_match', 'N/A')}\n"
        formatted_text += f"partial_match: {result.get('partial_match', 'N/A')}\n"
        formatted_text += f"cross_ref_match: {result.get('cross_ref_match', 'N/A')}\n"
        # Emphasize inventory information
        quantity = result.get('quantity', 'N/A')
        formatted_text += f"INVENTORY/QUANTITY: {quantity}\n"
        
        formatted_text += f"URL: {result.get('url', 'N/A')}\n"
        formatted_text += "---\n"
    
    return formatted_text

# --- Inventory Parsing Utilities ---
def parse_inventory_quantity(quantity_str: str) -> Tuple[int, str]:
    """
    Parses inventory quantity string and returns numeric value and status.
    
    Args:
        quantity_str: The quantity string from scraped data
        
    Returns:
        Tuple of (numeric_quantity, status_string)
    """
    if not quantity_str or quantity_str == 'N/A':
        return 0, "Unknown"
    
    # Extract numeric value
    numeric_match = re.search(r'(\d+)', str(quantity_str))
    if numeric_match:
        qty = int(numeric_match.group(1))
        if qty == 0:
            return 0, "Out of Stock"
        elif qty < 5:  # Threshold for low stock
            return qty, "Low Stock"
        else:
            return qty, "Available"
    
    # Handle text-based indicators
    quantity_lower = str(quantity_str).lower()
    if any(term in quantity_lower for term in ['out of stock', 'unavailable', '0', 'N/A']):
        return 0, "Out of Stock"
    elif any(term in quantity_lower for term in ['low stock', 'limited']):
        return 1, "Low Stock"
    elif any(term in quantity_lower for term in ['in stock', 'available']):
        return 999, "Available"  # High number for available but unknown quantity
    
    return 0, "Unknown"

# --- Post-Processing for Inventory-Aware Ranking ---
def apply_inventory_aware_ranking(evaluations: List[Dict[str, Any]], 
                                 original_results: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Post-processes evaluations to ensure inventory-aware ranking within relevance tiers.
    
    Args:
        evaluations: List of evaluation results from LLM
        original_results: Original scraped results with inventory data
        
    Returns:
        Reordered evaluations with inventory-aware ranking applied
    """
    # Group evaluations by relevance level
    relevance_groups = {"High": [], "Medium": [], "Low": []}
    
    for eval_item in evaluations:
        relevance = eval_item.get("relevance", "Low")
        
        # Get original result for inventory data
        result_index = eval_item.get("result_index", 0)
        if result_index < len(original_results):
            original_result = original_results[result_index]
            quantity_str = original_result.get('quantity', 'N/A')
            numeric_qty, status = parse_inventory_quantity(quantity_str)
            
            # Add inventory data to evaluation
            eval_item["parsed_quantity"] = numeric_qty
            eval_item["inventory_status_parsed"] = status
        else:
            eval_item["parsed_quantity"] = 0
            eval_item["inventory_status_parsed"] = "Unknown"
        
        if relevance in relevance_groups:
            relevance_groups[relevance].append(eval_item)
    
    # Sort each relevance group by inventory (descending)
    for relevance_level in relevance_groups:
        relevance_groups[relevance_level].sort(
            key=lambda x: x["parsed_quantity"], 
            reverse=True
        )
    
    # Combine back in order: High -> Medium -> Low
    reordered_evaluations = (
        relevance_groups["High"] + 
        relevance_groups["Medium"] + 
        relevance_groups["Low"]
    )
    print(f"Reordered evaluations: {reordered_evaluations} (High: {len(relevance_groups['High'])}, Medium: {len(relevance_groups['Medium'])}, Low: {len(relevance_groups['Low'])})      ")
    return reordered_evaluations

# --- Ollama API Interaction with Configuration Support ---
def query_ollama(prompt: str, model: str = DEFAULT_MODEL, api_endpoint: str = OLLAMA_API_ENDPOINT, 
                timeout: int = TIMEOUT, max_retries: int = MAX_RETRIES) -> Dict[str, Any]:
    """
    Sends a prompt to the Ollama API and returns the response.
    
    Args:
        prompt: The prompt text to send to the LLM
        model: The Ollama model to use
        api_endpoint: The Ollama API endpoint URL
        timeout: Request timeout in seconds
        max_retries: Number of retry attempts
        
    Returns:
        Dictionary containing the API response or error information
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                api_endpoint,
                json=payload,
                timeout=timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"API error (attempt {attempt+1}/{max_retries}): Status {response.status_code}")
                print(f"Response: {response.text}")
                time.sleep(1)
                
        except requests.exceptions.RequestException as e:
            print(f"Request failed (attempt {attempt+1}/{max_retries}): {e}")
            time.sleep(1)
    
    return {"error": f"Failed after {max_retries} attempts"}


def fix_common_json_issues(json_str: str) -> str:
    """
    Fix common JSON formatting issues in LLM responses
    
    Args:
        json_str: Raw JSON string from LLM
        
    Returns:
        Fixed JSON string
    """
    # Remove markdown code blocks
    if "```json" in json_str:
        start_marker = "```json"
        end_marker = "```"
        start_idx = json_str.find(start_marker)
        if start_idx != -1:
            start_idx += len(start_marker)
            end_idx = json_str.find(end_marker, start_idx)
            if end_idx != -1:
                json_str = json_str[start_idx:end_idx].strip()
    
    # Fix missing commas between JSON objects/arrays
    # Pattern: }\n  "key" -> },\n  "key"
    json_str = re.sub(r'}\s*\n\s*"', '},\n  "', json_str)
    json_str = re.sub(r']\s*\n\s*"', '],\n  "', json_str)
    
    # Fix missing commas in search_analysis section specifically
    # Pattern: }\n  "evaluations" -> },\n  "evaluations"
    json_str = re.sub(r'(\s*true\s*)\n(\s*}\s*)\n(\s*"evaluations")', r'\1\2,\3', json_str)
    json_str = re.sub(r'(\s*false\s*)\n(\s*}\s*)\n(\s*"evaluations")', r'\1\2,\3', json_str)
    json_str = re.sub(r'(\s*\d+\s*)\n(\s*}\s*)\n(\s*"evaluations")', r'\1\2,\3', json_str)
    
    # Fix trailing commas before closing braces/brackets
    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
    
    # Fix unescaped quotes in string values
    # This is tricky, so we'll be conservative and only fix obvious cases
    json_str = re.sub(r':\s*"([^"]*)"([^",}\]]*)"([^",}\]]*)"', r': "\1\2\3"', json_str)
    
    # Fix single quotes to double quotes (but be careful not to break contractions)
    json_str = re.sub(r"'([^']*)':", r'"\1":', json_str)
    
    return json_str.strip()

def extract_json_from_response(response_text: str) -> Optional[str]:
    """
    Extract JSON from LLM response text
    
    Args:
        response_text: Full LLM response
        
    Returns:
        Extracted JSON string or None
    """
    # Try to find JSON block with various patterns
    json_patterns = [
        # Pattern 1: JSON in code blocks
        r'```json\s*(.*?)\s*```',
        # Pattern 2: JSON starting with { and ending with }
        r'({[\s\S]*?})\s*$',
        # Pattern 3: JSON anywhere in the text
        r'({[\s\S]*?"evaluations"[\s\S]*?})',
        # Pattern 4: Just look for opening brace to end of string
        r'({[\s\S]*)'
    ]
    
    for pattern in json_patterns:
        match = re.search(pattern, response_text, re.DOTALL | re.MULTILINE)
        if match:
            potential_json = match.group(1).strip()
            # Basic validation - should start with { and end with }
            if potential_json.startswith('{') and potential_json.endswith('}'):
                return potential_json
    
    return None

def parse_enhanced_llm_response_improved(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Improved parsing of enhanced LLM response with better error handling
    
    Args:
        response: Raw response from Ollama API
        
    Returns:
        Parsed evaluation data or None if parsing failed
    """
    if "error" in response:
        print(f"Error in LLM response: {response['error']}")
        return None
    
    try:

        generated_text = response.get("response", "")
        print(f"📝 Raw LLM response length: {len(generated_text)} characters")
        
         # --- Remove ```json at the beginning and ``` at the end if present ---
        if generated_text.strip().startswith("```json"):
            generated_text = generated_text.strip()[7:]  # Remove the first 7 chars (```json)
        if generated_text.strip().endswith("```"):
            generated_text = generated_text.strip()
            generated_text = generated_text[:-3]  # Remove the last 3 chars (```)

        # Step 1: Extract JSON from response
        json_str = extract_json_from_response(generated_text)
        if not json_str:
            print("❌ Could not extract JSON from response")
            print(f"Response preview: {generated_text[:500]}...")
            return fallback_manual_extraction(generated_text)
        
        print(f"✅ Extracted JSON ({len(json_str)} chars)")
        
        # Step 2: Fix common JSON issues
        fixed_json = fix_common_json_issues(json_str)
        print(f"🔧 Applied JSON fixes")
        
        # Step 3: Try to parse JSON
        try:
            parsed_data = json.loads(fixed_json)
            
            # Step 4: Validate structure
            if validate_evaluation_structure(parsed_data):
                print(f"✅ Successfully parsed evaluation with {len(parsed_data.get('evaluations', []))} evaluations")
                return parsed_data
            else:
                print("⚠️ Parsed JSON but structure validation failed")
                return fallback_manual_extraction(generated_text)
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed even after fixes: {e}")
            print(f"Problematic JSON preview: {fixed_json[:300]}...")
            
            # Try one more aggressive fix
            aggressive_fix = aggressive_json_repair(fixed_json)
            try:
                parsed_data = json.loads(aggressive_fix)
                if validate_evaluation_structure(parsed_data):
                    print(f"✅ Successfully parsed after aggressive repair")
                    return parsed_data
            except:
                pass
            
            return fallback_manual_extraction(generated_text)
    
    except Exception as e:
        print(f"Unexpected error in parsing: {e}")
        return fallback_manual_extraction(response.get("response", ""))

def aggressive_json_repair(json_str: str) -> str:
    """
    Apply aggressive fixes to malformed JSON
    
    Args:
        json_str: Malformed JSON string
        
    Returns:
        Repaired JSON string
    """
    # Fix common LLM JSON issues
    
    # 1. Add missing commas after closing braces/brackets when followed by quotes
    json_str = re.sub(r'}\s*\n\s*"', '},\n"', json_str)
    json_str = re.sub(r']\s*\n\s*"', '],\n"', json_str)
    
    # 2. Fix the specific search_analysis missing comma issue
    json_str = re.sub(r'(true|false|\d+)\s*\n\s*}\s*\n\s*"evaluations"', r'\1\n  },\n  "evaluations"', json_str)
    
    # 3. Ensure proper comma placement in arrays
    json_str = re.sub(r'}\s*\n\s*{', '},\n    {', json_str)
    
    # 4. Fix quote escaping issues
    json_str = json_str.replace('\\"', '"').replace("'", '"')
    
    # 5. Remove any trailing content after the last }
    last_brace = json_str.rfind('}')
    if last_brace != -1:
        json_str = json_str[:last_brace + 1]
    
    return json_str

def validate_evaluation_structure(data: Dict[str, Any]) -> bool:
    """
    Validate that the parsed data has the expected evaluation structure
    
    Args:
        data: Parsed JSON data
        
    Returns:
        True if structure is valid, False otherwise
    """
    try:
        # Check for required top-level keys
        required_keys = ["evaluations"]
        for key in required_keys:
            if key not in data:
                print(f"Missing required key: {key}")
                return False
        
        # Check evaluations array
        evaluations = data.get("evaluations", [])
        if not isinstance(evaluations, list):
            print("evaluations is not a list")
            return False
        
        if len(evaluations) == 0:
            print("evaluations array is empty")
            return False
        
        # Check each evaluation entry
        required_eval_keys = ["result_index", "relevance_tier", "justification"]
        for i, evaluation in enumerate(evaluations):
            if not isinstance(evaluation, dict):
                print(f"Evaluation {i} is not a dictionary")
                return False
            
            for key in required_eval_keys:
                if key not in evaluation:
                    print(f"Evaluation {i} missing required key: {key}")
                    return False
        
        print(f"✅ Structure validation passed for {len(evaluations)} evaluations")
        return True
        
    except Exception as e:
        print(f"Error in structure validation: {e}")
        return False

def fallback_manual_extraction(text: str) -> Optional[Dict[str, Any]]:
    """
    Fallback manual extraction when JSON parsing completely fails
    
    Args:
        text: Raw LLM response text
        
    Returns:
        Manually extracted evaluation data
    """
    print("🔧 Attempting fallback manual extraction...")
    
    try:
        evaluations = []
        
        # Look for result_index patterns
        result_patterns = [
            r'"result_index":\s*(\d+)',
            r'result_index.*?(\d+)',
        ]
        
        relevance_patterns = [
            r'"relevance_tier":\s*"(High|Medium|Low)"',
            r'relevance.*?(High|Medium|Low)',
        ]
        
        justification_patterns = [
            r'"justification":\s*"([^"]+)"',
            r'justification.*?"([^"]+)"',
        ]
        
        # Extract all matches
        result_indices = []
        for pattern in result_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            result_indices.extend([int(m) for m in matches])
        
        relevances = []
        for pattern in relevance_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            relevances.extend(matches)
        
        justifications = []
        for pattern in justification_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            justifications.extend([m.strip() for m in matches])
        
        # Create evaluations from extracted data
        max_results = max(len(result_indices), len(relevances), len(justifications)) if any([result_indices, relevances, justifications]) else 0
        
        # Remove duplicates while preserving order
        seen_indices = set()
        unique_indices = []
        for idx in result_indices:
            if idx not in seen_indices:
                unique_indices.append(idx)
                seen_indices.add(idx)
        
        # Create evaluation entries
        for i in range(min(len(unique_indices), len(relevances), len(justifications))):
            evaluation = {
                "result_index": unique_indices[i],
                "relevance_tier": relevances[i] if i < len(relevances) else "Medium",
                "justification": justifications[i] if i < len(justifications) else f"Manual extraction for result {i}",
                "inventory_status": "Unknown",
                "inventory_quantity": "N/A",
                "inventory_impact": "N/A"
            }
            evaluations.append(evaluation)
        
        if evaluations:
            print(f"✅ Manual extraction successful: {len(evaluations)} evaluations")
            return {
                "evaluations": evaluations,
                "ranking_summary": "Manually extracted due to JSON parsing issues"
            }
        else:
            print("❌ Manual extraction also failed")
            return None
            
    except Exception as e:
        print(f"Manual extraction error: {e}")
        return None
    
# --- Enhanced LLM Response Parsing ---
def parse_enhanced_llm_response_old(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parses the enhanced LLM response including inventory considerations.
    Enhanced to handle various JSON formatting issues.
    """
    if "error" in response:
        print(f"Error in LLM response: {response['error']}")
        return None
    
    try:
        generated_text = response.get("response", "")
        print(f"Raw LLM response: {generated_text[:1500]}...")  # Print first 1500 chars for debugging
        # Remove markdown code blocks if present
        if "```json" in generated_text:
            # Extract content between ```json and ```
            start_marker = "```json"
            end_marker = "```"
            start_idx = generated_text.find(start_marker)
            if start_idx != -1:
                start_idx += len(start_marker)
                end_idx = generated_text.find(end_marker, start_idx)
                if end_idx != -1:
                    generated_text = generated_text[start_idx:end_idx].strip()
        
        # Try to find JSON block in the response (more flexible pattern)
        json_patterns = [
            r'({[\s\S]*?"evaluations"[\s\S]*?})',  # Original pattern
            r'(\{[^{}]*?"evaluations"[^{}]*?\})',   # Simpler pattern
            r'({.*?"evaluations".*?})',             # Even simpler
        ]
        
        json_str = None
        for pattern in json_patterns:
            json_match = re.search(pattern, generated_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                break
        
        if not json_str:
            # Fallback: try to extract JSON-like content manually
            lines = generated_text.split('\n')
            json_lines = []
            in_json = False
            brace_count = 0
            
            for line in lines:
                if '{' in line and not in_json:
                    in_json = True
                    brace_count += line.count('{') - line.count('}')
                    json_lines.append(line)
                elif in_json:
                    brace_count += line.count('{') - line.count('}')
                    json_lines.append(line)
                    if brace_count <= 0:
                        break
            
            if json_lines:
                json_str = '\n'.join(json_lines)
        
        if json_str:
            # Clean up common JSON formatting issues
            json_str = json_str.strip()
            
            # Fix common trailing comma issues
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
            
            # Fix unescaped quotes in strings
            json_str = re.sub(r'(?<!\\)"(?=[^,}\]]*[,}\]])', r'\\"', json_str)
            
            # Try to parse
            try:
                evaluations = json.loads(json_str)
                return evaluations
            except json.JSONDecodeError as e:
                print(f"JSON parsing failed, attempting to fix: {e}")
                
                # More aggressive cleaning
                json_str = json_str.replace("'", '"')  # Replace single quotes
                json_str = re.sub(r'([{,]\s*)(\w+):', r'\1"\2":', json_str)  # Quote unquoted keys
                json_str = re.sub(r':\s*([^",\[\]{}]+)([,}])', r': "\1"\2', json_str)  # Quote unquoted values
                
                try:
                    evaluations = json.loads(json_str)
                    return evaluations
                except json.JSONDecodeError as e2:
                    print(f"Still failed to parse JSON after cleanup: {e2}")
                    
                    # Last resort: try to extract evaluations manually
                    return extract_evaluations_manually(generated_text)
        
        print("Could not find valid JSON in LLM response")
        print(f"Raw response (first 500 chars): {generated_text[:500]}...")
        return extract_evaluations_manually(generated_text)
        
    except Exception as e:
        print(f"Unexpected error parsing LLM response: {e}")
        return extract_evaluations_manually(response.get("response", ""))

def extract_evaluations_manually(text: str) -> Optional[Dict[str, Any]]:
    """
    Manually extract evaluation information from text when JSON parsing fails.
    """
    try:
        evaluations = []
        
        # Look for result patterns
        result_patterns = [
            r'result_index["\']?\s*:\s*(\d+)',
            r'Result\s*(\d+)',
            r'result\s*(\d+)',
        ]
        
        relevance_patterns = [
            r'relevance["\']?\s*:\s*["\']?(High|Medium|Low)["\']?',
            r'(High|Medium|Low)\s*relevance',
            r'relevance.*?(High|Medium|Low)',
        ]
        
        justification_patterns = [
            r'justification["\']?\s*:\s*["\']([^"\']+)["\']',
            r'justification.*?[:]\s*([^,}\]]+)',
        ]
        
        # Extract all matches
        result_indices = []
        for pattern in result_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                result_indices.extend([int(m) for m in matches])
        
        relevances = []
        for pattern in relevance_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                relevances.extend(matches)
        
        justifications = []
        for pattern in justification_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            if matches:
                justifications.extend([m.strip() for m in matches])
        
        # Create evaluations from extracted data
        max_results = max(len(result_indices), len(relevances), len(justifications))
        
        for i in range(max_results):
            evaluation = {
                "result_index": result_indices[i] if i < len(result_indices) else i,
                "relevance": relevances[i] if i < len(relevances) else "Medium",
                "justification": justifications[i] if i < len(justifications) else f"Manual extraction for result {i}",
                "inventory_status": "Unknown",
                "inventory_quantity": "N/A",
                "inventory_impact": "N/A"
            }
            evaluations.append(evaluation)
        
        if evaluations:
            print(f"Manually extracted {len(evaluations)} evaluations")
            return {
                "evaluations": evaluations,
                "ranking_summary": "Manually extracted due to JSON parsing issues"
            }
        else:
            print("Manual extraction also failed")
            return None
            
    except Exception as e:
        print(f"Manual extraction error: {e}")
        return None# Enhanced LLM Evaluation Module with Inventory-Aware Ranking - COMPLETE VERSION


# --- Main Enhanced Evaluation Function ---
def evaluate_search_results_with_inventory(query: str, results: List[Dict[str, str]], 
                                          search_type: Optional[str] = None, 
                                          model: str = DEFAULT_MODEL,
                                          apply_post_ranking: bool = True,
                                          api_endpoint: str = OLLAMA_API_ENDPOINT,
                                          timeout: int = TIMEOUT,
                                          max_retries: int = MAX_RETRIES) -> Dict[str, Any]:
    """
    Enhanced evaluation function that considers inventory in ranking decisions.
    
    Args:
        query: The original search term/phrase
        results: List of dictionaries containing scraped product data
        search_type: Optional type override
        model: The Ollama model to use
        apply_post_ranking: Whether to apply additional inventory-based post-processing
        api_endpoint: The Ollama API endpoint URL
        timeout: Request timeout in seconds
        max_retries: Number of retry attempts
        
    Returns:
        Dictionary containing enhanced evaluation results with inventory considerations
    """
    # Determine search type if not provided
    if search_type is None:
        search_type = classify_search_type(query)
    
    print(f"Enhanced evaluation for query: '{query}' (Type: {search_type})")
    print(f"Results with inventory data: {len(results)} items")
    
    # Get enhanced prompt template and format results
    prompt_template = get_enhanced_prompt_template(search_type)
    results_text = format_results_for_enhanced_prompt(results)
    
    # Fill in the prompt template
    prompt = prompt_template.format(query=query, results_text=results_text, search_result_count=len(results), search_result_count_minus_one=len(results)-1)
    
    # Create a safe filename with date-time
    debug_dir = "llm_debug"
    os.makedirs(debug_dir, exist_ok=True)
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"prompt_{now}.txt"

    # Write the prompt to the file
    with open(os.path.join(debug_dir, filename), "w", encoding="utf-8") as f:
        f.write(prompt)

    print(f"Prompt dumped to {filename}")
    # Query the LLM with configuration parameters
    print("Step 1: Generating detailed search analysis...")
    llm_response = query_ollama(prompt, model, api_endpoint, timeout, max_retries)
    
    # Parse the enhanced response
    parsed_evaluations = parse_enhanced_llm_response_improved(llm_response)
    
    # Save prompt, llm_response, and parsed evaluations for debugging    
    debug_file = os.path.join(debug_dir, f"llm_debug_data_{now}.json")
    try:
        with open(debug_file, "w", encoding="utf-8") as f:
            json.dump({
                "prompt": prompt,
                "llm_response": llm_response,
                "parsed_evaluations": parsed_evaluations
            }, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Failed to save debug data: {e}")

    if parsed_evaluations:
        # Step 2: Generate executive summary prompt
        print("Step 2: Generating executive summary...")
        summary_prompt = get_enhanced_prompt_template('executive_summary', parsed_evaluations, query) # generate_executive_summary_prompt(parsed_evaluations, query)
        
        # Step 3: Query LLM for executive summary
        summary_response = query_ollama(summary_prompt, model, api_endpoint, timeout, max_retries)
        
        try:
            debug_file = os.path.join(debug_dir, f"llm_executive_summary_{now}.json")
            with open(debug_file, "w", encoding="utf-8") as f:
                json.dump({
                    "prompt": summary_prompt,
                    "llm_response": summary_response,
                    "parsed_evaluations": parsed_evaluations
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save debug data: {e}")
    
        if not summary_response or 'response' not in summary_response:
            raise ValueError("Invalid response from executive summary LLM query")
        
         # Parse executive summary JSON
        executive_summary = parse_executive_summary_llm_response(summary_response)
        if executive_summary:
            print("✓ Executive summary generated and parsed successfully")
            print(f"[DEBUG] Executive summary content:\n{json.dumps(executive_summary, indent=2, ensure_ascii=False)}")
        else:
            print("✗ Failed to parse executive summary")

        evaluations = parsed_evaluations.get("evaluations", [])
        
        # Apply post-processing for inventory-aware ranking if enabled
        if apply_post_ranking and evaluations:
            print("Applying inventory-aware post-processing...")
            evaluations = apply_inventory_aware_ranking(evaluations, results)
        
        return {
            "query": query,
            "search_type": search_type,
            "model_used": model,
            "evaluations": evaluations,
            "ranking_summary": parsed_evaluations.get("ranking_summary", ""),
            "inventory_aware_ranking_applied": apply_post_ranking,
            "status": "success",
            "executive_summary": executive_summary
        }
    else:
        return {
            "query": query,
            "search_type": search_type,
            "model_used": model,
            "evaluations": [],
            "inventory_aware_ranking_applied": False,
            "status": "error",
            "error": "Failed to parse LLM response"
        }

def parse_executive_summary_llm_response(response: dict) -> Optional[dict]:
    """
    Parses the executive summary LLM response and validates its structure.
    Args:
        response: Raw response from Ollama API
    Returns:
        Parsed summary data or None if parsing failed
    """
    if "error" in response:
        print(f"Error in LLM response: {response['error']}")
        return None

    try:
        generated_text = response.get("response", "")
        print(f"📝 Raw executive summary response length: {len(generated_text)} characters")

        # Step 1: Extract JSON from response
        json_str = extract_json_from_response(generated_text)
        if not json_str:
            print("❌ Could not extract JSON from executive summary response")
            print(f"Response preview: {generated_text[:500]}...")
            return None

        print(f"✅ Extracted JSON ({len(json_str)} chars)")

        # Step 2: Fix common JSON issues
        fixed_json = fix_common_json_issues(json_str)
        print(f"🔧 Applied JSON fixes")

        # Step 3: Try to parse JSON
        try:
            parsed_data = json.loads(fixed_json)
            # Step 4: Validate structure
            if validate_executive_summary_structure(parsed_data):
                print(f"✅ Successfully parsed executive summary")
                return parsed_data
            else:
                print("⚠️ Executive summary structure validation failed")
                return None
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed even after fixes: {e}")
            print(f"Problematic JSON preview: {fixed_json[:300]}...")
            return None

    except Exception as e:
        print(f"Unexpected error in executive summary parsing: {e}")
        return None

def validate_executive_summary_structure(data: dict) -> bool:
    """
    Validates that the parsed data has the expected executive summary structure.
    Args:
        data: Parsed JSON data
    Returns:
        True if structure is valid, False otherwise
    """
    try:
        # Top-level keys
        required_keys = ["business_recommendations", "quality_score", "conversion_likelihood"]
        for key in required_keys:
            if key not in data:
                print(f"Missing required key in executive summary: {key}")
                return False

        # business_recommendations subkeys
        br = data["business_recommendations"]
        br_keys = [
            "relevancy_assessment", "inventory_impact", "customer_satisfaction_risk",
            "key_insights", "recommended_actions"
        ]
        for key in br_keys:
            if key not in br:
                print(f"Missing key in business_recommendations: {key}")
                return False

        # recommended_actions subkeys
        ra = br["recommended_actions"]
        ra_keys = ["promote", "maintain", "demote", "remove", "urgent_action"]
        is_at_least_one_action = False
        for key in ra_keys:
            if key in ra:
                print(f"Missing key in recommended_actions: {key}")
                is_at_least_one_action= True

        return is_at_least_one_action
    except Exception as e:
        print(f"Error in executive summary structure validation: {e}")
        return False
    

# --- Backward Compatibility Function ---
def evaluate_search_results(query: str, results: List[Dict[str, str]], 
                           search_type: Optional[str] = None, 
                           model: str = DEFAULT_MODEL) -> Dict[str, Any]:
    """
    Backward compatible function that calls the enhanced version.
    This maintains compatibility with existing code.
    """
    return evaluate_search_results_with_inventory(
        query, results, search_type, model, apply_post_ranking=True
    )




def validate_prompt_template(template: str, search_type: str) -> Dict[str, Any]:
    """
    Validates the prompt template for common issues.
    
    Args:
        template: The prompt template string
        search_type: The type of search this template is for
        
    Returns:
        Dictionary with validation results
    """
    validation_result = {
        "is_valid": True,
        "warnings": [],
        "errors": [],
        "suggestions": []
    }
    
    # Check for required placeholders
    required_placeholders = ["{query}", "{results_text}", "{search_result_count}", "{search_result_count_minus_one}"]
    for placeholder in required_placeholders:
        if placeholder not in template:
            validation_result["errors"].append(f"Missing required placeholder: {placeholder}")
            validation_result["is_valid"] = False
    
    # Check for JSON format specification
    if "json" not in template.lower():
        validation_result["warnings"].append("Template should specify JSON output format")
    
    # Check for inventory considerations
    if "inventory" not in template.lower():
        validation_result["warnings"].append("Template should include inventory considerations")
    
    # Check for business context
    if "business" not in template.lower():
        validation_result["suggestions"].append("Consider adding business context for better AI understanding")
    
    # Check template length (should be comprehensive but not too verbose)
    if len(template) < 1000:
        validation_result["warnings"].append("Template might be too short for comprehensive evaluation")
    elif len(template) > 5000:
        validation_result["warnings"].append("Template might be too long, consider reducing verbosity")
    
    return validation_result

def test_prompt_generation():
    """Test the prompt generation function with sample data."""
    
    search_types = ["english_word", "part_number", "multiple_terms"]
    
    for search_type in search_types:
        print(f"\n{'='*60}")
        print(f"Testing {search_type} template:")
        print(f"{'='*60}")
        
        # Generate template
        template = get_enhanced_prompt_template(search_type)
        
        # Validate template
        validation = validate_prompt_template(template, search_type)
        
        print(f"Template Length: {len(template)} characters")
        print(f"Validation Status: {'✅ Valid' if validation['is_valid'] else '❌ Invalid'}")
        
        if validation["errors"]:
            print("❌ Errors:")
            for error in validation["errors"]:
                print(f"  - {error}")
        
        if validation["warnings"]:
            print("⚠️ Warnings:")
            for warning in validation["warnings"]:
                print(f"  - {warning}")
        
        if validation["suggestions"]:
            print("💡 Suggestions:")
            for suggestion in validation["suggestions"]:
                print(f"  - {suggestion}")
        
        # Test template formatting
        try:
            sample_query = "test_query"
            sample_results = "Sample result data"
            formatted_template = template.format(query=sample_query, results_text=sample_results)
            print("✅ Template formatting successful")
        except Exception as e:
            print(f"❌ Template formatting failed: {e}")
        
        print(f"\nTemplate Preview (first 200 chars):")
        print(f"{template[:200]}...")

# --- Enhanced Test Function ---
def test_enhanced_evaluation(model: str = DEFAULT_MODEL) -> None:
    """
    Tests the enhanced evaluation functionality with inventory-aware sample data.
    """
    test_cases = [
        {
            "query": "ABCD",
            "search_type": "part_number",
            "results": [
                {
                    "title": "12ABCD - Premium Part",
                    "part_number": "12ABCD",
                    "url": "https://example.com/12abcd",
                    "price": "$45.99",
                    "quantity": "0"  # Out of stock
                },
                {
                    "title": "AAABCD - Compatible Part",
                    "part_number": "AAABCD", 
                    "url": "https://example.com/aaabcd",
                    "price": "$42.99",
                    "quantity": "500"  # High stock
                },
                {
                    "title": "ABCD-ALT - Alternative Part",
                    "part_number": "ABCD-ALT",
                    "url": "https://example.com/abcd-alt", 
                    "price": "$39.99",
                    "quantity": "2"  # Low stock
                }
            ]
        },
        {
            "query": "gasket",
            "search_type": "english_word",
            "results": [
                {
                    "title": "Premium Gasket Set",
                    "part_number": "GSK001",
                    "url": "https://example.com/gsk001",
                    "price": "$25.99",
                    "quantity": "0"
                },
                {
                    "title": "Standard Gasket",
                    "part_number": "GSK002", 
                    "url": "https://example.com/gsk002",
                    "price": "$15.99",
                    "quantity": "150"
                }
            ]
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n{'='*60}")
        print(f"TEST CASE {i+1}: Enhanced evaluation for '{test_case['query']}'")
        print(f"{'='*60}")
        
        # Show original order
        print("Original scraped order:")
        for j, result in enumerate(test_case["results"]):
            print(f"  {j}: {result['title']} - Qty: {result['quantity']}")
        
        # Run enhanced evaluation
        evaluation_result = evaluate_search_results_with_inventory(
            test_case["query"], 
            test_case["results"],
            test_case["search_type"],
            model
        )
        
        print(f"\nEvaluation Status: {evaluation_result['status']}")
        
        if evaluation_result['status'] == 'success':
            print(f"Inventory-aware ranking applied: {evaluation_result['inventory_aware_ranking_applied']}")
            print(f"Ranking summary: {evaluation_result.get('ranking_summary', 'N/A')}")
            
            print("\nFinal ranked results:")
            for eval_item in evaluation_result.get("evaluations", []):
                idx = eval_item.get('result_index', 0)
                original_result = test_case["results"][idx]
                print(f"  Rank {eval_item.get('result_index')}: {original_result['title']}")
                print(f"    Relevance: {eval_item.get('relevance')}")
                print(f"    Inventory: {eval_item.get('inventory_quantity', 'N/A')} ({eval_item.get('inventory_status', 'N/A')})")
                print(f"    Justification: {eval_item.get('justification', 'N/A')}")
                print(f"    Inventory Impact: {eval_item.get('inventory_impact', 'N/A')}")
                print()
        else:
            print(f"Error: {evaluation_result.get('error', 'Unknown error')}")

if __name__ == "__main__":

    # Run the test prompt generation
    print("Testing prompt generation and validation...")
    test_prompt_generation()    
    # Check if Ollama is running
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            available_models = [model["name"] for model in response.json().get("models", [])]
            print(f"Ollama is running. Available models: {available_models}")
            
            if available_models:
                if DEFAULT_MODEL not in available_models:
                    print(f"Warning: Default model '{DEFAULT_MODEL}' not found. Using '{available_models[0]}' instead.")
                    DEFAULT_MODEL = available_models[0]
                
                # Run enhanced test
                test_enhanced_evaluation(DEFAULT_MODEL)
            else:
                print("No models available in Ollama. Please pull a model first.")
        else:
            print(f"Ollama API returned status code {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Ollama: {e}")
        print("Is Ollama running? Start it with 'ollama serve' or install from https://ollama.ai/")