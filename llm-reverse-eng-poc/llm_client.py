from __future__ import annotations
import os
from typing import Dict, Any
from openai import OpenAI

class LLMClient:
    """
    Minimal wrapper for an OpenAI-compatible API.
    Configure via environment:
    - OPENAI_API_KEY (required for OpenAI)
    - OPENAI_BASE (optional; for compatible endpoints like Azure/others)
    """

    def __init__(self, provider: str = "openai", model: str = "gpt-4o-mini", temperature: float = 0.2, max_tokens: int = 2000):
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        base = os.environ.get("OPENAI_BASE")
        self.client = OpenAI(base_url=base) if base else OpenAI()

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            messages=[
                {"role":"system","content":system_prompt},
                {"role":"user","content":user_prompt},
            ],
        )
        return resp.choices[0].message.content
