from pathlib import Path
from corsarioxxx.file_ops import FileOperations
import tempfile


def test_safe_create_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        ops = FileOperations(tmpdir)
        result = ops.create_file("test.txt", "conteudo")
        assert result.ok is True
        assert (Path(tmpdir) / "test.txt").exists()


def test_safe_edit_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        ops = FileOperations(tmpdir)
        path = Path(tmpdir) / "test.txt"
        path.write_text("original")
        result = ops.edit_file("test.txt", "novo conteudo")
        assert result.ok is True
        assert path.read_text() == "novo conteudo"


def test_prevents_path_traversal():
    with tempfile.TemporaryDirectory() as tmpdir:
        ops = FileOperations(tmpdir)
        result = ops.create_file("../../../etc/passwd", "hacked")
        assert result.ok is False
        assert "fora do projeto" in result.message.lower()


def test_read_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        ops = FileOperations(tmpdir)
        path = Path(tmpdir) / "test.txt"
        path.write_text("conteudo para ler")
        result = ops.read_file("test.txt")
        assert result.ok is True
        assert "conteudo para ler" in result.message
