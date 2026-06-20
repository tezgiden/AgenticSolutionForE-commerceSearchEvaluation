# TruckPro Search Evaluation Plan

## Overview

This document outlines the plan to evaluate TruckPro search quality across two environments:
- **PROD**: `search-ecprodauth.truckpro.com`
- **PERF**: `search.tpdevauth.truckpro.com`

Base API endpoint pattern:
```
/search/resources/api/v2/products?langId=-1&storeId=10151&profileName=X_findProductsBySearchTerm&landingPage=true&searchSource=E&offset=0&searchTerm={TERM}&catalogId=10101&limit=15&searchType=100
```

---

## Search Terms and Expected Results (from TP Search Tuning doc)

The following search terms are extracted from the "Search Terms and Analysis" section of the TP Search Tuning document. Note: the document is dated and some expected results may have changed due to data/catalog updates. PROD AUTH results serve as the current baseline.

### Part Number Searches

| # | Search Term | Type | PROD AUTH Expected Top Results | PROD AUTH Total Count | Tolerance | Notes |
|---|-------------|------|-------------------------------|----------------------|-----------|-------|
| 1 | `4707Q` | part_number | SDWK4707QVHP1, BK4707QPAR2, LS4707QPEN | 426 | 50 | Partial match on SKU containing "4707Q" |
| 2 | `BK4707` | part_number | BK4707QPV23, BK4707QPAR1, BK4707QPFS20 | 45 | 5 | Armada Brake Shoe Kit Reman parts |
| 3 | `B7177` | part_number | BAB7177, DNP550428, DNP551019 | 5 | 2 | Cross-reference matches expected |
| 4 | `BK4515` | part_number | BK4515X3AR2, BK4515QAR1, BK4515QV23 | 69 | 10 | Results starting with BK4515 in part number |
| 5 | `VS17573T` | part_number | VS17-573T | 1 | 0 | Exact match with special char handling |
| 6 | `TQ16010` | part_number | TQ16010 | 1 | 0 | Single exact match expected |
| 7 | `HFK-3539` | part_number | HFK-3539 | 1 | 0 | Exact match with hyphen |
| 8 | `K-2924` | part_number | HFK-2924, HFK-2924M, HFK-2924NSM | 14 | 2 | Hyphen/special char handling |
| 9 | `K2924` | part_number | K-2924, CRSTK2924, TBTRK2924 | 14 | 2 | Should return same results as K-2924 |
| 10 | `308925-25` | part_number | SC308925-25, IANMU898-147-6 | 4 | 0 | Hyphen handling in part numbers |
| 11 | `3529900C98` | part_number | 3529900C98, RQ888-5125 | 2 | 0 | Cross-reference to rq888-5125 (known defect ENHV1-5900) |

### Multiple Terms Searches

| # | Search Term | Type | PROD AUTH Expected Top Results | PROD AUTH Total Count | Tolerance | Notes |
|---|-------------|------|-------------------------------|----------------------|-----------|-------|
| 12 | `armada 4707q` | multiple_terms | BK4707QPAR2, LS4707QPEN, BK4707QPAR23P, BK4707QPV23 | 129 | 20 | Armada brand + 4707Q part; Armada products should rank first |
| 13 | `gunite 1140` | multiple_terms | GUAS1140, GUAS1141, GUAS1132 | 166 | 10 | GUAS1140 should be the top result (known defect ENHV1-5901) |
| 14 | `Armada Battery` | multiple_terms | DB850-58R, DB1050-4D, DB950-31P | 180 | 20 | Brand + category search |

### English Word / Category Searches

| # | Search Term | Type | PROD AUTH Expected Top Results | PROD AUTH Total Count | Tolerance | Notes |
|---|-------------|------|-------------------------------|----------------------|-----------|-------|
| 15 | `truck-lite` | english_word | TK80255C3, TK37640C, TK33050Y3 | 3479 | 400 | Brand search with hyphen |
| 16 | `trucklite` | english_word | TK07092, TK30250R3, TK3050-P | 3479 | 400 | Should return same results as truck-lite (known defect ENHV1-5902) |
| 17 | `air drier` | english_word | EX109493PG, ML109493X, ML109994K | 1228 | 200 | Synonym handling: drier vs dryer |
| 18 | `air dryer` | english_word | EX109493PG, ML109493X, ML109994K | 1228 | - | Should return equivalent results to "air drier" |
| 19 | `gladhand seal` | english_word | TC16010, TC16110, TC16015, TC16013 | 92 | 50 | Stemming test |
| 20 | `gladhand seals` | english_word | TC16010, TC16110, TC16015, TC16013 | 85 | 5 | Should match "gladhand seal" (stemming) |
| 21 | `glad hand seal` | english_word | HRGAFF17676, HRGAFF17674 | 12 | 2 | Synonym test (known defect ENHV1-5912) |
| 22 | `Brake Drum` | english_word | WE63680F32, DU60611, DU61353, WE56864B | - | - | Relevance ordering test; partial SKU matches should not outrank actual brake drums |
| 23 | `brake chamber` | english_word | TVTR24SC, MM3531851X, TVTR3030C | - | - | Category-level match; products in brake chamber L2 category |
| 24 | `Wheel nut` | english_word | HQH-150, HQH-185, CG111 | 946 | 100 | Top selling items in Wheel Nut L2 category |
| 25 | `air spring` | english_word | VX8709, VX8864, VX8050 | - | - | Description match expected |
| 26 | `Vent, Axle, Tire Inflation, Intraax/Vantraax` | english_word | HNVS-32101 | 1 | 0 | Long product name search (known defect ENHV1-5911) |

---

## Key Search Behaviors to Evaluate

These are the high-level search quality dimensions from the TP Search Tuning document:

1. **Exact Match Priority**: Products with exact part number matches should always rank highest (boosted by EXACT_MATCH_FIELDS with scores up to 200 for vendor SKU, 180 for SKU, 140 for manufacturer).

2. **Partial/Substring Match**: When query is a substring of a part number (e.g., "4707Q" in "NK4707QPEX"), results should appear but ranked lower than exact matches.

3. **Cross-Reference Resolution**: Searching for a cross-reference number (e.g., "3529900C98") should return the primary product (e.g., "RQ888-5125").

4. **Special Character Handling**: Hyphens, periods, and other special characters should be normalized. "K-2924" and "K2924" should return the same results.

5. **Multi-Word Relevance**: For queries like "armada 4707q", products matching BOTH terms should rank higher than those matching only one term. Brand matches should influence ranking.

6. **Synonym/Stemming**: "air drier" and "air dryer" should return equivalent results. "gladhand seal" and "gladhand seals" should return the same results.

7. **Category/Keyword Match**: For generic terms like "Brake Drum", actual brake drum products should rank above products that merely contain "drum" in an unrelated SKU (e.g., NPGDRUM828-WD is a pig drum cover, not a brake drum).

8. **TP Ranking Influence**: Sales-based ranking (TP_tpranking 0-12) should boost popular products within the same relevance tier.

---

## Evaluation Methodology

### Step 1: Data Collection
For each of the 26 search terms above, call both environments:
- **PROD**: `https://search-ecprodauth.truckpro.com/search/resources/api/v2/products?...&searchTerm={TERM}&limit=15`
- **PERF**: `https://search.tpdevauth.truckpro.com/search/resources/api/v2/products?...&searchTerm={TERM}&limit=15`

Capture the top 15 results from each, extracting: SKU, product name, part number, vendor part number, price, and any available inventory/ranking data.

### Step 2: PERF Standalone Evaluation
For each search term, evaluate whether the PERF top 15 results "make sense":
- Do expected products (from baseline) appear in top 15?
- Is the ranking order logical for the query type?
- Are there irrelevant results that should not be there?

### Step 3: PROD vs PERF Comparison
For each search term, compare PERF against PROD baseline:
- Which expected products are present in both, only in PROD, or only in PERF?
- How does ranking order differ?
- Total result count comparison (within tolerance?)
- Which environment produces a "better" result set and why?

### Step 4: Summary Report
Aggregate findings into:
- Per-query scorecards
- Overall quality comparison (PROD vs PERF)
- Specific regressions or improvements in PERF
- Actionable recommendations

---

## LLM Judge Recommendation

### Options Considered

| Option | Cost | JSON Reliability | Judgment Quality | Speed per Query | Total Time (est.) |
|--------|------|-----------------|-----------------|-----------------|-------------------|
| **Ollama gemma3** (local) | Free | Poor (needs json_fixer) | Inconsistent for nuanced comparison | 60-120s | 1-2 hours |
| **Claude Haiku 4.5** (API) | ~$0.50 total | Excellent | Strong reasoning, reliable | 2-5s | 2-3 minutes |
| **Claude Sonnet 4.6** (API) | ~$5-10 total | Excellent | Best judgment quality | 3-8s | 5-8 minutes |

### Token Estimate
- 26 search terms x 2 environments = 52 API calls for evaluation
- 26 comparison calls = 26 additional calls
- ~78 total calls x ~7K tokens/call = ~550K tokens
- Haiku 4.5: ~$0.50 total
- Sonnet 4.6: ~$8 total

### Recommendation: Claude Haiku 4.5

**Rationale:**
1. **Cost-effective**: Under $1 for the entire evaluation suite
2. **Reliable JSON**: Eliminates the json_fixer/response_parser workarounds needed for gemma3
3. **Consistent judgment**: The comparison task (PROD vs PERF) requires nuanced reasoning about why one ranking is "better" -- gemma3 struggles with this based on commit history
4. **Fast iteration**: 2-3 minutes total vs 1-2 hours with Ollama, enabling rapid re-runs during tuning
5. **Fallback**: Ollama can remain as an offline/free fallback option; the judge can be made configurable

If budget is a non-concern and maximum judgment quality is desired, Sonnet 4.6 would be the upgrade path for ~$8 total.
