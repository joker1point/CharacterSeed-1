"""
数据库迁移工具

用途：处理 schema 演进。当前内置两个迁移：
  - MIGRATION_V001_SESSIONS: 引入 ChatSession，给 Conversation 加 session_id
    并把存量"孤儿"对话回填到每个角色的"默认会话"。

设计原则：
  - 幂等：可重复执行，不会重复添加列/重复回填
  - 不依赖 alembic 等第三方库，纯 SQL 兼容性最大
  - 失败抛异常让启动失败，便于及早发现
"""
import logging
import sqlite3
from typing import List

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def _sqlite_columns(engine: Engine, table: str) -> List[str]:
    """读取 SQLite 表的列名列表（其它数据库 PRAGMA 行为可能不同）"""
    if not engine.url.get_backend_name().startswith("sqlite"):
        # 其它数据库暂时不处理，启动后端时跳过迁移
        return []
    with engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return [r[1] for r in rows]


def _sqlite_table_exists(engine: Engine, table: str) -> bool:
    if not engine.url.get_backend_name().startswith("sqlite"):
        return False
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:n"),
            {"n": table},
        ).fetchone()
    return row is not None


def migrate_v001_sessions(engine: Engine) -> dict:
    """
    迁移 v001：引入 ChatSession + Conversation.session_id + 回填

    步骤：
      1) 确保 chat_sessions 表存在（Base.metadata.create_all 已创建）
      2) 给 conversations 加 session_id 列（若已存在则跳过）
      3) 给每条 session_id IS NULL 的对话，分配到一个名为"默认会话"的 session
         （按 character_id 分组，每个角色一个默认 session）

    Returns:
        {"added_column": bool, "backfilled": int, "default_sessions_created": int}
    """
    result = {"added_column": False, "backfilled": 0, "default_sessions_created": 0}

    if not _sqlite_table_exists(engine, "conversations"):
        return result  # 全新库，不需要迁移

    # 1) 加列
    cols = _sqlite_columns(engine, "conversations")
    if "session_id" not in cols:
        logger.info("迁移 v001: 添加 conversations.session_id 列")
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE conversations ADD COLUMN session_id INTEGER "
                "REFERENCES chat_sessions(id) ON DELETE CASCADE"
            ))
        result["added_column"] = True
    else:
        logger.debug("迁移 v001: conversations.session_id 已存在，跳过")

    # 2) 回填
    with engine.connect() as conn:
        # 找所有存在孤儿对话的 character_id
        rows = conn.execute(text(
            "SELECT DISTINCT character_id FROM conversations WHERE session_id IS NULL"
        )).fetchall()
    char_ids = [r[0] for r in rows]
    if not char_ids:
        logger.debug("迁移 v001: 无孤儿对话，无需回填")
        return result

    logger.info("迁移 v001: 为 %d 个角色回填默认会话", len(char_ids))
    with engine.begin() as conn:
        for cid in char_ids:
            # 用最早一条对话的时间作为 created_at（让默认会话在列表里更靠下）
            earliest = conn.execute(text(
                "SELECT MIN(timestamp) FROM conversations "
                "WHERE character_id = :cid AND session_id IS NULL"
            ), {"cid": cid}).scalar()

            # 创建默认 session
            res = conn.execute(text(
                "INSERT INTO chat_sessions (character_id, title, created_at, updated_at) "
                "VALUES (:cid, :title, :ts, :ts)"
            ), {"cid": cid, "title": "默认会话", "ts": earliest})
            new_sid = res.lastrowid
            result["default_sessions_created"] += 1

            # 把该角色的所有孤儿对话指给新 session
            upd = conn.execute(text(
                "UPDATE conversations SET session_id = :sid "
                "WHERE character_id = :cid AND session_id IS NULL"
            ), {"sid": new_sid, "cid": cid})
            result["backfilled"] += upd.rowcount or 0

    logger.info(
        "迁移 v001 完成: 加列=%s, 回填=%d 条, 创建默认会话=%d",
        result["added_column"], result["backfilled"], result["default_sessions_created"],
    )
    return result


def run_all_migrations(engine: Engine) -> List[dict]:
    """
    按版本顺序执行所有迁移。在应用启动时调用一次。
    新增迁移时在此函数中追加。
    """
    history = []
    history.append({
        "version": "v001_sessions",
        **migrate_v001_sessions(engine),
    })
    return history
