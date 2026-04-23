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
    def __init__(self, model: str = "qwen2.5-coder:7b", base_url: str = "http://localhost:11434/api/generate") -> None:
        self.model = model
        self.base_url = base_url

    def generate(self, prompt: str, system_prompt: str) -> LLMResult:
        payload = json.dumps(
            {
                "model": self.model,
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

        return LLMResult(True, body.get("response", "").strip() or "Resposta vazia.", "ollama")
