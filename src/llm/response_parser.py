"""LLM response parsing and validation utilities."""

import json
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .llm_client import LLMResponse


@dataclass
class ParsedEvaluation:
    """Structured representation of parsed evaluation data."""
    search_analysis: Dict[str, Any]
    evaluations: List[Dict[str, Any]]
    ranking_summary: str
    quality_score: str
    conversion_likelihood: str
    raw_response: str


class ResponseParser(ABC):
    """Abstract base class for response parsers."""
    
    @abstractmethod
    def parse(self, response: LLMResponse) -> Optional[ParsedEvaluation]:
        """Parse LLM response into structured data."""
        pass


class JSONResponseParser(ResponseParser):
    """Parser for JSON-formatted LLM responses."""
    
    def __init__(self, strict: bool = False):
        self.strict = strict
    
    def parse(self, response: LLMResponse) -> Optional[ParsedEvaluation]:
        """
        Parse enhanced LLM response with error handling and recovery.
        
        Args:
            response: LLM response to parse
            
        Returns:
            ParsedEvaluation or None if parsing failed
        """
        if not response.success:
            print(f"Error in LLM response: {response.error_message}")
            return None
        
        try:
            content = response.content
            print(f"📝 Raw LLM response length: {len(content)} characters")
            
            # Step 1: Extract JSON from response
            json_str = self._extract_json_from_response(content)
            if not json_str:
                print("❌ Could not extract JSON from response")
                if self.strict:
                    return None
                return self._fallback_manual_extraction(content)
            
            print(f"✅ Extracted JSON ({len(json_str)} chars)")
            
            # Step 2: Try to parse JSON
            try:
                parsed_data = json.loads(json_str)
                
                # Step 3: Validate structure
                if self._validate_evaluation_structure(parsed_data):
                    print(f"✅ Successfully parsed evaluation with {len(parsed_data.get('evaluations', []))} evaluations")
                    return self._create_parsed_evaluation(parsed_data, content)
                else:
                    print("⚠️ Parsed JSON but structure validation failed")
                    if self.strict:
                        return None
                    return self._fallback_manual_extraction(content)
                    
            except json.JSONDecodeError as e:
                print(f"❌ Initial JSON parsing failed: {e}")
                
                if self.strict:
                    return None
                
                # Step 4: Try to fix common JSON issues
                fixed_json = self._fix_common_json_issues(json_str)
                try:
                    parsed_data = json.loads(fixed_json)
                    if self._validate_evaluation_structure(parsed_data):
                        print(f"✅ Successfully parsed after fixes")
                        return self._create_parsed_evaluation(parsed_data, content)
                except json.JSONDecodeError:
                    pass
                
                # Last resort: manual extraction
                return self._fallback_manual_extraction(content)
        
        except Exception as e:
            print(f"Unexpected error in parsing: {e}")
            if self.strict:
                return None
            return self._fallback_manual_extraction(response.content)
    
    def _extract_json_from_response(self, response_text: str) -> Optional[str]:
        """Extract JSON from LLM response text."""
        # Remove markdown code blocks if present
        if "```json" in response_text:
            start_marker = "```json"
            end_marker = "```"
            start_idx = response_text.find(start_marker)
            if start_idx != -1:
                start_idx += len(start_marker)
                end_idx = response_text.find(end_marker, start_idx)
                if end_idx != -1:
                    return response_text[start_idx:end_idx].strip()
        
        # Try different JSON extraction patterns
        json_patterns = [
            r'({[\s\S]*?})\s*$',  # From first { to last }
            r'({[\s\S]*?"evaluations"[\s\S]*?})',  # Must contain evaluations
            r'({[\s\S]*)"conversion_likelihood"[\s\S]*?})',  # Must end properly
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, response_text, re.DOTALL | re.MULTILINE)
            if match:
                potential_json = match.group(1).strip()
                if potential_json.startswith('{'):
                    # Attempt to auto-close if missing closing brackets/braces
                    open_braces = potential_json.count('{')
                    close_braces = potential_json.count('}')
                    open_brackets = potential_json.count('[')
                    close_brackets = potential_json.count(']')
                    
                    # Add missing closing brackets/braces
                    potential_json += ']' * (open_brackets - close_brackets)
                    potential_json += '}' * (open_braces - close_braces)
                    
                    if potential_json.endswith('}'):
                        return potential_json
        
        return None
    
    def _fix_common_json_issues(self, json_str: str) -> str:
        """Fix common JSON formatting issues."""
        # Remove markdown code blocks
        if "```json" in json_str:
            json_str = re.sub(r'```json\s*', '', json_str)
            json_str = re.sub(r'\s*```', '', json_str)
        
        # Fix missing commas between objects/arrays
        json_str = re.sub(r'}\s*\n\s*"', '},\n  "', json_str)
        json_str = re.sub(r']\s*\n\s*"', '],\n  "', json_str)
        
        # Fix missing commas in search_analysis section
        json_str = re.sub(r'(true|false|\d+)\s*\n\s*}\s*\n\s*"evaluations"', r'\1\n  },\n  "evaluations"', json_str)
        
        # Fix trailing commas before closing braces/brackets
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # Fix unescaped quotes in string values (conservative approach)
        json_str = re.sub(r':\s*"([^"]*)"([^",}\]]*)"([^",}\]]*)"', r': "\1\2\3"', json_str)
        
        return json_str.strip()
    
    def _validate_evaluation_structure(self, data: Dict[str, Any]) -> bool:
        """Validate that the parsed data has the expected structure."""
        try:
            # Check for required top-level keys
            required_keys = ["evaluations"]
            for key in required_keys:
                if key not in data:
                    print(f"Missing required key: {key}")
                    return False
            
            # Check evaluations array
            evaluations = data.get("evaluations", [])
            if not isinstance(evaluations, list):
                print("evaluations is not a list")
                return False
            
            if len(evaluations) == 0:
                print("evaluations array is empty")
                return False
            
            # Check each evaluation entry
            required_eval_keys = ["result_index", "relevance_tier", "justification"]
            for i, evaluation in enumerate(evaluations):
                if not isinstance(evaluation, dict):
                    print(f"Evaluation {i} is not a dictionary")
                    return False
                
                for key in required_eval_keys:
                    if key not in evaluation:
                        print(f"Evaluation {i} missing required key: {key}")
                        return False
            
            print(f"✅ Structure validation passed for {len(evaluations)} evaluations")
            return True
            
        except Exception as e:
            print(f"Error in structure validation: {e}")
            return False
    
    def _create_parsed_evaluation(self, data: Dict[str, Any], raw_response: str) -> ParsedEvaluation:
        """Create ParsedEvaluation from validated data."""
        return ParsedEvaluation(
            search_analysis=data.get("search_analysis", {}),
            evaluations=data.get("evaluations", []),
            ranking_summary=data.get("ranking_summary", ""),
            quality_score=data.get("quality_score", ""),
            conversion_likelihood=data.get("conversion_likelihood", ""),
            raw_response=raw_response
        )
    
    def _fallback_manual_extraction(self, text: str) -> Optional[ParsedEvaluation]:
        """Fallback manual extraction when JSON parsing fails."""
        print("🔧 Attempting fallback manual extraction...")
        
        try:
            evaluations = []
            
            # Extract result indices
            result_indices = self._extract_values(text, [
                r'"result_index":\s*(\d+)',
                r'result_index.*?(\d+)'
            ])
            
            # Extract relevance tiers
            relevances = self._extract_values(text, [
                r'"relevance_tier":\s*"(High|Medium|Low)"',
                r'relevance.*?(High|Medium|Low)'
            ])
            
            # Extract justifications
            justifications = self._extract_values(text, [
                r'"justification":\s*"([^"]+)"',
                r'justification.*?"([^"]+)"'
            ])
            
            # Create evaluation entries
            max_count = max(len(result_indices), len(relevances), len(justifications))
            
            for i in range(min(max_count, 10)):  # Limit to reasonable number
                evaluation = {
                    "result_index": int(result_indices[i]) if i < len(result_indices) else i,
                    "relevance_tier": relevances[i] if i < len(relevances) else "Medium",
                    "justification": justifications[i] if i < len(justifications) else f"Manual extraction for result {i}",
                    "inventory_status": "Unknown",
                    "inventory_quantity": "N/A"
                }
                evaluations.append(evaluation)
            
            if evaluations:
                print(f"✅ Manual extraction successful: {len(evaluations)} evaluations")
                return ParsedEvaluation(
                    search_analysis={"total_results": len(evaluations)},
                    evaluations=evaluations,
                    ranking_summary="Manually extracted due to JSON parsing issues",
                    quality_score="N/A",
                    conversion_likelihood="Unknown",
                    raw_response=text
                )
            
            print("❌ Manual extraction also failed")
            return None
            
        except Exception as e:
            print(f"Manual extraction error: {e}")
            return None
    
    def _extract_values(self, text: str, patterns: List[str]) -> List[str]:
        """Extract values using multiple regex patterns."""
        values = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            values.extend(matches)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_values = []
        for value in values:
            if value not in seen:
                unique_values.append(value)
                seen.add(value)
        
        return unique_values


class ExecutiveSummaryParser(ResponseParser):
    """Specialized parser for executive summary responses."""
    
    def parse(self, response: LLMResponse) -> Optional[Dict[str, Any]]:
        """Parse executive summary response."""
        if not response.success:
            print(f"Error in executive summary response: {response.error_message}")
            return None
        
        try:
            content = response.content
            
            # Extract JSON
            json_str = self._extract_json_from_response(content)
            if not json_str:
                print("❌ Could not extract JSON from executive summary response")
                return None
            
            # Parse JSON
            parsed_data = json.loads(json_str)
            
            # Validate executive summary structure
            if self._validate_executive_summary_structure(parsed_data):
                print("✅ Successfully parsed executive summary")
                return parsed_data
            else:
                print("⚠️ Executive summary structure validation failed")
                return None
                
        except json.JSONDecodeError as e:
            print(f"❌ Executive summary JSON parsing failed: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error in executive summary parsing: {e}")
            return None
    
    def _extract_json_from_response(self, response_text: str) -> Optional[str]:
        """Extract JSON from executive summary response."""
        # Similar to JSONResponseParser but may have different patterns
        return JSONResponseParser()._extract_json_from_response(response_text)
    
    def _validate_executive_summary_structure(self, data: Dict[str, Any]) -> bool:
        """Validate executive summary structure."""
        required_keys = ["business_recommendations", "quality_score", "conversion_likelihood"]
        for key in required_keys:
            if key not in data:
                print(f"Missing required key in executive summary: {key}")
                return False
        
        # Check business_recommendations structure
        br = data["business_recommendations"]
        br_required = ["relevancy_assessment", "inventory_impact", "recommended_actions"]
        for key in br_required:
            if key not in br:
                print(f"Missing key in business_recommendations: {key}")
                return False
        
        return True


class ResponseParserFactory:
    """Factory for creating response parsers."""
    
    @staticmethod
    def create_parser(parser_type: str = "json", **kwargs) -> ResponseParser:
        """Create a response parser instance."""
        if parser_type == "json":
            return JSONResponseParser(**kwargs)
        elif parser_type == "executive_summary":
            return ExecutiveSummaryParser(**kwargs)
        else:
            raise ValueError(f"Unknown parser type: {parser_type}")
