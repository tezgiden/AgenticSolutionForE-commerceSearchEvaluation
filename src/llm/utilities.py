"""Utilities for debugging, testing, and validation."""

import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .config import LLMConfig
from .evaluation_engine import SearchEvaluationEngine, EvaluationRequest
from .prompt_manager import PromptValidator
from .search_classifier import SearchType


@dataclass
class TestCase:
    """Test case for evaluation testing."""
    name: str
    query: str
    search_type: SearchType
    results: List[Dict[str, str]]
    expected_high_relevance_count: Optional[int] = None
    expected_out_of_stock_count: Optional[int] = None


class DebugUtils:
    """Utilities for debugging LLM evaluation system."""
    
    def __init__(self, debug_dir: str = "llm_debug"):
        self.debug_dir = debug_dir
        os.makedirs(debug_dir, exist_ok=True)
    
    def dump_prompt(self, prompt: str, filename: Optional[str] = None) -> str:
        """
        Dump prompt to debug directory with timestamped filename.
        
        Args:
            prompt: The prompt text to dump
            filename: Optional custom filename
            
        Returns:
            The filename used
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"prompt_{timestamp}.txt"
        
        file_path = os.path.join(self.debug_dir, filename)
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(prompt)
            print(f"Prompt dumped to {filename}")
            return filename
        except Exception as e:
            print(f"Failed to dump prompt: {e}")
            return ""
    
    def dump_evaluation_debug_data(self, prompt: str, llm_response: Dict[str, Any], 
                                   parsed_evaluations: Optional[Dict[str, Any]]) -> str:
        """Dump complete debug data for an evaluation."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"evaluation_debug_{timestamp}.json"
        file_path = os.path.join(self.debug_dir, filename)
        
        debug_data = {
            "timestamp": timestamp,
            "prompt": prompt,
            "llm_response": llm_response,
            "parsed_evaluations": parsed_evaluations
        }
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(debug_data, f, indent=2, ensure_ascii=False)
            print(f"Debug data saved to {filename}")
            return filename
        except Exception as e:
            print(f"Failed to save debug data: {e}")
            return ""
    
    def dump_executive_summary_debug(self, prompt: str, llm_response: Dict[str, Any], 
                                   parsed_summary: Optional[Dict[str, Any]]) -> str:
        """Dump executive summary debug data."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"executive_summary_debug_{timestamp}.json"
        file_path = os.path.join(self.debug_dir, filename)
        
        debug_data = {
            "timestamp": timestamp,
            "prompt": prompt,
            "llm_response": llm_response,
            "parsed_summary": parsed_summary
        }
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(debug_data, f, indent=2, ensure_ascii=False)
            return filename
        except Exception as e:
            print(f"Failed to save executive summary debug data: {e}")
            return ""


class TestDataGenerator:
    """Generates test data for evaluation testing."""
    
    @staticmethod
    def create_sample_results(count: int = 5, include_inventory: bool = True) -> List[Dict[str, str]]:
        """Create sample search results for testing."""
        results = []
        
        for i in range(count):
            result = {
                "title": f"Sample Product {i+1}",
                "part_number": f"SP{1000+i}",
                "vendor_part_number": f"VSP{2000+i}",
                "description": f"Description for sample product {i+1}",
                "price": f"${10 + i*5}.99",
                "url": f"https://example.com/product/{i+1}"
            }
            
            if include_inventory:
                # Vary inventory levels for testing
                if i == 0:
                    result["quantity"] = "0"  # Out of stock
                elif i == 1:
                    result["quantity"] = "3"  # Low stock
                elif i == 2:
                    result["quantity"] = "N/A"  # Unknown
                else:
                    result["quantity"] = str(50 + i*10)  # Available
            
            results.append(result)
        
        return results
    
    @staticmethod
    def create_part_number_test_cases() -> List[TestCase]:
        """Create test cases for part number queries."""
        return [
            TestCase(
                name="Exact Part Number Match",
                query="ABCD123",
                search_type=SearchType.PART_NUMBER,
                results=[
                    {
                        "title": "Premium ABCD123 Component",
                        "part_number": "ABCD123",
                        "vendor_part_number": "V-ABCD123",
                        "quantity": "100",
                        "price": "$45.99"
                    },
                    {
                        "title": "Alternative Part",
                        "part_number": "XYZ456",
                        "vendor_part_number": "V-XYZ456",
                        "quantity": "50",
                        "price": "$42.99"
                    }
                ],
                expected_high_relevance_count=1
            ),
            TestCase(
                name="Partial Part Number Match",
                query="4707Q",
                search_type=SearchType.PART_NUMBER,
                results=[
                    {
                        "title": "Brake Component",
                        "part_number": "LS4707QPAR23P",
                        "vendor_part_number": "4707QPAR23P",
                        "quantity": "518",
                        "price": "$32.99"
                    },
                    {
                        "title": "Different Component",
                        "part_number": "ABC123",
                        "vendor_part_number": "DEF456",
                        "quantity": "0",
                        "price": "$25.99"
                    }
                ],
                expected_high_relevance_count=1,
                expected_out_of_stock_count=1
            )
        ]
    
    @staticmethod
    def create_english_word_test_cases() -> List[TestCase]:
        """Create test cases for English word queries."""
        return [
            TestCase(
                name="Category Match",
                query="gasket",
                search_type=SearchType.ENGLISH_WORD,
                results=[
                    {
                        "title": "Premium Gasket Set",
                        "part_number": "GSK001",
                        "quantity": "0",
                        "price": "$25.99"
                    },
                    {
                        "title": "Standard Gasket",
                        "part_number": "GSK002",
                        "quantity": "150",
                        "price": "$15.99"
                    },
                    {
                        "title": "Unrelated Brake Pad",
                        "part_number": "BP001",
                        "quantity": "75",
                        "price": "$35.99"
                    }
                ],
                expected_high_relevance_count=2,
                expected_out_of_stock_count=1
            )
        ]


class ValidationUtils:
    """Utilities for validating system components."""
    
    @staticmethod
    def validate_config(config: LLMConfig) -> Dict[str, Any]:
        """Validate configuration."""
        try:
            config.validate()
            return {"valid": True, "errors": []}
        except Exception as e:
            return {"valid": False, "errors": [str(e)]}
    
    @staticmethod
    def validate_prompt_templates() -> Dict[str, Any]:
        """Validate all prompt templates."""
        from prompt_manager import PromptTemplateManager
        
        manager = PromptTemplateManager()
        results = {}
        
        for search_type in SearchType:
            template = manager.get_template(search_type)
            # Get template content - this is a simplified approach
            # In a real implementation, you'd have a way to get the template string
            template_content = str(template)  # Simplified
            
            validation = PromptValidator.validate_template(template_content, search_type)
            results[search_type.value] = validation
        
        return results
    
    @staticmethod
    def validate_service_connectivity(config: LLMConfig) -> Dict[str, Any]:
        """Validate connectivity to LLM service."""
        from llm_client import LLMClientFactory
        
        try:
            client = LLMClientFactory.create_client("ollama", config)
            is_available = client.is_available()
            
            models = []
            if hasattr(client, 'get_available_models'):
                models = client.get_available_models()
            
            return {
                "available": is_available,
                "models": models,
                "endpoint": config.ollama_api_endpoint
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "endpoint": config.ollama_api_endpoint
            }


class TestRunner:
    """Runs comprehensive tests on the evaluation system."""
    
    def __init__(self, config: LLMConfig = None):
        self.config = config or LLMConfig.from_environment()
        self.debug_utils = DebugUtils()
        self.test_generator = TestDataGenerator()
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all available tests."""
        print("🧪 Running comprehensive evaluation system tests...")
        
        results = {
            "config_validation": self._test_config_validation(),
            "service_connectivity": self._test_service_connectivity(),
            "prompt_template_validation": self._test_prompt_validation(),
            "evaluation_tests": self._test_evaluations()
        }
        
        # Summary
        total_tests = sum(len(v) if isinstance(v, dict) else 1 for v in results.values())
        passed_tests = sum(
            sum(1 for test in v.values() if test.get("passed", False)) 
            if isinstance(v, dict) else (1 if v.get("passed", False) else 0)
            for v in results.values()
        )
        
        results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
        }
        
        print(f"✅ Tests completed: {passed_tests}/{total_tests} passed ({results['summary']['success_rate']})")
        
        return results
    
    def _test_config_validation(self) -> Dict[str, Any]:
        """Test configuration validation."""
        return ValidationUtils.validate_config(self.config)
    
    def _test_service_connectivity(self) -> Dict[str, Any]:
        """Test service connectivity."""
        return ValidationUtils.validate_service_connectivity(self.config)
    
    def _test_prompt_validation(self) -> Dict[str, Any]:
        """Test prompt template validation."""
        return ValidationUtils.validate_prompt_templates()
    
    def _test_evaluations(self) -> Dict[str, Any]:
        """Test evaluation functionality."""
        test_cases = (
            self.test_generator.create_part_number_test_cases() +
            self.test_generator.create_english_word_test_cases()
        )
        
        engine = SearchEvaluationEngine(self.config)
        results = {}
        
        for test_case in test_cases:
            try:
                print(f"Running test: {test_case.name}")
                
                request = EvaluationRequest(
                    query=test_case.query,
                    results=test_case.results,
                    search_type=test_case.search_type,
                    include_executive_summary=False  # Skip for faster testing
                )
                
                result = engine.evaluate(request)
                
                # Validate result
                validation_result = self._validate_evaluation_result(test_case, result)
                results[test_case.name] = validation_result
                
            except Exception as e:
                results[test_case.name] = {
                    "passed": False,
                    "error": str(e)
                }
        
        return results
    
    def _validate_evaluation_result(self, test_case: TestCase, result) -> Dict[str, Any]:
        """Validate an evaluation result against expected outcomes."""
        validation = {"passed": True, "issues": []}
        
        # Check basic success
        if result.status != "success":
            validation["passed"] = False
            validation["issues"].append(f"Evaluation failed: {result.error}")
            return validation
        
        # Check evaluation count
        if len(result.evaluations) != len(test_case.results):
            validation["passed"] = False
            validation["issues"].append(
                f"Expected {len(test_case.results)} evaluations, got {len(result.evaluations)}"
            )
        
        # Check high relevance count if specified
        if test_case.expected_high_relevance_count is not None:
            high_relevance_count = sum(
                1 for eval in result.evaluations 
                if eval.get("relevance_tier") == "High"
            )
            if high_relevance_count != test_case.expected_high_relevance_count:
                validation["issues"].append(
                    f"Expected {test_case.expected_high_relevance_count} high relevance items, "
                    f"got {high_relevance_count}"
                )
        
        # Check out of stock count if specified
        if test_case.expected_out_of_stock_count is not None:
            out_of_stock_count = sum(
                1 for i, eval in enumerate(result.evaluations)
                if i < len(test_case.results) and test_case.results[i].get("quantity") in ("0", "N/A")
            )
            if out_of_stock_count != test_case.expected_out_of_stock_count:
                validation["issues"].append(
                    f"Expected {test_case.expected_out_of_stock_count} out of stock items, "
                    f"got {out_of_stock_count}"
                )
        
        return validation


# Convenience function for quick testing
def run_quick_test(query: str = "test part", model: str = None) -> None:
    """Run a quick test of the evaluation system."""
    print(f"🚀 Running quick test with query: '{query}'")
    
    # Generate test data
    test_results = TestDataGenerator.create_sample_results(3)
    
    # Run evaluation
    engine = SearchEvaluationEngine()
    request = EvaluationRequest(query=query, results=test_results, model=model)
    result = engine.evaluate(request)
    
    # Print results
    print(f"Status: {result.status}")
    if result.status == "success":
        print(f"Search Type: {result.search_type.value}")
        print(f"Evaluations: {len(result.evaluations)}")
        print(f"Model Used: {result.model_used}")
        if result.executive_summary:
            print("Executive Summary: ✅ Generated")
        print("\nEvaluation Summary:")
        for i, eval in enumerate(result.evaluations):
            title = test_results[i].get('title', 'N/A')
            relevance = eval.get('relevance_tier', 'N/A')
            print(f"  {i}: {title} - {relevance}")
    else:
        print(f"Error: {result.error}")
