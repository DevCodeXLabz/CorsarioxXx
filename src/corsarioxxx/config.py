from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


APP_DIR_NAME = "data"


@dataclass(frozen=True)
class AppPaths:
    root_dir: Path
    data_dir: Path
    config_file: Path
    memory_file: Path
    log_file: Path


def get_paths(root_dir: Path | None = None) -> AppPaths:
    resolved_root = Path(root_dir or Path.cwd()).resolve()
    data_dir = resolved_root / APP_DIR_NAME
    return AppPaths(
        root_dir=resolved_root,
        data_dir=data_dir,
        config_file=data_dir / "config.json",
        memory_file=data_dir / "memory.json",
        log_file=data_dir / "session.log",
    )


def ensure_data_dir(paths: AppPaths) -> None:
    paths.data_dir.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default: dict | list) -> dict | list:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict | list) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
