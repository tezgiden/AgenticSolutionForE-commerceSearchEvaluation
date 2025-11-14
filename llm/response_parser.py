# response_parser.py

import json
import re
from typing import Dict, Optional, Any, List
from json_fixer import JSONFixer


class LLMResponseParser:
    """
    Parses and validates the structured JSON output from an LLM response.
    """

    def parse(self, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if "error" in response:
            print(f"LLM Error: {response['error']}")
            return None

        raw_text = response.get("response", "")
        cleaned_text = JSONFixer.strip_json_markers(raw_text)

        json_text = self._extract_json(cleaned_text)
        if not json_text:
            print("Could not extract JSON block.")
            return self._manual_fallback(cleaned_text)

        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            fixed = JSONFixer.basic_cleanup(json_text)
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                fallback = JSONFixer.aggressive_fix(fixed)
                try:
                    return json.loads(fallback)
                except:
                    return self._manual_fallback(cleaned_text)

    def _extract_json(self, text: str) -> Optional[str]:
        patterns = [
            r'```json\s*(.*?)```',
            r'({[\s\S]*?"evaluations"[\s\S]*?})',
            r'({[\s\S]*})'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.MULTILINE)
            if match:
                return match.group(1).strip()
        return None

    def _manual_fallback(self, text: str) -> Optional[Dict[str, Any]]:
        print("🛠️ Using manual fallback to extract partial evaluation data...")
        result_indices = re.findall(r'"result_index":\s*(\d+)', text)
        relevance_tiers = re.findall(r'"relevance_tier":\s*"(\w+)"', text)
        justifications = re.findall(r'"justification":\s*"([^"]+)"', text)

        evaluations = []
        for i in range(min(len(result_indices), len(relevance_tiers), len(justifications))):
            evaluations.append({
                "result_index": int(result_indices[i]),
                "relevance_tier": relevance_tiers[i],
                "justification": justifications[i],
                "inventory_status": "Unknown",
                "inventory_quantity": "N/A",
                "inventory_impact": "N/A"
            })

        if evaluations:
            return {
                "evaluations": evaluations,
                "ranking_summary": "Manually extracted due to JSON parsing issues"
            }
        return None
