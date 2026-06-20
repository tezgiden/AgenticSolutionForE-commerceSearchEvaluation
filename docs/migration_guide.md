# Migration Guide: From Monolithic to Refactored LLM Evaluator

This guide helps you migrate from the old `llm_evaluator.py` monolithic file to the new modular architecture.

## Overview of Changes

### Before (Monolithic)
```
llm_evaluator.py (2000+ lines)
├── Configuration constants
├── Search classification function
├── Prompt templates (huge strings)
├── Result formatting
├── Inventory parsing
├── LLM API calls
├── Response parsing
├── Main evaluation function
└── Test functions
```

### After (Modular)
```
llm_evaluator/
├── __init__.py              # Public API
├── config.py                # Configuration management
├── search_classifier.py     # Search type classification
├── inventory_analyzer.py    # Inventory management
├── prompt_manager.py        # Prompt templates
├── result_formatter.py      # Result formatting
├── llm_client.py           # LLM client interface
├── response_parser.py      # Response parsing
├── evaluation_engine.py    # Main orchestrator
└── utilities.py            # Debug and testing
```

## Migration Steps

### Step 1: Update Imports

**Old Code:**
```python
from llm_evaluator import evaluate_search_results_with_inventory
from llm_evaluator import classify_search_type
from llm_evaluator import parse_inventory_quantity
```

**New Code:**
```python
# For backward compatibility (no changes needed)
from llm_evaluator import evaluate_search_results_with_inventory

# Or use the new API
from llm_evaluator import SearchEvaluationEngine, EvaluationRequest

# For specific functionality
from llm_evaluator import SearchClassifier, InventoryAnalyzer
```

### Step 2: Update Function Calls

#### Basic Evaluation (No Changes Required)

**Old & New (backward compatible):**
```python
result = evaluate_search_results(query, results)
```

#### Advanced Evaluation

**Old Code:**
```python
result = evaluate_search_results_with_inventory(
    query="brake pads",
    results=search_results,
    search_type="english_word",
    model="gemma3",
    apply_post_ranking=True,
    api_endpoint="http://localhost:11434/api/generate",
    timeout=600,
    max_retries=3
)
```

**New Code (Option 1 - Backward Compatible):**
```python
result = evaluate_search_results_with_inventory(
    query="brake pads",
    results=search_results,
    search_type="english_word",
    model="gemma3",
    apply_post_ranking=True,
    api_endpoint="http://localhost:11434/api/generate",
    timeout=600,
    max_retries=3
)
```

**New Code (Option 2 - Modern API):**
```python
from llm_evaluator import SearchEvaluationEngine, EvaluationRequest, LLMConfig, SearchType

# Configure once
config = LLMConfig(
    ollama_api_endpoint="http://localhost:11434/api/generate",
    timeout=600,
    max_retries=3,
    default_model="gemma3"
)

# Create engine
engine = SearchEvaluationEngine(config)

# Create request
request = EvaluationRequest(
    query="brake pads",
    results=search_results,
    search_type=SearchType.ENGLISH_WORD,
    model="gemma3",
    apply_inventory_ranking=True
)

# Evaluate
result = engine.evaluate(request)
```

### Step 3: Update Configuration

**Old Code:**
```python
# Global constants
OLLAMA_API_ENDPOINT = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "gemma3"
TIMEOUT = 600
MAX_RETRIES = 3
```

**New Code:**
```python
from llm_evaluator import LLMConfig

# Option 1: Use environment variables
config = LLMConfig.from_environment()

# Option 2: Explicit configuration
config = LLMConfig(
    ollama_api_endpoint="http://localhost:11434/api/generate",
    default_model="gemma3",
    timeout=600,
    max_retries=3
)
```

### Step 4: Update Direct Function Usage

#### Search Classification

**Old Code:**
```python
from llm_evaluator import classify_search_type
search_type = classify_search_type("brake pads")
```

**New Code:**
```python
from llm_evaluator import SearchClassifierFactory
classifier = SearchClassifierFactory.create_classifier("regex")
search_type = classifier.classify("brake pads")
```

#### Inventory Parsing

**Old Code:**
```python
from llm_evaluator import parse_inventory_quantity
quantity, status = parse_inventory_quantity("150")
```

**New Code:**
```python
from llm_evaluator import InventoryParser
parser = InventoryParser()
inventory_info = parser.parse("150")
print(inventory_info.quantity, inventory_info.status)
```

#### Prompt Generation

**Old Code:**
```python
from llm_evaluator import get_enhanced_prompt_template
template = get_enhanced_prompt_template("english_word")
prompt = template.format(query="test", results_text="...", search_result_count=5)
```

**New Code:**
```python
from llm_evaluator import PromptTemplateManager, SearchType
manager = PromptTemplateManager()
prompt = manager.generate_prompt(SearchType.ENGLISH_WORD, "test", "...", 5)
```

### Step 5: Update Testing Code

**Old Code:**
```python
from llm_evaluator import test_enhanced_evaluation
test_enhanced_evaluation("gemma3")
```

**New Code:**
```python
from llm_evaluator import TestRunner, run_quick_test

# Quick test
run_quick_test("test query", "gemma3")

# Comprehensive testing
test_runner = TestRunner()
results = test_runner.run_all_tests()
```

## Key Benefits of Migration

### 1. Better Maintainability
- Each component has a single responsibility
- Easier to test individual components
- Clearer code organization

### 2. Enhanced Flexibility
- Easy to swap implementations (e.g., different LLM clients)
- Configuration through dependency injection
- Support for multiple prompt strategies

### 3. Improved Error Handling
- Specific error types for different failures
- Better error recovery mechanisms
- Detailed logging and debugging

### 4. Advanced Features
- Builder pattern for complex configurations
- Factory patterns for easy customization
- Protocol-based interfaces for extensibility

## Common Migration Issues

### Issue 1: Import Errors

**Problem:**
```python
ImportError: cannot import name 'some_function' from 'llm_evaluator'
```

**Solution:**
Check the new public API in `__init__.py`. Some internal functions are no longer exposed.

### Issue 2: Configuration Changes

**Problem:**
Global configuration variables no longer work.

**Solution:**
Use the `LLMConfig` class:
```python
from llm_evaluator import LLMConfig
config = LLMConfig(timeout=300, max_retries=5)
```

### Issue 3: Different Return Types

**Problem:**
The new API returns different objects.

**Solution:**
Use backward compatibility functions or update your code to handle the new `EvaluationResult` type:

```python
# Old way (still works)
result = evaluate_search_results(query, results)
evaluations = result.get('evaluations', [])

# New way
from llm_evaluator import quick_evaluate
result = quick_evaluate(query, results)
evaluations = result.evaluations  # Direct attribute access
```

## Advanced Migration Examples

### Custom LLM Client

If you were using a custom LLM client:

**Old Code:**
```python
def custom_query_ollama(prompt, model):
    # Custom implementation
    pass
```

**New Code:**
```python
from llm_evaluator import LLMClient, LLMRequest, LLMResponse

class CustomLLMClient(LLMClient):
    def generate(self, request: LLMRequest) -> LLMResponse:
        # Your custom implementation
        pass
    
    def is_available(self) -> bool:
        return True

# Use with engine
from llm_evaluator import EvaluationEngineBuilder
engine = (EvaluationEngineBuilder()
          .with_client("custom")  # Register your client
          .build())
```

### Custom Prompt Templates

**Old Code:**
```python
# Modify global template strings
CUSTOM_TEMPLATE = "Your custom template..."
```

**New Code:**
```python
from llm_evaluator import PromptTemplate

class CustomPromptTemplate(PromptTemplate):
    def generate(self, query, results_text, result_count, **kwargs):
        return f"Custom template for {query}..."

# Use with prompt manager
```

## Testing Your Migration

Run the following tests to ensure your migration is successful:

```python
# 1. Test backward compatibility
from llm_evaluator import evaluate_search_results
result = evaluate_search_results("test", [{"title": "test"}])
assert result['status'] == 'success'

# 2. Test new API
from llm_evaluator import quick_evaluate
result = quick_evaluate("test", [{"title": "test"}])
assert result.status == 'success'

# 3. Test configuration
from llm_evaluator import LLMConfig
config = LLMConfig()
assert config.validate()

# 4. Run comprehensive tests
from llm_evaluator import run_quick_test
run_quick_test()
```

## Support and Troubleshooting

If you encounter issues during migration:

1. **Check the examples.py file** for usage patterns
2. **Use the validation utilities** to check your configuration
3. **Enable debug mode** to see detailed logging
4. **Check the test suite** for expected behavior

```python
from llm_evaluator import ValidationUtils, DebugUtils

# Validate your setup
validation = ValidationUtils.validate_config(your_config)
connectivity = ValidationUtils.validate_service_connectivity(your_config)

# Enable debugging
debug = DebugUtils()
debug.dump_prompt(your_prompt)
```

## Timeline Recommendations

1. **Phase 1 (Immediate)**: Use backward compatibility functions
2. **Phase 2 (1-2 weeks)**: Migrate to new configuration system
3. **Phase 3 (1 month)**: Adopt new API patterns
4. **Phase 4 (Ongoing)**: Leverage advanced features and customizations

The modular architecture will make future updates and customizations much easier!
