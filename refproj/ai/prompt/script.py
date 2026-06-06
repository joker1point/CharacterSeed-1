import json
from pathlib import Path

from ..config import CHARACTER_SCRIPTS_DIR


def script_path_for_name(script_name: str) -> Path:
    return CHARACTER_SCRIPTS_DIR / f"{script_name}.json"


def save_script(script_name: str, script) -> Path:
    # [优化] 使用 config 路径，并返回保存位置
    script_path = script_path_for_name(script_name)
    script_path.parent.mkdir(parents=True, exist_ok=True)

    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=4)

    return script_path


def load_script(script_path: str):
    path = Path(script_path)
    if not path.exists():
        return None

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
