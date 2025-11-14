"""Configuration data models."""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ScrapingConfig:
    """Configuration for web scraping parameters."""
    search_input_selectors: List[str]
    search_button_selectors: List[str]
    product_card_selectors: List[str]
    product_link_selector: str
    product_title_selectors: List[str]
    product_sku_selectors: List[str]
    product_price_selectors: List[str]
    product_quantity_selectors: List[str]
    badges_selectors: List[str]
    exact_match_selectors: List[str]
    no_results_selectors: List[str]
    max_results_per_query: int
    wait_timeout: int
    page_load_timeout: int


@dataclass
class OutputConfig:
    """Configuration for output files."""
    output_file: str
    detailed_output_file: str


@dataclass
class SiteConfig:
    """Configuration for a specific site."""
    site_name: str
    target_url: str
    search_tasks: List[Dict[str, str]]
    inventory_test_cases: List[Dict[str, str]]
    scraping_config: ScrapingConfig
    output_config: OutputConfig


@dataclass
class LLMConfig:
    """Configuration for LLM/Ollama settings."""
    ollama_api_endpoint: str
    default_model: str
    timeout: int
    max_retries: int


@dataclass
class EvaluationConfig:
    """Configuration for evaluation parameters."""
    enable_inventory_ranking: bool
    enable_detailed_analysis: bool
    inventory_weight_factor: float
    apply_post_ranking: bool
    low_stock_threshold: int


@dataclass
class ChromeConfig:
    """Configuration for Chrome browser settings."""
    chrome_driver_path: Optional[str]
    headless: bool
    window_size: Dict[str, int]
    implicit_wait: int
    user_agent: str


@dataclass
class DeploymentConfig:
    """Configuration for deployment settings."""
    environment: str
    log_level: str
    enable_screenshots: bool
    delay_between_searches: int
    enable_metrics_collection: bool


@dataclass
class AppConfig:
    """Main application configuration."""
    site_config: SiteConfig
    llm_config: LLMConfig
    evaluation_config: EvaluationConfig
    chrome_config: ChromeConfig
    deployment_config: DeploymentConfig