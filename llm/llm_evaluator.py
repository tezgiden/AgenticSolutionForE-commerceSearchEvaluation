# llm_evaluator.py

# from search_classifier import SearchTypeClassifier
from services.search_classifier import SearchTypeClassifier
from prompt_templates import PromptTemplateFactory
from result_formatter import ResultFormatter
from ollama_client import OllamaClient
from response_parser import LLMResponseParser
from ranking_utils import InventoryAwareRanker

from typing import List, Dict, Any


class LLMEvaluator:
    """
    Orchestrates query classification, prompt construction, LLM interaction,
    and post-processing for inventory-aware product ranking.
    """

    def __init__(self, llm_config: Dict[str, Any]):
        self.prompt_factory = PromptTemplateFactory()
        self.ollama = OllamaClient(
            endpoint=llm_config["ollama_api_endpoint"],
            model=llm_config["default_model"],
            timeout=llm_config.get("timeout", 600),
            max_retries=llm_config.get("max_retries", 3)
        )
        self.parser = LLMResponseParser()

    def evaluate(self, query: str, results: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Main entry point for evaluating a search query and its results.

        Args:
            query (str): The search string to evaluate.
            results (List[Dict]): The search results returned by the site.

        Returns:
            Dict[str, Any]: Final parsed and ranked evaluation result.
        """
        search_type = SearchTypeClassifier.classify(query)
        print(f"[LLMEvaluator] Search type classified as: {search_type}")

        results_text = ResultFormatter.format_results(results)
        prompt = self.prompt_factory.get_prompt(
            search_type=search_type,
            query=query,
            result_count=len(results)
        ).replace("{results_text}", results_text)

        print(f"[LLMEvaluator] Sending prompt to LLM ({len(prompt)} chars)...")
        raw_response = self.ollama.query(prompt)
        parsed = self.parser.parse(raw_response)

        if not parsed:
            raise RuntimeError("Failed to parse LLM response")

        evaluations = parsed.get("evaluations", [])
        ranker = InventoryAwareRanker(original_results=results)
        ranked = ranker.apply(evaluations)

        parsed["evaluations"] = ranked
        return parsed
