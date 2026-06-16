"""
TruckPro Search Evaluation Pipeline

Compares search results between PROD and PERF environments using Claude Haiku as judge.

Usage:
    python scripts/tp_search_eval.py                    # Run full evaluation
    python scripts/tp_search_eval.py --collect-only      # Only collect API results, skip LLM eval
    python scripts/tp_search_eval.py --eval-only         # Only evaluate (uses cached results)
    python scripts/tp_search_eval.py --terms "4707Q,BK4707"  # Run specific terms only
"""

import os
import sys
import json
import time
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict

import requests
import urllib3
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Suppress InsecureRequestWarning for PERF env (self-signed cert)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROD_BASE = "https://search-ecprodauth.truckpro.com"
PERF_BASE = "https://search.tpdevauth.truckpro.com"

API_PATH = (
    "/search/resources/api/v2/products"
    "?langId=-1&storeId=10151"
    "&profileName=X_findProductsBySearchTerm"
    "&landingPage=true&searchSource=E&offset=0"
    "&catalogId=10101&limit=15&searchType=100"
)

CLAUDE_MODEL = "claude-haiku-4-5-20251001"
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "analysis_result")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("tp_search_eval")

# ---------------------------------------------------------------------------
# Search term definitions (from TP Search Tuning doc)
# ---------------------------------------------------------------------------

@dataclass
class SearchTermDef:
    term: str
    search_type: str  # part_number | multiple_terms | english_word
    expected_top_skus: List[str] = field(default_factory=list)
    expected_total_count: Optional[int] = None
    count_tolerance: Optional[int] = None
    notes: str = ""


SEARCH_TERMS: List[SearchTermDef] = [
    # Part number searches
    SearchTermDef("4707Q", "part_number",
                  ["SDWK4707QVHP1", "BK4707QPAR2", "LS4707QPEN"], 426, 50),
    SearchTermDef("BK4707", "part_number",
                  ["BK4707QPV23", "BK4707QPAR1", "BK4707QPFS20"], 45, 5),
    SearchTermDef("B7177", "part_number",
                  ["BAB7177", "DNP550428", "DNP551019"], 5, 2,
                  "Cross-reference matches expected"),
    SearchTermDef("BK4515", "part_number",
                  ["BK4515X3AR2", "BK4515QAR1", "BK4515QV23"], 69, 10),
    SearchTermDef("VS17573T", "part_number",
                  ["VS17-573T"], 1, 0, "Exact match with special char"),
    SearchTermDef("TQ16010", "part_number",
                  ["TQ16010"], 1, 0, "Single exact match"),
    SearchTermDef("HFK-3539", "part_number",
                  ["HFK-3539"], 1, 0, "Exact match with hyphen"),
    SearchTermDef("K-2924", "part_number",
                  ["HFK-2924", "HFK-2924M", "HFK-2924NSM"], 14, 2,
                  "Special char handling"),
    SearchTermDef("K2924", "part_number",
                  ["K-2924", "CRSTK2924", "TBTRK2924"], 14, 2,
                  "Should match K-2924 results"),
    SearchTermDef("308925-25", "part_number",
                  ["SC308925-25", "IANMU898-147-6"], 4, 0,
                  "Hyphen handling"),
    SearchTermDef("3529900C98", "part_number",
                  ["3529900C98", "RQ888-5125"], 2, 0,
                  "Cross-reference to rq888-5125"),

    # Multiple terms searches
    SearchTermDef("armada 4707q", "multiple_terms",
                  ["BK4707QPAR2", "LS4707QPEN", "BK4707QPAR23P", "BK4707QPV23"], 129, 20,
                  "Armada brand should rank first"),
    SearchTermDef("gunite 1140", "multiple_terms",
                  ["GUAS1140", "GUAS1141", "GUAS1132"], 166, 10,
                  "GUAS1140 should be top result"),
    SearchTermDef("Armada Battery", "multiple_terms",
                  ["DB850-58R", "DB1050-4D", "DB950-31P"], 180, 20),

    # English word / category searches
    SearchTermDef("truck-lite", "english_word",
                  ["TK80255C3", "TK37640C", "TK33050Y3"], 3479, 400,
                  "Brand search with hyphen"),
    SearchTermDef("trucklite", "english_word",
                  ["TK07092", "TK30250R3", "TK3050-P"], 3479, 400,
                  "Should match truck-lite results"),
    SearchTermDef("air drier", "english_word",
                  ["EX109493PG", "ML109493X", "ML109994K"], 1228, 200,
                  "Synonym: drier vs dryer"),
    SearchTermDef("air dryer", "english_word",
                  ["EX109493PG", "ML109493X", "ML109994K"], 1228, None,
                  "Should match air drier"),
    SearchTermDef("gladhand seal", "english_word",
                  ["TC16010", "TC16110", "TC16015", "TC16013"], 92, 50),
    SearchTermDef("gladhand seals", "english_word",
                  ["TC16010", "TC16110", "TC16015", "TC16013"], 85, 5,
                  "Stemming: should match gladhand seal"),
    SearchTermDef("glad hand seal", "english_word",
                  ["HRGAFF17676", "HRGAFF17674"], 12, 2,
                  "Synonym test"),
    SearchTermDef("Brake Drum", "english_word",
                  ["WE63680F32", "DU60611", "DU61353", "WE56864B"], None, None,
                  "Relevance ordering: actual brake drums should rank above partial SKU matches"),
    SearchTermDef("brake chamber", "english_word",
                  ["TVTR24SC", "MM3531851X", "TVTR3030C"], None, None,
                  "Category-level match"),
    SearchTermDef("Wheel nut", "english_word",
                  ["HQH-150", "HQH-185", "CG111"], 946, 100),
    SearchTermDef("air spring", "english_word",
                  ["VX8709", "VX8864", "VX8050"], None, None,
                  "Description match expected"),
    SearchTermDef("Vent, Axle, Tire Inflation, Intraax/Vantraax", "english_word",
                  ["HNVS-32101"], 1, 0,
                  "Long product name search"),
]


# ---------------------------------------------------------------------------
# API collection
# ---------------------------------------------------------------------------

def build_search_url(base_url: str, search_term: str) -> str:
    return f"{base_url}{API_PATH}&searchTerm={requests.utils.quote(search_term)}"


def fetch_search_results(base_url: str, search_term: str, timeout: int = 30) -> Dict[str, Any]:
    """Call the TruckPro search API and return raw JSON."""
    url = build_search_url(base_url, search_term)
    is_perf = "tpdevauth" in base_url
    log.info(f"  Fetching: {'PERF' if is_perf else 'PROD'} | term='{search_term}'")
    try:
        resp = requests.get(url, timeout=timeout, verify=(not is_perf), headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        })
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        log.error(f"  API error for '{search_term}' on {'PERF' if is_perf else 'PROD'}: {e}")
        return {"error": str(e)}


def extract_products(raw: Dict[str, Any]) -> tuple:
    """Extract a normalized product list from the raw API response.

    The TruckPro search API returns data in the ``contents`` array with
    ``total`` as the overall match count.  Attribute values are exposed
    both as top-level ``custom.attribute.<id>.raw`` fields and inside the
    nested ``attributes`` list.
    """
    products = []
    entries = raw.get("contents", [])
    total_count = raw.get("total", 0)

    for i, entry in enumerate(entries[:15]):
        product = {
            "rank": i,
            "name": entry.get("name", ""),
            "sku": entry.get("partNumber", ""),
            "manufacturer": entry.get("manufacturer", ""),
            "price": "",
            "short_description": entry.get("shortDescription", ""),
        }

        # --- Price (prefer Offer / "I" price) ---
        for p in entry.get("price", []):
            if p.get("usage") == "Offer" or p.get("description") == "I":
                product["price"] = p.get("value", "")
                break

        # --- Flat custom attributes (top-level keys) ---
        product["vendor_part_number"] = entry.get(
            "custom.attribute.TP_tpvendorsku.raw", ""
        )
        product["cross_reference"] = entry.get(
            "custom.attribute.TP_tpcrossref.raw", ""
        )
        product["wholesale_sku"] = entry.get(
            "custom.attribute.TP_tpwholesalesku.raw", ""
        )
        short_desc = entry.get(
            "custom.attribute.TP_tpshortdescription.raw", ""
        )
        if short_desc:
            product["short_description"] = short_desc

        # --- Nested attributes (fallback) ---
        for attr in entry.get("attributes", []):
            ident = attr.get("identifier", "")
            vals = attr.get("values", [])
            val = vals[0].get("value", "") if vals else ""
            if not val:
                continue
            if ident == "TP_tpvendorsku" and not product["vendor_part_number"]:
                product["vendor_part_number"] = val
            elif ident == "TP_tpcrossref" and not product["cross_reference"]:
                product["cross_reference"] = val
            elif ident == "TP_tpwholesalesku" and not product["wholesale_sku"]:
                product["wholesale_sku"] = val

        products.append(product)

    return products, int(total_count) if total_count else 0


def collect_all_results(terms: List[SearchTermDef]) -> Dict[str, Any]:
    """Collect search results from both environments for all terms."""
    results = {}
    total = len(terms)

    for idx, term_def in enumerate(terms):
        log.info(f"[{idx+1}/{total}] Collecting: '{term_def.term}'")
        entry = {
            "term": term_def.term,
            "search_type": term_def.search_type,
            "expected_top_skus": term_def.expected_top_skus,
            "expected_total_count": term_def.expected_total_count,
            "count_tolerance": term_def.count_tolerance,
            "notes": term_def.notes,
        }

        # Fetch PROD
        raw_prod = fetch_search_results(PROD_BASE, term_def.term)
        if "error" not in raw_prod:
            prods, count = extract_products(raw_prod)
            entry["prod"] = {"products": prods, "total_count": count}
        else:
            entry["prod"] = {"products": [], "total_count": 0, "error": raw_prod["error"]}

        # Fetch PERF
        raw_perf = fetch_search_results(PERF_BASE, term_def.term)
        if "error" not in raw_perf:
            prods, count = extract_products(raw_perf)
            entry["perf"] = {"products": prods, "total_count": count}
        else:
            entry["perf"] = {"products": [], "total_count": 0, "error": raw_perf["error"]}

        results[term_def.term] = entry
        time.sleep(0.5)  # Be polite to the API

    return results


# ---------------------------------------------------------------------------
# Claude Haiku judge
# ---------------------------------------------------------------------------

def call_claude(prompt: str, api_key: str, max_tokens: int = 4096) -> str:
    """Call Claude Haiku API and return the text response."""
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    resp = requests.post(CLAUDE_API_URL, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["content"][0]["text"]


def format_products_for_prompt(products: List[Dict[str, Any]]) -> str:
    """Format product list into readable text for the LLM prompt."""
    if not products:
        return "  (no results)"
    lines = []
    for p in products:
        parts = [
            f"Rank {p['rank']}: SKU={p['sku']}",
            f"Name=\"{p['name']}\"",
        ]
        if p.get("vendor_part_number"):
            parts.append(f"VendorPN={p['vendor_part_number']}")
        if p.get("cross_reference"):
            parts.append(f"CrossRef={p['cross_reference']}")
        if p.get("manufacturer"):
            parts.append(f"Mfg={p['manufacturer']}")
        if p.get("price"):
            parts.append(f"Price=${p['price']}")
        if p.get("short_description"):
            desc = p["short_description"][:80]
            parts.append(f"Desc=\"{desc}\"")
        lines.append("  " + " | ".join(parts))
    return "\n".join(lines)


def build_evaluation_prompt(term_data: Dict[str, Any]) -> str:
    """Build the prompt for Claude to evaluate and compare results."""
    term = term_data["term"]
    search_type = term_data["search_type"]
    expected = term_data["expected_top_skus"]
    notes = term_data.get("notes", "")
    exp_count = term_data.get("expected_total_count")

    prod_products = term_data["prod"]["products"]
    prod_count = term_data["prod"]["total_count"]
    perf_products = term_data["perf"]["products"]
    perf_count = term_data["perf"]["total_count"]

    prod_text = format_products_for_prompt(prod_products)
    perf_text = format_products_for_prompt(perf_products)

    return f"""You are an expert e-commerce search quality analyst for an automotive/truck parts distributor (TruckPro).

## Task
Evaluate and compare search results from two environments for the query below.

## Search Query
- **Term**: "{term}"
- **Type**: {search_type}
- **Expected top SKUs** (from baseline doc): {json.dumps(expected)}
- **Expected total count**: {exp_count if exp_count else "Not specified"}
- **Notes**: {notes if notes else "None"}

## PERF Environment Results (top 15) — Total: {perf_count}
{perf_text}

## PROD Environment Results (top 15) — Total: {prod_count}
{prod_text}

## Evaluation Criteria

For a **{search_type}** query, consider:
{"- Exact part number match should be ranked #1" if search_type == "part_number" else ""}
{"- Products matching ALL query terms should rank above those matching only one term" if search_type == "multiple_terms" else ""}
{"- Products whose name/description directly matches the search concept should rank highest" if search_type == "english_word" else ""}
- Do the expected baseline SKUs appear in the top 15?
- Is the ranking order logical for the query intent?
- Are there irrelevant results that should not be present?
- How do total counts compare to the expected count?

## Output Format

Respond with ONLY valid JSON in this exact structure:
```json
{{
  "search_term": "{term}",
  "search_type": "{search_type}",
  "perf_evaluation": {{
    "relevance_score": 1-10,
    "expected_skus_found": ["list of expected SKUs found in PERF top 15"],
    "expected_skus_missing": ["list of expected SKUs NOT in PERF top 15"],
    "top_result_relevant": true/false,
    "irrelevant_results": ["SKUs of results that seem irrelevant, if any"],
    "ranking_quality": "Good|Acceptable|Poor",
    "total_count_assessment": "description of whether total count is reasonable",
    "issues": ["list of specific issues found"]
  }},
  "prod_evaluation": {{
    "relevance_score": 1-10,
    "expected_skus_found": ["list of expected SKUs found in PROD top 15"],
    "expected_skus_missing": ["list of expected SKUs NOT in PROD top 15"],
    "top_result_relevant": true/false,
    "irrelevant_results": ["SKUs of results that seem irrelevant, if any"],
    "ranking_quality": "Good|Acceptable|Poor",
    "total_count_assessment": "description of whether total count is reasonable",
    "issues": ["list of specific issues found"]
  }},
  "comparison": {{
    "winner": "PERF|PROD|TIE",
    "perf_advantages": ["what PERF does better"],
    "prod_advantages": ["what PROD does better"],
    "ranking_differences": "description of key ranking order differences",
    "count_difference": {{
      "prod_count": {prod_count},
      "perf_count": {perf_count},
      "difference_pct": 0.0,
      "assessment": "description"
    }},
    "regressions_in_perf": ["specific things that got worse in PERF vs PROD"],
    "improvements_in_perf": ["specific things that got better in PERF vs PROD"]
  }},
  "recommendation": "1-2 sentence actionable recommendation"
}}
```"""


def evaluate_single_term(term_data: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    """Evaluate a single search term using Claude Haiku."""
    prompt = build_evaluation_prompt(term_data)
    try:
        raw_response = call_claude(prompt, api_key)
        # Extract JSON from response (handle markdown code blocks)
        json_str = raw_response.strip()
        if json_str.startswith("```"):
            json_str = json_str.split("\n", 1)[1]  # Remove first ``` line
            json_str = json_str.rsplit("```", 1)[0]  # Remove last ```
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        log.error(f"  JSON parse error for '{term_data['term']}': {e}")
        return {"error": f"JSON parse failed: {e}", "raw_response": raw_response}
    except Exception as e:
        log.error(f"  Claude API error for '{term_data['term']}': {e}")
        return {"error": str(e)}


def evaluate_all(collected: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    """Run Claude evaluation on all collected results."""
    evaluations = {}
    total = len(collected)

    for idx, (term, data) in enumerate(collected.items()):
        log.info(f"[{idx+1}/{total}] Evaluating: '{term}'")

        # Skip if either env had an error
        if data["prod"].get("error") or data["perf"].get("error"):
            log.warning(f"  Skipping '{term}' due to collection error")
            evaluations[term] = {
                "error": "Collection error",
                "prod_error": data["prod"].get("error"),
                "perf_error": data["perf"].get("error"),
            }
            continue

        evaluation = evaluate_single_term(data, api_key)
        evaluations[term] = evaluation
        time.sleep(0.3)  # Rate limiting courtesy

    return evaluations


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_summary_report(
    collected: Dict[str, Any],
    evaluations: Dict[str, Any],
) -> Dict[str, Any]:
    """Generate a summary report from all evaluations."""
    perf_wins = 0
    prod_wins = 0
    ties = 0
    errors = 0
    perf_scores = []
    prod_scores = []
    regressions = []
    improvements = []

    for term, ev in evaluations.items():
        if ev.get("error"):
            errors += 1
            continue

        winner = ev.get("comparison", {}).get("winner", "TIE")
        if winner == "PERF":
            perf_wins += 1
        elif winner == "PROD":
            prod_wins += 1
        else:
            ties += 1

        perf_score = ev.get("perf_evaluation", {}).get("relevance_score", 0)
        prod_score = ev.get("prod_evaluation", {}).get("relevance_score", 0)
        if isinstance(perf_score, (int, float)):
            perf_scores.append(perf_score)
        if isinstance(prod_score, (int, float)):
            prod_scores.append(prod_score)

        for reg in ev.get("comparison", {}).get("regressions_in_perf", []):
            regressions.append({"term": term, "issue": reg})
        for imp in ev.get("comparison", {}).get("improvements_in_perf", []):
            improvements.append({"term": term, "improvement": imp})

    return {
        "generated_at": datetime.now().isoformat(),
        "total_terms_evaluated": len(evaluations),
        "errors": errors,
        "overall_winner": "PERF" if perf_wins > prod_wins else "PROD" if prod_wins > perf_wins else "TIE",
        "score_summary": {
            "perf_wins": perf_wins,
            "prod_wins": prod_wins,
            "ties": ties,
            "perf_avg_relevance": round(sum(perf_scores) / len(perf_scores), 2) if perf_scores else 0,
            "prod_avg_relevance": round(sum(prod_scores) / len(prod_scores), 2) if prod_scores else 0,
        },
        "regressions_in_perf": regressions,
        "improvements_in_perf": improvements,
    }


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

def save_json(data: Any, filename: str) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log.info(f"Saved: {path}")
    return path


def load_json(filename: str) -> Any:
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="TruckPro Search Evaluation Pipeline")
    parser.add_argument("--collect-only", action="store_true",
                        help="Only collect API results, skip LLM evaluation")
    parser.add_argument("--eval-only", action="store_true",
                        help="Only run LLM evaluation on cached results")
    parser.add_argument("--terms", type=str, default=None,
                        help="Comma-separated list of specific search terms to run")
    parser.add_argument("--api-key", type=str, default=None,
                        help="Anthropic API key (or set ANTHROPIC_API_KEY env var)")
    return parser.parse_args()


def main():
    args = parse_args()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Filter terms if specified
    terms = SEARCH_TERMS
    if args.terms:
        requested = [t.strip() for t in args.terms.split(",")]
        terms = [t for t in SEARCH_TERMS if t.term in requested]
        if not terms:
            log.error(f"No matching terms found for: {args.terms}")
            sys.exit(1)
        log.info(f"Running {len(terms)} selected terms: {[t.term for t in terms]}")

    # --- Step 1: Collect ---
    if args.eval_only:
        log.info("Loading cached collection results...")
        collected = load_json("tp_collected_results.json")
        # Filter if specific terms requested
        if args.terms:
            requested = [t.strip() for t in args.terms.split(",")]
            collected = {k: v for k, v in collected.items() if k in requested}
    else:
        log.info(f"Collecting results for {len(terms)} search terms from PROD and PERF...")
        collected = collect_all_results(terms)
        save_json(collected, "tp_collected_results.json")
        log.info("Collection complete.")

    if args.collect_only:
        log.info("--collect-only mode: stopping after collection.")
        return

    # --- Step 2: Evaluate with Claude ---
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
    if not api_key:
        log.error("No API key provided. Set ANTHROPIC_API_KEY or use --api-key")
        sys.exit(1)

    log.info("Starting Claude Haiku evaluation...")
    evaluations = evaluate_all(collected, api_key)
    save_json(evaluations, f"tp_evaluations_{timestamp}.json")
    save_json(evaluations, "tp_evaluations_latest.json")

    # --- Step 3: Generate summary ---
    summary = generate_summary_report(collected, evaluations)
    save_json(summary, f"tp_summary_{timestamp}.json")
    save_json(summary, "tp_summary_latest.json")

    # --- Print summary to console ---
    print("\n" + "=" * 70)
    print("  TRUCKPRO SEARCH EVALUATION SUMMARY")
    print("=" * 70)
    s = summary["score_summary"]
    print(f"  Terms evaluated: {summary['total_terms_evaluated']} (errors: {summary['errors']})")
    print(f"  Overall winner:  {summary['overall_winner']}")
    print(f"  PERF wins: {s['perf_wins']}  |  PROD wins: {s['prod_wins']}  |  Ties: {s['ties']}")
    print(f"  PERF avg relevance: {s['perf_avg_relevance']}/10")
    print(f"  PROD avg relevance: {s['prod_avg_relevance']}/10")

    if summary["regressions_in_perf"]:
        print(f"\n  PERF Regressions ({len(summary['regressions_in_perf'])}):")
        for r in summary["regressions_in_perf"][:10]:
            print(f"    - [{r['term']}] {r['issue']}")

    if summary["improvements_in_perf"]:
        print(f"\n  PERF Improvements ({len(summary['improvements_in_perf'])}):")
        for imp in summary["improvements_in_perf"][:10]:
            print(f"    + [{imp['term']}] {imp['improvement']}")

    print("=" * 70)
    print(f"  Full results: {OUTPUT_DIR}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
