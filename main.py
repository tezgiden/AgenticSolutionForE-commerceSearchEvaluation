# Main Orchestrator for Agentic Search Solution

import json
import time
import os
from scraper import setup_driver, scrape_tundra
from llm_evaluator import evaluate_search_results, classify_search_type, DEFAULT_MODEL

# --- Configuration ---
INPUT_SEARCH_TASKS = [
    {"query": "gasket"},
    {"query": "BK608"},
    {"query": "brake pads toyota camry"},
    {"query": "513188"}, # Another part number example
    {"query": "commercial refrigerator"} # Another english word example
]
OUTPUT_FILE = "final_evaluation_results.json"
# Optional: Read tasks from a file instead
# INPUT_FILE = "search_tasks.json"
# Optional: Specify Ollama model
# OLLAMA_MODEL = "mistral"
OLLAMA_MODEL = DEFAULT_MODEL

def run_agentic_search():
    """Runs the end-to-end agentic search and evaluation process."""
    all_final_results = []
    
    # Optional: Load tasks from file
    # search_tasks = []
    # if os.path.exists(INPUT_FILE):
    #     with open(INPUT_FILE, "r") as f:
    #         try:
    #             search_tasks = json.load(f)
    #             print(f"Loaded {len(search_tasks)} tasks from {INPUT_FILE}")
    #         except json.JSONDecodeError:
    #             print(f"Error reading {INPUT_FILE}. Using default tasks.")
    #             search_tasks = INPUT_SEARCH_TASKS
    # else:
    #     print(f"Input file {INPUT_FILE} not found. Using default tasks.")
    search_tasks = INPUT_SEARCH_TASKS

    # Setup WebDriver
    driver = setup_driver()
    if not driver:
        print("Failed to initialize WebDriver. Aborting.")
        return

    try:
        for task in search_tasks:
            query = task.get("query")
            if not query:
                print("Skipping task with no query.")
                continue

            print(f"\n{'='*20} Processing Query: 	{query}	 {'='*20}")

            # 1. Scrape Search Results
            print("--- Step 1: Scraping website --- ")
            scraped_results = scrape_tundra(driver, query)
            if not scraped_results:
                print(f"No results found or error during scraping for 	{query}	. Skipping evaluation.")
                all_final_results.append({
                    "query": query,
                    "status": "scraping_failed",
                    "scraped_results": [],
                    "evaluation": None
                })
                continue
            print(f"--- Step 1: Scraping finished. Found {len(scraped_results)} results. --- ")

            # 2. Evaluate Results with LLM
            print("--- Step 2: Evaluating results with LLM --- ")
            # Determine search type (can be passed explicitly in task if needed)
            search_type = task.get("search_type") or classify_search_type(query)
            
            evaluation = evaluate_search_results(
                query=query,
                results=scraped_results,
                search_type=search_type,
                model=OLLAMA_MODEL
            )
            print(f"--- Step 2: Evaluation finished. Status: {evaluation.get('status')} --- ")

            # Combine results
            all_final_results.append({
                "query": query,
                "status": evaluation.get("status", "unknown"),
                "search_type": search_type,
                "scraped_results": scraped_results,
                "evaluation": evaluation.get("evaluations", [])
            })
            
            # Small delay between tasks
            time.sleep(2)

    finally:
        # Ensure driver is closed
        if driver:
            driver.quit()
            print("\nWebDriver closed.")

    # Save final results
    try:
        with open(OUTPUT_FILE, "w") as f:
            json.dump(all_final_results, f, indent=4)
        print(f"\nFinal results saved to {OUTPUT_FILE}")
    except IOError as e:
        print(f"Error saving results to {OUTPUT_FILE}: {e}")

if __name__ == "__main__":
    print("Starting Agentic Search Solution...")
    run_agentic_search()
    print("Agentic Search Solution finished.")


