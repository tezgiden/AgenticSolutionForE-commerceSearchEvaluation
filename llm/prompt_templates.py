# prompt_templates.py

from typing import Optional, Dict
import json

class PromptTemplateFactory:
    def __init__(self):
        self._templates = self._load_templates()

    def get_prompt(self, search_type: str, query: str = "", result_count: int = 0, initial_response=None) -> str:
        template = self._templates.get(search_type, self._templates["english_word"])
        return template.format(
            query=query,
            search_result_count=result_count,
            search_result_count_minus_one=max(result_count - 1, 0),
            results_text="{{results_text}}",  # Placeholder to be filled later
            initial_llm_response=json.dumps(initial_response or {}, indent=2)
        )

    def _load_templates(self) -> Dict[str, str]:
        # In production, we could load these from .md/.txt files for better manageability.
        return {
            "english_word": self._english_word_template(),
            "part_number": self._part_number_template(),
            "multiple_terms": self._multiple_terms_template(),
            "executive_summary": self._executive_summary_template()
        }

    def _english_word_template(self) -> str:
        return """
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

        **SEARCH QUERY**: "{query}"
        **SEARCH TYPE**: english_word
        ...
        ## RESULTS TO EVALUATE:
        {results_text}
        """

    def _part_number_template(self) -> str:
        return """
        # E-commerce Search Relevance Evaluation: Part Number Query
        ...
        
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
        ...
        ## RESULTS TO EVALUATE:
        {results_text}
        """

    def _multiple_terms_template(self) -> str:
        return """
        You are a JSON generation specialist. Your ONLY task is to output valid JSON evaluating 10 search results.
        ...
        SEARCH QUERY: "{query}"
        
        
SEARCH QUERY: "{query}"

CRITICAL RULES:
1. Output ONLY valid JSON - no other text
2. Must have exactly 10 evaluations (indices 0-9)
3. Use EXACT field names from template
4. Copy titles and part numbers EXACTLY from input data
5. Find "4707q" substring in part numbers or title for relevance scoring

ANALYSIS LOGIC:
- Query terms: ["armada", "4707q"]
- High relevance (8-10): Contains "4707q" in part_number and/or vendor_part_number + "armada" or "4707q" in title + good stock
- Medium relevance (6-7): Contains "4707q" in part number  or vendor_part_number + "armada" or "4707q"  in title + poor/no stock
- Low relevance (1-5): Only "armada" or  "4707q"  matches either in part number or vendor_part_number or title, poor/no stock 

INVENTORY RULES:
- inventory_quantity > 10 → "Available"
- inventory_quantity 1-10 → "Low Stock"
- inventory_quantity = "N/A" or 0 → "Out of Stock"
- "Available", "Low Stock", "Out of Stock" must be used in inventory_status field. DO NOT use anything else to classify the inventory_status.

BUSINESS IMPACT RULES:
Consider:
- Conversion Likelihood**: Will customer purchase this result?
- Customer Satisfaction**: Does this meet search expectations?
- Inventory Efficiency**: Does ranking optimize available stock?
- Brand Trust**: Does result quality maintain platform credibility?

INVENTORY IMPACT RULES:
Analyze how stock levels affect customer experience and conversion. 
Quantity 'N/A' means no stock, 'Low Stock' means limited availability  and 'High Stock' means good availability.
Quantity 'N/A' requires URGENT action to fix inventory issues.


RECOMMENDED ACTION RULES:
- "Promote" → High relevance AND Available in stock. DO NOT promote if stock is low or out of stock  or quantity with 'N/A'. NO EXCEPTIONS.  
- "Maintain" → Medium relevance OR Low stock  
- "Demote" → Low stock AND Medium/Low relevance  
- "Remove" → Out of Stock AND Low relevance
- "Urgent Action" → Critical issues like Out of Stock or quantity with 'N/A'


RELEVANCE SCORE RULES:

### 🎯 **HIGH RELEVANCE (Score: 9-10)**
**Exact Match Criteria (Prioritized Order):**    
1. **Primary Part Number**: Complete character-for-character match in 'part_number' field of all or one of the query terms
2. **Vendor Part Number**: Complete character-for-character match in 'vendor_part_number' field   of all or one of the query terms
3- There must be Available inventory for the product to be considered high relevance."Out of Stock" or quantity with 'N/A'  products are NOT considered High relevance.

**Examples:**
- ✅ Search: "4707Q" → Part Number: "4707Q" (EXACT MATCH)
- ❌ Search: "4707Q" → Part Number: "SDNS-4707Q" (PARTIAL  MATCH- NOT AN EXACT MATCH)
- ✅ Search: "BK608" → Title: "Vulcan BK608 Bearing Kit" (EXACT MATCH in title)

### 🎯 **MEDIUM RELEVANCE (Score: 6-8)**
**Partial Match Criteria:**
1. **Substring Match**: All or one of the query terms is contained within 'part_number' or 'vendor_part_number' or 'Title' (e.g., "4707Q" in "SDNS-4707Q" or "4707Q-AK" in "Armada Brake pad WWAK4707Q-AK12") 
2- There must be Low Stock or Available for the product to be considered Medium relevance. "Out of Stock"  or quantity with 'N/A'  products are NOT considered Medium relevance.

**Examples:**
- ✅ Search: "4707Q" → Part Number: "AK4707Q-AK" (PARTIAL MATCH "4707Q" in "AK4707Q-AK")
- ✅ Search: "BK608" → Title: "Vulcan 12BK608ABC Bearing Kit" (PARTIAL MATCH to "BK608" in title)


### 🎯 **LOW RELEVANCE (Score: 1-5)**
**Weak or No Match:**
1- No match to any of the query terms in part_number, vendor_part_number or title
2- Or there is no stock available for the product

### 🎯 **RELEVANCE TIER, INVENTORY STATUS AND ACTION MAPPING**
| Relevance Tier | Inventory Status | Action        |
| -------------- | ---------------- | ------------- |
| High (9-10)    | Available        | Promote       |
| High (9-10)    | Low Stock        | Maintain      |
| High (9-10)    | Out of Stock/N/A | Remove        |
| Medium (6-8)   | Available        | Maintain      |
| Medium (6-8)   | Low Stock        | Demote        |
| Medium         | Out of Stock/N/A | Remove        |
| Low (1-5)      | Available        | Maintain      |
| Low (1-5)      | Low Stock        | Demote        |
| Low            | Out of Stock/N/A | Remove/Urgent |


EXACT JSON TEMPLATE TO FILL:
{{{{
  "search_analysis": {{{{
    "query": "{query}",
    "query_terms": ["armada", "4707q"],
    "total_results": 10,
    "full_matches_found": 0,
    "partial_matches_found": 10,
    "inventory_considerations_applied": true
  }}}},
  "evaluations": [
    {{{{
      "result_index": COPY_RESULT_INDEX_FROM_INPUT,
      "title": "COPY_EXACT_TITLE_FROM_RESULT",
      "inventory_quantity": "COPY_EXACT_INVENTORY/QUANTITY_FROM_RESULT",
      "part_number": "COPY_EXACT_PART_NUMBER",
      "vendor_part_number": "COPY_EXACT_VENDOR_PART_NUMBER",
      "price": "COPY_EXACT_PRICE_FROM_RESULT_0",
      "relevance_tier": "Medium",
      "relevance_score": "7",
      "terms_matched": ["armada", "4707q"],
      "terms_missing": [],
      "match_quality": "set match_quality to "All Key Terms" if all key terms match, "Some Key Terms" if some key terms match, otherwise "No Key Terms"",
      "contextual_accuracy": "Set contextual_accuracy to "Excellent" if all key terms match, "Good" or "Fair" depending on how many matches we have in all fields, otherwise "Poor". ",
      "inventory_status": "Set inventory_status based on INVENTORY RULES",
      "justification": "4707Q found in vendor part number with armada brand match",
      "inventory_impact": "Write 10-word justification explaining matches.Use BUSINESS IMPACT RULES to set business_impact",
      "business_impact": "Good",
      "recommended_action": "Promote"
    }}}},
  ],
  "ranking_summary": "All results show armada brand with 4707Q pattern matches",
  "quality_score": "7",
  "conversion_likelihood": "Medium"
}}}}

STEP-BY-STEP PROCESS:
1. Copy JSON template above
2. For each result 0-9:
   - Copy EXACT title from input
   - Copy EXACT part_number from input  
   - Copy EXACT vendor_part_number from input if available or set it to "N/A"
   - Copy EXACT inventory_quantity from input set it to "N/A" if not available or not parsable or "N/A"
   - Check if vendor_part_number contains "4707q" (case insensitive)
   - Check if title contains "armada" (case insensitive)
   - Check if part_number contains "armada" or "4707q" (case insensitive)
   - Use BUSINESS IMPACT RULES to set business_impact
   - Use RECOMMENDED ACTION RULES to set recommended_action
   - Use INVENTORY IMPACT RULES to set inventory_impact
   - Set inventory_status based on INVENTORY RULES
   - Set terms_missing: list of any query terms not found in title, part_number, or vendor_part_number
   - Set terms_matched: list of query terms found in title or part_number or vendor_part_number
   - set match_quality to "All Key Terms" if all key terms match, "Some Key Terms" if some key terms match, otherwise "No Key Terms"
   - Set numeric relevance_score based on RELEVANCE SCORE RULES:
   - Set text relevance_tier based on RELEVANCE SCORE RULES:
   - Write 10-word justification explaining matches
   - Set contextual_accuracy to "Excellent" if all key terms match, "Good" or "Fair" depending on how many matches we have in all fields, otherwise "Poor". 
3. Populate the "ranking_summary", "quality_score", and "conversion_likelihood" fields based on overall evaluation.
4. Validate JSON syntax
5. Count evaluations array = 10

VALIDATION CHECKLIST:
□ Exactly 10 items in evaluations array
□ All field names match template exactly
□ No extra fields added
□ All titles/part numbers copied exactly from input
□ Valid JSON syntax with proper commas and brackets
□ All required fields present in each evaluation

COMMON ERRORS TO AVOID:
- DO NOT add extra fields like "manufacturer_part_number", "description", "price"
- DO NOT make up data - copy exactly from input- 
- DO NOT ASSUME MEANING OR MATCH FROM IT. If a field is EMPTY or "N/A", treat it as MISSING. 
- DO NOT use "..." or skip entries
- DO NOT have trailing commas
- DO NOT mix up data between different results

START WITH RESULT 0 DATA:
Title: "Armada Brake Shoe Reman"
Part Number: "LS4707QPAR23P" 
Vendor Part Number: "4707QPAR23P"
Inventory: 518

Analysis: "4707Q" appears in "4707QPAR23P" → High match with good stock

        ## RESULTS TO EVALUATE:
        {results_text}
        """

    def _executive_summary_template(self) -> str:
        return """
        # Executive Summary Generation for E-commerce Search Analysis

        **SEARCH QUERY ANALYZED**: "{query}"
        You are an expert e-commerce analyst tasked with creating a concise executive summary based on the search relevance analysis below.

**SEARCH QUERY ANALYZED**: "{Query}"
**INITIAL ANALYSIS RESULTS**:
{json.dumps(initial_llm_response, indent=2)}

## INSTRUCTIONS

Generate a comprehensive business recommendations summary in the EXACT JSON format specified below. Focus on:

1. **Relevancy Assessment**: Evaluate overall match quality (High if exact matches exist, Medium for good partial matches, Low for poor matches)
2. **Inventory Impact**: Analyze how stock levels affect customer experience and conversion. Quantity 'N/A' means no stock, 'Low Stock' means limited availability, 'Medium Stock' means some availability, and 'High Stock' means good availability.
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

        **INITIAL ANALYSIS RESULTS**:
        {initial_llm_response}

        ## REQUIRED OUTPUT FORMAT
        ...
        """
