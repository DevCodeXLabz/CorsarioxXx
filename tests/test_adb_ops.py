import pytest
from corsarioxxx.adb_ops import AdbOperations, AdbResult


class TestAdbOperations:
    @pytest.fixture
    def adb_ops(self):
        """Cria instancia AdbOperations para testes."""
        try:
            return AdbOperations()
        except RuntimeError:
            pytest.skip("ADB nao disponivel")

    def test_has_shell_metacharacters_detects_pipe(self, adb_ops):
        assert adb_ops._has_shell_metacharacters("ls | grep test")

    def test_has_shell_metacharacters_detects_and(self, adb_ops):
        assert adb_ops._has_shell_metacharacters("cmd1 && cmd2")

    def test_has_shell_metacharacters_allows_safe_command(self, adb_ops):
        assert not adb_ops._has_shell_metacharacters("ls")

    def test_is_dangerous_shell_command_detects_rm(self, adb_ops):
        assert adb_ops._is_dangerous_shell_command("rm file.txt")

    def test_is_dangerous_shell_command_detects_reboot(self, adb_ops):
        assert adb_ops._is_dangerous_shell_command("reboot")

    def test_is_dangerous_shell_command_allows_cat(self, adb_ops):
        assert not adb_ops._is_dangerous_shell_command("cat /data/test.txt")

    def test_is_dangerous_shell_command_rejects_unknown_cmd(self, adb_ops):
        # Any command not in SAFE_SHELL_COMMANDS should be dangerous
        assert adb_ops._is_dangerous_shell_command("unknown_command")

    def test_shell_rejects_metacharacters(self, adb_ops):
        result = adb_ops.shell("ls | grep test")
        assert not result.ok
        assert "metacommand" in result.stderr.lower()

    def test_shell_rejects_dangerous_commands(self, adb_ops):
        result = adb_ops.shell("rm -rf /")
        assert not result.ok
        assert "nao permitido" in result.stderr.lower()

    def test_push_rejects_protected_directories(self, adb_ops):
        # Mock local file exists
        import tempfile
        with tempfile.NamedTemporaryFile() as f:
            result = adb_ops.push(f.name, "/system/app/test.apk")
            assert not result.ok
            assert "protegido" in result.stderr.lower()

    def test_install_validates_apk_magic_bytes(self, adb_ops):
        # Create a non-APK file
        import tempfile
        import os
        f = tempfile.NamedTemporaryFile(suffix=".apk", delete=False)
        try:
            f.write(b"NOT_AN_APK_FILE")
            f.close()
            result = adb_ops.install(f.name)
            assert not result.ok
            assert "magic" in result.stderr.lower()
        finally:
            try:
                os.unlink(f.name)
            except Exception:
                pass

    def test_select_device_on_empty_list(self, adb_ops):
        # If no devices, select should fail gracefully
        result = adb_ops.select_device("nonexistent-device")
        # Will fail because device doesn't exist
        assert not result.ok

    def test_devices_command_returns_result(self, adb_ops):
        result = adb_ops.devices()
        assert isinstance(result, AdbResult)
        assert result.command == "adb devices -l"

    def test_current_with_no_device_selected(self, adb_ops):
        if not adb_ops.device_id:
            result = adb_ops.current()
            # Should either return current device or error
            assert isinstance(result, AdbResult)
