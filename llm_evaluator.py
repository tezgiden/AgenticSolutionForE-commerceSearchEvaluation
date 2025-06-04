# Enhanced LLM Evaluation Module with Inventory-Aware Ranking

import json
import requests
import time
import re
from typing import Dict, List, Any, Optional, Union, Tuple

# --- Configuration ---
OLLAMA_API_ENDPOINT = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "gemma3"  # Change to your preferred model
TIMEOUT = 120  # Seconds to wait for Ollama response
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
def get_enhanced_prompt_template(search_type: str) -> str:
    """
    Returns the enhanced prompt template with inventory consideration based on search type.
    
    Args:
        search_type: "english_word", "part_number", or "multiple_terms"
        
    Returns:
        String containing the enhanced prompt template
    """
    base_inventory_instruction = """
IMPORTANT INVENTORY CONSIDERATION:
When products have the same relevance level, prioritize those with higher available inventory/quantity.
- If two products both have "High" relevance, the one with more inventory should be ranked higher
- Only consider inventory as a tie-breaker when relevance levels are equal
- Products with 0 inventory should be ranked lower than those with available stock, even within the same relevance category
"""

    templates = {
        "english_word": f"""
Evaluate the relevance of the following search results for the English word query: "{{query}}".

Search Type: english_word
Criteria: Assess if the product is contextually relevant to the search term "{{query}}" in an automotive/restaurant supply context. Direct matches (e.g., searching 'gasket' returns gaskets) are High relevance. Related items or accessories might be Medium. Unrelated items are Low.

{base_inventory_instruction}

Results:
{{results_text}}

Provide your evaluation for each result in JSON format. Include both relevance and inventory considerations:
{{{{
  "evaluations": [
    {{{{
      "result_index": 0,
      "relevance": "High|Medium|Low",
      "inventory_status": "Available|Low Stock|Out of Stock",
      "inventory_quantity": "parsed quantity or 'N/A'",
      "justification": "Your justification here, including inventory consideration if applicable",
      "inventory_impact": "Whether inventory affected the ranking within the same relevance tier"
    }}}},
    ...
  ],
  "ranking_summary": "Brief explanation of how inventory influenced the final ranking"
}}}}
""",
        "part_number": f"""
Evaluate the relevance of the following search results for the part number query: "{{query}}".

Search Type: part_number
Criteria: Assess the match between the input part number "{{query}}" and the part numbers listed in the results.
- High Relevance: Exact match of the primary part number in the 'Part Number' field or clearly in the 'Title'.
- Medium Relevance: Input is a substring of the result's part number, the result's part number is a substring of the input, or the result is explicitly identified as a cross-reference/alternative/compatible part in the title.
- Low Relevance: No discernible match or relationship found in the part number or title.

{base_inventory_instruction}

Results:
{{results_text}}

Provide your evaluation for each result in JSON format. Include both relevance and inventory considerations:
{{{{
  "evaluations": [
    {{{{
      "result_index": 0,
      "relevance": "High|Medium|Low",
      "inventory_status": "Available|Low Stock|Out of Stock",
      "inventory_quantity": "parsed quantity or 'N/A'",
      "justification": "Your justification here, mentioning the match type and inventory consideration if applicable",
      "inventory_impact": "Whether inventory affected the ranking within the same relevance tier"
    }}}},
    ...
  ],
  "ranking_summary": "Brief explanation of how inventory influenced the final ranking"
}}}}
""",
        "multiple_terms": f"""
Evaluate the relevance of the following search results for the multi-term query: "{{query}}".

Search Type: multiple_terms
Criteria: Assess if the product result satisfies the combination of key constraints specified in the query "{{query}}". Consider product type, brand, application details, etc., mentioned in the query. High relevance if the product title/details match most or all key terms. Relevance decreases as fewer terms are matched or if details contradict the query.

{base_inventory_instruction}

Results:
{{results_text}}

Provide your evaluation for each result in JSON format. Include both relevance and inventory considerations:
{{{{
  "evaluations": [
    {{{{
      "result_index": 0,
      "relevance": "High|Medium|Low",
      "inventory_status": "Available|Low Stock|Out of Stock",
      "inventory_quantity": "parsed quantity or 'N/A'",
      "justification": "Your justification here, explaining which terms matched and inventory consideration if applicable",
      "inventory_impact": "Whether inventory affected the ranking within the same relevance tier"
    }}}},
    ...
  ],
  "ranking_summary": "Brief explanation of how inventory influenced the final ranking"
}}}}
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
        formatted_text += f"Price: {result.get('price', 'N/A')}\n"
        
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
    if any(term in quantity_lower for term in ['out of stock', 'unavailable', '0']):
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
    
    return reordered_evaluations

# --- Ollama API Interaction with Configuration Support ---
def query_ollama(prompt: str, model: str = DEFAULT_MODEL, api_endpoint: str = OLLAMA_API_ENDPOINT, 
                timeout: int = TIMEOUT, max_retries: int = MAX_RETRIES) -> Dict[str, Any]:
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

# --- Enhanced LLM Response Parsing ---
def parse_enhanced_llm_response(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parses the enhanced LLM response including inventory considerations.
    """
    if "error" in response:
        print(f"Error in LLM response: {response['error']}")
        return None
    
    try:
        generated_text = response.get("response", "")
        
        # Find JSON block in the response (more flexible pattern)
        json_match = re.search(r'({[\s\S]*?"evaluations"[\s\S]*?})', generated_text, re.DOTALL)
        
        if json_match:
            json_str = json_match.group(1)
            # Clean up potential formatting issues
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)  # Remove trailing commas
            
            evaluations = json.loads(json_str)
            return evaluations
        else:
            print("Could not find JSON in LLM response")
            print(f"Raw response: {generated_text[:500]}...")  # Truncate for readability
            return None
            
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        print(f"Raw response: {response.get('response', '')[:500]}...")
        return None
    except Exception as e:
        print(f"Unexpected error parsing LLM response: {e}")
        return None

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
    prompt = prompt_template.format(query=query, results_text=results_text)
    
    # Query the LLM with configuration parameters
    llm_response = query_ollama(prompt, model, api_endpoint, timeout, max_retries)
    
    # Parse the enhanced response
    parsed_evaluations = parse_enhanced_llm_response(llm_response)
    
    if parsed_evaluations:
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
            "status": "success"
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