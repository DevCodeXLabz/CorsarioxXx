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
                "notes": [],
            },
        )

    def save(self, payload: dict) -> None:
        write_json(self.paths.memory_file, payload)

    def append_note(self, note: str) -> None:
        payload = self.load()
        payload.setdefault("notes", []).append(note)
        self.save(payload)
