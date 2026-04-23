import pytest
from corsarioxxx.memory import MemoryStore
from corsarioxxx.config import get_paths
from pathlib import Path
import tempfile


class TestMemoryStore:
    @pytest.fixture
    def temp_dir(self):
        """Cria diretorio temporario."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def memory_store(self, temp_dir):
        """Cria MemoryStore com diretorio temp."""
        paths = get_paths(temp_dir)
        paths.data_dir.mkdir(exist_ok=True)
        return MemoryStore(paths)

    def test_load_creates_default_structure(self, memory_store):
        payload = memory_store.load()
        assert "owner_facts" in payload
        assert "assistant_facts" in payload
        assert "session_history" in payload
        assert "context_awareness" in payload
        assert "notes" in payload

    def test_add_session_entry(self, memory_store):
        memory_store.add_session_entry("test prompt", "test response", "chat")
        payload = memory_store.load()
        assert len(payload["session_history"]) == 1
        assert payload["session_history"][0]["prompt"] == "test prompt"

    def test_session_history_truncates_at_50(self, memory_store):
        # Add 60 entries
        for i in range(60):
            memory_store.add_session_entry(f"prompt {i}", f"response {i}", "chat")
        payload = memory_store.load()
        assert len(payload["session_history"]) == 50

    def test_set_and_get_context(self, memory_store):
        memory_store.set_context("last_project", "CorsarioXxX")
        value = memory_store.get_context("last_project")
        assert value == "CorsarioXxX"

    def test_append_note(self, memory_store):
        memory_store.append_note("Test note")
        payload = memory_store.load()
        assert "Test note" in payload["notes"]
