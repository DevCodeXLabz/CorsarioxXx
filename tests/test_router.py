from corsarioxxx.config import ensure_data_dir, get_paths
from corsarioxxx.memory import MemoryStore
from corsarioxxx.router import route_prompt


def test_identity_is_deterministic(tmp_path):
    paths = get_paths(tmp_path)
    ensure_data_dir(paths)
    memory = MemoryStore(paths)
    routed = route_prompt("quem sou eu", memory)
    assert routed.mode == "deterministic"
    assert "sr71n3" in routed.content


def test_exec_route_is_detected(tmp_path):
    paths = get_paths(tmp_path)
    ensure_data_dir(paths)
    memory = MemoryStore(paths)
    routed = route_prompt("/exec Get-ChildItem", memory)
    assert routed.mode == "exec"
    assert routed.content == "Get-ChildItem"
