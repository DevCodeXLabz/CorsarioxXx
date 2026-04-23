from __future__ import annotations

from dataclasses import dataclass

from .llm import OllamaClient
from .memory import MemoryStore
from .permissions import PermissionDecision, classify_command
from .router import build_system_prompt, route_prompt
from .tools import CommandRunner, CommandResult


@dataclass
class AssistantRuntime:
    memory: MemoryStore
    llm: OllamaClient
    runner: CommandRunner

    def handle_prompt(self, prompt: str) -> tuple[str, PermissionDecision | None, CommandResult | None]:
        routed = route_prompt(prompt, self.memory)
        if routed.mode == "deterministic":
            return routed.content, None, None

        if routed.mode == "exec":
            decision = classify_command(routed.content)
            if decision.requires_confirmation:
                return f"Confirmacao necessaria: {decision.reason}", decision, None
            result = self.runner.run(routed.content)
            return result.render(), decision, result

        from .router import detect_model_context
        context = detect_model_context(routed.content)
        response = self.llm.generate(routed.content, build_system_prompt(self.memory), context)
        return response.text, None, None
