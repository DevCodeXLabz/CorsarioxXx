from __future__ import annotations

from dataclasses import dataclass

from .llm import OllamaClient
from .memory import MemoryStore
from .permissions import PermissionDecision, classify_command
from .router import build_system_prompt, route_prompt
from .tools import CommandRunner, CommandResult
from .file_ops import FileOperations
from .git_ops import GitOperations
from .adb_ops import AdbOperations


@dataclass
class AssistantRuntime:
    memory: MemoryStore
    llm: OllamaClient
    runner: CommandRunner
    file_ops: FileOperations
    git_ops: GitOperations
    adb_ops: AdbOperations

    def handle_prompt(self, prompt: str) -> tuple[str, PermissionDecision | None, CommandResult | None]:
        routed = route_prompt(prompt, self.memory)
        if routed.mode == "deterministic":
            return routed.content, None, None

        if routed.mode == "exec":
            return self._handle_exec(routed.content)

        from .router import detect_model_context
        context = detect_model_context(routed.content)
        
        # Inject recent session context if available
        system_prompt = build_system_prompt(self.memory)
        session_summary = self.memory.get_session_summary(last_n=3)
        if session_summary:
            system_prompt += f"\n\n{session_summary}"
        
        response = self.llm.generate(routed.content, system_prompt, context)
        
        # Save to session history with error handling
        try:
            self.memory.add_session_entry(routed.content, response.text, context)
        except Exception as e:
            # Log error but don't crash
            self.memory.add_session_entry(routed.content, f"[ERROR: {str(e)}]", "error")
        
        return response.text, None, None

    def _handle_exec(self, content: str) -> tuple[str, PermissionDecision | None, CommandResult | None]:
        """Processa comandos /exec, /createfile, /editfile, /readfile, /git, /adb."""
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
            # Log git operations for debugging
            try:
                self.memory.add_session_entry(f"/git {git_cmd}", result.render(), "git")
            except Exception:
                pass
            return result.render(), None, None
        
        if lower.startswith("/adb "):
            return self._handle_adb(content[5:].strip())
        
        decision = classify_command(content)
        if decision.requires_confirmation:
            return f"Confirmacao necessaria: {decision.reason}", decision, None
        result = self.runner.run(content)
        return result.render(), decision, result

    def _handle_adb(self, adb_cmd: str) -> tuple[str, PermissionDecision | None, CommandResult | None]:
        """Processa subcomandos ADB: devices, select, current, shell, logcat, push, pull, install, uninstall."""
        parts = adb_cmd.split(maxsplit=1)
        if not parts:
            return "Uso: /adb <comando> [args]. Ex: /adb devices, /adb shell ls", None, None
        
        subcommand = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if subcommand == "devices":
            result = self.adb_ops.devices()
            return result.render(), None, None
        
        if subcommand == "current":
            result = self.adb_ops.current()
            return result.render(), None, None
        
        if subcommand == "select":
            if not args:
                return "Uso: /adb select <device_id>", None, None
            result = self.adb_ops.select_device(args.strip())
            return result.render(), None, None
        
        if subcommand == "shell":
            if not args:
                return "Uso: /adb shell <comando>", None, None
            result = self.adb_ops.shell(args)
            return result.render(), None, None
        
        if subcommand == "logcat":
            package = args.strip() if args else ""
            result = self.adb_ops.logcat(package)
            return result.render(), None, None
        
        if subcommand == "push":
            parts_push = args.split("|", 1)
            if len(parts_push) != 2:
                return "Uso: /adb push <local_path>|<remote_path>", None, None
            local_path = parts_push[0].strip()
            remote_path = parts_push[1].strip()
            result = self.adb_ops.push(local_path, remote_path)
            return result.render(), None, None
        
        if subcommand == "pull":
            parts_pull = args.split("|", 1)
            if len(parts_pull) != 2:
                return "Uso: /adb pull <remote_path>|<local_path>", None, None
            remote_path = parts_pull[0].strip()
            local_path = parts_pull[1].strip()
            result = self.adb_ops.pull(remote_path, local_path)
            return result.render(), None, None
        
        if subcommand == "install":
            if not args:
                return "Uso: /adb install <apk_path>", None, None
            result = self.adb_ops.install(args.strip())
            return result.render(), None, None
        
        if subcommand == "uninstall":
            if not args:
                return "Uso: /adb uninstall <package_name>", None, None
            result = self.adb_ops.uninstall(args.strip())
            return result.render(), None, None
        
        return (
            f"Comando ADB desconhecido: {subcommand}. "
            "Comandos validos: devices, current, select, shell, logcat, push, pull, install, uninstall",
            None,
            None,
        )
