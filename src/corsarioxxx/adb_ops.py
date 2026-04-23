from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AdbResult:
    ok: bool
    command: str
    stdout: str
    stderr: str

    def render(self) -> str:
        if self.ok:
            return f"✓ {self.command}: {self.stdout.strip()}"
        return f"✗ {self.command}: {self.stderr.strip()}"


class AdbOperations:
    """Operacoes ADB seguras para controlar dispositivos Android."""

    # Comandos shell seguros (whitelist)
    SAFE_SHELL_COMMANDS = {
        "cat",
        "ls",
        "getprop",
        "logcat",
        "ps",
        "top",
        "id",
        "whoami",
        "pm",  # package manager (read-only variants only)
        "dumpsys",
        "am",  # activity manager (read-only variants only)
    }

    # Padroes perigosos em shell commands
    DANGEROUS_PATTERNS = ("rm", "dd", "mkfs", "reboot", "shutdown", "wipe")

    # Caracteres de metacommand a rejeitar
    SHELL_METACHARACTERS = ("||", "&&", "|", ";", ">", "<", "$", "(`)", "`")

    MAX_RETRIES = 2
    RETRY_DELAY = 2
    DEFAULT_TIMEOUT = 30

    def __init__(self, device_id: str | None = None):
        self.device_id = device_id
        self._validate_adb_available()

    def _validate_adb_available(self) -> None:
        """Verifica que ADB esta disponivel no PATH."""
        try:
            subprocess.run(
                ["adb", "version"],
                capture_output=True,
                timeout=5,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            raise RuntimeError("ADB nao encontrado. Instale Android SDK.") from e

    def _get_connected_devices(self) -> list[str]:
        """Retorna lista de device IDs conectados."""
        try:
            result = subprocess.run(
                ["adb", "devices"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            devices = []
            for line in result.stdout.split("\n"):
                if "\tdevice" in line:
                    device_id = line.split("\t")[0]
                    if device_id:
                        devices.append(device_id)
            return devices
        except Exception:
            return []

    def _get_or_select_device(self) -> str | None:
        """Retorna o device_id a usar, ou None se nao ha dispositivos."""
        if self.device_id:
            # Valida que o device ainda esta conectado
            if self.device_id in self._get_connected_devices():
                return self.device_id
            else:
                raise RuntimeError(
                    f"Device {self.device_id} nao esta conectado. Use /adb devices para listar."
                )

        # Auto-detect: se ha apenas 1 device, use-o
        devices = self._get_connected_devices()
        if len(devices) == 1:
            return devices[0]
        elif len(devices) > 1:
            raise RuntimeError(
                f"Multiplos devices encontrados: {', '.join(devices)}. "
                "Use /adb select <device_id> para escolher um."
            )
        else:
            raise RuntimeError(
                "Nenhum device Android conectado. Conecte um device ou inicie um emulador."
            )

    def _has_shell_metacharacters(self, cmd: str) -> bool:
        """Detecta caracteres de metacommand perigosos."""
        for char in self.SHELL_METACHARACTERS:
            if char in cmd:
                return True
        return False

    def _is_dangerous_shell_command(self, cmd: str) -> bool:
        """Verifica se um comando shell eh perigoso."""
        lower = cmd.lower()
        # Check base command
        base_cmd = cmd.split()[0].lower()
        if base_cmd not in self.SAFE_SHELL_COMMANDS:
            return True
        # Check dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern.lower() in lower:
                return True
        return False

    def _run_adb(
        self,
        args: list[str],
        retry_count: int = 0,
    ) -> AdbResult:
        """Executa um comando ADB com retry logica."""
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=self.DEFAULT_TIMEOUT,
                shell=False,
            )
            return AdbResult(
                ok=result.returncode == 0,
                command=" ".join(args),
                stdout=result.stdout,
                stderr=result.stderr,
            )
        except subprocess.TimeoutExpired:
            if retry_count < self.MAX_RETRIES:
                time.sleep(self.RETRY_DELAY)
                return self._run_adb(args, retry_count + 1)
            return AdbResult(
                False,
                " ".join(args),
                "",
                f"Timeout apos {self.MAX_RETRIES} tentativas (device desconectado?)",
            )
        except Exception as e:
            return AdbResult(False, " ".join(args), "", str(e))

    def select_device(self, device_id: str) -> AdbResult:
        """Seleciona um device especifico."""
        devices = self._get_connected_devices()
        if device_id not in devices:
            return AdbResult(
                False,
                f"select {device_id}",
                "",
                f"Device nao encontrado. Disponveis: {', '.join(devices)}",
            )
        self.device_id = device_id
        return AdbResult(True, f"select {device_id}", f"Device {device_id} selecionado.", "")

    def devices(self) -> AdbResult:
        """Lista todos os devices conectados."""
        return self._run_adb(["adb", "devices", "-l"])

    def current(self) -> AdbResult:
        """Mostra o device selecionado."""
        try:
            device = self._get_or_select_device()
            return AdbResult(True, "current", f"Device atual: {device}", "")
        except RuntimeError as e:
            return AdbResult(False, "current", "", str(e))

    def shell(self, command: str) -> AdbResult:
        """Executa um comando shell seguro no device."""
        try:
            device = self._get_or_select_device()
        except RuntimeError as e:
            return AdbResult(False, f"shell {command}", "", str(e))

        # Verifica metacharacters
        if self._has_shell_metacharacters(command):
            return AdbResult(
                False,
                f"shell {command}",
                "",
                "Comando rejeitado: contem caracteres de metacommand (|, &&, ;, etc).",
            )

        # Verifica se eh comando seguro
        if self._is_dangerous_shell_command(command):
            return AdbResult(
                False,
                f"shell {command}",
                "",
                f"Comando nao permitido. Comandos seguros: {', '.join(sorted(self.SAFE_SHELL_COMMANDS))}",
            )

        return self._run_adb(["adb", "-s", device, "shell", command])

    def logcat(self, package_name: str = "", duration_seconds: int = 30) -> AdbResult:
        """Stream logcat para um package especifico com timeout."""
        try:
            device = self._get_or_select_device()
        except RuntimeError as e:
            return AdbResult(False, f"logcat {package_name}", "", str(e))

        try:
            if package_name:
                cmd = f"logcat --pid=$(pidof {package_name})"
            else:
                cmd = "logcat"

            subprocess.run(
                ["adb", "-s", device, "shell", cmd],
                timeout=duration_seconds,
                shell=False,
            )
            return AdbResult(
                True,
                f"logcat {package_name}",
                f"[Auto-parou apos {duration_seconds}s]",
                "",
            )
        except subprocess.TimeoutExpired:
            return AdbResult(
                True,
                f"logcat {package_name}",
                f"[Auto-parou apos {duration_seconds}s. Use Ctrl+C para parar mais cedo]",
                "",
            )
        except Exception as e:
            return AdbResult(False, f"logcat {package_name}", "", str(e))

    def push(self, local_path: str, remote_path: str) -> AdbResult:
        """Copia arquivo local para device."""
        try:
            device = self._get_or_select_device()
        except RuntimeError as e:
            return AdbResult(False, f"push {local_path} {remote_path}", "", str(e))

        # Valida arquivo local
        if not os.path.isfile(local_path):
            return AdbResult(
                False,
                f"push {local_path} {remote_path}",
                "",
                f"Arquivo nao encontrado: {local_path}",
            )

        if not os.access(local_path, os.R_OK):
            return AdbResult(
                False,
                f"push {local_path} {remote_path}",
                "",
                f"Nao consegue ler arquivo: {local_path}",
            )

        # Rejeita push para diretorios protegidos
        if remote_path.startswith("/system/") or remote_path.startswith("/data/data/"):
            return AdbResult(
                False,
                f"push {local_path} {remote_path}",
                "",
                f"Nao pode fazer push para diretorio protegido: {remote_path}",
            )

        return self._run_adb(["adb", "-s", device, "push", local_path, remote_path])

    def pull(self, remote_path: str, local_path: str) -> AdbResult:
        """Copia arquivo do device para local."""
        try:
            device = self._get_or_select_device()
        except RuntimeError as e:
            return AdbResult(False, f"pull {remote_path} {local_path}", "", str(e))

        # Cria diretorio local se nao existe
        local_dir = os.path.dirname(local_path)
        if local_dir and not os.path.exists(local_dir):
            try:
                os.makedirs(local_dir, exist_ok=True)
            except Exception as e:
                return AdbResult(
                    False,
                    f"pull {remote_path} {local_path}",
                    "",
                    f"Nao consegue criar diretorio: {e}",
                )

        return self._run_adb(["adb", "-s", device, "pull", remote_path, local_path])

    def install(self, apk_path: str) -> AdbResult:
        """Instala um APK no device."""
        try:
            device = self._get_or_select_device()
        except RuntimeError as e:
            return AdbResult(False, f"install {apk_path}", "", str(e))

        # Valida arquivo local
        if not os.path.isfile(apk_path):
            return AdbResult(
                False,
                f"install {apk_path}",
                "",
                f"APK nao encontrado: {apk_path}",
            )

        # Valida magic bytes (PK\x03\x04 para ZIP/APK)
        try:
            with open(apk_path, "rb") as f:
                magic = f.read(4)
                if magic != b"PK\x03\x04":
                    return AdbResult(
                        False,
                        f"install {apk_path}",
                        "",
                        "Arquivo nao eh um APK valido (magic bytes incorretos)",
                    )
        except Exception as e:
            return AdbResult(
                False, f"install {apk_path}", "", f"Nao consegue ler APK: {e}"
            )

        return self._run_adb(["adb", "-s", device, "install", apk_path])

    def uninstall(self, package_name: str) -> AdbResult:
        """Desinstala um package do device."""
        try:
            device = self._get_or_select_device()
        except RuntimeError as e:
            return AdbResult(False, f"uninstall {package_name}", "", str(e))

        return self._run_adb(["adb", "-s", device, "uninstall", package_name])
