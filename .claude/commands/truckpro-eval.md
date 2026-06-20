Run the TruckPro PERF vs PROD search evaluation pipeline.

## What this does

1. Runs `python scripts/tp_search_eval.py` which:
   - Collects search results from both PROD (search-ecprodauth.truckpro.com) and PERF (search.tpdevauth.truckpro.com) for 26 search terms
   - Evaluates results using Claude Haiku 4.5 as an LLM judge
   - Generates comparison report with relevance scores
2. Reads the output summary and evaluation JSON files from `analysis_result/`
3. Updates `docs/perf-vs-prod-evaluation-report.md` with the new results, comparing against the previous run's scores

## Arguments

- No arguments: run full pipeline (collect + evaluate + report)
- `--collect-only`: only fetch API results, skip LLM evaluation
- `--eval-only`: only run LLM evaluation on cached results (skip API calls)
- `--terms "term1,term2"`: run specific search terms only (comma-separated)

## Instructions

Run the pipeline with the provided arguments: $ARGUMENTS

If no arguments are provided, run the full pipeline.

After the pipeline completes:
1. Read `analysis_result/tp_summary_latest.json` for the summary stats
2. Read `analysis_result/tp_evaluations_latest.json` for per-term details
3. Compare against the previous report in `docs/perf-vs-prod-evaluation-report.md` to identify what changed
4. Update `docs/perf-vs-prod-evaluation-report.md` with the new results, preserving the before/after comparison format showing improvements and regressions
5. Print a concise summary to the user showing: overall winner, PERF wins/PROD wins/ties, avg relevance scores, and any notable changes from the previous run
