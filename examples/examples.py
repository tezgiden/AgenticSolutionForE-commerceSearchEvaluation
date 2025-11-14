"""
Examples demonstrating how to use the refactored LLM evaluation system.

This file shows various usage patterns from basic to advanced configurations.
"""

import os
import sys
from typing import List, Dict

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.llm_evaluator import (
    SearchEvaluationEngine,
    EvaluationRequest,
    EvaluationEngineBuilder,
    LLMConfig,
    SearchType,
    evaluate_search_results,  # Backward compatibility
    quick_evaluate,
    run_quick_test
)


def example_basic_usage():
    """Example 1: Basic usage with default configuration."""
    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)
    
    # Sample search results (what you'd get from your web scraping)
    search_results = [
        {
            "title": "Premium Brake Pads Set",
            "part_number": "BP001",
            "vendor_part_number": "V-BP001",
            "price": "$45.99",
            "quantity": "150",
            "url": "https://example.com/bp001"
        },
        {
            "title": "Economy Brake Pads",
            "part_number": "BP002", 
            "vendor_part_number": "V-BP002",
            "price": "$29.99",
            "quantity": "0",  # Out of stock
            "url": "https://example.com/bp002"
        },
        {
            "title": "Performance Brake Kit",
            "part_number": "BK100",
            "vendor_part_number": "V-BK100", 
            "price": "$89.99",
            "quantity": "5",  # Low stock
            "url": "https://example.com/bk100"
        }
    ]
    
    # Create engine and evaluate
    engine = SearchEvaluationEngine()
    
    # Check if service is available
    if not engine.is_service_available():
        print("❌ Ollama service is not available. Please start Ollama first.")
        return
    
    request = EvaluationRequest(
        query="brake pads",
        results=search_results,
        include_executive_summary=True,
        apply_inventory_ranking=True
    )
    
    result = engine.evaluate(request)
    
    # Display results
    print(f"Query: {result.query}")
    print(f"Search Type: {result.search_type.value}")
    print(f"Status: {result.status}")
    print(f"Model Used: {result.model_used}")
    print(f"Results Evaluated: {len(result.evaluations)}")
    
    if result.status == "success":
        print("\nEvaluation Results:")
        for i, evaluation in enumerate(result.evaluations):
            original_result = search_results[evaluation.get('result_index', i)]
            print(f"  {i+1}. {original_result['title']}")
            print(f"     Relevance: {evaluation.get('relevance_tier', 'N/A')}")
            print(f"     Inventory: {evaluation.get('inventory_status', 'N/A')} "
                  f"({evaluation.get('inventory_quantity', 'N/A')})")
            print(f"     Justification: {evaluation.get('justification', 'N/A')[:100]}...")
            print()
        
        print(f"Ranking Summary: {result.ranking_summary}")
        
        if result.executive_summary:
            print("\nExecutive Summary:")
            br = result.executive_summary.get('business_recommendations', {})
            print(f"  Relevancy Assessment: {br.get('relevancy_assessment', 'N/A')}")
            print(f"  Customer Satisfaction Risk: {br.get('customer_satisfaction_risk', 'N/A')}")
            print(f"  Overall Quality Score: {result.executive_summary.get('quality_score', 'N/A')}")
    else:
        print(f"❌ Evaluation failed: {result.error}")


def example_part_number_search():
    """Example 2: Part number specific search."""
    print("=" * 60)
    print("Example 2: Part Number Search")
    print("=" * 60)
    
    # Sample results for part number search
    search_results = [
        {
            "title": "Armada Brake Shoe Reman",
            "part_number": "LS4707QPAR23P",
            "vendor_part_number": "4707QPAR23P",
            "exact_match": "No",
            "partial_match": "Yes", 
            "cross_ref_match": "No",
            "quantity": "518",
            "price": "$34.99"
        },
        {
            "title": "Brake Shoe Set Alternative", 
            "part_number": "ALT4707Q",
            "vendor_part_number": "A-4707Q-SET",
            "exact_match": "No",
            "partial_match": "Yes",
            "cross_ref_match": "Yes",
            "quantity": "25",
            "price": "$42.99"
        },
        {
            "title": "Unrelated Gasket Set",
            "part_number": "GSK999",
            "vendor_part_number": "V-GSK999",
            "exact_match": "No", 
            "partial_match": "No",
            "cross_ref_match": "No",
            "quantity": "100",
            "price": "$15.99"
        }
    ]
    
    # Use quick_evaluate for convenience
    result = quick_evaluate(
        query="4707Q",
        results=search_results,
        search_type=SearchType.PART_NUMBER,
        include_executive_summary=False  # Skip for faster execution
    )
    
    print(f"Search Type: {result.search_type.value}")
    print(f"Results: {len(result.evaluations)} evaluations")
    
    if result.status == "success":
        # Show results ordered by relevance
        high_relevance = [e for e in result.evaluations if e.get('relevance_tier') == 'High']
        medium_relevance = [e for e in result.evaluations if e.get('relevance_tier') == 'Medium'] 
        low_relevance = [e for e in result.evaluations if e.get('relevance_tier') == 'Low']
        
        print(f"\nHigh Relevance ({len(high_relevance)}):")
        for eval in high_relevance:
            idx = eval.get('result_index', 0)
            print(f"  - {search_results[idx]['title']} (Part: {search_results[idx]['part_number']})")
        
        print(f"\nMedium Relevance ({len(medium_relevance)}):")
        for eval in medium_relevance:
            idx = eval.get('result_index', 0)
            print(f"  - {search_results[idx]['title']} (Part: {search_results[idx]['part_number']})")
            
        print(f"\nLow Relevance ({len(low_relevance)}):")
        for eval in low_relevance:
            idx = eval.get('result_index', 0)
            print(f"  - {search_results[idx]['title']} (Part: {search_results[idx]['part_number']})")


def example_custom_configuration():
    """Example 3: Custom configuration and advanced features."""
    print("=" * 60)
    print("Example 3: Custom Configuration")
    print("=" * 60)
    
    # Create custom configuration
    custom_config = LLMConfig(
        default_model="llama2",  # Use different model
        timeout=300,  # 5 minute timeout
        max_retries=5,  # More retries
        debug_dir="custom_debug"
    )
    
    # Build custom engine
    engine = (EvaluationEngineBuilder()
              .with_config(custom_config)
              .with_formatter("compact")  # Use compact formatter
              .with_strict_parsing(True)  # Enable strict parsing
              .build())
    
    # Sample results
    results = [
        {"title": "Test Product 1", "part_number": "TP001", "quantity": "50"},
        {"title": "Test Product 2", "part_number": "TP002", "quantity": "0"},
    ]
    
    request = EvaluationRequest(
        query="test product",
        results=results,
        model="llama2",  # Override model for this request
        apply_inventory_ranking=True
    )
    
    if engine.is_service_available():
        result = engine.evaluate(request)
        print(f"Custom evaluation completed with model: {result.model_used}")
        print(f"Debug files saved to: {custom_config.debug_dir}")
    else:
        print("Service not available for custom configuration test")


def example_backward_compatibility():
    """Example 4: Using backward compatibility functions."""
    print("=" * 60)
    print("Example 4: Backward Compatibility")
    print("=" * 60)
    
    # This shows how existing code can continue to work
    results = [
        {"title": "Legacy Product 1", "part_number": "LP001", "quantity": "100"},
        {"title": "Legacy Product 2", "part_number": "LP002", "quantity": "5"},
    ]
    
    # Old style function call
    evaluation_result = evaluate_search_results(
        query="legacy search",
        results=results,
        search_type="english_word"
    )
    
    print("Backward compatibility test:")
    print(f"  Status: {evaluation_result.get('status')}")
    print(f"  Evaluations: {len(evaluation_result.get('evaluations', []))}")
    print("  ✅ Old API still works!")


def example_batch_processing():
    """Example 5: Processing multiple queries in batch."""
    print("=" * 60)
    print("Example 5: Batch Processing")
    print("=" * 60)
    
    # Multiple queries to process
    queries_and_results = [
        {
            "query": "brake fluid",
            "results": [
                {"title": "DOT 3 Brake Fluid", "part_number": "BF003", "quantity": "200"},
                {"title": "DOT 4 Brake Fluid", "part_number": "BF004", "quantity": "150"},
            ]
        },
        {
            "query": "oil filter", 
            "results": [
                {"title": "Standard Oil Filter", "part_number": "OF001", "quantity": "75"},
                {"title": "Premium Oil Filter", "part_number": "OF002", "quantity": "0"},
            ]
        },
        {
            "query": "spark plugs",
            "results": [
                {"title": "Platinum Spark Plugs", "part_number": "SP001", "quantity": "500"},
                {"title": "Iridium Spark Plugs", "part_number": "SP002", "quantity": "300"},
            ]
        }
    ]
    
    # Process all queries
    engine = SearchEvaluationEngine()
    
    if not engine.is_service_available():
        print("❌ Service not available for batch processing")
        return
    
    batch_results = []
    
    for i, query_data in enumerate(queries_and_results, 1):
        print(f"Processing query {i}/{len(queries_and_results)}: '{query_data['query']}'")
        
        request = EvaluationRequest(
            query=query_data["query"],
            results=query_data["results"],
            include_executive_summary=False  # Skip for faster batch processing
        )
        
        result = engine.evaluate(request)
        batch_results.append(result)
    
    # Summary of batch results
    print(f"\nBatch Processing Summary:")
    successful = sum(1 for r in batch_results if r.status == "success")
    print(f"  Successful evaluations: {successful}/{len(batch_results)}")
    
    for i, result in enumerate(batch_results):
        query_data = queries_and_results[i]
        status_icon = "✅" if result.status == "success" else "❌"
        print(f"  {status_icon} '{query_data['query']}': {result.status}")


def example_testing_and_validation():
    """Example 6: Testing and validation utilities."""
    print("=" * 60)
    print("Example 6: Testing and Validation")
    print("=" * 60)
    
    from llm.llm_evaluator import TestRunner, ValidationUtils, LLMConfig
    
    # Validate configuration
    config = LLMConfig.from_environment()
    config_validation = ValidationUtils.validate_config(config)
    print(f"Configuration valid: {config_validation['valid']}")
    if not config_validation['valid']:
        print(f"  Errors: {config_validation['errors']}")
    
    # Check service connectivity
    connectivity = ValidationUtils.validate_service_connectivity(config)
    print(f"Service available: {connectivity['available']}")
    if connectivity['available']:
        print(f"  Available models: {connectivity.get('models', [])}")
    
    # Run comprehensive tests (if service is available)
    if connectivity['available']:
        print("\nRunning comprehensive test suite...")
        test_runner = TestRunner(config)
        
        # This would run all tests - commented out for demo
        # test_results = test_runner.run_all_tests()
        # print(f"Test results: {test_results['summary']}")
        
        print("✅ Test runner initialized successfully")
    else:
        print("⚠️ Skipping comprehensive tests - service not available")


def main():
    """Run all examples."""
    print("🚀 LLM Evaluation System - Usage Examples")
    print("=" * 60)
    
    examples = [
        ("Basic Usage", example_basic_usage),
        ("Part Number Search", example_part_number_search),
        ("Custom Configuration", example_custom_configuration),
        ("Backward Compatibility", example_backward_compatibility),
        ("Batch Processing", example_batch_processing),
        ("Testing and Validation", example_testing_and_validation),
    ]
    
    for name, example_func in examples:
        try:
            print(f"\n🔄 Running: {name}")
            example_func()
            print(f"✅ {name} completed successfully")
        except Exception as e:
            print(f"❌ {name} failed: {e}")
        
        print("-" * 60)
    
    print("\n🎉 All examples completed!")
    print("\nNext steps:")
    print("  1. Ensure Ollama is running: 'ollama serve'")
    print("  2. Pull a model: 'ollama pull gemma3'")
    print("  3. Run quick test: python -c 'from llm_evaluator import run_quick_test; run_quick_test()'")


if __name__ == "__main__":
    main()
