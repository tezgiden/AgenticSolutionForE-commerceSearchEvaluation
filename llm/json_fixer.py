# json_fixer.py

import re


class JSONFixer:
    """
    Applies common repairs to malformed JSON output from LLMs.
    """

    @staticmethod
    def strip_json_markers(text: str) -> str:
        """
        Remove ```json ... ``` markers if present.
        """
        if text.strip().startswith("```json"):
            text = text.strip()[7:]
        if text.strip().endswith("```"):
            text = text.strip()[:-3]
        return text.strip()

    @staticmethod
    def basic_cleanup(json_str: str) -> str:
        """
        Apply basic text cleanups and fix common formatting issues.
        """
        json_str = re.sub(r'}\s*\n\s*"', '},\n"', json_str)
        json_str = re.sub(r']\s*\n\s*"', '],\n"', json_str)
        json_str = re.sub(r'(\s*true\s*)\n(\s*}\s*)\n(\s*"evaluations")', r'\1\2,\3', json_str)
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        json_str = re.sub(r"'([^']*)':", r'"\1":', json_str)
        return json_str.strip()

    @staticmethod
    def aggressive_fix(json_str: str) -> str:
        """
        Last-resort aggressive fix for unparseable JSON.
        """
        json_str = re.sub(r'}\s*\n\s*{', '},\n{', json_str)
        json_str = json_str.replace('\\"', '"').replace("'", '"')
        if json_str.rfind('}') != -1:
            json_str = json_str[:json_str.rfind('}') + 1]
        return json_str
