# LLM Search Evaluator - Architecture Summary

## Overview

This document provides a comprehensive overview of the refactored LLM Search Result Evaluation System architecture, explaining how the modular design improves upon the original monolithic implementation.

## 🏗️ Architecture Principles

### SOLID Principles Applied

1. **Single Responsibility Principle (SRP)**
   - Each class has one clear, well-defined purpose
   - `InventoryAnalyzer` only handles inventory logic
   - `PromptTemplateManager` only manages prompt templates
   - `ResponseParser` only parses LLM responses

2. **Open/Closed Principle (OCP)**
   - System is open for extension, closed for modification
   - New search classifiers can be added without changing existing code
   - New LLM clients can be plugged in via the interface
   - New prompt templates can be added through the template system

3. **Liskov Substitution Principle (LSP)**
   - All implementations can be substituted for their interfaces
   - `MockLLMClient` can replace `OllamaClient` seamlessly
   - Different `ResponseParser` implementations are interchangeable

4. **Interface Segregation Principle (ISP)**
   - Small, focused interfaces instead of large monolithic ones
   - `SearchClassifier` protocol is minimal and focused
   - `LLMClient` interface only includes essential methods

5. **Dependency Inversion Principle (DIP)**
   - High-level modules don't depend on low-level modules
   - `SearchEvaluationEngine` depends on abstractions, not concrete classes
   - Easy to mock and test individual components

### Design Patterns Used

#### 1. Factory Pattern
```python
# Easy creation of different implementations
classifier = SearchClassifierFactory.create_classifier("regex")
llm_client = LLMClientFactory.create_client("ollama", config)
formatter = ResultFormatterFactory.create_formatter("standard")
```

#### 2. Builder Pattern
```python
# Flexible configuration of complex objects
engine = (EvaluationEngineBuilder()
          .with_config(custom_config)
          .with_formatter("compact")
          .with_strict_parsing(True)
          .build())
```

#### 3. Strategy Pattern
```python
# Different prompt strategies for different search types
prompt_manager.get_template(SearchType.PART_NUMBER)
prompt_manager.get_template(SearchType.ENGLISH_WORD)
```

#### 4. Template Method Pattern
```python
# Base template with customizable steps
class PromptTemplate(ABC):
    @abstractmethod
    def generate(self, query: str, results_text: str, result_count: int) -> str:
        pass
```

#### 5. Observer Pattern (Implicit)
```python
# Debug utilities can observe and log system behavior
debug_utils.dump_evaluation_debug_data(prompt, response, parsed)
```

## 📁 Module Structure

### Core Modules

#### 1. `config.py` - Configuration Management
**Responsibility**: Centralized configuration with validation
```python
@dataclass
class LLMConfig:
    ollama_api_endpoint: str = "http://localhost:11434/api/generate"
    default_model: str = "gemma3"
    timeout: int = 600
    max_retries: int = 3
    debug_dir: str = "llm_debug"
```

**Benefits**:
- Type-safe configuration
- Environment variable support
- Validation and error checking
- Easy testing with mock configs

#### 2. `search_classifier.py` - Search Type Detection
**Responsibility**: Classify queries into types (part number, English word, multi-term)
```python
class SearchClassifier(Protocol):
    def classify(self, query: str) -> SearchType
```

**Benefits**:
- Pluggable classification strategies
- Easy to add ML-based classifiers
- Clear separation from evaluation logic

#### 3. `inventory_analyzer.py` - Inventory Management
**Responsibility**: Parse inventory data and apply inventory-aware ranking
```python
class InventoryAnalyzer:
    def analyze_results(self, results: List[Dict[str, str]]) -> List[InventoryInfo]
    def apply_inventory_ranking(self, evaluations: List[Dict], inventory_data: List[InventoryInfo])
```

**Benefits**:
- Sophisticated inventory parsing
- Configurable stock thresholds
- Priority scoring for ranking
- Detailed inventory summaries

#### 4. `prompt_manager.py` - Template Management
**Responsibility**: Manage and generate prompts for different search scenarios
```python
class PromptTemplateManager:
    def get_template(self, search_type: SearchType) -> PromptTemplate
    def generate_prompt(self, search_type: SearchType, query: str, results_text: str, result_count: int) -> str
```

**Benefits**:
- Search-type specific prompts
- Template validation
- Easy prompt customization
- Separation of prompt logic from evaluation

#### 5. `llm_client.py` - LLM Interface
**Responsibility**: Abstract interface to LLM services
```python
class LLMClient(ABC):
    @abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse
    @abstractmethod
    def is_available(self) -> bool
```

**Benefits**:
- Service abstraction
- Easy mocking for tests
- Retry mechanisms
- Future support for multiple LLM providers

#### 6. `response_parser.py` - Response Processing
**Responsibility**: Parse and validate LLM responses
```python
class ResponseParser(ABC):
    @abstractmethod
    def parse(self, response: LLMResponse) -> Optional[ParsedEvaluation]
```

**Benefits**:
- Robust JSON parsing with error recovery
- Structured response validation
- Fallback mechanisms for malformed responses
- Separation of parsing concerns

#### 7. `result_formatter.py` - Data Formatting
**Responsibility**: Format search results for LLM consumption
```python
class ResultFormatter(ABC):
    @abstractmethod
    def format(self, results: List[Dict[str, str]]) -> str
```

**Benefits**:
- Multiple formatting strategies
- Clean separation of data presentation
- Easy customization for different LLM requirements

#### 8. `evaluation_engine.py` - Main Orchestrator
**Responsibility**: Coordinate all components to perform evaluations
```python
class SearchEvaluationEngine:
    def evaluate(self, request: EvaluationRequest) -> EvaluationResult
```

**Benefits**:
- Clear orchestration logic
- Dependency injection
- Comprehensive error handling
- Executive summary generation

### Supporting Modules

#### 9. `utilities.py` - Debug and Testing
**Responsibility**: Debugging, testing, and validation utilities
```python
class DebugUtils:
    def dump_prompt(self, prompt: str, filename: str = None) -> str
    def dump_evaluation_debug_data(self, prompt: str, llm_response: Dict, parsed: Dict) -> str

class TestRunner:
    def run_all_tests(self) -> Dict[str, Any]
```

**Benefits**:
- Comprehensive debugging support
- Automated testing framework
- System validation utilities
- Performance monitoring

## 🔄 Data Flow Architecture

### 1. Request Processing Flow
```
EvaluationRequest
    ↓
SearchClassifier (determine query type)
    ↓
InventoryAnalyzer (parse inventory data)
    ↓
ResultFormatter (format for LLM)
    ↓
PromptTemplateManager (generate prompt)
    ↓
LLMClient (send to LLM)
    ↓
ResponseParser (parse response)
    ↓
InventoryAnalyzer (apply inventory ranking)
    ↓
EvaluationResult
```

### 2. Component Interaction Diagram
```
┌─────────────────────────────────────────────────────────────┐
│                    SearchEvaluationEngine                    │
│                      (Orchestrator)                          │
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

## 🎯 Key Benefits of Refactored Architecture

### 1. Maintainability
- **Single Responsibility**: Each module has one clear purpose
- **Separation of Concerns**: Business logic separated from technical implementation
- **Clear Dependencies**: Easy to understand component relationships
- **Modular Testing**: Each component can be tested independently

### 2. Extensibility
- **Plugin Architecture**: Easy to add new classifiers, clients, parsers
- **Factory Pattern**: Simple creation of new implementations
- **Interface-Based Design**: Loose coupling between components
- **Template System**: Easy customization of prompts

### 3. Testability
- **Dependency Injection**: Easy mocking and testing
- **Interface Abstractions**: Clean test boundaries
- **Mock Implementations**: Built-in testing support
- **Isolation**: Components can be tested in isolation

### 4. Performance
- **Lazy Loading**: Components created only when needed
- **Caching Opportunities**: Results can be cached at component level
- **Parallel Processing**: Independent components can run concurrently
- **Resource Management**: Better control over resource usage

### 5. Error Handling
- **Layered Error Handling**: Errors handled at appropriate levels
- **Graceful Degradation**: System continues working with partial failures
- **Detailed Logging**: Component-level logging and debugging
- **Recovery Mechanisms**: Fallback strategies for failures

### 6. Configuration Management
- **Centralized Configuration**: Single source of truth for settings
- **Environment Support**: Easy deployment across environments
- **Validation**: Configuration validation at startup
- **Type Safety**: Type-safe configuration with dataclasses

## 🔧 Deployment Considerations

### 1. Development Environment
```bash
# Install in development mode
pip install -e .

# Run tests
pytest tests/

# Format code
black .
isort .
```

### 2. Production Environment
```bash
# Install package
pip install llm-search-evaluator

# Set environment variables
export OLLAMA_API_ENDPOINT="http://ollama:11434/api/generate"
export DEFAULT_MODEL="gemma3"
export TIMEOUT=600
```

### 3. Docker Deployment
```dockerfile
FROM python:3.11-slim

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY llm_evaluator/ ./llm_evaluator/
RUN pip install -e .

CMD ["python", "-m", "llm_evaluator.cli"]
```

### 4. Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llm-evaluator
spec:
  replicas: 3
  selector:
    matchLabels:
      app: llm-evaluator
  template:
    metadata:
      labels:
        app: llm-evaluator
    spec:
      containers:
      - name: llm-evaluator
        image: llm-evaluator:latest
        env:
        - name: OLLAMA_API_ENDPOINT
          value: "http://ollama-service:11434/api/generate"
```

## 📊 Performance Characteristics

### 1. Memory Usage
- **Reduced Memory Footprint**: Modular loading reduces memory usage
- **Component Lifecycle**: Components created/destroyed as needed
- **Caching Strategy**: Intelligent caching at component boundaries

### 2. Processing Speed
- **Optimized Parsing**: Efficient JSON parsing with fallbacks
- **Parallel Processing**: Independent components can run concurrently
- **Lazy Evaluation**: Work done only when needed

### 3. Scalability
- **Horizontal Scaling**: Easy to deploy multiple instances
- **Load Balancing**: Stateless design supports load balancing
- **Resource Isolation**: Components don't interfere with each other

## 🔮 Future Enhancements

### 1. Machine Learning Integration
- **ML-Based Classification**: Replace regex classifier with ML model
- **Relevance Scoring**: Use ML for more sophisticated scoring
- **Pattern Recognition**: Learn from evaluation patterns

### 2. Advanced LLM Support
- **Multiple Providers**: Support for OpenAI, Anthropic, etc.
- **Model Switching**: Dynamic model selection based on query type
- **Cost Optimization**: Choose models based on cost/performance trade-offs

### 3. Business Intelligence
- **Analytics Dashboard**: Real-time evaluation metrics
- **A/B Testing**: Compare different evaluation strategies
- **Performance Monitoring**: Track system performance over time

### 4. Integration Features
- **REST API**: HTTP API for evaluation services
- **Message Queues**: Async processing with RabbitMQ/Kafka
- **Database Integration**: Store evaluation results and analytics

## 🎓 Learning Outcomes

This refactoring demonstrates several important software engineering principles:

1. **Clean Architecture**: How to structure complex systems
2. **Design Patterns**: Practical application of common patterns
3. **Testing Strategy**: Comprehensive testing approach
4. **Configuration Management**: Professional configuration handling
5. **Error Handling**: Robust error handling and recovery
6. **Documentation**: Clear, comprehensive documentation

The modular architecture makes the system more maintainable, testable, and extensible while preserving all the functionality of the original monolithic implementation.
