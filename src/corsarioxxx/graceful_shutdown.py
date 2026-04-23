from __future__ import annotations

import signal
import sys
import traceback
from typing import Callable


class GracefulShutdown:
    """Gerencia sinal handling para shutdown gracioso e crash logging."""

    def __init__(self, session_db=None):
        self.session_db = session_db
        self.is_shutting_down = False
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Configura handlers para SIGINT (Ctrl+C) e SIGTERM."""
        signal.signal(signal.SIGINT, self._handle_sigint)
        signal.signal(signal.SIGTERM, self._handle_sigterm)

    def _handle_sigint(self, signum: int, frame) -> None:
        """Handler para SIGINT (Ctrl+C) - shutdown gracioso."""
        self.is_shutting_down = True
        if self.session_db:
            try:
                self.session_db.log_session_entry(
                    prompt="[SYSTEM]",
                    response="User initiated shutdown (Ctrl+C)",
                    context="system",
                    status="shutdown",
                )
            except Exception:
                pass
        print("\nShutdown... Adeus!")
        sys.exit(0)

    def _handle_sigterm(self, signum: int, frame) -> None:
        """Handler para SIGTERM - shutdown gracioso."""
        self.is_shutting_down = True
        if self.session_db:
            try:
                self.session_db.log_session_entry(
                    prompt="[SYSTEM]",
                    response="Process terminated (SIGTERM)",
                    context="system",
                    status="shutdown",
                )
            except Exception:
                pass
        print("\nTerminating... Adeus!")
        sys.exit(0)

    def log_crash(self, exc: Exception) -> None:
        """Log um crash com traceback."""
        if self.session_db:
            try:
                tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
                self.session_db.log_crash(
                    exception_type=type(exc).__name__,
                    message=str(exc),
                    traceback=tb_str,
                )
            except Exception as e:
                print(f"Erro ao logar crash: {e}", file=sys.stderr)

    def handle_exception(self, exc: Exception) -> None:
        """Loga um crash e exibe mensagem de erro."""
        print(f"\n❌ Erro: {type(exc).__name__}: {exc}", file=sys.stderr)
        self.log_crash(exc)
        print("Use /sair para encerrar ou tente novamente.", file=sys.stderr)


def wrap_main_loop(loop_func: Callable, session_db=None) -> int:
    """Wrapper para main loop com crash handling."""
    graceful = GracefulShutdown(session_db)
    
    try:
        return loop_func()
    except KeyboardInterrupt:
        # Ja tratado por signal handler
        return 0
    except Exception as e:
        graceful.handle_exception(e)
        return 1
