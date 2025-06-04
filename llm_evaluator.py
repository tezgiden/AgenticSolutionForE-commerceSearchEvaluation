# LLM Evaluation Module (Python + Ollama)

import json
import requests
import time
import re
from typing import Dict, List, Any, Optional, Union

# --- Configuration ---
OLLAMA_API_ENDPOINT = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "gemma3" #"llama3"  # Change to your preferred model (e.g., "llama3", "mistral", etc.)
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
    # First, normalize spaces
    normalized_query = re.sub(r'\s+', ' ', query).strip()
    
    # Count words (excluding common separators in part numbers)
    words = normalized_query.split()
    
    if len(words) > 1:
        return "multiple_terms"
    
    # Check if it's likely a part number (contains digits or special characters typical in part numbers)
    if re.search(r'[0-9\-/]', query):
        return "part_number"
    
    # Default to english_word for single-word text queries
    return "english_word"

# --- Prompt Templates ---
def get_prompt_template(search_type: str) -> str:
    """
    Returns the appropriate prompt template based on search type.
    
    Args:
        search_type: "english_word", "part_number", or "multiple_terms"
        
    Returns:
        String containing the prompt template
    """
    templates = {
        "english_word": """
Evaluate the relevance of the following search results for the English word query: "{query}".

Search Type: english_word
Criteria: Assess if the product is contextually relevant to the search term "{query}" in an automotive/restaurant supply context. Direct matches (e.g., searching 'gasket' returns gaskets) are High relevance. Related items or accessories might be Medium. Unrelated items are Low.

Results:
{results_text}

Provide your evaluation for each result in JSON format like this:
{{
  "evaluations": [
    {{
      "result_index": 0,
      "relevance": "High|Medium|Low",
      "justification": "Your justification here"
    }},
    ...
  ]
}}
""",
        "part_number": """
Evaluate the relevance of the following search results for the part number query: "{query}".

Search Type: part_number
Criteria: Assess the match between the input part number "{query}" and the part numbers listed in the results.
- High Relevance: Exact match of the primary part number in the 'Part Number' field or clearly in the 'Title'.
- Medium Relevance: Input is a substring of the result's part number, the result's part number is a substring of the input, or the result is explicitly identified as a cross-reference/alternative/compatible part in the title.
- Low Relevance: No discernible match or relationship found in the part number or title.

Results:
{results_text}

Provide your evaluation for each result in JSON format like this:
{{
  "evaluations": [
    {{
      "result_index": 0,
      "relevance": "High|Medium|Low",
      "justification": "Your justification here, mentioning the match type if applicable"
    }},
    ...
  ]
}}
""",
        "multiple_terms": """
Evaluate the relevance of the following search results for the multi-term query: "{query}".

Search Type: multiple_terms
Criteria: Assess if the product result satisfies the combination of key constraints specified in the query "{query}". Consider product type, brand, application details, etc., mentioned in the query. High relevance if the product title/details match most or all key terms. Relevance decreases as fewer terms are matched or if details contradict the query.

Results:
{results_text}

Provide your evaluation for each result in JSON format like this:
{{
  "evaluations": [
    {{
      "result_index": 0,
      "relevance": "High|Medium|Low",
      "justification": "Your justification here, explaining which terms matched or didn't"
    }},
    ...
  ]
}}
"""
    }
    
    return templates.get(search_type, templates["english_word"])  # Default to english_word if type not found

# --- Format Results for Prompt ---
def format_results_for_prompt(results: List[Dict[str, str]]) -> str:
    """
    Formats the scraped results into a text format suitable for the prompt.
    
    Args:
        results: List of dictionaries containing scraped product data
        
    Returns:
        Formatted string of results
    """
    formatted_text = ""
    for i, result in enumerate(results):
        formatted_text += f"Result {i}:\n"
        formatted_text += f"Title: {result.get('title', 'N/A')}\n"
        formatted_text += f"Part Number: {result.get('part_number', 'N/A')}\n"
        formatted_text += f"Price: {result.get('price', 'N/A')}\n"
        formatted_text += f"URL: {result.get('url', 'N/A')}\n"
        formatted_text += "---\n"
    
    return formatted_text

# --- Ollama API Interaction ---
def query_ollama(prompt: str, model: str = DEFAULT_MODEL) -> Dict[str, Any]:
    """
    Sends a prompt to the Ollama API and returns the response.
    
    Args:
        prompt: The prompt text to send to the LLM
        model: The Ollama model to use
        
    Returns:
        Dictionary containing the API response or error information
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False  # Get complete response at once
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                OLLAMA_API_ENDPOINT,
                json=payload,
                timeout=TIMEOUT
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"API error (attempt {attempt+1}/{MAX_RETRIES}): Status {response.status_code}")
                print(f"Response: {response.text}")
                time.sleep(1)  # Wait before retry
                
        except requests.exceptions.RequestException as e:
            print(f"Request failed (attempt {attempt+1}/{MAX_RETRIES}): {e}")
            time.sleep(1)  # Wait before retry
    
    return {"error": f"Failed after {MAX_RETRIES} attempts"}

# --- Parse LLM Response ---
def parse_llm_response(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parses the LLM's response to extract the structured evaluations.
    
    Args:
        response: The raw response from the Ollama API
        
    Returns:
        Dictionary containing the parsed evaluations or None if parsing failed
    """
    if "error" in response:
        print(f"Error in LLM response: {response['error']}")
        return None
    
    try:
        # Extract the generated text from the response
        generated_text = response.get("response", "")
        
        # Find JSON block in the response
        json_match = re.search(r'({[\s\S]*"evaluations"[\s\S]*})', generated_text)
        
        if json_match:
            json_str = json_match.group(1)
            # Parse the JSON
            evaluations = json.loads(json_str)
            return evaluations
        else:
            print("Could not find JSON in LLM response")
            print(f"Raw response: {generated_text}")
            return None
            
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        print(f"Raw response: {response.get('response', '')}")
        return None
    except Exception as e:
        print(f"Unexpected error parsing LLM response: {e}")
        return None

# --- Main Evaluation Function ---
def evaluate_search_results(query: str, results: List[Dict[str, str]], 
                           search_type: Optional[str] = None, model: str = DEFAULT_MODEL) -> Dict[str, Any]:
    """
    Evaluates search results using the Ollama LLM.
    
    Args:
        query: The original search term/phrase
        results: List of dictionaries containing scraped product data
        search_type: Optional type override ("english_word", "part_number", "multiple_terms")
        model: The Ollama model to use
        
    Returns:
        Dictionary containing the evaluation results and metadata
    """
    # Determine search type if not provided
    if search_type is None:
        search_type = classify_search_type(query)
    
    print(f"Evaluating query: '{query}' (Type: {search_type})")
    
    # Get appropriate prompt template and format results
    prompt_template = get_prompt_template(search_type)
    results_text = format_results_for_prompt(results)
    
    # Fill in the prompt template
    prompt = prompt_template.format(query=query, results_text=results_text)
    
    # Query the LLM
    llm_response = query_ollama(prompt, model)
    
    # Parse the response
    parsed_evaluations = parse_llm_response(llm_response)
    
    if parsed_evaluations:
        return {
            "query": query,
            "search_type": search_type,
            "model_used": model,
            "evaluations": parsed_evaluations.get("evaluations", []),
            "status": "success"
        }
    else:
        return {
            "query": query,
            "search_type": search_type,
            "model_used": model,
            "evaluations": [],
            "status": "error",
            "error": "Failed to parse LLM response"
        }

# --- Test Function ---
def test_evaluation(model: str = DEFAULT_MODEL) -> None:
    """
    Tests the evaluation functionality with sample data.
    
    Args:
        model: The Ollama model to use
    """
    # Sample data for testing
    test_cases = [
        {
            "query": "gasket",
            "search_type": "english_word",
            "results": [
                {
                    "title": "Southbend - 1187010 - Gasket",
                    "part_number": "1187010",
                    "url": "https://www.tundrafmp.com/p/southbend-1187010-gasket/",
                    "price": "$139.40"
                },
                {
                    "title": "Fisher - 10464 - Gasket",
                    "part_number": "10464",
                    "url": "https://www.tundrafmp.com/p/fisher-10464-gasket/",
                    "price": "$14.71"
                }
            ]
        },
        {
            "query": "BK608",
            "search_type": "part_number",
            "results": [
                {
                    "title": "Vulcan - BK608 - Bearing Kit",
                    "part_number": "BK608",
                    "url": "https://www.tundrafmp.com/p/vulcan-bk608-bearing-kit/",
                    "price": "$45.99"
                },
                {
                    "title": "Hobart - BK60-84 - Bearing Kit",
                    "part_number": "BK60-84",
                    "url": "https://www.tundrafmp.com/p/hobart-bk60-84-bearing-kit/",
                    "price": "$52.30"
                }
            ]
        }
    ]
    
    for test_case in test_cases:
        print(f"\n--- Testing evaluation for: {test_case['query']} ---")
        evaluation_result = evaluate_search_results(
            test_case["query"], 
            test_case["results"],
            test_case["search_type"],
            model
        )
        
        print(f"Status: {evaluation_result['status']}")
        if evaluation_result['status'] == 'success':
            print("Evaluations:")
            for eval_item in evaluation_result.get("evaluations", []):
                print(f"  Result {eval_item.get('result_index')}: {eval_item.get('relevance')}")
                print(f"  Justification: {eval_item.get('justification')}")
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
                # Use the first available model if DEFAULT_MODEL is not available
                if DEFAULT_MODEL not in available_models:
                    print(f"Warning: Default model '{DEFAULT_MODEL}' not found. Using '{available_models[0]}' instead.")
                    DEFAULT_MODEL = available_models[0]
                
                # Run test
                test_evaluation(DEFAULT_MODEL)
            else:
                print("No models available in Ollama. Please pull a model first.")
        else:
            print(f"Ollama API returned status code {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Ollama: {e}")
        print("Is Ollama running? Start it with 'ollama serve' or install from https://ollama.ai/")
