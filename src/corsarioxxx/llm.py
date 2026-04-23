from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class LLMResult:
    ok: bool
    text: str
    source: str


class OllamaClient:
    MODEL_ROUTING = {
        "code-python": "qwen2.5-coder:7b",
        "code-android": "qwen3.5:latest",
        "reasoning": "dolphin-llama3:8b-256k",
        "chat": "dolphin-llama3:8b-256k",
        "fallback": "llama3.1:8b",
    }

    def __init__(self, base_url: str = "http://localhost:11434/api/generate") -> None:
        self.base_url = base_url

    def select_model(self, context: str) -> str:
        return self.MODEL_ROUTING.get(context, self.MODEL_ROUTING["fallback"])

    def generate(self, prompt: str, system_prompt: str, context: str = "chat") -> LLMResult:
        model = self.select_model(context)
        payload = json.dumps(
            {
                "model": model,
                "prompt": f"{system_prompt}\n\n{prompt}",
                "stream": False,
            }
        ).encode("utf-8")
        request = Request(
            self.base_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=60) as response:
                body = json.loads(response.read().decode("utf-8"))
        except URLError:
            return LLMResult(False, "Ollama indisponivel no momento.", "fallback")

        return LLMResult(True, body.get("response", "").strip() or "Resposta vazia.", f"ollama ({model})")
