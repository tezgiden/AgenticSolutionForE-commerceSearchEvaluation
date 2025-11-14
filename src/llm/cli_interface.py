"""
Command Line Interface for the LLM Search Result Evaluation System.

Provides a convenient CLI for running evaluations, testing, and system management.
"""

import click
import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from llm.llm_evaluator import (
    SearchEvaluationEngine,
    EvaluationRequest,
    LLMConfig,
    SearchType,
    TestRunner,
    ValidationUtils,
    run_quick_test,
    __version__
)


class CLIError(Exception):
    """Custom exception for CLI errors."""
    pass


def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load and parse a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise CLIError(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        raise CLIError(f"Invalid JSON in {file_path}: {e}")


def save_json_file(data: Dict[str, Any], file_path: str, pretty: bool = True) -> None:
    """Save data to a JSON file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        raise CLIError(f"Failed to save file {file_path}: {e}")


@click.group()
@click.version_option(version=__version__)
@click.option('--config-file', '-c', type=click.Path(exists=True), 
              help='Path to configuration file')
@click.option('--debug/--no-debug', default=False, 
              help='Enable debug mode')
@click.option('--verbose', '-v', count=True, 
              help='Increase verbosity (use -vv for more verbose)')
@click.pass_context
def cli(ctx, config_file, debug, verbose):
    """
    LLM Search Result Evaluation System CLI.
    
    A comprehensive tool for evaluating e-commerce search results using
    Large Language Models with inventory-aware ranking.
    """
    # Ensure that ctx.obj exists and is a dict
    ctx.ensure_object(dict)
    
    # Store global options
    ctx.obj['debug'] = debug
    ctx.obj['verbose'] = verbose
    ctx.obj['config_file'] = config_file
    
    # Load configuration
    if config_file:
        try:
            config_data = load_json_file(config_file)
            ctx.obj['config'] = LLMConfig(**config_data)
        except Exception as e:
            click.echo(f"Error loading config file: {e}", err=True)
            sys.exit(1)
    else:
        ctx.obj['config'] = LLMConfig.from_environment()
    
    if debug:
        click.echo(f"Debug mode enabled")
        click.echo(f"Config: {ctx.obj['config']}")


@cli.command()
@click.argument('query')
@click.argument('results_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), 
              help='Output file for results (JSON format)')
@click.option('--search-type', '-t', 
              type=click.Choice(['english_word', 'part_number', 'multiple_terms']),
              help='Force specific search type')
@click.option('--model', '-m', 
              help='LLM model to use (overrides config)')
@click.option('--no-executive-summary', is_flag=True,
              help='Skip executive summary generation')
@click.option('--no-inventory-ranking', is_flag=True,
              help='Skip inventory-aware ranking')
@click.option('--pretty/--compact', default=True,
              help='Pretty print JSON output')
@click.pass_context
def evaluate(ctx, query, results_file, output, search_type, model, 
             no_executive_summary, no_inventory_ranking, pretty):
    """
    Evaluate search results for a given query.
    
    QUERY: The search query to evaluate
    RESULTS_FILE: JSON file containing search results to evaluate
    """
    try:
        # Load search results
        results_data = load_json_file(results_file)
        
        # Handle different input formats
        if isinstance(results_data, list):
            results = results_data
        elif isinstance(results_data, dict) and 'results' in results_data:
            results = results_data['results']
        else:
            raise CLIError("Results file must contain a list of results or a dict with 'results' key")
        
        if ctx.obj['verbose']:
            click.echo(f"Loaded {len(results)} search results from {results_file}")
        
        # Create evaluation engine
        config = ctx.obj['config']
        if model:
            config.default_model = model
            
        engine = SearchEvaluationEngine(config)
        
        # Check service availability
        if not engine.is_service_available():
            raise CLIError("LLM service is not available. Please check your configuration and ensure Ollama is running.")
        
        # Convert search type
        search_type_enum = None
        if search_type:
            search_type_enum = SearchType(search_type)
        
        # Create evaluation request
        request = EvaluationRequest(
            query=query,
            results=results,
            search_type=search_type_enum,
            model=model,
            include_executive_summary=not no_executive_summary,
            apply_inventory_ranking=not no_inventory_ranking
        )
        
        # Perform evaluation
        if ctx.obj['verbose']:
            click.echo(f"Evaluating query: '{query}'")
            click.echo(f"Search type: {search_type or 'auto-detect'}")
            click.echo(f"Model: {model or config.default_model}")
        
        with click.progressbar(length=1, label='Evaluating') as bar:
            result = engine.evaluate(request)
            bar.update(1)
        
        # Check result status
        if result.status != "success":
            raise CLIError(f"Evaluation failed: {result.error}")
        
        # Prepare output data
        output_data = {
            "query": result.query,
            "search_type": result.search_type.value,
            "model_used": result.model_used,
            "timestamp": datetime.now().isoformat(),
            "status": result.status,
            "summary": {
                "total_results": len(result.evaluations),
                "high_relevance": len([e for e in result.evaluations if e.get('relevance_tier') == 'High']),
                "medium_relevance": len([e for e in result.evaluations if e.get('relevance_tier') == 'Medium']),
                "low_relevance": len([e for e in result.evaluations if e.get('relevance_tier') == 'Low']),
                "inventory_aware_ranking": result.inventory_aware_ranking_applied
            },
            "evaluations": result.evaluations,
            "ranking_summary": result.ranking_summary,
            "inventory_summary": result.inventory_summary
        }
        
        if result.executive_summary:
            output_data["executive_summary"] = result.executive_summary
        
        # Output results
        if output:
            save_json_file(output_data, output, pretty)
            click.echo(f"Results saved to: {output}")
        else:
            click.echo(json.dumps(output_data, indent=2 if pretty else None, ensure_ascii=False))
        
        # Print summary
        if ctx.obj['verbose'] >= 1:
            click.echo(f"\n✅ Evaluation completed successfully!")
            click.echo(f"   Results: {len(result.evaluations)}")
            click.echo(f"   High relevance: {output_data['summary']['high_relevance']}")
            click.echo(f"   Quality score: {result.executive_summary.get('quality_score', 'N/A') if result.executive_summary else 'N/A'}")
        
    except CLIError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        if ctx.obj['debug']:
            import traceback
            traceback.print_exc()
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--output', '-o', type=click.Path(), 
              help='Output file for test results')
@click.option('--comprehensive', is_flag=True,
              help='Run comprehensive test suite')
@click.option('--quick', is_flag=True, default=True,
              help='Run quick test (default)')
@click.option('--query', default="test brake pads",
              help='Query for quick test')
@click.pass_context
def test(ctx, output, comprehensive, quick, query):
    """
    Run system tests to validate functionality.
    
    Tests the evaluation system with sample data to ensure everything
    is working correctly.
    """
    try:
        config = ctx.obj['config']
        
        if comprehensive:
            click.echo("Running comprehensive test suite...")
            test_runner = TestRunner(config)
            
            with click.progressbar(length=1, label='Testing') as bar:
                results = test_runner.run_all_tests()
                bar.update(1)
            
            # Display results
            summary = results.get('summary', {})
            click.echo(f"\n📊 Test Results:")
            click.echo(f"   Total tests: {summary.get('total_tests', 0)}")
            click.echo(f"   Passed: {summary.get('passed_tests', 0)}")
            click.echo(f"   Success rate: {summary.get('success_rate', '0%')}")
            
            # Show detailed results if verbose
            if ctx.obj['verbose'] >= 1:
                for test_category, test_results in results.items():
                    if test_category != 'summary' and isinstance(test_results, dict):
                        click.echo(f"\n{test_category}:")
                        for test_name, test_result in test_results.items():
                            status = "✅" if test_result.get('passed', False) else "❌"
                            click.echo(f"  {status} {test_name}")
            
            if output:
                save_json_file(results, output, pretty=True)
                click.echo(f"\nDetailed results saved to: {output}")
        
        else:  # Quick test
            click.echo(f"Running quick test with query: '{query}'")
            
            try:
                run_quick_test(query)
                click.echo("✅ Quick test passed!")
            except Exception as e:
                raise CLIError(f"Quick test failed: {e}")
    
    except CLIError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        if ctx.obj['debug']:
            import traceback
            traceback.print_exc()
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def validate(ctx):
    """
    Validate system configuration and connectivity.
    
    Checks configuration, service availability, and system health.
    """
    try:
        config = ctx.obj['config']
        
        click.echo("🔍 Validating system configuration...")
        
        # Validate configuration
        config_validation = ValidationUtils.validate_config(config)
        if config_validation['valid']:
            click.echo("✅ Configuration is valid")
        else:
            click.echo("❌ Configuration validation failed:")
            for error in config_validation['errors']:
                click.echo(f"   - {error}")
        
        # Check service connectivity
        click.echo("\n🌐 Checking service connectivity...")
        connectivity = ValidationUtils.validate_service_connectivity(config)
        
        if connectivity['available']:
            click.echo("✅ LLM service is available")
            if ctx.obj['verbose'] >= 1:
                models = connectivity.get('models', [])
                click.echo(f"   Available models: {models}")
                click.echo(f"   Endpoint: {connectivity['endpoint']}")
        else:
            click.echo("❌ LLM service is not available")
            if 'error' in connectivity:
                click.echo(f"   Error: {connectivity['error']}")
            click.echo(f"   Endpoint: {connectivity['endpoint']}")
        
        # Validate prompt templates
        if ctx.obj['verbose'] >= 1:
            click.echo("\n📝 Validating prompt templates...")
            template_validation = ValidationUtils.validate_prompt_templates()
            
            for search_type, validation_result in template_validation.items():
                status = "✅" if validation_result.get('is_valid', False) else "⚠️"
                click.echo(f"   {status} {search_type}")
                
                if ctx.obj['verbose'] >= 2 and not validation_result.get('is_valid', False):
                    for error in validation_result.get('errors', []):
                        click.echo(f"      Error: {error}")
                    for warning in validation_result.get('warnings', []):
                        click.echo(f"      Warning: {warning}")
        
        # Overall status
        all_valid = (config_validation['valid'] and connectivity['available'])
        if all_valid:
            click.echo(f"\n🎉 System validation passed! Ready to use.")
        else:
            click.echo(f"\n⚠️ System validation found issues. Please fix before using.")
            sys.exit(1)
    
    except Exception as e:
        if ctx.obj['debug']:
            import traceback
            traceback.print_exc()
        click.echo(f"Validation error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--format', '-f', type=click.Choice(['json', 'yaml', 'env']), 
              default='json', help='Output format')
@click.option('--output', '-o', type=click.Path(), 
              help='Output file (default: stdout)')
@click.pass_context
def config(ctx, format, output):
    """
    Display or export current configuration.
    
    Shows the current system configuration in various formats.
    """
    try:
        config = ctx.obj['config']
        
        if format == 'json':
            config_dict = {
                'ollama_api_endpoint': config.ollama_api_endpoint,
                'default_model': config.default_model,
                'timeout': config.timeout,
                'max_retries': config.max_retries,
                'debug_dir': config.debug_dir
            }
            config_output = json.dumps(config_dict, indent=2)
        
        elif format == 'yaml':
            config_output = f"""# LLM Evaluator Configuration
ollama_api_endpoint: {config.ollama_api_endpoint}
default_model: {config.default_model}
timeout: {config.timeout}
max_retries: {config.max_retries}
debug_dir: {config.debug_dir}
"""
        
        elif format == 'env':
            config_output = f"""# Environment variables for LLM Evaluator
export OLLAMA_API_ENDPOINT="{config.ollama_api_endpoint}"
export DEFAULT_MODEL="{config.default_model}"
export TIMEOUT="{config.timeout}"
export MAX_RETRIES="{config.max_retries}"
export DEBUG_DIR="{config.debug_dir}"
"""
        
        if output:
            with open(output, 'w') as f:
                f.write(config_output)
            click.echo(f"Configuration saved to: {output}")
        else:
            click.echo(config_output)
    
    except Exception as e:
        click.echo(f"Error displaying configuration: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--results-count', '-n', default=5, type=int,
              help='Number of sample results to generate')
@click.option('--output', '-o', type=click.Path(), required=True,
              help='Output file for sample results')
@click.option('--query-type', '-t', 
              type=click.Choice(['english_word', 'part_number', 'multiple_terms']),
              default='english_word', help='Type of sample query')
@click.pass_context
def generate_sample(ctx, results_count, output, query_type):
    """
    Generate sample data for testing and development.
    
    Creates sample search results that can be used for testing
    the evaluation system.
    """
    try:
        from llm.llm_evaluator import TestDataGenerator
        
        generator = TestDataGenerator()
        
        # Generate sample results
        sample_results = generator.create_sample_results(
            count=results_count, 
            include_inventory=True
        )
        
        # Create sample query based on type
        sample_queries = {
            'english_word': 'brake pads',
            'part_number': '4707Q',
            'multiple_terms': 'armada brake parts'
        }
        
        sample_data = {
            'query': sample_queries[query_type],
            'query_type': query_type,
            'timestamp': datetime.now().isoformat(),
            'results': sample_results
        }
        
        save_json_file(sample_data, output, pretty=True)
        
        click.echo(f"✅ Generated {results_count} sample results")
        click.echo(f"   Query: '{sample_data['query']}'")
        click.echo(f"   Type: {query_type}")
        click.echo(f"   Saved to: {output}")
    
    except Exception as e:
        click.echo(f"Error generating sample data: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--format', '-f', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
@click.pass_context
def status(ctx):
    """
    Show system status and health information.
    
    Displays current system status, configuration, and health metrics.
    """
    try:
        config = ctx.obj['config']
        
        # Gather status information
        connectivity = ValidationUtils.validate_service_connectivity(config)
        
        if format == 'table':
            click.echo("🚀 LLM Search Evaluator Status")
            click.echo("=" * 40)
            click.echo(f"Version: {__version__}")
            click.echo(f"Config file: {ctx.obj.get('config_file', 'Environment variables')}")
            click.echo(f"Debug mode: {'On' if ctx.obj['debug'] else 'Off'}")
            click.echo()
            click.echo("Configuration:")
            click.echo(f"  Model: {config.default_model}")
            click.echo(f"  Endpoint: {config.ollama_api_endpoint}")
            click.echo(f"  Timeout: {config.timeout}s")
            click.echo(f"  Max retries: {config.max_retries}")
            click.echo()
            click.echo("Service Status:")
            status_icon = "🟢" if connectivity['available'] else "🔴"
            click.echo(f"  LLM Service: {status_icon} {'Available' if connectivity['available'] else 'Unavailable'}")
            
            if connectivity['available']:
                models = connectivity.get('models', [])
                click.echo(f"  Available models: {len(models)}")
                if ctx.obj['verbose'] >= 1:
                    for model in models[:5]:  # Show first 5 models
                        click.echo(f"    - {model}")
                    if len(models) > 5:
                        click.echo(f"    ... and {len(models) - 5} more")
        
        elif format == 'json':
            status_data = {
                'version': __version__,
                'config': {
                    'model': config.default_model,
                    'endpoint': config.ollama_api_endpoint,
                    'timeout': config.timeout,
                    'max_retries': config.max_retries
                },
                'service': connectivity,
                'timestamp': datetime.now().isoformat()
            }
            click.echo(json.dumps(status_data, indent=2))
    
    except Exception as e:
        click.echo(f"Error checking status: {e}", err=True)
        sys.exit(1)


def main():
    """Main CLI entry point."""
    cli()


if __name__ == '__main__':
    main()
