from __future__ import annotations

import json
import urllib.request

from app.core.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


class ModelClient:
    """Small OpenAI-compatible wrapper with deterministic fallback."""

    def __init__(self) -> None:
        self.enabled = bool(LLM_API_KEY)

    def complete(self, system: str, user: str) -> str:
        if not self.enabled:
            return ""
        base_url = (LLM_BASE_URL or "https://api.openai.com/v1").rstrip("/")
        payload = json.dumps(
            {
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {LLM_API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                data = json.loads(response.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except Exception:
            return ""
