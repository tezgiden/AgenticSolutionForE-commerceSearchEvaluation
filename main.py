# Configurable Main Orchestrator for Multi-Site Agentic Search Solution

import json
import time
import os
import sys
import argparse
from typing import Dict, List, Any, Optional

# Import configuration system
from config_loader import ConfigLoader, AppConfig, load_config_for_site, get_available_sites, validate_site_config

# Import modules (these will be updated to use config)
from scraper import setup_driver_with_config, scrape_site_with_config
from llm_evaluator import evaluate_search_results_with_inventory, classify_search_type

def analyze_inventory_impact(evaluation_results: dict, original_results: list) -> dict:
    """
    Analyzes how inventory affected the ranking compared to relevance-only ranking.
    
    Args:
        evaluation_results: Results from enhanced evaluation
        original_results: Original scraped results
        
    Returns:
        Dictionary with inventory impact analysis
    """
    analysis = {
        "inventory_changes_detected": False,
        "ranking_changes": [],
        "inventory_summary": {},
        "recommendations": []
    }
    
    if evaluation_results['status'] != 'success':
        return analysis
    
    evaluations = evaluation_results.get('evaluations', [])
    
    # Group by relevance to see inventory impact within each tier
    relevance_groups = {"High": [], "Medium": [], "Low": []}
    
    for eval_item in evaluations:
        relevance = eval_item.get('relevance', 'Low')
        result_idx = eval_item.get('result_index', 0)
        
        if result_idx < len(original_results):
            original_result = original_results[result_idx]
            quantity = original_result.get('quantity', 'N/A')
            
            item_data = {
                'index': result_idx,
                'title': original_result.get('title', 'N/A')[:50] + '...',
                'part_number': original_result.get('part_number', 'N/A'),
                'quantity': quantity,
                'relevance': relevance,
                'evaluation': eval_item
            }
            
            if relevance in relevance_groups:
                relevance_groups[relevance].append(item_data)
    
    # Analyze inventory distribution
    total_items = len(evaluations)
    out_of_stock = sum(1 for eval_item in evaluations 
                      if eval_item.get('parsed_quantity', 0) == 0)
    in_stock = total_items - out_of_stock
    
    analysis['inventory_summary'] = {
        'total_items': total_items,
        'in_stock_items': in_stock,
        'out_of_stock_items': out_of_stock,
        'stock_availability_ratio': in_stock / total_items if total_items > 0 else 0
    }
    
    # Check for ranking changes within relevance tiers
    for relevance_level, items in relevance_groups.items():
        if len(items) > 1:
            # Sort by original index (scraped order)
            original_order = sorted(items, key=lambda x: x['index'])
            # Current order is already in evaluation order
            current_order = items
            
            if original_order != current_order:
                analysis['inventory_changes_detected'] = True
                analysis['ranking_changes'].append({
                    'relevance_tier': relevance_level,
                    'original_order': [item['index'] for item in original_order],
                    'new_order': [item['index'] for item in current_order],
                    'reasoning': f"Inventory-based reordering within {relevance_level} relevance tier"
                })
    
    # Generate recommendations
    if out_of_stock > 0:
        analysis['recommendations'].append(
            f"Consider highlighting {out_of_stock} out-of-stock items differently in search results"
        )
    
    if analysis['inventory_changes_detected']:
        analysis['recommendations'].append(
            "Inventory-based ranking is actively improving result relevance"
        )
    else:
        analysis['recommendations'].append(
            "No inventory-based ranking changes needed for this query"
        )
    
    return analysis

def generate_business_summary(query: str, evaluation: dict, scraped_results: list, 
                            inventory_analysis: dict, config: AppConfig) -> dict:
    """
    Generates a business-focused summary with relevancy assessment and product movement recommendations.
    
    Args:
        query: The search query
        evaluation: Evaluation results from LLM
        scraped_results: Original scraped results
        inventory_analysis: Inventory impact analysis
        config: Application configuration
        
    Returns:
        Dictionary containing business summary and recommendations
    """
    summary = {
        "relevancy_assessment": "",
        "product_movement_recommendations": [],
        "key_insights": [],
        "action_items": []
    }
    
    if evaluation.get('status') != 'success' or not scraped_results:
        summary["relevancy_assessment"] = f"Search for '{query}' failed to return evaluable results. Consider investigating search functionality or product catalog coverage for {config.site_config.site_name}."
        summary["action_items"].append("Investigate why search failed to return results")
        return summary
    
    evaluations = evaluation.get('evaluations', [])
    total_results = len(evaluations)
    
    # Analyze relevancy distribution
    relevancy_counts = {"High": 0, "Medium": 0, "Low": 0}
    inventory_stats = {"in_stock": 0, "out_of_stock": 0, "low_stock": 0}
    
    low_stock_threshold = config.evaluation_config.low_stock_threshold
    
    for eval_item in evaluations:
        relevance = eval_item.get('relevance', 'Low')
        if relevance in relevancy_counts:
            relevancy_counts[relevance] += 1
            
        # Analyze inventory
        parsed_qty = eval_item.get('parsed_quantity', 0)
        if parsed_qty == 0:
            inventory_stats["out_of_stock"] += 1
        elif parsed_qty < low_stock_threshold:
            inventory_stats["low_stock"] += 1
        else:
            inventory_stats["in_stock"] += 1
    
    # Generate relevancy assessment
    high_relevance_pct = (relevancy_counts["High"] / total_results * 100) if total_results > 0 else 0
    in_stock_pct = (inventory_stats["in_stock"] / total_results * 100) if total_results > 0 else 0
    
    if high_relevance_pct >= 60:
        relevancy_quality = "excellent"
    elif high_relevance_pct >= 40:
        relevancy_quality = "good" 
    elif high_relevance_pct >= 20:
        relevancy_quality = "moderate"
    else:
        relevancy_quality = "poor"
    
    summary["relevancy_assessment"] = (
        f"Search for '{query}' on {config.site_config.site_name} returned {total_results} results with {relevancy_quality} relevancy "
        f"({relevancy_counts['High']} high, {relevancy_counts['Medium']} medium, {relevancy_counts['Low']} low relevance). "
        f"Inventory availability is {'strong' if in_stock_pct >= 70 else 'moderate' if in_stock_pct >= 40 else 'concerning'} "
        f"with {inventory_stats['in_stock']} items in stock, {inventory_stats['out_of_stock']} out of stock."
    )
    
    # Generate product movement recommendations
    if inventory_stats["out_of_stock"] > 0:
        summary["product_movement_recommendations"].append(
            f"Restock {inventory_stats['out_of_stock']} out-of-stock items or consider removing them from search results to improve customer experience"
        )
    
    if relevancy_counts["Low"] > relevancy_counts["High"]:
        summary["product_movement_recommendations"].append(
            f"Improve search algorithm or product tagging on {config.site_config.site_name} to surface more relevant results higher in rankings"
        )
    
    if inventory_analysis and inventory_analysis.get('inventory_changes_detected'):
        summary["product_movement_recommendations"].append(
            "Continue using inventory-aware ranking as it's successfully prioritizing available products"
        )
    
    # Identify top performers and problem products
    top_products = []
    problem_products = []
    
    for i, eval_item in enumerate(evaluations[:3]):  # Top 3 results
        idx = eval_item.get('result_index', 0)
        if idx < len(scraped_results):
            result = scraped_results[idx]
            relevance = eval_item.get('relevance')
            qty = eval_item.get('parsed_quantity', 0)
            
            if relevance == "High" and qty > 0:
                top_products.append(result.get('part_number', f'Product {idx}'))
            elif relevance == "Low" or qty == 0:
                problem_products.append(result.get('part_number', f'Product {idx}'))
    
    # Generate key insights
    if top_products:
        summary["key_insights"].append(f"Top performing products: {', '.join(top_products[:2])}")
    
    if problem_products:
        summary["key_insights"].append(f"Products needing attention: {', '.join(problem_products[:2])}")
    
    if high_relevance_pct < 30:
        summary["key_insights"].append(f"Search relevancy on {config.site_config.site_name} is below optimal - consider improving product metadata or search algorithm")
    
    if in_stock_pct < 50:
        summary["key_insights"].append("Low inventory availability may be impacting sales conversion")
    
    # Generate action items
    if relevancy_counts["High"] == 0:
        summary["action_items"].append(f"URGENT: No highly relevant results found on {config.site_config.site_name} - review product catalog and search functionality")
    
    if inventory_stats["out_of_stock"] > inventory_stats["in_stock"]:
        summary["action_items"].append("PRIORITY: More items out of stock than in stock - review inventory management")
    
    if high_relevance_pct > 70 and in_stock_pct > 70:
        summary["action_items"].append("OPTIMIZE: Strong performance - consider promoting these search results in marketing")
    
    return summary

def generate_overall_summary(all_results: list, config: AppConfig) -> dict:
    """
    Generates an overall summary across all search queries for a specific site.
    
    Args:
        all_results: List of all search result evaluations
        config: Application configuration
        
    Returns:
        Dictionary containing overall performance summary
    """
    overall = {
        "site_name": config.site_config.site_name,
        "site_url": config.site_config.target_url,
        "total_queries": len(all_results),
        "successful_queries": 0,
        "failed_queries": 0,
        "average_relevancy_score": 0,
        "inventory_performance": {},
        "top_recommendations": [],
        "critical_issues": [],
        "configuration_summary": {
            "inventory_ranking_enabled": config.evaluation_config.enable_inventory_ranking,
            "model_used": config.llm_config.default_model,
            "max_results_per_query": config.site_config.scraping_config.max_results_per_query
        }
    }
    
    successful_results = [r for r in all_results if r.get('status') == 'success']
    overall["successful_queries"] = len(successful_results)
    overall["failed_queries"] = overall["total_queries"] - overall["successful_queries"]
    
    if successful_results:
        # Calculate average relevancy
        total_relevancy_score = 0
        total_products = 0
        total_in_stock = 0
        total_out_of_stock = 0
        
        for result in successful_results:
            evaluations = result.get('evaluation', [])
            for eval_item in evaluations:
                total_products += 1
                relevance = eval_item.get('relevance', 'Low')
                
                # Convert relevance to numeric score
                if relevance == 'High':
                    total_relevancy_score += 3
                elif relevance == 'Medium':
                    total_relevancy_score += 2
                else:
                    total_relevancy_score += 1
                
                # Count inventory
                if eval_item.get('parsed_quantity', 0) > 0:
                    total_in_stock += 1
                else:
                    total_out_of_stock += 1
        
        if total_products > 0:
            overall["average_relevancy_score"] = round(total_relevancy_score / total_products, 2)
            overall["inventory_performance"] = {
                "in_stock_percentage": round(total_in_stock / total_products * 100, 1),
                "out_of_stock_percentage": round(total_out_of_stock / total_products * 100, 1),
                "total_products_analyzed": total_products
            }
    
    # Generate top recommendations
    if overall["average_relevancy_score"] < 2.0:
        overall["top_recommendations"].append(f"Improve search relevancy algorithms on {config.site_config.site_name} - average score below target")
    
    in_stock_pct = overall["inventory_performance"].get("in_stock_percentage", 0)
    if in_stock_pct < 60:
        overall["top_recommendations"].append(f"Address inventory issues on {config.site_config.site_name} - only {in_stock_pct}% of products in stock")
    
    if overall["failed_queries"] > 0:
        overall["top_recommendations"].append(f"Investigate {overall['failed_queries']} failed searches on {config.site_config.site_name}")
    
    # Identify critical issues
    if overall["failed_queries"] > overall["successful_queries"]:
        overall["critical_issues"].append(f"More searches failing than succeeding on {config.site_config.site_name} - major system issue")
    
    if in_stock_pct < 30:
        overall["critical_issues"].append(f"Critical inventory shortage across most products on {config.site_config.site_name}")
    
    return overall

def run_configurable_agentic_search(config: AppConfig) -> None:
    """
    Runs the configurable end-to-end agentic search with inventory-aware evaluation.
    
    Args:
        config: Complete application configuration
    """
    all_final_results = []
    detailed_analysis = []
    
    # Combine regular tasks with inventory test cases
    all_search_tasks = config.site_config.search_tasks + config.site_config.inventory_test_cases
    
    print(f"Starting search for {config.site_config.site_name}")
    print(f"Target URL: {config.site_config.target_url}")
    print(f"Total queries: {len(all_search_tasks)}")
    print(f"Model: {config.llm_config.default_model}")
    print(f"Inventory ranking: {'Enabled' if config.evaluation_config.enable_inventory_ranking else 'Disabled'}")
    
    # Setup WebDriver with configuration
    driver = setup_driver_with_config(config.chrome_config)
    if not driver:
        print("Failed to initialize WebDriver. Aborting.")
        return

    try:
        for task_idx, task in enumerate(all_search_tasks):
            query = task.get("query")
            if not query:
                print("Skipping task with no query.")
                continue

            print(f"\n{'='*70}")
            print(f"Processing Query {task_idx + 1}/{len(all_search_tasks)}: '{query}'")
            print(f"{'='*70}")

            # 1. Scrape Search Results
            print("--- Step 1: Scraping website ---")
            scraped_results = scrape_site_with_config(driver, query, config.site_config)
            if not scraped_results:
                print(f"No results found or error during scraping for '{query}'. Skipping evaluation.")
                all_final_results.append({
                    "query": query,
                    "status": "scraping_failed",
                    "scraped_results": [],
                    "evaluation": None,
                    "inventory_analysis": None,
                    "business_summary": None,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                })
                continue
            
            print(f"--- Step 1: Scraping finished. Found {len(scraped_results)} results ---")
            
            # Display scraped results with inventory
            print("Scraped results (original order):")
            for i, result in enumerate(scraped_results):
                title_short = result.get('title', 'N/A')[:40] + '...' if len(result.get('title', '')) > 40 else result.get('title', 'N/A')
                quantity = result.get('quantity', 'N/A')
                print(f"  {i}: {title_short} | Qty: {quantity}")

            # 2. Enhanced Evaluation with Inventory Awareness
            print("--- Step 2: Enhanced evaluation with inventory-aware LLM ---")
            search_type = task.get("search_type") or classify_search_type(query)
            
            # Configure LLM evaluator with config settings
            evaluation = evaluate_search_results_with_inventory(
                query=query,
                results=scraped_results,
                search_type=search_type,
                model=config.llm_config.default_model,
                apply_post_ranking=config.evaluation_config.apply_post_ranking,
                api_endpoint=config.llm_config.ollama_api_endpoint,
                timeout=config.llm_config.timeout,
                max_retries=config.llm_config.max_retries
            )
            
            print(f"--- Step 2: Enhanced evaluation finished. Status: {evaluation.get('status')} ---")
            
            # 3. Detailed Inventory Impact Analysis
            inventory_analysis = None
            if config.evaluation_config.enable_detailed_analysis and evaluation.get('status') == 'success':
                print("--- Step 3: Analyzing inventory impact ---")
                inventory_analysis = analyze_inventory_impact(evaluation, scraped_results)
                
                if inventory_analysis['inventory_changes_detected']:
                    print("✓ Inventory-based ranking changes detected")
                    for change in inventory_analysis['ranking_changes']:
                        print(f"  - {change['reasoning']}")
                else:
                    print("- No inventory-based ranking changes needed")
                
                print(f"Inventory summary: {inventory_analysis['inventory_summary']['in_stock_items']}/{inventory_analysis['inventory_summary']['total_items']} items in stock")

            # Display final ranked results
            if evaluation.get('status') == 'success':
                print("\nFinal ranked results:")
                for rank, eval_item in enumerate(evaluation.get('evaluations', []), 1):
                    idx = eval_item.get('result_index', 0)
                    if idx < len(scraped_results):
                        result = scraped_results[idx]
                        title_short = result.get('title', 'N/A')[:40] + '...' if len(result.get('title', '')) > 40 else result.get('title', 'N/A')
                        relevance = eval_item.get('relevance', 'N/A')
                        quantity = result.get('quantity', 'N/A')
                        print(f"  {rank}: {title_short} | Relevance: {relevance} | Qty: {quantity}")

            # 4. Generate Business Summary and Recommendations
            print("--- Step 4: Generating business summary and recommendations ---")
            business_summary = generate_business_summary(query, evaluation, scraped_results, inventory_analysis, config)

            # Combine results
            final_result = {
                "query": query,
                "status": evaluation.get("status", "unknown"),
                "search_type": search_type,
                "scraped_results": scraped_results,
                "evaluation": evaluation.get("evaluations", []),
                "inventory_analysis": inventory_analysis,
                "business_summary": business_summary,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            all_final_results.append(final_result)
            
            # Add to detailed analysis
            if config.evaluation_config.enable_detailed_analysis:
                detailed_analysis.append({
                    "query": query,
                    "search_type": search_type,
                    "inventory_analysis": inventory_analysis,
                    "business_summary": business_summary,
                    "evaluation_metadata": {
                        "model_used": evaluation.get("model_used"),
                        "inventory_aware_ranking_applied": evaluation.get("inventory_aware_ranking_applied", False),
                        "ranking_summary": evaluation.get("ranking_summary", "")
                    }
                })
            
            # Delay between tasks
            time.sleep(config.deployment_config.delay_between_searches)

    finally:
        # Ensure driver is closed
        if driver:
            driver.quit()
            print("\nWebDriver closed.")

    # Generate overall summary
    overall_summary = generate_overall_summary(all_final_results, config)

    # Save final results
    try:
        final_output = {
            "search_results": all_final_results,
            "overall_summary": overall_summary,
            "configuration": {
                "site_name": config.site_config.site_name,
                "site_url": config.site_config.target_url,
                "inventory_ranking_enabled": config.evaluation_config.enable_inventory_ranking,
                "detailed_analysis_enabled": config.evaluation_config.enable_detailed_analysis,
                "model_used": config.llm_config.default_model,
                "total_queries_processed": len(all_final_results),
                "generation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "environment": config.deployment_config.environment
            }
        }
        
        output_file = config.site_config.output_config.output_file
        with open(output_file, "w") as f:
            json.dump(final_output, f, indent=4)
        print(f"\nFinal results saved to {output_file}")
        
        # Save detailed analysis if enabled
        if config.evaluation_config.enable_detailed_analysis and detailed_analysis:
            detailed_file = config.site_config.output_config.detailed_output_file
            with open(detailed_file, "w") as f:
                json.dump({
                    "detailed_analysis": detailed_analysis,
                    "site_name": config.site_config.site_name,
                    "generation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }, f, indent=4)
            print(f"Detailed analysis saved to {detailed_file}")
            
    except IOError as e:
        print(f"Error saving results: {e}")

def main():
    """Main entry point with command line argument support"""
    parser = argparse.ArgumentParser(description="Configurable Agentic Search Solution")
    parser.add_argument("--site", type=str, help="Site configuration key (e.g., truckpro, tundrafmp)")
    parser.add_argument("--config", type=str, default="config.json", help="Path to configuration file")
    parser.add_argument("--list-sites", action="store_true", help="List available site configurations")
    parser.add_argument("--validate", type=str, help="Validate configuration for a specific site")
    parser.add_argument("--model", type=str, help="Override the default LLM model")
    parser.add_argument("--max-results", type=int, help="Override max results per query")
    parser.add_argument("--headless", type=bool, help="Override headless browser setting")
    parser.add_argument("--output-file", type=str, help="Override output file path")
    
    args = parser.parse_args()
    
    try:
        # Handle list sites command
        if args.list_sites:
            sites = get_available_sites(args.config)
            print("Available site configurations:")
            for site in sites:
                print(f"  - {site}")
            return
        
        # Handle validation command
        if args.validate:
            errors = validate_site_config(args.validate, args.config)
            if errors:
                print(f"Configuration errors for {args.validate}:")
                for error in errors:
                    print(f"  - {error}")
                sys.exit(1)
            else:
                print(f"Configuration for {args.validate} is valid!")
            return
        
        # Require site parameter for running
        if not args.site:
            sites = get_available_sites(args.config)
            print("Error: --site parameter is required")
            print(f"Available sites: {sites}")
            sys.exit(1)
        
        # Load configuration
        loader = ConfigLoader(args.config)
        
        # Apply command line overrides
        overrides = {}
        if args.model:
            overrides["model"] = args.model
        if args.max_results:
            overrides["max_results"] = args.max_results
        if args.headless is not None:
            overrides["headless"] = args.headless
        if args.output_file:
            overrides["output_file"] = args.output_file
        
        if overrides:
            config = loader.override_config(args.site, overrides)
            print(f"Applied configuration overrides: {overrides}")
        else:
            config = loader.get_site_config(args.site)
        
        # Validate configuration
        errors = loader.validate_config(args.site)
        if errors:
            print(f"Configuration validation failed:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
        
        print(f"Starting Enhanced Agentic Search Solution for {config.site_config.site_name}...")
        
        # Run the search
        run_configurable_agentic_search(config)
        
        print(f"\nEnhanced Agentic Search Solution finished for {config.site_config.site_name}.")
        print(f"Results saved to: {config.site_config.output_config.output_file}")
        if config.evaluation_config.enable_detailed_analysis:
            print(f"Detailed analysis saved to: {config.site_config.output_config.detailed_output_file}")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()