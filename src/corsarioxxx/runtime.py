from __future__ import annotations

from dataclasses import dataclass

from .llm import OllamaClient
from .memory import MemoryStore
from .permissions import PermissionDecision, classify_command
from .router import build_system_prompt, route_prompt
from .tools import CommandRunner, CommandResult
from .file_ops import FileOperations
from .git_ops import GitOperations


@dataclass
class AssistantRuntime:
    memory: MemoryStore
    llm: OllamaClient
    runner: CommandRunner
    file_ops: FileOperations
    git_ops: GitOperations

    def handle_prompt(self, prompt: str) -> tuple[str, PermissionDecision | None, CommandResult | None]:
        routed = route_prompt(prompt, self.memory)
        if routed.mode == "deterministic":
            return routed.content, None, None

        if routed.mode == "exec":
            return self._handle_exec(routed.content)

        from .router import detect_model_context
        context = detect_model_context(routed.content)
        response = self.llm.generate(routed.content, build_system_prompt(self.memory), context)
        
        # Save to session history
        self.memory.add_session_entry(routed.content, response.text, context)
        
        return response.text, None, None

    def _handle_exec(self, content: str) -> tuple[str, PermissionDecision | None, CommandResult | None]:
        """Processa comandos /exec, /createfile, /editfile, /readfile, /git."""
        lower = content.lower()
        
        if lower.startswith("/createfile "):
            parts = content[12:].split("|", 1)
            if len(parts) != 2:
                return "Formato: /createfile <caminho> | <conteudo>", None, None
            filepath, filecontent = parts
            result = self.file_ops.create_file(filepath.strip(), filecontent.strip())
            return result.render(), None, None
        
        if lower.startswith("/editfile "):
            parts = content[10:].split("|", 1)
            if len(parts) != 2:
                return "Formato: /editfile <caminho> | <conteudo>", None, None
            filepath, filecontent = parts
            result = self.file_ops.edit_file(filepath.strip(), filecontent.strip())
            return result.render(), None, None
        
        if lower.startswith("/readfile "):
            filepath = content[10:].strip()
            result = self.file_ops.read_file(filepath)
            return result.render(), None, None
        
        if lower.startswith("/git "):
            git_cmd = content[5:].strip()
            result = self.git_ops.run(git_cmd)
            return result.render(), None, None
        
        decision = classify_command(content)
        if decision.requires_confirmation:
            return f"Confirmacao necessaria: {decision.reason}", decision, None
        result = self.runner.run(content)
        return result.render(), decision, result
