"""Main evaluation engine that orchestrates the LLM evaluation process."""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .config import LLMConfig
from .search_classifier import SearchClassifier, SearchClassifierFactory, SearchType
from .inventory_analyzer import InventoryAnalyzer, InventoryParser
from .prompt_manager import PromptTemplateManager
from .result_formatter import ResultProcessor, ResultFormatterFactory
from .llm_client import LLMClient, LLMClientFactory, LLMRequest
from .response_parser import ResponseParserFactory, ParsedEvaluation


@dataclass
class EvaluationRequest:
    """Request for search result evaluation."""
    query: str
    results: List[Dict[str, str]]
    search_type: Optional[SearchType] = None
    model: Optional[str] = None
    include_executive_summary: bool = True
    apply_inventory_ranking: bool = True


@dataclass
class EvaluationResult:
    """Result of search evaluation process."""
    query: str
    search_type: SearchType
    model_used: str
    evaluations: List[Dict[str, Any]]
    ranking_summary: str
    inventory_summary: Dict[str, Any]
    executive_summary: Optional[Dict[str, Any]] = None
    inventory_aware_ranking_applied: bool = False
    status: str = "success"
    error: Optional[str] = None


class SearchEvaluationEngine:
    """Main engine for evaluating search results using LLM."""
    
    def __init__(self, config: LLMConfig = None):
        self.config = config or LLMConfig.from_environment()
        self.config.validate()
        
        # Initialize components
        self.search_classifier = SearchClassifierFactory.create_classifier("regex")
        self.inventory_analyzer = InventoryAnalyzer(InventoryParser())
        self.prompt_manager = PromptTemplateManager()
        self.result_processor = ResultProcessor(
            ResultFormatterFactory.create_formatter("standard")
        )
        self.llm_client = LLMClientFactory.create_client("ollama", self.config)
        self.response_parser = ResponseParserFactory.create_parser("json")
        self.executive_summary_parser = ResponseParserFactory.create_parser("executive_summary")
    
    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        """
        Evaluate search results with inventory considerations.
        
        Args:
            request: Evaluation request containing query and results
            
        Returns:
            EvaluationResult with detailed analysis and recommendations
        """
        try:
            # Step 1: Determine search type
            search_type = request.search_type or self.search_classifier.classify(request.query)
            model = request.model or self.config.default_model
            
            print(f"Evaluating query: '{request.query}' (Type: {search_type.value})")
            print(f"Results count: {len(request.results)}")
            
            # Step 2: Analyze inventory
            inventory_data = self.inventory_analyzer.analyze_results(request.results)
            inventory_summary = self.inventory_analyzer.generate_inventory_summary(inventory_data)
            
            # Step 3: Format results for LLM
            results_text = self.result_processor.process_and_format(request.results)
            
            # Step 4: Generate and send prompt
            prompt = self.prompt_manager.generate_prompt(
                search_type, request.query, results_text, len(request.results)
            )
            
            llm_request = LLMRequest(prompt=prompt, model=model)
            llm_response = self.llm_client.generate(llm_request)
            
            # Step 5: Parse LLM response
            parsed_evaluation = self.response_parser.parse(llm_response)
            
            if not parsed_evaluation:
                return EvaluationResult(
                    query=request.query,
                    search_type=search_type,
                    model_used=model,
                    evaluations=[],
                    ranking_summary="",
                    inventory_summary=inventory_summary,
                    status="error",
                    error="Failed to parse LLM response"
                )
            
            # Step 6: Apply inventory-aware ranking if requested
            evaluations = parsed_evaluation.evaluations
            if request.apply_inventory_ranking:
                evaluations = self.inventory_analyzer.apply_inventory_ranking(
                    evaluations, inventory_data
                )
            
            # Step 7: Generate executive summary if requested
            executive_summary = None
            if request.include_executive_summary:
                executive_summary = self._generate_executive_summary(
                    request.query, parsed_evaluation, model
                )
            
            return EvaluationResult(
                query=request.query,
                search_type=search_type,
                model_used=model,
                evaluations=evaluations,
                ranking_summary=parsed_evaluation.ranking_summary,
                inventory_summary=inventory_summary,
                executive_summary=executive_summary,
                inventory_aware_ranking_applied=request.apply_inventory_ranking,
                status="success"
            )
            
        except Exception as e:
            print(f"Error in evaluation: {e}")
            return EvaluationResult(
                query=request.query,
                search_type=SearchType.ENGLISH_WORD,  # Default
                model_used=request.model or self.config.default_model,
                evaluations=[],
                ranking_summary="",
                inventory_summary={},
                status="error",
                error=str(e)
            )
    
    def _generate_executive_summary(self, query: str, evaluation: ParsedEvaluation, model: str) -> Optional[Dict[str, Any]]:
        """Generate executive summary for the evaluation."""
        try:
            print("Generating executive summary...")
            
            # Create summary prompt
            initial_analysis = json.dumps({
                "search_analysis": evaluation.search_analysis,
                "evaluations": evaluation.evaluations,
                "ranking_summary": evaluation.ranking_summary
            }, indent=2)
            
            summary_prompt = self.prompt_manager.generate_executive_summary_prompt(
                query, initial_analysis
            )
            
            # Send to LLM
            llm_request = LLMRequest(prompt=summary_prompt, model=model)
            llm_response = self.llm_client.generate(llm_request)
            
            # Parse response
            summary = self.executive_summary_parser.parse(llm_response)
            
            if summary:
                print("✅ Executive summary generated successfully")
                return summary
            else:
                print("❌ Failed to parse executive summary")
                return None
                
        except Exception as e:
            print(f"Error generating executive summary: {e}")
            return None
    
    def is_service_available(self) -> bool:
        """Check if the LLM service is available."""
        return self.llm_client.is_available()
    
    def get_available_models(self) -> List[str]:
        """Get list of available models (if supported by client)."""
        if hasattr(self.llm_client, 'get_available_models'):
            return self.llm_client.get_available_models()
        return [self.config.default_model]


# Backward compatibility functions
def evaluate_search_results_with_inventory(
    query: str, 
    results: List[Dict[str, str]], 
    search_type: Optional[str] = None,
    model: Optional[str] = None,
    apply_post_ranking: bool = True,
    api_endpoint: Optional[str] = None,
    timeout: Optional[int] = None,
    max_retries: Optional[int] = None
) -> Dict[str, Any]:
    """
    Backward compatible function for existing code.
    
    Args:
        query: Search query
        results: List of search results
        search_type: Optional search type override
        model: Model to use
        apply_post_ranking: Whether to apply inventory ranking
        api_endpoint: API endpoint (for config override)
        timeout: Request timeout (for config override)
        max_retries: Max retry attempts (for config override)
        
    Returns:
        Dictionary with evaluation results
    """
    # Create config with any overrides
    config = LLMConfig.from_environment()
    if api_endpoint:
        config.ollama_api_endpoint = api_endpoint
    if timeout:
        config.timeout = timeout
    if max_retries:
        config.max_retries = max_retries
    
    # Convert search_type string to enum if provided
    search_type_enum = None
    if search_type:
        try:
            search_type_enum = SearchType(search_type)
        except ValueError:
            print(f"Unknown search type: {search_type}, will auto-detect")
    
    # Create evaluation engine and request
    engine = SearchEvaluationEngine(config)
    request = EvaluationRequest(
        query=query,
        results=results,
        search_type=search_type_enum,
        model=model,
        apply_inventory_ranking=apply_post_ranking
    )
    
    # Evaluate and convert to old format
    result = engine.evaluate(request)
    
    return {
        "query": result.query,
        "search_type": result.search_type.value,
        "model_used": result.model_used,
        "evaluations": result.evaluations,
        "ranking_summary": result.ranking_summary,
        "inventory_aware_ranking_applied": result.inventory_aware_ranking_applied,
        "status": result.status,
        "error": result.error,
        "executive_summary": result.executive_summary
    }


def evaluate_search_results(
    query: str, 
    results: List[Dict[str, str]], 
    search_type: Optional[str] = None, 
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Simple backward compatible function.
    """
    return evaluate_search_results_with_inventory(
        query, results, search_type, model, apply_post_ranking=True
    )


class EvaluationEngineBuilder:
    """Builder pattern for creating customized evaluation engines."""
    
    def __init__(self):
        self._config = LLMConfig.from_environment()
        self._classifier_type = "regex"
        self._formatter_type = "standard"
        self._client_type = "ollama"
        self._parser_strict = False
    
    def with_config(self, config: LLMConfig) -> 'EvaluationEngineBuilder':
        """Set custom configuration."""
        self._config = config
        return self
    
    def with_classifier(self, classifier_type: str) -> 'EvaluationEngineBuilder':
        """Set search classifier type."""
        self._classifier_type = classifier_type
        return self
    
    def with_formatter(self, formatter_type: str) -> 'EvaluationEngineBuilder':
        """Set result formatter type."""
        self._formatter_type = formatter_type
        return self
    
    def with_client(self, client_type: str) -> 'EvaluationEngineBuilder':
        """Set LLM client type."""
        self._client_type = client_type
        return self
    
    def with_strict_parsing(self, strict: bool = True) -> 'EvaluationEngineBuilder':
        """Enable strict response parsing."""
        self._parser_strict = strict
        return self
    
    def build(self) -> SearchEvaluationEngine:
        """Build the evaluation engine."""
        engine = SearchEvaluationEngine(self._config)
        
        # Override components if needed
        if self._classifier_type != "regex":
            engine.search_classifier = SearchClassifierFactory.create_classifier(self._classifier_type)
        
        if self._formatter_type != "standard":
            formatter = ResultFormatterFactory.create_formatter(self._formatter_type)
            engine.result_processor = ResultProcessor(formatter)
        
        if self._client_type != "ollama":
            engine.llm_client = LLMClientFactory.create_client(self._client_type, self._config)
        
        if self._parser_strict:
            engine.response_parser = ResponseParserFactory.create_parser("json", strict=True)
        
        return engine
