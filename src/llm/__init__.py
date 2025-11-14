"""
LLM Search Result Evaluation System

A comprehensive system for evaluating e-commerce search results using Large Language Models,
with inventory-aware ranking and business intelligence features.

Main Components:
- SearchEvaluationEngine: Main orchestrator for the evaluation process
- InventoryAnalyzer: Handles inventory data and stock-aware ranking
- PromptTemplateManager: Manages LLM prompts for different search types
- ResponseParser: Parses and validates LLM responses
- Configuration and utilities for debugging and testing

Usage Examples:

Simple evaluation:
    from llm_evaluator import SearchEvaluationEngine, EvaluationRequest
    
    engine = SearchEvaluationEngine()
    request = EvaluationRequest(query="brake pads", results=search_results)
    result = engine.evaluate(request)

Backward compatible usage:
    from llm_evaluator import evaluate_search_results
    
    result = evaluate_search_results("brake pads", search_results)

Advanced configuration:
    from llm_evaluator import EvaluationEngineBuilder, LLMConfig
    
    config = LLMConfig(default_model="llama2", timeout=300)
    engine = EvaluationEngineBuilder().with_config(config).build()
"""

# Core evaluation classes
from .evaluation_engine import (
    SearchEvaluationEngine,
    EvaluationRequest,
    EvaluationResult,
    EvaluationEngineBuilder,
    # Backward compatibility functions
    evaluate_search_results,
    evaluate_search_results_with_inventory
)

# Configuration
from .config import LLMConfig

# Search classification
from .search_classifier import (
    SearchType,
    SearchClassifier,
    RegexSearchClassifier,
    SearchClassifierFactory
)

# Inventory analysis
from .inventory_analyzer import (
    InventoryStatus,
    InventoryInfo,
    InventoryParser,
    InventoryAnalyzer
)

# Prompt management
from .prompt_manager import (
    PromptTemplate,
    PromptTemplateManager,
    PromptValidator
)

# Result formatting
from .result_formatter import (
    ResultFormatter,
    StandardResultFormatter,
    ResultFormatterFactory,
    ResultProcessor
)

# LLM client interface
from .llm_client import (
    LLMClient,
    OllamaClient,
    LLMRequest,
    LLMResponse,
    LLMClientFactory
)

# Response parsing
from .response_parser import (
    ResponseParser,
    JSONResponseParser,
    ExecutiveSummaryParser,
    ParsedEvaluation,
    ResponseParserFactory
)

# Utilities
from .utilities import (
    DebugUtils,
    TestDataGenerator,
    ValidationUtils,
    TestRunner,
    run_quick_test
)

# Version info
__version__ = "2.0.0"
__author__ = "Tekin Tezgiden"
__description__ = "Advanced LLM-based search result evaluation with inventory awareness"

# Public API shortcuts
def create_engine(config=None):
    """Create a default evaluation engine."""
    return SearchEvaluationEngine(config)

def create_custom_engine():
    """Create a builder for custom engine configuration."""
    return EvaluationEngineBuilder()

def quick_evaluate(query, results, **kwargs):
    """Quick evaluation with default settings."""
    engine = create_engine()
    request = EvaluationRequest(query=query, results=results, **kwargs)
    return engine.evaluate(request)

# Export main classes for easy import
__all__ = [
    # Core classes
    'SearchEvaluationEngine',
    'EvaluationRequest', 
    'EvaluationResult',
    'EvaluationEngineBuilder',
    
    # Configuration
    'LLMConfig',
    
    # Enums
    'SearchType',
    'InventoryStatus',
    
    # Main components
    'InventoryAnalyzer',
    'PromptTemplateManager',
    'ResultProcessor',
    'OllamaClient',
    'JSONResponseParser',
    
    # Utilities
    'DebugUtils',
    'TestRunner',
    'ValidationUtils',
    
    # Convenience functions
    'evaluate_search_results',
    'evaluate_search_results_with_inventory',
    'create_engine',
    'create_custom_engine', 
    'quick_evaluate',
    'run_quick_test',
    
    # Version
    '__version__'
]

# Configuration validation on import
def _validate_environment():
    """Validate the environment on import."""
    try:
        config = LLMConfig.from_environment()
        config.validate()
        return True
    except Exception as e:
        print(f"⚠️ Configuration warning: {e}")
        return False

# Validate environment on import (non-blocking)
_validate_environment()

# Module-level docstring for the package
"""
LLM Search Result Evaluation System Architecture:

┌─────────────────────────────────────────────────────────────┐
│                    SearchEvaluationEngine                    │
│                      (Main Orchestrator)                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
    ┌─────────────────┼─────────────────────────────────────┐
    │                 │                                     │
    ▼                 ▼                                     ▼
┌─────────┐    ┌──────────────┐                    ┌──────────────┐
│ Config  │    │Search        │                    │ Inventory    │
│ Manager │    │Classifier    │                    │ Analyzer     │
└─────────┘    └──────────────┘                    └──────────────┘
    │                 │                                     │
    ▼                 ▼                                     ▼
┌─────────┐    ┌──────────────┐    ┌─────────────┐ ┌──────────────┐
│LLM      │    │Prompt        │    │Result       │ │Response      │
│Client   │◄──►│Template      │◄──►│Formatter    │ │Parser        │
└─────────┘    │Manager       │    └─────────────┘ └──────────────┘
               └──────────────┘

Key Design Principles:
- Single Responsibility: Each class has one clear purpose
- Dependency Injection: Components are loosely coupled
- Factory Pattern: Easy creation of different implementations
- Builder Pattern: Flexible configuration of complex objects
- Protocol/Interface: Clear contracts between components
- Backward Compatibility: Maintains existing API while adding new features
"""
