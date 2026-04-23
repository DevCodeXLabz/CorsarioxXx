import pytest
from corsarioxxx.git_ops import GitOperations, GitOpResult


class TestGitOperations:
    def test_init_with_repo_dir(self):
        from pathlib import Path
        ops = GitOperations(repo_dir=Path.cwd())
        assert ops.repo_dir == Path.cwd().resolve()

    def test_is_dangerous_detects_reset(self):
        ops = GitOperations()
        assert ops._is_dangerous("reset --hard HEAD")

    def test_is_dangerous_detects_force_flag(self):
        ops = GitOperations()
        assert ops._is_dangerous("push -f origin main")

    def test_is_dangerous_allows_safe_commits(self):
        ops = GitOperations()
        assert not ops._is_dangerous("commit -m 'test commit'")

    def test_is_dangerous_allows_status(self):
        ops = GitOperations()
        assert not ops._is_dangerous("status")

    def test_run_returns_result(self):
        ops = GitOperations()
        result = ops.status()
        assert isinstance(result, GitOpResult)
        assert result.command == "status"

    def test_commit_escapes_quotes(self):
        ops = GitOperations()
        # Just test that it doesn't crash on quotes
        result = ops.commit('Test "quoted" message')
        assert isinstance(result, GitOpResult)

    def test_dangerous_command_returns_false(self):
        ops = GitOperations()
        result = ops.run("reset --hard HEAD")
        assert not result.ok
        assert "perigosa" in result.stderr.lower()
