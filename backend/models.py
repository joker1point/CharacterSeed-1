from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
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

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    user_input = Column(Text, nullable=False)
    npc_response = Column(Text, nullable=True)
    emotion = Column(String(50), nullable=True)
    action = Column(Text, nullable=True)
    expression = Column(String(100), nullable=True)
    director_raw = Column(Text, nullable=True)  # Director LLM原始响应
    actor_raw = Column(Text, nullable=True)  # Actor LLM原始响应
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

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
