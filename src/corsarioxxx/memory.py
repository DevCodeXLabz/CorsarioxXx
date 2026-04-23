from __future__ import annotations

from dataclasses import dataclass

from .config import AppPaths, load_json, write_json


@dataclass
class MemoryStore:
    paths: AppPaths

    def load(self) -> dict:
        return load_json(
            self.paths.memory_file,
            {
                "owner_facts": {
                    "owner_name": "sr71n3",
                },
                "assistant_facts": {
                    "name": "CorsarioXxX",
                    "persona": "Amigavel, leal e direto.",
                },
                "session_history": [],
                "context_awareness": {
                    "last_project": None,
                    "recent_files": [],
                    "recent_errors": [],
                    "coding_patterns": {},
                },
                "notes": [],
            },
        )

    def save(self, payload: dict) -> None:
        write_json(self.paths.memory_file, payload)

    def append_note(self, note: str) -> None:
        payload = self.load()
        payload.setdefault("notes", []).append(note)
        self.save(payload)

    def add_session_entry(self, prompt: str, response: str, context: str = "chat") -> None:
        """Salva uma entrada de sessão para aprendizado iterativo."""
        payload = self.load()
        payload.setdefault("session_history", []).append({
            "prompt": prompt,
            "response": response[:500],  # Truncate long responses
            "context": context,
        })
        # Manter últimas 50 entradas apenas
        if len(payload["session_history"]) > 50:
            payload["session_history"] = payload["session_history"][-50:]
        self.save(payload)

    def set_context(self, key: str, value: str) -> None:
        """Atualiza contexto de awareness."""
        payload = self.load()
        payload.setdefault("context_awareness", {})[key] = value
        self.save(payload)

    def get_context(self, key: str) -> str | None:
        """Recupera contexto de awareness."""
        payload = self.load()
        return payload.get("context_awareness", {}).get(key)
