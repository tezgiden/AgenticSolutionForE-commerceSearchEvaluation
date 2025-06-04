# LLM Prompts for Search Result Evaluation

This document outlines the prompts designed for the local LLM (via Ollama) to evaluate the relevance of search results scraped from tundrafmp.com based on the original search query and its type.

**General Instructions for LLM:**

You are an AI assistant evaluating the relevance of e-commerce search results from an automotive/restaurant supply website (tundrafmp.com). You will be given the original search query, the type of query (english_word, part_number, or multiple_terms), and a list of search results. For each result, provide a relevance assessment (High, Medium, Low) and a brief justification based on the criteria for the given query type. Structure your response clearly for each result.

**Input Format (Sent to LLM):**
```json
{
  "query": "[Original Search Query]",
  "search_type": "[english_word | part_number | multiple_terms]",
  "results": [
    {
      "title": "[Product Title]",
      "part_number": "[Extracted Part Number/SKU]",
      "url": "[Product URL]",
      "price": "[Product Price]"
      // Potentially add description snippet if scraped later
    },
    // ... more results
  ]
}
```

**Expected Output Format (From LLM):**
```json
{
  "evaluations": [
    {
      "result_index": 0, // Corresponds to the index in the input results list
      "relevance": "[High | Medium | Low]",
      "justification": "[Brief explanation for the relevance score]"
    },
    // ... more evaluations
  ]
}
```
*(Note: Requesting JSON output directly from the LLM simplifies parsing. If the LLM struggles with strict JSON, a structured text format might be needed, requiring more complex parsing.)*

---

## Prompt Template 1: English Word Search

**Context:** The user searched for a general English word related to parts or supplies.
**Goal:** Evaluate if the results are contextually relevant products matching the word's meaning.

**Prompt:**
```
Evaluate the relevance of the following search results for the English word query: "{{query}}".

Search Type: english_word
Criteria: Assess if the product is contextually relevant to the search term "{{query}}" in an automotive/restaurant supply context. Direct matches (e.g., searching 'gasket' returns gaskets) are High relevance. Related items or accessories might be Medium. Unrelated items are Low.

Results:
{{#results}}
Result {{index}}:
Title: {{title}}
Part Number: {{part_number}}
Price: {{price}}
URL: {{url}}
---
{{/results}}

Provide your evaluation for each result in JSON format like this:
{
  "evaluations": [
    {
      "result_index": 0,
      "relevance": "[High | Medium | Low]",
      "justification": "[Your justification here]"
    },
    // ... more evaluations for other results
  ]
}
```

---

## Prompt Template 2: Part Number Search

**Context:** The user searched for a specific part number (full or partial).
**Goal:** Evaluate if the results match the provided part number.

**Prompt:**
```
Evaluate the relevance of the following search results for the part number query: "{{query}}".

Search Type: part_number
Criteria: Assess the match between the input part number "{{query}}" and the part numbers listed in the results.
- High Relevance: Exact match of the primary part number in the 'Part Number' field or clearly in the 'Title'.
- Medium Relevance: Input is a substring of the result's part number, the result's part number is a substring of the input, or the result is explicitly identified as a cross-reference/alternative/compatible part in the title.
- Low Relevance: No discernible match or relationship found in the part number or title.

Results:
{{#results}}
Result {{index}}:
Title: {{title}}
Part Number: {{part_number}}
Price: {{price}}
URL: {{url}}
---
{{/results}}

Provide your evaluation for each result in JSON format like this:
{
  "evaluations": [
    {
      "result_index": 0,
      "relevance": "[High | Medium | Low]",
      "justification": "[Your justification here, mentioning the match type if applicable]"
    },
    // ... more evaluations for other results
  ]
}
```

---

## Prompt Template 3: Multiple Term Search

**Context:** The user searched using multiple terms, potentially including product type, brand, application details (like vehicle model/year), etc.
**Goal:** Evaluate if the results satisfy the combination of constraints in the query.

**Prompt:**
```
Evaluate the relevance of the following search results for the multi-term query: "{{query}}".

Search Type: multiple_terms
Criteria: Assess if the product result satisfies the combination of key constraints specified in the query "{{query}}". Consider product type, brand, application details, etc., mentioned in the query. High relevance if the product title/details match most or all key terms. Relevance decreases as fewer terms are matched or if details contradict the query.

Results:
{{#results}}
Result {{index}}:
Title: {{title}}
Part Number: {{part_number}}
Price: {{price}}
URL: {{url}}
---
{{/results}}

Provide your evaluation for each result in JSON format like this:
{
  "evaluations": [
    {
      "result_index": 0,
      "relevance": "[High | Medium | Low]",
      "justification": "[Your justification here, explaining which terms matched or didn't]"
    },
    // ... more evaluations for other results
  ]
}
```

