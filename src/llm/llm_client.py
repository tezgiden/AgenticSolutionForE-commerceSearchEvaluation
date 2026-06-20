"""LLM client interface and implementations."""

from asyncio.log import logger
import requests
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .config import LLMConfig


@dataclass 
class LLMRequest:
    """Request data for LLM API calls."""
    prompt: str
    model: str
    temperature: float = 0.1
    max_tokens: Optional[int] = None
    stream: bool = False


@dataclass
class LLMResponse:
    """Response data from LLM API calls."""
    content: str
    model: str
    success: bool
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response from LLM."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if LLM service is available."""
        pass


class OllamaClient(LLMClient):
    """Ollama API client implementation."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.api_endpoint = config.ollama_api_endpoint
        self.timeout = config.timeout
        self.max_retries = config.max_retries
    
    def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Send a request to the Ollama API and return the response.
        
        Args:
            request: LLM request containing prompt and parameters
            
        Returns:
            LLMResponse containing the API response or error information
        """
        payload = {
            "model": request.model,
            "prompt": request.prompt,
            "stream": request.stream
        }
        
        if request.temperature is not None:
            payload["options"] = {"temperature": request.temperature}
        # Dump prompt to debug file
        self._dump_prompt_to_file(request.prompt)
        
        for attempt in range(self.max_retries):
            try:
                # Send POST request to Ollama API
                print(f"Sending request to Ollama API: {self.api_endpoint}")
                print(f"Request payload: {payload}")
                print(f"Timeout: {self.timeout} seconds")
                print(f"Attempt {attempt+1}/{self.max_retries}: Sending request to Ollama API")
                response = requests.post(
                    self.api_endpoint,
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    return LLMResponse(
                        content=response_data.get("response", ""),
                        model=request.model,
                        success=True,
                        metadata=response_data
                    )
                else:
                    error_msg = f"API error: Status {response.status_code}, Response: {response.text}"
                    print(f"Attempt {attempt+1}/{self.max_retries}: {error_msg}")
                    
                    if attempt == self.max_retries - 1:  # Last attempt
                        return LLMResponse(
                            content="",
                            model=request.model,
                            success=False,
                            error_message=error_msg
                        )
                    time.sleep(1)
                    
            except requests.exceptions.RequestException as e:
                error_msg = f"Request failed: {e}"
                print(f"Attempt {attempt+1}/{self.max_retries}: {error_msg}")
                
                if attempt == self.max_retries - 1:  # Last attempt
                    return LLMResponse(
                        content="",
                        model=request.model,
                        success=False,
                        error_message=error_msg
                    )
                time.sleep(1)
        
        return LLMResponse(
            content="",
            model=request.model,
            success=False,
            error_message=f"Failed after {self.max_retries} attempts"
        )
    
    def is_available(self) -> bool:
        """Check if Ollama service is available."""
        try:
            response = requests.get(
                self.api_endpoint.replace('/api/generate', '/api/tags'),
                timeout=5
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        try:
            response = requests.get(
                self.api_endpoint.replace('/api/generate', '/api/tags'),
                timeout=5
            )
            if response.status_code == 200:
                models_data = response.json()
                return [model["name"] for model in models_data.get("models", [])]
            return []
        except requests.exceptions.RequestException:
            return []
    
    def _dump_prompt_to_file(self, prompt: str) -> None:
        """
        Dump the prompt to a timestamped file in the debug directory.
        
        Args:
            prompt: The prompt text to dump
        """
        import os
        import json
        from datetime import datetime
        
        try:
            # Get debug directory from config or use default
            debug_dir = getattr(self.config, 'debug_dir', 'analysis_result')
            
            # Create directory if it doesn't exist
            os.makedirs(debug_dir, exist_ok=True)
            
            # Generate timestamp
            now = datetime.now().strftime("%Y%m%d-%H%M%S")
            
            # Get site name from config or use default
            site_name = getattr(self.config, 'site_name', 'unknown').lower().replace(' ', '').replace('-', '')
            
            # Create filename
            filename = f"{site_name}-prompt-{now}.json"
            filepath = os.path.join(debug_dir, filename)
            
            # Create prompt data structure
            prompt_data = {
                "timestamp": datetime.now().isoformat(),
                "site_name": site_name,
                "model": getattr(self.config, 'default_model', 'unknown'),
                "prompt": prompt
            }
            
            # Write to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(prompt_data, f, indent=2, ensure_ascii=False)
            
            print(f"[DEBUG] Prompt dumped to: {filepath}")
            
        except Exception as e:
            print(f"[WARNING] Failed to dump prompt to file: {e}")


class MockLLMClient(LLMClient):
    """Mock LLM client for testing purposes."""
    
    def __init__(self, mock_response: str = None):
        self.mock_response = mock_response or self._default_mock_response()
    
    def generate(self, request: LLMRequest) -> LLMResponse:
        """Return mock response."""
        return LLMResponse(
            content=self.mock_response,
            model=request.model,
            success=True,
            metadata={"mock": True}
        )
    
    def is_available(self) -> bool:
        """Always available for testing."""
        return True
    
    def _default_mock_response(self) -> str:
        """Default mock response in JSON format."""
        return '''
        {
            "search_analysis": {
                "query": "test_query",
                "total_results": 2,
                "inventory_considerations_applied": true
            },
            "evaluations": [
                {
                    "result_index": 0,
                    "title": "Mock Product 1",
                    "relevance_tier": "High",
                    "relevance_score": "9",
                    "inventory_status": "Available",
                    "inventory_quantity": "100",
                    "justification": "Mock evaluation for testing"
                },
                {
                    "result_index": 1,
                    "title": "Mock Product 2",
                    "relevance_tier": "Medium",
                    "relevance_score": "7",
                    "inventory_status": "Low Stock",
                    "inventory_quantity": "5",
                    "justification": "Mock evaluation for testing"
                }
            ],
            "ranking_summary": "Mock ranking summary",
            "quality_score": "8",
            "conversion_likelihood": "High"
        }
        '''


class LLMClientFactory:
    """Factory for creating LLM clients."""
    
    @staticmethod
    def create_client(client_type: str, config: LLMConfig = None, **kwargs) -> LLMClient:
        """Create an LLM client instance."""
        if client_type == "ollama":
            if not config:
                config = LLMConfig.from_environment()
            return OllamaClient(config)
        elif client_type == "mock":
            return MockLLMClient(**kwargs)
        else:
            raise ValueError(f"Unknown client type: {client_type}")


class RetryableLLMClient:
    """Wrapper that adds retry logic to any LLM client."""
    
    def __init__(self, client: LLMClient, max_retries: int = 3, retry_delay: float = 1.0):
        self.client = client
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate with retry logic."""
        for attempt in range(self.max_retries):
            response = self.client.generate(request)
            
            if response.success:
                return response
            
            if attempt < self.max_retries - 1:
                print(f"Retry attempt {attempt + 1} after {self.retry_delay}s delay")
                time.sleep(self.retry_delay)
        
        return response  # Return last failed response
    
    def is_available(self) -> bool:
        """Check availability through wrapped client."""
        return self.client.is_available()
