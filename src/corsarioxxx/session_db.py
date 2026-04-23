from __future__ import annotations

import sqlite3
import re
from datetime import datetime, timedelta
from pathlib import Path


class SessionDatabase:
    """SQLite database para persistencia de sessoes entre runs."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_schema()

    def _init_schema(self) -> None:
        """Cria tabelas se nao existem."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS session_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    prompt TEXT,
                    response TEXT,
                    context TEXT,
                    status TEXT,
                    duration_ms INTEGER,
                    is_sensitive INTEGER DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS crash_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    exception_type TEXT,
                    message TEXT,
                    traceback TEXT,
                    is_sensitive INTEGER DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )
            # Set schema version
            conn.execute(
                "INSERT OR REPLACE INTO schema_version (key, value) VALUES ('version', '1.0')"
            )
            conn.commit()

    @staticmethod
    def _redact_sensitive(text: str) -> tuple[str, bool]:
        """Redacta dados sensiveis. Retorna (texto redactado, eh_sensivel)."""
        if not text:
            return text, False

        is_sensitive = False

        # Redacta API keys
        if re.search(r"api[_-]?key[:\s=]*\S+", text, re.IGNORECASE):
            text = re.sub(
                r"api[_-]?key[:\s=]*\S+",
                "[REDACTED_API_KEY]",
                text,
                flags=re.IGNORECASE,
            )
            is_sensitive = True

        # Redacta GitHub tokens
        if re.search(r"(ghp_|github_token)\S+", text, re.IGNORECASE):
            text = re.sub(
                r"(ghp_|github_token)\S+",
                "[REDACTED_TOKEN]",
                text,
                flags=re.IGNORECASE,
            )
            is_sensitive = True

        # Redacta senhas (simples heuristic)
        if re.search(r"password[:\s=]*\S+", text, re.IGNORECASE):
            text = re.sub(
                r"password[:\s=]*\S+",
                "[REDACTED_PASSWORD]",
                text,
                flags=re.IGNORECASE,
            )
            is_sensitive = True

        # Redacta emails
        if re.search(r"[\w.-]+@[\w.-]+\.\w+", text):
            text = re.sub(r"[\w.-]+@[\w.-]+\.\w+", "[REDACTED_EMAIL]", text)
            is_sensitive = True

        # Redacta IPs privados
        if re.search(r"192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+", text):
            text = re.sub(
                r"192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+",
                "[REDACTED_IP]",
                text,
            )
            is_sensitive = True

        return text, is_sensitive

    def log_session_entry(
        self,
        prompt: str,
        response: str,
        context: str = "chat",
        status: str = "success",
        duration_ms: int = 0,
    ) -> None:
        """Log uma entrada de sessao com redactacao de dados sensiveis."""
        prompt_clean, prompt_sensitive = self._redact_sensitive(prompt)
        response_clean, response_sensitive = self._redact_sensitive(response)
        is_sensitive = 1 if (prompt_sensitive or response_sensitive) else 0

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO session_entries
                (timestamp, prompt, response, context, status, duration_ms, is_sensitive)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now().isoformat(),
                    prompt_clean,
                    response_clean,
                    context,
                    status,
                    duration_ms,
                    is_sensitive,
                ),
            )
            conn.commit()

    def log_crash(
        self,
        exception_type: str,
        message: str,
        traceback: str = "",
    ) -> None:
        """Log um crash com traceback redactado."""
        traceback_clean, is_sensitive = self._redact_sensitive(traceback)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO crash_logs
                (timestamp, exception_type, message, traceback, is_sensitive)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    datetime.now().isoformat(),
                    exception_type,
                    message,
                    traceback_clean,
                    1 if is_sensitive else 0,
                ),
            )
            conn.commit()

    def cleanup_old_entries(self, days: int = 30) -> int:
        """Remove entradas com mais de N dias. Retorna numero deletado."""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM session_entries WHERE timestamp < ?",
                (cutoff_date,),
            )
            deleted = cursor.rowcount
            conn.commit()

        return deleted

    def get_recent_sessions(self, limit: int = 10) -> list[dict]:
        """Recupera ultimas N sessoes para debugging/recall."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT timestamp, context, status, duration_ms, is_sensitive
                FROM session_entries
                WHERE is_sensitive = 0
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_recent_crashes(self, limit: int = 5) -> list[dict]:
        """Recupera ultimos crashes."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT timestamp, exception_type, message
                FROM crash_logs
                WHERE is_sensitive = 0
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_session_summary(self, context: str = None) -> dict:
        """Retorna resumo de sessoes (contagens por contexto/status)."""
        with sqlite3.connect(self.db_path) as conn:
            if context:
                cursor = conn.execute(
                    """
                    SELECT status, COUNT(*) as count
                    FROM session_entries
                    WHERE context = ?
                    GROUP BY status
                    """,
                    (context,),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT context, status, COUNT(*) as count
                    FROM session_entries
                    GROUP BY context, status
                    """
                )
            return {row[0] if not context else row[0]: row[1] for row in cursor.fetchall()}
