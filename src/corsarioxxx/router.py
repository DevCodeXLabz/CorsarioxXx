from __future__ import annotations

from dataclasses import dataclass

from .memory import MemoryStore


@dataclass(frozen=True)
class RoutedPrompt:
    mode: str
    content: str


IDENTITY_KEYS = {
    "quem sou eu": "owner",
    "quem e voce": "assistant",
    "quem é você": "assistant",
    "status": "status",
    "o que voce pode fazer": "help",
    "o que você pode fazer": "help",
}


def route_prompt(prompt: str, memory: MemoryStore) -> RoutedPrompt:
    normalized = prompt.strip().lower()
    if normalized.startswith("/exec "):
        return RoutedPrompt("exec", prompt[6:].strip())

    if normalized in IDENTITY_KEYS:
        payload = memory.load()
        owner_name = payload["owner_facts"]["owner_name"]
        assistant_name = payload["assistant_facts"]["name"]

        key = IDENTITY_KEYS[normalized]
        if key == "owner":
            return RoutedPrompt("deterministic", f"Voce e {owner_name}, meu operador autenticado.")
        if key == "assistant":
            return RoutedPrompt("deterministic", f"Eu sou {assistant_name}, seu assistente local no terminal.")
        if key == "status":
            return RoutedPrompt("deterministic", "Status: autenticacao local, roteamento deterministico e integracao Ollama habilitados.")
        return RoutedPrompt(
            "deterministic",
            "Eu posso conversar, analisar pedidos, executar comandos seguros automaticamente e pedir confirmacao para acoes sensiveis.",
        )

    return RoutedPrompt("chat", prompt)


def detect_model_context(prompt: str) -> str:
    """Detecta o contexto da tarefa para rotear para o modelo certo."""
    lower = prompt.lower()
    
    if any(word in lower for word in ["python", "script", "funcao", "classe", "codigo", "bug", "erro de sintaxe"]):
        return "code-python"
    
    if any(word in lower for word in ["android", "kotlin", "studio", "apk", "gradle", "xml", "activity"]):
        return "code-android"
    
    if any(word in lower for word in ["explore", "analisa", "pensa", "raciocina", "strategy", "plano"]):
        return "reasoning"
    
    return "chat"


def build_system_prompt(memory: MemoryStore) -> str:
    payload = memory.load()
    owner_name = payload["owner_facts"]["owner_name"]
    assistant_name = payload["assistant_facts"]["name"]
    persona = payload["assistant_facts"]["persona"]
    return (
        f"Voce e {assistant_name}, um assistente local para {owner_name}. "
        f"Seja {persona} "
        "Nao invente identidade, regras ou status do sistema. "
        "Quando o assunto for identidade, regras, permissoes ou status, prefira respostas objetivas."
    )
