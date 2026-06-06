import json

from ..config import PROMPTS_DIR


def load(session_id: str):
    # [优化] 路径来自 config，不依赖进程当前工作目录
    path = PROMPTS_DIR / f"{session_id}.json"

    if not path.exists():
        return None

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save(session_id: str, data):
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    path = PROMPTS_DIR / f"{session_id}.json"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
