from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Index
from sqlalchemy.sql import func
from backend.database import Base

class Character(Base):
    __tablename__ = "characters"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)  # 用户原始输入
    world_setting = Column(Text, nullable=True)  # 世界设定（LLM生成）
    personality = Column(Text, nullable=True)  # 人格属性（JSON格式）
    current_state = Column(Text, nullable=True)  # 当前状态（JSON格式）
    creation_raw = Column(Text, nullable=True)  # Creation LLM原始响应
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ChatSession(Base):
    """
    对话会话（多轮消息的容器，参考 NextChat 的 session 概念）

    与 Conversation 的关系：
      - ChatSession 1 → N Conversation
      - 每个 session 有一个 title（自动生成首条消息前缀 or 用户手动改）
      - 删除 session 会级联删除其下所有 conversation
    """
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(
        Integer, ForeignKey("characters.id"), nullable=False, index=True,
    )
    title = Column(String(200), nullable=False, default="新对话")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        index=True,  # 列表页按更新时间倒序，常查
    )


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    # 会话归属（可空以兼容旧数据；migrate 时会回填到默认 session）
    session_id = Column(
        Integer,
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_input = Column(Text, nullable=False)
    npc_response = Column(Text, nullable=True)
    emotion = Column(String(50), nullable=True)
    action = Column(Text, nullable=True)
    expression = Column(String(100), nullable=True)
    director_raw = Column(Text, nullable=True)  # Director LLM原始响应
    actor_raw = Column(Text, nullable=True)  # Actor LLM原始响应
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class Memory(Base):
    __tablename__ = "memories"
    
    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    content = Column(Text, nullable=False)
    importance = Column(Integer, default=5)  # 1-10，默认5
    memory_type = Column(String(50), default="conversation")  # conversation, event, growth
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class GrowthLog(Base):
    __tablename__ = "growth_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    personality_delta = Column(Text, nullable=True)  # 人格变化（JSON格式）
    event_summary = Column(Text, nullable=True)
    new_memories = Column(Text, nullable=True)  # 新增记忆（JSON数组）
    growth_raw = Column(Text, nullable=True)  # Growth LLM原始响应
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# 复合索引：高频查询模式
# ============================================================
# 1) 会话列表：按 character_id + updated_at desc
Index(
    "ix_chat_sessions_char_updated",
    ChatSession.character_id, ChatSession.updated_at.desc(),
)
# 2) 单会话的消息列表：按 session_id + timestamp
Index(
    "ix_conversations_session_timestamp",
    Conversation.session_id, Conversation.timestamp,
)
