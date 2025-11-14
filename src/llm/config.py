"""Configuration management for LLM evaluation system."""

from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class LLMConfig:
    """Configuration settings for LLM evaluation system."""
    
    ollama_api_endpoint: str = "http://localhost:11434/api/generate"
    default_model: str = "gemma3"
    timeout: int = 720
    max_retries: int = 3
    debug_dir: str = "llm_debug"
    
    @classmethod
    def from_environment(cls) -> 'LLMConfig':
        """Create configuration from environment variables."""
        return cls(
            ollama_api_endpoint=os.getenv('OLLAMA_API_ENDPOINT', cls.ollama_api_endpoint),
            default_model=os.getenv('DEFAULT_MODEL', cls.default_model),
            timeout=int(os.getenv('TIMEOUT', cls.timeout)),
            max_retries=int(os.getenv('MAX_RETRIES', cls.max_retries)),
            debug_dir=os.getenv('DEBUG_DIR', cls.debug_dir)
        )
    
    def validate(self) -> bool:
        """Validate configuration settings."""
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("Max retries cannot be negative")
        if not self.ollama_api_endpoint:
            raise ValueError("API endpoint cannot be empty")
        if not self.default_model:
            raise ValueError("Default model cannot be empty")
        return True