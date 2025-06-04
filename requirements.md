# Agentic E-commerce Search Solution: Requirements Analysis

This document outlines the requirements and scope for the agentic solution designed to search an e-commerce website (tundrafmp.com) and evaluate the relevance of search results using a local Large Language Model (LLM).

## 1. Core Functionality

The system must perform the following actions:
1.  Accept a target website URL and a list of search terms as input.
2.  For each search term, navigate to the website and execute the search.
3.  Extract relevant information from the search results page (e.g., product title, part number, description, URL).
4.  Determine the type of search term (English word, part number, multiple terms).
5.  Send the search term, its type, and the extracted results to a locally running LLM (via Ollama) for relevance evaluation.
6.  Receive and process the LLM's evaluation (relevance score/category and justification).
7.  Compile and present the original search term, the extracted results, and their corresponding relevance evaluations in a structured output format.

## 2. Search Scenarios and Evaluation Criteria

The LLM evaluation logic must adapt based on the type of search term:

*   **Scenario 1: English Word Search**
    *   **Input Example:** "gasket", "bearing", "alternator"
    *   **Goal:** Find products generally matching the word's meaning in an automotive/industrial parts context.
    *   **LLM Evaluation:** Assess if the product results are contextually relevant to the search term. High relevance for direct product matches (e.g., searching "gasket" returns various gaskets), lower relevance for tangential or unrelated items.

*   **Scenario 2: Part Number Search**
    *   **Input Example:** "BK608", "513188", "HB88548"
    *   **Goal:** Find the specific product associated with the given part number (full or partial).
    *   **LLM Evaluation:** Assess the match between the input part number and the part numbers listed in the search results.
        *   **High Relevance:** Exact match of the primary part number.
        *   **Medium Relevance:** Input is a substring of the result's part number, the result's part number is a substring of the input, or the result is identified as a cross-reference/alternative.
        *   **Low Relevance:** No discernible match or relationship found in the part number field or description.

*   **Scenario 3: Multiple Term Search**
    *   **Input Example:** "brake pads toyota camry", "fuel pump assembly ford explorer 2015"
    *   **Goal:** Find products that match the combination of descriptive terms, application details, and potentially part numbers.
    *   **LLM Evaluation:** Assess if the product results satisfy the combination of constraints specified in the search query. High relevance if the product matches most or all key terms (e.g., correct part type for the specified vehicle model/year). Relevance decreases as fewer terms are matched.

## 3. System Components

The solution will likely consist of the following components:

1.  **Input Handler:** Parses user input (URL, search terms, potentially search types).
2.  **Web Scraping Module:** Uses browser automation (e.g., Selenium, Playwright) to interact with the target website, perform searches, and extract structured data from results pages. Must handle potential challenges like dynamic content loading and anti-scraping mechanisms.
3.  **Search Type Classifier (Optional but Recommended):** Analyzes the search term to automatically determine if it's an English word, part number, or multiple terms. Regular expressions and simple heuristics can be used.
4.  **LLM Interaction Module:** Constructs appropriate prompts based on the search type and results, communicates with the local Ollama API endpoint, and retrieves the evaluation.
5.  **Evaluation Processor:** Parses the LLM's response (which might be unstructured text) to extract a standardized relevance score/category and justification.
6.  **Output Generator:** Formats the final results, including the original query, extracted product details, and LLM evaluations, into a user-friendly format (e.g., JSON, CSV).
7.  **Orchestrator/Main Application:** Manages the overall workflow, coordinating the execution of the other components.
8.  **Local LLM Environment:** Requires Ollama installed and a suitable model (e.g., Llama 3, Mistral) downloaded and running.

## 4. Input/Output Formats

*   **System Input:**
    *   `target_url`: String (e.g., "https://www.tundrafmp.com/")
    *   `search_tasks`: List of dictionaries, each containing:
        *   `query`: String (The search term/phrase)
        *   `search_type`: String (Optional: "english_word", "part_number", "multiple_terms". If not provided, the system should attempt classification.)

*   **Intermediate Data (Scraper Output -> LLM Input):**
    *   `query`: String
    *   `search_type`: String
    *   `results`: List of dictionaries, each representing a product:
        *   `title`: String
        *   `part_number`: String (Extracted, may be empty)
        *   `description`: String (Optional, snippet if available)
        *   `url`: String (Link to product page)
        *   `price`: String (Optional)

*   **Intermediate Data (LLM Output -> Evaluation Processor Input):**
    *   Raw text response from the LLM containing relevance assessment and justification for each result.

*   **System Output:**
    *   A JSON file or similar structured format containing a list of evaluated search tasks. Each task includes:
        *   `query`: String
        *   `search_type`: String
        *   `evaluated_results`: List of dictionaries, each containing:
            *   `title`: String
            *   `part_number`: String
            *   `url`: String
            *   `price`: String
            *   `llm_relevance`: String ("High", "Medium", "Low", or similar category)
            *   `llm_justification`: String (Explanation from the LLM)

## 5. Non-Functional Requirements

*   **Technology Stack:** Java preferred, Python acceptable. Use standard libraries for web scraping (Selenium/Playwright), HTTP requests, and JSON/CSV processing.
*   **LLM:** Must integrate with a locally running Ollama instance.
*   **Deployment:** Solution should be deployable on AWS. Infrastructure as Code (IaC) is preferred (e.g., AWS CDK, Terraform, CloudFormation).
*   **Error Handling:** Implement robust error handling for web scraping (e.g., timeouts, element not found) and LLM interaction (e.g., API errors, malformed responses).
*   **Configuration:** Key parameters (target URL, Ollama endpoint, model name) should be configurable.

