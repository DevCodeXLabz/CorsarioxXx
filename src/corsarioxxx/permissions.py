from __future__ import annotations

from dataclasses import dataclass


SAFE_PREFIXES = (
    "Get-ChildItem",
    "Get-Content",
    "Select-String",
    "git status",
    "git diff",
    "python -m pytest",
    "pytest",
    "where.exe",
    "Get-Process",
    "Get-Service",
    "echo ",
)

SENSITIVE_MARKERS = (
    "Remove-Item",
    "del ",
    "erase ",
    "Stop-Process",
    "Restart-Computer",
    "shutdown",
    "Format-",
    "Set-ExecutionPolicy",
    "reg add",
    "taskkill",
    "Invoke-WebRequest",
    "curl ",
    "wget ",
    "pip install",
    "npm install",
    "git commit",
    "git push",
)


@dataclass(frozen=True)
class PermissionDecision:
    category: str
    requires_confirmation: bool
    reason: str


def classify_command(command: str) -> PermissionDecision:
    normalized = command.strip()
    lower = normalized.lower()

    if not normalized:
        return PermissionDecision("invalid", True, "Comando vazio.")

    for marker in SENSITIVE_MARKERS:
        if marker.lower() in lower:
            return PermissionDecision("sensitive", True, f"Contem marcador sensivel: {marker}.")

    for prefix in SAFE_PREFIXES:
        if lower.startswith(prefix.lower()):
            return PermissionDecision("safe", False, "Comando de leitura ou diagnostico.")

    return PermissionDecision("review", True, "Comando nao classificado como seguro.")
