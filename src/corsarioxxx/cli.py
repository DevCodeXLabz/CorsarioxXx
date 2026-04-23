from __future__ import annotations

import getpass
from dataclasses import dataclass

from .auth import create_password_record, verify_password
from .config import ensure_data_dir, get_paths, load_json, write_json
from .llm import OllamaClient
from .memory import MemoryStore
from .runtime import AssistantRuntime
from .tools import CommandRunner


@dataclass
class AppConfig:
    owner_name: str
    assistant_name: str
    password: dict[str, str]


def load_config() -> tuple[AppConfig, MemoryStore]:
    paths = get_paths()
    ensure_data_dir(paths)

    raw_config = load_json(paths.config_file, {})
    if not raw_config:
        owner_name = "sr71n3"
        assistant_name = "CorsarioXxX"
        password = getpass.getpass("Defina a senha mestra local: ")
        confirm = getpass.getpass("Confirme a senha mestra local: ")
        if password != confirm:
            raise ValueError("As senhas nao conferem.")

        raw_config = {
            "owner_name": owner_name,
            "assistant_name": assistant_name,
            "password": create_password_record(password),
        }
        write_json(paths.config_file, raw_config)

    memory = MemoryStore(paths)
    payload = memory.load()
    payload["owner_facts"]["owner_name"] = raw_config["owner_name"]
    payload["assistant_facts"]["name"] = raw_config["assistant_name"]
    memory.save(payload)

    config = AppConfig(
        owner_name=raw_config["owner_name"],
        assistant_name=raw_config["assistant_name"],
        password=raw_config["password"],
    )
    return config, memory


def authenticate(config: AppConfig) -> None:
    password = getpass.getpass("Senha mestra: ")
    if not verify_password(password, config.password):
        raise PermissionError("Autenticacao falhou.")


def main() -> int:
    config, memory = load_config()
    authenticate(config)

    from .file_ops import FileOperations
    from pathlib import Path
    
    file_ops = FileOperations(Path.cwd())
    runtime = AssistantRuntime(memory=memory, llm=OllamaClient(), runner=CommandRunner(), file_ops=file_ops)

    print(f"{config.assistant_name} online. Digite /sair para encerrar.")
    print("Comandos disponiveis: /exec, /createfile, /editfile, /readfile, /sair")
    while True:
        prompt = input(f"{config.owner_name}> ").strip()
        if not prompt:
            continue
        if prompt.lower() == "/sair":
            return 0

        response, decision, _ = runtime.handle_prompt(prompt)
        print(f"{config.assistant_name}> {response}")

        if decision and decision.requires_confirmation:
            answer = input("Executar mesmo assim? [s/N] ").strip().lower()
            if answer == "s" and prompt.lower().startswith("/exec "):
                result = runtime.runner.run(prompt[6:].strip())
                print(f"{config.assistant_name}> {result.render()}")

