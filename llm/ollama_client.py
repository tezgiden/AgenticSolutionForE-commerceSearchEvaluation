# ollama_client.py

import time
import requests
from typing import Dict


class OllamaClient:
    """
    Handles API interactions with the Ollama LLM server.
    """

    def __init__(self, endpoint: str, model: str, timeout: int = 600, max_retries: int = 3):
        self.endpoint = endpoint
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries

    def query(self, prompt: str) -> Dict:
        """
        Send a prompt to the LLM and return parsed JSON response.

        Args:
            prompt (str): Text prompt for the model.

        Returns:
            Dict: Response dictionary (or error dict).
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }

        for attempt in range(self.max_retries):
            try:
                response = requests.post(self.endpoint, json=payload, timeout=self.timeout)
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"[OllamaClient] Attempt {attempt+1}: HTTP {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as e:
                print(f"[OllamaClient] Attempt {attempt+1} failed: {e}")

            time.sleep(1)  # Delay before retry

        return {"error": f"Failed to get response after {self.max_retries} attempts"}
