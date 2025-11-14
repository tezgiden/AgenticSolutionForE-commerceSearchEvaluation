"""
Test framework for the LLM Evaluation Engine.

This file demonstrates how to write comprehensive tests for the refactored system,
including unit tests, integration tests, and mocks.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

# Import our modules
from llm import (
    SearchEvaluationEngine,
    EvaluationRequest,
    EvaluationResult,
    LLMConfig,
    SearchType,
    InventoryStatus,
    InventoryInfo,
    LLMRequest,
    LLMResponse,
    ParsedEvaluation
)
from llm.search_classifier import RegexSearchClassifier
from llm.inventory_analyzer import InventoryParser, InventoryAnalyzer
from llm.llm_client import MockLLMClient
from llm.response_parser import JSONResponseParser


class TestLLMConfig:
    """Test configuration management."""
    
    def test_config_creation_with_defaults(self):
        """Test creating config with default values."""
        config = LLMConfig()
        
        assert config.ollama_api_endpoint == "http://localhost:11434/api/generate"
        assert config.default_model == "gemma3"
        assert config.timeout == 600
        assert config.max_retries == 3
    
    def test_config_creation_with_custom_values(self):
        """Test creating config with custom values."""
        config = LLMConfig(
            ollama_api_endpoint="http://custom:8080/api",
            default_model="llama2",
            timeout=300,
            max_retries=5
        )
        
        assert config.ollama_api_endpoint == "http://custom:8080/api"
        assert config.default_model == "llama2"
        assert config.timeout == 300
        assert config.max_retries == 5
    
    def test_config_validation_success(self):
        """Test successful config validation."""
        config = LLMConfig()
        assert config.validate() is True
    
    def test_config_validation_failure(self):
        """Test config validation with invalid values."""
        config = LLMConfig(timeout=-1)
        
        with pytest.raises(ValueError, match="Timeout must be positive"):
            config.validate()
    
    @patch.dict('os.environ', {
        'OLLAMA_API_ENDPOINT': 'http://env:9999/api',
        'DEFAULT_MODEL': 'env_model',
        'TIMEOUT': '999',
        'MAX_RETRIES': '7'
    })
    def test_config_from_environment(self):
        """Test creating config from environment variables."""
        config = LLMConfig.from_environment()
        
        assert config.ollama_api_endpoint == 'http://env:9999/api'
        assert config.default_model == 'env_model'
        assert config.timeout == 999
        assert config.max_retries == 7


class TestSearchClassifier:
    """Test search type classification."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.classifier = RegexSearchClassifier()
    
    def test_classify_english_word(self):
        """Test classification of English words."""
        test_cases = [
            "brake",
            "gasket",
            "filter",
            "bearing"
        ]
        
        for query in test_cases:
            result = self.classifier.classify(query)
            assert result == SearchType.ENGLISH_WORD
    
    def test_classify_part_number(self):
        """Test classification of part numbers."""
        test_cases = [
            "4707Q",
            "BP-001",
            "12345",
            "ABC/123",
            "XYZ-456-789"
        ]
        
        for query in test_cases:
            result = self.classifier.classify(query)
            assert result == SearchType.PART_NUMBER
    
    def test_classify_multiple_terms(self):
        """Test classification of multiple terms."""
        test_cases = [
            "brake pads",
            "oil filter",
            "spark plugs",
            "armada 4707Q"
        ]
        
        for query in test_cases:
            result = self.classifier.classify(query)
            assert result == SearchType.MULTIPLE_TERMS
    
    def test_classify_edge_cases(self):
        """Test edge cases in classification."""
        # Empty string
        assert self.classifier.classify("") == SearchType.ENGLISH_WORD
        
        # Whitespace only
        assert self.classifier.classify("   ") == SearchType.ENGLISH_WORD
        
        # Single character
        assert self.classifier.classify("A") == SearchType.ENGLISH_WORD
        assert self.classifier.classify("1") == SearchType.PART_NUMBER


class TestInventoryAnalyzer:
    """Test inventory analysis functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = InventoryParser()
        self.analyzer = InventoryAnalyzer(self.parser)
    
    def test_inventory_parser_numeric_values(self):
        """Test parsing numeric inventory values."""
        test_cases = [
            ("0", 0, InventoryStatus.OUT_OF_STOCK),
            ("5", 5, InventoryStatus.LOW_STOCK),
            ("50", 50, InventoryStatus.AVAILABLE),
            ("100", 100, InventoryStatus.AVAILABLE),
        ]
        
        for quantity_str, expected_qty, expected_status in test_cases:
            result = self.parser.parse(quantity_str)
            assert result.quantity == expected_qty
            assert result.status == expected_status
            assert result.raw_value == quantity_str
    
    def test_inventory_parser_text_values(self):
        """Test parsing text-based inventory values."""
        test_cases = [
            ("N/A", 0, InventoryStatus.UNKNOWN),
            ("out of stock", 0, InventoryStatus.OUT_OF_STOCK),
            ("in stock", 999, InventoryStatus.AVAILABLE),
            ("low stock", 1, InventoryStatus.LOW_STOCK),
            ("limited", 1, InventoryStatus.LOW_STOCK),
        ]
        
        for quantity_str, expected_qty, expected_status in test_cases:
            result = self.parser.parse(quantity_str)
            assert result.quantity == expected_qty
            assert result.status == expected_status
    
    def test_inventory_info_properties(self):
        """Test InventoryInfo computed properties."""
        # Available inventory
        info_available = InventoryInfo(50, InventoryStatus.AVAILABLE, "50")
        assert info_available.is_available is True
        assert info_available.priority_score == 150  # 100 + 50
        
        # Out of stock
        info_out = InventoryInfo(0, InventoryStatus.OUT_OF_STOCK, "0")
        assert info_out.is_available is False
        assert info_out.priority_score == 0  # 0 + 0
        
        # Low stock
        info_low = InventoryInfo(3, InventoryStatus.LOW_STOCK, "3")
        assert info_low.is_available is True
        assert info_low.priority_score == 53  # 50 + 3
    
    def test_analyze_results(self):
        """Test analyzing a list of search results."""
        results = [
            {"title": "Product 1", "quantity": "100"},
            {"title": "Product 2", "quantity": "0"},
            {"title": "Product 3", "quantity": "N/A"},
            {"title": "Product 4", "quantity": "5"},
        ]
        
        inventory_data = self.analyzer.analyze_results(results)
        
        assert len(inventory_data) == 4
        assert inventory_data[0].status == InventoryStatus.AVAILABLE
        assert inventory_data[1].status == InventoryStatus.OUT_OF_STOCK
        assert inventory_data[2].status == InventoryStatus.UNKNOWN
        assert inventory_data[3].status == InventoryStatus.LOW_STOCK
    
    def test_generate_inventory_summary(self):
        """Test generating inventory summary statistics."""
        inventory_data = [
            InventoryInfo(100, InventoryStatus.AVAILABLE, "100"),
            InventoryInfo(0, InventoryStatus.OUT_OF_STOCK, "0"),
            InventoryInfo(5, InventoryStatus.LOW_STOCK, "5"),
            InventoryInfo(0, InventoryStatus.UNKNOWN, "N/A"),
        ]
        
        summary = self.analyzer.generate_inventory_summary(inventory_data)
        
        assert summary["total_results"] == 4
        assert summary["total_quantity"] == 105
        assert summary["average_quantity"] == 26.25
        assert summary["distribution"]["Available"]["count"] == 1
        assert summary["distribution"]["Out of Stock"]["count"] == 1
        assert summary["distribution"]["Low Stock"]["count"] == 1
        assert summary["distribution"]["Unknown"]["count"] == 1


class TestLLMClient:
    """Test LLM client functionality."""
    
    def test_mock_llm_client(self):
        """Test mock LLM client for testing."""
        mock_client = MockLLMClient()
        
        request = LLMRequest(prompt="test prompt", model="test_model")
        response = mock_client.generate(request)
        
        assert response.success is True
        assert response.model == "test_model"
        assert "search_analysis" in response.content
        assert mock_client.is_available() is True
    
    def test_llm_request_creation(self):
        """Test LLM request object creation."""
        request = LLMRequest(
            prompt="Test prompt",
            model="gemma3",
            temperature=0.5,
            stream=False
        )
        
        assert request.prompt == "Test prompt"
        assert request.model == "gemma3"
        assert request.temperature == 0.5
        assert request.stream is False
    
    def test_llm_response_creation(self):
        """Test LLM response object creation."""
        response = LLMResponse(
            content="Test response",
            model="gemma3",
            success=True,
            metadata={"test": "data"}
        )
        
        assert response.content == "Test response"
        assert response.model == "gemma3"
        assert response.success is True
        assert response.metadata["test"] == "data"


class TestResponseParser:
    """Test response parsing functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = JSONResponseParser()
    
    def test_parse_valid_json_response(self):
        """Test parsing a valid JSON response."""
        mock_response_content = '''
        {
            "search_analysis": {
                "query": "test_query",
                "total_results": 2
            },
            "evaluations": [
                {
                    "result_index": 0,
                    "relevance_tier": "High",
                    "justification": "Test justification"
                },
                {
                    "result_index": 1,
                    "relevance_tier": "Medium", 
                    "justification": "Another justification"
                }
            ],
            "ranking_summary": "Test summary",
            "quality_score": "8",
            "conversion_likelihood": "High"
        }
        '''
        
        mock_llm_response = LLMResponse(
            content=mock_response_content,
            model="test_model",
            success=True
        )
        
        parsed = self.parser.parse(mock_llm_response)
        
        assert parsed is not None
        assert isinstance(parsed, ParsedEvaluation)
        assert len(parsed.evaluations) == 2
        assert parsed.evaluations[0]["relevance_tier"] == "High"
        assert parsed.ranking_summary == "Test summary"
    
    def test_parse_json_with_markdown(self):
        """Test parsing JSON wrapped in markdown code blocks."""
        mock_response_content = '''
        Here's the evaluation:
        
        ```json
        {
            "search_analysis": {"query": "test", "total_results": 1},
            "evaluations": [
                {"result_index": 0, "relevance_tier": "High", "justification": "Test"}
            ],
            "ranking_summary": "Summary"
        }
        ```
        
        End of response.
        '''
        
        mock_llm_response = LLMResponse(
            content=mock_response_content,
            model="test_model",
            success=True
        )
        
        parsed = self.parser.parse(mock_llm_response)
        
        assert parsed is not None
        assert len(parsed.evaluations) == 1
    
    def test_parse_malformed_json(self):
        """Test parsing malformed JSON with recovery."""
        mock_response_content = '''
        {
            "search_analysis": {
                "query": "test",
                "total_results": 1
            }
            "evaluations": [
                {
                    "result_index": 0,
                    "relevance_tier": "High",
                    "justification": "Missing comma above"
                }
            ]
        }
        '''
        
        mock_llm_response = LLMResponse(
            content=mock_response_content,
            model="test_model",
            success=True
        )
        
        # Should attempt to fix and parse
        parsed = self.parser.parse(mock_llm_response)
        
        # Might succeed with fixes or fall back to manual extraction
        assert parsed is not None
    
    def test_parse_failed_response(self):
        """Test parsing when LLM response failed."""
        failed_response = LLMResponse(
            content="",
            model="test_model",
            success=False,
            error_message="Connection failed"
        )
        
        parsed = self.parser.parse(failed_response)
        assert parsed is None


class TestEvaluationEngine:
    """Test the main evaluation engine."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = LLMConfig()
        
        # Create mock components
        self.mock_search_results = [
            {
                "title": "Test Product 1",
                "part_number": "TP001",
                "vendor_part_number": "V-TP001",
                "quantity": "100",
                "price": "$25.99"
            },
            {
                "title": "Test Product 2", 
                "part_number": "TP002",
                "vendor_part_number": "V-TP002",
                "quantity": "0",
                "price": "$35.99"
            }
        ]
    
    @patch('llm_evaluator.evaluation_engine.LLMClientFactory')
    @patch('llm_evaluator.evaluation_engine.ResponseParserFactory')
    def test_engine_initialization(self, mock_parser_factory, mock_client_factory):
        """Test engine initialization with mocked dependencies."""
        # Mock the factories
        mock_client_factory.create_client.return_value = MockLLMClient()
        mock_parser_factory.create_parser.return_value = JSONResponseParser()
        
        engine = SearchEvaluationEngine(self.config)
        
        assert engine.config == self.config
        assert engine.search_classifier is not None
        assert engine.inventory_analyzer is not None
        assert engine.prompt_manager is not None
    
    @patch('llm_evaluator.evaluation_engine.LLMClientFactory')
    @patch('llm_evaluator.evaluation_engine.ResponseParserFactory')
    def test_successful_evaluation(self, mock_parser_factory, mock_client_factory):
        """Test successful evaluation end-to-end."""
        # Set up mocks
        mock_client = MockLLMClient()
        mock_client_factory.create_client.return_value = mock_client
        
        mock_parser = Mock()
        mock_parser.parse.return_value = ParsedEvaluation(
            search_analysis={"query": "test", "total_results": 2},
            evaluations=[
                {"result_index": 0, "relevance_tier": "High", "justification": "Test 1"},
                {"result_index": 1, "relevance_tier": "Low", "justification": "Test 2"}
            ],
            ranking_summary="Test ranking",
            quality_score="8",
            conversion_likelihood="High",
            raw_response="mock response"
        )
        mock_parser_factory.create_parser.return_value = mock_parser
        
        # Create engine and request
        engine = SearchEvaluationEngine(self.config)
        request = EvaluationRequest(
            query="test query",
            results=self.mock_search_results,
            include_executive_summary=False  # Skip for simpler test
        )
        
        # Execute evaluation
        result = engine.evaluate(request)
        
        # Verify results
        assert result.status == "success"
        assert result.query == "test query"
        assert len(result.evaluations) == 2
        assert result.evaluations[0]["relevance_tier"] == "High"
        assert result.ranking_summary == "Test ranking"
    
    def test_evaluation_request_creation(self):
        """Test evaluation request object creation."""
        request = EvaluationRequest(
            query="brake pads",
            results=self.mock_search_results,
            search_type=SearchType.ENGLISH_WORD,
            model="gemma3",
            include_executive_summary=True,
            apply_inventory_ranking=True
        )
        
        assert request.query == "brake pads"
        assert len(request.results) == 2
        assert request.search_type == SearchType.ENGLISH_WORD
        assert request.model == "gemma3"
        assert request.include_executive_summary is True
        assert request.apply_inventory_ranking is True
    
    def test_evaluation_result_creation(self):
        """Test evaluation result object creation."""
        result = EvaluationResult(
            query="test query",
            search_type=SearchType.ENGLISH_WORD,
            model_used="gemma3",
            evaluations=[{"test": "evaluation"}],
            ranking_summary="Test summary",
            inventory_summary={"total": 2},
            status="success"
        )
        
        assert result.query == "test query"
        assert result.search_type == SearchType.ENGLISH_WORD
        assert result.model_used == "gemma3"
        assert len(result.evaluations) == 1
        assert result.status == "success"


class TestIntegration:
    """Integration tests for the complete system."""
    
    def setup_method(self):
        """Set up integration test fixtures."""
        self.sample_results = [
            {
                "title": "Premium Brake Pads Set",
                "part_number": "BP001",
                "vendor_part_number": "V-BP001",
                "manufacturer_part_number": "M-BP001",
                "description": "High quality brake pads",
                "price": "$45.99",
                "quantity": "150",
                "exact_match": "No",
                "partial_match": "Yes",
                "cross_ref_match": "No",
                "url": "https://example.com/bp001"
            },
            {
                "title": "Economy Brake Pads",
                "part_number": "BP002",
                "vendor_part_number": "V-BP002", 
                "manufacturer_part_number": "M-BP002",
                "description": "Basic brake pads",
                "price": "$29.99",
                "quantity": "0",
                "exact_match": "No",
                "partial_match": "Yes", 
                "cross_ref_match": "No",
                "url": "https://example.com/bp002"
            }
        ]
    
    @patch('llm_evaluator.llm_client.requests.post')
    def test_end_to_end_with_mock_ollama(self, mock_post):
        """Test end-to-end evaluation with mocked Ollama response."""
        # Mock successful Ollama response
        mock_ollama_response = {
            "response": json.dumps({
                "search_analysis": {
                    "query": "brake pads",
                    "total_results": 2,
                    "category_matches_found": 2,
                    "inventory_considerations_applied": True
                },
                "evaluations": [
                    {
                        "result_index": 0,
                        "title": "Premium Brake Pads Set",
                        "relevance_tier": "High",
                        "relevance_score": "9",
                        "inventory_status": "Available",
                        "inventory_quantity": "150",
                        "part_number": "BP001",
                        "vendor_part_number": "V-BP001",
                        "justification": "Direct match for brake pads with excellent availability",
                        "inventory_impact": "High stock supports top ranking",
                        "business_impact": "Excellent",
                        "recommended_action": "Promote"
                    },
                    {
                        "result_index": 1,
                        "title": "Economy Brake Pads",
                        "relevance_tier": "High",
                        "relevance_score": "8",
                        "inventory_status": "Out of Stock",
                        "inventory_quantity": "0",
                        "part_number": "BP002",
                        "vendor_part_number": "V-BP002",
                        "justification": "Good match but no inventory available",
                        "inventory_impact": "Out of stock reduces ranking priority",
                        "business_impact": "Poor",
                        "recommended_action": "Remove"
                    }
                ],
                "ranking_summary": "Strong product matches with mixed inventory situation",
                "quality_score": "8",
                "conversion_likelihood": "Medium"
            })
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_ollama_response
        mock_post.return_value = mock_response
        
        # Also mock the availability check
        with patch('llm_evaluator.llm_client.requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"models": [{"name": "gemma3"}]}
            
            # Create engine and run evaluation
            engine = SearchEvaluationEngine()
            request = EvaluationRequest(
                query="brake pads",
                results=self.sample_results,
                include_executive_summary=False
            )
            
            result = engine.evaluate(request)
            
            # Verify results
            assert result.status == "success"
            assert result.query == "brake pads"
            assert result.search_type == SearchType.MULTIPLE_TERMS  # "brake pads" is multiple terms
            assert len(result.evaluations) == 2
            
            # Check first evaluation
            eval1 = result.evaluations[0]
            assert eval1["relevance_tier"] == "High"
            assert eval1["inventory_status"] == "Available"
            assert eval1["recommended_action"] == "Promote"
            
            # Check second evaluation
            eval2 = result.evaluations[1]
            assert eval2["relevance_tier"] == "High"
            assert eval2["inventory_status"] == "Out of Stock"
            assert eval2["recommended_action"] == "Remove"
    
    def test_backward_compatibility_functions(self):
        """Test that backward compatibility functions work."""
        from .evaluation_engine import evaluate_search_results, evaluate_search_results_with_inventory
        
        # Mock the underlying engine
        with patch('llm_evaluator.evaluation_engine.SearchEvaluationEngine') as mock_engine_class:
            mock_engine = Mock()
            mock_engine.evaluate.return_value = EvaluationResult(
                query="test",
                search_type=SearchType.ENGLISH_WORD,
                model_used="gemma3",
                evaluations=[{"test": "evaluation"}],
                ranking_summary="Test",
                inventory_summary={"total": 1},
                status="success"
            )
            mock_engine_class.return_value = mock_engine
            
            # Test simple function
            result1 = evaluate_search_results("test query", self.sample_results)
            assert result1["status"] == "success"
            assert result1["query"] == "test"
            
            # Test advanced function
            result2 = evaluate_search_results_with_inventory(
                "test query", 
                self.sample_results,
                apply_post_ranking=True
            )
            assert result2["status"] == "success"
            assert result2["query"] == "test"


# Fixtures for pytest
@pytest.fixture
def sample_search_results():
    """Fixture providing sample search results."""
    return [
        {
            "title": "Test Product 1",
            "part_number": "TP001",
            "vendor_part_number": "V-TP001",
            "quantity": "100",
            "price": "$25.99"
        },
        {
            "title": "Test Product 2",
            "part_number": "TP002", 
            "vendor_part_number": "V-TP002",
            "quantity": "5",
            "price": "$35.99"
        },
        {
            "title": "Test Product 3",
            "part_number": "TP003",
            "vendor_part_number": "V-TP003",
            "quantity": "0",
            "price": "$45.99"
        }
    ]


@pytest.fixture
def mock_llm_config():
    """Fixture providing a mock LLM configuration."""
    return LLMConfig(
        ollama_api_endpoint="http://localhost:11434/api/generate",
        default_model="test_model",
        timeout=30,
        max_retries=1,
        debug_dir="test_debug"
    )


# Performance tests
class TestPerformance:
    """Performance and benchmark tests."""
    
    def test_evaluation_performance(self, sample_search_results):
        """Test evaluation performance with timing."""
        import time
        
        with patch('llm_evaluator.llm_client.requests.post') as mock_post:
            # Mock fast response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "response": json.dumps({
                    "search_analysis": {"query": "test", "total_results": 3},
                    "evaluations": [
                        {"result_index": i, "relevance_tier": "Medium", "justification": f"Test {i}"}
                        for i in range(3)
                    ],
                    "ranking_summary": "Test",
                    "quality_score": "7",
                    "conversion_likelihood": "Medium"
                })
            }
            mock_post.return_value = mock_response
            
            start_time = time.time()
            
            engine = SearchEvaluationEngine()
            request = EvaluationRequest(
                query="performance test",
                results=sample_search_results,
                include_executive_summary=False
            )
            result = engine.evaluate(request)
            
            end_time = time.time()
            evaluation_time = end_time - start_time
            
            assert result.status == "success"
            assert evaluation_time < 5.0  # Should complete within 5 seconds
    
    def test_batch_evaluation_performance(self, sample_search_results):
        """Test performance of batch evaluations."""
        import time
        
        with patch('llm_evaluator.llm_client.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "response": json.dumps({
                    "search_analysis": {"query": "test", "total_results": 3},
                    "evaluations": [
                        {"result_index": i, "relevance_tier": "Medium", "justification": f"Test {i}"}
                        for i in range(3)
                    ],
                    "ranking_summary": "Test"
                })
            }
            mock_post.return_value = mock_response
            
            engine = SearchEvaluationEngine()
            
            start_time = time.time()
            
            # Evaluate multiple batches
            for i in range(5):
                request = EvaluationRequest(
                    query=f"batch test {i}",
                    results=sample_search_results,
                    include_executive_summary=False
                )
                result = engine.evaluate(request)
                assert result.status == "success"
            
            end_time = time.time()
            total_time = end_time - start_time
            
            assert total_time < 10.0  # 5 evaluations should complete within 10 seconds


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
