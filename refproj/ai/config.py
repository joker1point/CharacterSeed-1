# [优化] 集中管理数据目录路径，避免硬编码 "ai/data/..." 导致启动目录不一致
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parent
DATA_DIR = AI_ROOT / "data"
PROMPTS_DIR = DATA_DIR / "prompts"
VECTORS_DIR = DATA_DIR / "vectors"
CHARACTER_SCRIPTS_DIR = DATA_DIR / "character_scripts"
RAW_DIR = DATA_DIR / "raw"


def vector_path_for_source(source_path: str) -> Path:
    """根据原始文本路径生成对应的向量文件路径。"""
    filename = Path(source_path.replace("\\", "/")).name
    return VECTORS_DIR / f"{filename}.jsonl"
