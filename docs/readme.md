# LLM Search Result Evaluation System

A comprehensive, modular system for evaluating e-commerce search results using Large Language Models with inventory-aware ranking and business intelligence features.

## 🚀 Features

- **Inventory-Aware Ranking**: Automatically considers stock levels in result ranking
- **Multiple Search Types**: Supports part numbers, English words, and multi-term queries  
- **Business Intelligence**: Generates executive summaries with actionable recommendations
- **Modular Architecture**: Clean, maintainable code following SOLID principles
- **Flexible Configuration**: Easy customization of models, endpoints, and behavior
- **Comprehensive Testing**: Built-in validation and testing utilities
- **Backward Compatibility**: Seamless migration from legacy systems

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Usage Examples](#usage-examples)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Migration Guide](#migration-guide)
- [Contributing](#contributing)

## 🔧 Installation

### Prerequisites

- Python 3.8+
- [Ollama](https://ollama.ai/) running locally
- A compatible LLM model (e.g., `gemma3`, `llama2`)

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Setup Ollama

```bash
# Install and start Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve

# Pull a model
ollama pull gemma3
```

### Environment Configuration

Create a `.env` file or set environment variables:

```bash
export OLLAMA_API_ENDPOINT="http://localhost:11434/api/generate"
export DEFAULT_MODEL="gemma3"
export TIMEOUT=600
export MAX_RETRIES=3
export DEBUG_DIR="llm_debug"
```

## ⚡ Quick Start

```python
from llm_evaluator import quick_evaluate

# Your search results from web scraping
search_results = [
    {
        "title": "Premium Brake Pads",
        "part_number": "BP001",
        "vendor_part_number": "V-BP001", 
        "price": "$45.99",
        "quantity": "150",  # In stock
        "url": "https://example.com/bp001"
    },
    {
        "title": "Economy Brake Pads", 
        "part_number": "BP002",
        "vendor_part_number": "V-BP002",
        "price": "$29.99", 
        "quantity": "0",  # Out of stock
        "url": "https://example.com/bp002"
    }
]

# Evaluate with LLM
result = quick_evaluate(
    query="brake pads",
    results=search_results
)

# Check results
if result.status == "success":
    print(f"Evaluated {len(result.evaluations)} results")
    print(f"Search type: {result.search_type.value}")
    
    for evaluation in result.evaluations:
        print(f"- {evaluation['title']}: {evaluation['relevance_tier']}")
```

## 🏗️ Architecture

The system is built with a modular architecture following SOLID principles:

```
┌─────────────────────────────────────────────────────────────┐
│                    SearchEvaluationEngine                    │
│                      (Main Orchestrator)                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
    ┌─────────────────┼─────────────────────────────────────┐
    │                 │                                     │
    ▼                 ▼                                     ▼
┌─────────┐    ┌──────────────┐                    ┌──────────────┐
│ Config  │    │ Search       │                    │ Inventory    │
│ Manager │    │ Classifier   │                    │ Analyzer     │
└─────────┘    └──────────────┘                    └──────────────┘
    │                 │                                     │
    ▼                 ▼                                     ▼
┌─────────┐    ┌──────────────┐    ┌─────────────┐ ┌──────────────┐
│ LLM     │◄──►│ Prompt       │◄──►│ Result      │ │ Response     │
│ Client  │    │ Template     │    │ Formatter   │ │ Parser       │
└─────────┘    │ Manager      │    └─────────────┘ └──────────────┘
               └──────────────┘
```

### Core Components

- **SearchEvaluationEngine**: Main orchestrator that coordinates all components
- **SearchClassifier**: Determines query type (part number, English word, multi-term)
- **InventoryAnalyzer**: Handles stock levels and inventory-aware ranking
- **PromptTemplateManager**: Manages LLM prompts for different search types
- **LLMClient**: Interfaces with Ollama API
- **ResponseParser**: Parses and validates LLM responses
- **ResultFormatter**: Formats search results for LLM consumption

## 📚 Usage Examples

### Basic Usage

```python
from llm_evaluator import SearchEvaluationEngine, EvaluationRequest

engine = SearchEvaluationEngine()

request = EvaluationRequest(
    query="oil filter",
    results=your_search_results,
    include_executive_summary=True,
    apply_inventory_ranking=True
)

result = engine.evaluate(request)
```

### Custom Configuration

```python
from llm_evaluator import EvaluationEngineBuilder, LLMConfig

# Custom configuration
config = LLMConfig(
    default_model="llama2",
    timeout=300,
    max_retries=5
)

# Build custom engine
engine = (EvaluationEngineBuilder()
          .with_config(config)
          .with_formatter("compact")
          .with_strict_parsing(True)
          .build())
```

### Part Number Search

```python
from llm_evaluator import SearchType

result = quick_evaluate(
    query="4707Q",
    results=search_results,
    search_type=SearchType.PART_NUMBER
)
```

### Batch Processing

```python
engine = SearchEvaluationEngine()

for query_data in multiple_queries:
    request = EvaluationRequest(
        query=query_data["query"],
        results=query_data["results"]
    )
    result = engine.evaluate(request)
    # Process result...
```

### Backward Compatibility

```python
# Old API still works
from llm_evaluator import evaluate_search_results

result = evaluate_search_results(
    query="brake pads",
    results=search_results,
    search_type="english_word"
)
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_API_ENDPOINT` | Ollama API URL | `http://localhost:11434/api/generate` |
| `DEFAULT_MODEL` | Default LLM model | `gemma3` |
| `TIMEOUT` | Request timeout (seconds) | `600` |
| `MAX_RETRIES` | Maximum retry attempts | `3` |
| `DEBUG_DIR` | Debug output directory | `llm_debug` |

### Configuration Class

```python
from llm_evaluator import LLMConfig

# From environment
config = LLMConfig.from_environment()

# Explicit configuration
config = LLMConfig(
    ollama_api_endpoint="http://localhost:11434/api/generate",
    default_model="gemma3",
    timeout=600,
    max_retries=3,
    debug_dir="custom_debug"
)

# Validate configuration
config.validate()
```

## 📖 API Reference

### Main Classes

#### SearchEvaluationEngine

Main engine for evaluating search results.

```python
class SearchEvaluationEngine:
    def __init__(self, config: LLMConfig = None)
    def evaluate(self, request: EvaluationRequest) -> EvaluationResult
    def is_service_available(self) -> bool
    def get_available_models(self) -> List[str]
```

#### EvaluationRequest

Request object for evaluation.

```python
@dataclass
class EvaluationRequest:
    query: str
    results: List[Dict[str, str]]
    search_type: Optional[SearchType] = None
    model: Optional[str] = None
    include_executive_summary: bool = True
    apply_inventory_ranking: bool = True
```

#### EvaluationResult

Result object from evaluation.

```python
@dataclass
class EvaluationResult:
    query: str
    search_type: SearchType
    model_used: str
    evaluations: List[Dict[str, Any]]
    ranking_summary: str
    inventory_summary: Dict[str, Any]
    executive_summary: Optional[Dict[str, Any]] = None
    status: str = "success"
    error: Optional[str] = None
```

### Enums

#### SearchType

```python
class SearchType(Enum):
    ENGLISH_WORD = "english_word"
    PART_NUMBER = "part_number"
    MULTIPLE_TERMS = "multiple_terms"
```

#### InventoryStatus

```python
class InventoryStatus(Enum):
    AVAILABLE = "Available"
    LOW_STOCK = "Low Stock"
    OUT_OF_STOCK = "Out of Stock"
    UNKNOWN = "Unknown"
```

### Convenience Functions

```python
# Quick evaluation
quick_evaluate(query: str, results: List[Dict], **kwargs) -> EvaluationResult

# Create default engine
create_engine(config: LLMConfig = None) -> SearchEvaluationEngine

# Create custom engine builder
create_custom_engine() -> EvaluationEngineBuilder

# Backward compatibility
evaluate_search_results(query: str, results: List[Dict], **kwargs) -> Dict
evaluate_search_results_with_inventory(query: str, results: List[Dict], **kwargs) -> Dict
```

## 🧪 Testing

### Quick Test

```python
from llm_evaluator import run_quick_test

# Test with default settings
run_quick_test()

# Test with custom query and model
run_quick_test("custom query", "llama2")
```

### Comprehensive Testing

```python
from llm_evaluator import TestRunner

test_runner = TestRunner()
results = test_runner.run_all_tests()

print(f"Tests passed: {results['summary']['success_rate']}")
```

### Validation Utilities

```python
from llm_evaluator import ValidationUtils, LLMConfig

# Validate configuration
config = LLMConfig.from_environment()
validation = ValidationUtils.validate_config(config)

# Check service connectivity
connectivity = ValidationUtils.validate_service_connectivity(config)

# Validate prompt templates  
template_validation = ValidationUtils.validate_prompt_templates()
```

### Running Tests

```bash
# Run unit tests
pytest tests/

# Run with coverage
pytest --cov=llm_evaluator tests/

# Run specific test category
pytest tests/test_inventory.py
pytest tests/test_prompts.py
pytest tests/test_parsing.py
```

## 🔄 Migration Guide

If you're migrating from the old monolithic system, see [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for detailed instructions.

### Quick Migration

1. **No changes required** for basic usage:
   ```python
   from llm_evaluator import evaluate_search_results
   result = evaluate_search_results(query, results)  # Still works!
   ```

2. **Update imports** for advanced features:
   ```python
   # Old
   from llm_evaluator import classify_search_type
   
   # New
   from llm_evaluator import SearchClassifierFactory
   classifier = SearchClassifierFactory.create_classifier()
   ```

3. **Use new configuration system**:
   ```python
   from llm_evaluator import LLMConfig
   config = LLMConfig.from_environment()
   ```

## 🛠️ Development

### Project Structure

```
llm_evaluator/
├── __init__.py              # Public API
├── config.py                # Configuration management
├── search_classifier.py     # Search classification
├── inventory_analyzer.py    # Inventory analysis
├── prompt_manager.py        # Prompt templates
├── result_formatter.py      # Result formatting
├── llm_client.py           # LLM client interface
├── response_parser.py      # Response parsing
├── evaluation_engine.py    # Main orchestrator
└── utilities.py            # Debug and testing utilities

tests/
├── test_config.py
├── test_classifier.py
├── test_inventory.py
├── test_prompts.py
├── test_client.py
├── test_parser.py
├── test_engine.py
└── test_integration.py

examples/
├── examples.py             # Usage examples
├── benchmark.py            # Performance benchmarks
└── custom_implementations.py

docs/
├── README.md
├── MIGRATION_GUIDE.md
├── API_REFERENCE.md
└── CONTRIBUTING.md
```

### Code Quality

The project follows Python best practices:

- **Type hints** throughout the codebase
- **Docstrings** for all public methods
- **Unit tests** with >90% coverage
- **Code formatting** with Black
- **Linting** with flake8
- **Type checking** with mypy

### Design Principles

- **Single Responsibility Principle**: Each class has one clear purpose
- **Open/Closed Principle**: Easy to extend without modifying existing code
- **Dependency Inversion**: Depends on abstractions, not concrete implementations
- **Interface Segregation**: Small, focused interfaces
- **Factory Pattern**: Easy creation of different implementations
- **Builder Pattern**: Flexible configuration of complex objects

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run the test suite (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Development Setup

```bash
# Clone repository
git clone https://github.com/your-org/llm-evaluator.git
cd llm-evaluator

# Install development dependencies
pip install -r requirements.txt
pip install -e .

# Run tests
pytest

# Format code
black .
isort .

# Type checking
mypy llm_evaluator/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Ollama](https://ollama.ai/) for providing the LLM infrastructure
- The Python community for excellent libraries and tools
- Contributors and testers who helped improve the system

## 📞 Support

- **Documentation**: See the `docs/` directory
- **Issues**: Open an issue on GitHub
- **Discussions**: Use GitHub Discussions for questions
- **Examples**: Check `examples/examples.py` for usage patterns

## 🗓️ Changelog

### Version 2.0.0
- Complete architectural refactor
- Modular component design
- Enhanced inventory analysis
- Executive summary generation
- Comprehensive testing framework
- Backward compatibility maintained

### Version 1.0.0
- Initial monolithic implementation
- Basic LLM evaluation
- Simple inventory consideration
- Part number and English word support

---

**Built with ❤️ for better e-commerce search experiences**
