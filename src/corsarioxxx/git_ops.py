from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GitOpResult:
    ok: bool
    command: str
    stdout: str
    stderr: str

    def render(self) -> str:
        if self.ok:
            return f"✓ {self.command}: {self.stdout.strip()}"
        return f"✗ {self.command}: {self.stderr.strip()}"


class GitOperations:
    """Operacoes Git seguras para o assistente."""

    def __init__(self, repo_dir: Path | None = None):
        self.repo_dir = (repo_dir or Path.cwd()).resolve()

    # Comandos permitidos automaticamente
    SAFE_COMMANDS = {
        "status": "git status",
        "log": "git log --oneline -10",
        "diff": "git diff",
        "branch": "git branch -a",
        "add": "git add",
        "commit": "git commit",
        "push": "git push origin",
        "pull": "git pull origin",
    }

    # Operacoes perigosas que exigem confirmacao
    DANGEROUS_PATTERNS = ("reset", "force", "-f", "rebase", "clean -fd", "rm -r")

    def _is_dangerous(self, command: str) -> bool:
        """Detecta se um comando Git eh perigoso."""
        lower = command.lower()
        return any(pattern.lower() in lower for pattern in self.DANGEROUS_PATTERNS)

    def _validate_repo(self) -> bool:
        """Valida que estamos em um repositorio Git."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=self.repo_dir,
            )
            return result.returncode == 0
        except Exception:
            return False

    def run(self, git_command: str) -> GitOpResult:
        """Executa um comando git seguro no repo_dir."""
        if not self._validate_repo():
            return GitOpResult(False, git_command, "", f"Nao eh um repositorio Git: {self.repo_dir}")

        if self._is_dangerous(git_command):
            return GitOpResult(False, git_command, "", "Operacao perigosa detectada. Requer confirmacao manual.")

        try:
            result = subprocess.run(
                ["git"] + git_command.split(),
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.repo_dir,
            )
            return GitOpResult(
                ok=result.returncode == 0,
                command=git_command,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        except subprocess.TimeoutExpired:
            return GitOpResult(False, git_command, "", "Comando excedeu timeout (30s).")
        except Exception as e:
            return GitOpResult(False, git_command, "", str(e))

    def status(self) -> GitOpResult:
        return self.run("status")

    def log(self, lines: int = 10) -> GitOpResult:
        return self.run(f"log --oneline -{lines}")

    def diff(self) -> GitOpResult:
        return self.run("diff")

    def add(self, path: str) -> GitOpResult:
        return self.run(f"add {path}")

    def commit(self, message: str) -> GitOpResult:
        # Escape aspas na mensagem
        safe_msg = message.replace('"', '\\"')
        return self.run(f'commit -m "{safe_msg}"')

    def push(self, branch: str = "main") -> GitOpResult:
        return self.run(f"push origin {branch}")

    def pull(self, branch: str = "main") -> GitOpResult:
        return self.run(f"pull origin {branch}")

    def branch(self, name: str | None = None) -> GitOpResult:
        if name:
            return self.run(f"checkout -b {name}")
        return self.run("branch -a")
