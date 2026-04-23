from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileOpResult:
    ok: bool
    path: str
    operation: str
    message: str

    def render(self) -> str:
        status = "✓" if self.ok else "✗"
        return f"{status} {self.operation.upper()} {self.path}: {self.message}"


class FileOperations:
    """Permitem criar e editar arquivos dentro do projeto de forma segura."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = Path(root_dir).resolve()

    def _is_safe_path(self, target: Path) -> bool:
        """Verifica se o caminho está dentro do diretório raiz do projeto."""
        try:
            target_resolved = (self.root_dir / target).resolve()
            return str(target_resolved).startswith(str(self.root_dir))
        except (ValueError, OSError):
            return False

    def create_file(self, relative_path: str, content: str = "") -> FileOpResult:
        """Cria um novo arquivo dentro do projeto."""
        target = self.root_dir / relative_path
        if not self._is_safe_path(target):
            return FileOpResult(False, relative_path, "create", "Caminho fora do projeto.")

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                return FileOpResult(False, relative_path, "create", "Arquivo já existe.")
            target.write_text(content, encoding="utf-8")
            return FileOpResult(True, relative_path, "create", f"Criado ({len(content)} bytes).")
        except Exception as e:
            return FileOpResult(False, relative_path, "create", f"Erro: {str(e)}")

    def edit_file(self, relative_path: str, content: str) -> FileOpResult:
        """Edita um arquivo existente dentro do projeto."""
        target = self.root_dir / relative_path
        if not self._is_safe_path(target):
            return FileOpResult(False, relative_path, "edit", "Caminho fora do projeto.")

        try:
            if not target.exists():
                return FileOpResult(False, relative_path, "edit", "Arquivo não existe.")
            target.write_text(content, encoding="utf-8")
            return FileOpResult(True, relative_path, "edit", f"Editado ({len(content)} bytes).")
        except Exception as e:
            return FileOpResult(False, relative_path, "edit", f"Erro: {str(e)}")

    def read_file(self, relative_path: str) -> FileOpResult:
        """Lê um arquivo dentro do projeto."""
        target = self.root_dir / relative_path
        if not self._is_safe_path(target):
            return FileOpResult(False, relative_path, "read", "Caminho fora do projeto.")

        try:
            if not target.exists():
                return FileOpResult(False, relative_path, "read", "Arquivo não existe.")
            content = target.read_text(encoding="utf-8")
            return FileOpResult(True, relative_path, "read", f"Conteúdo ({len(content)} bytes):\n{content[:500]}...")
        except Exception as e:
            return FileOpResult(False, relative_path, "read", f"Erro: {str(e)}")
