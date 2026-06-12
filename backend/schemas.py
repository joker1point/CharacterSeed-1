from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# ==================== Character Schemas ====================

class CharacterCreate(BaseModel):
    description: str  # 用户描述（一句话或故事）
    # 注意：文件上传通过FastAPI的UploadFile处理，不在这里定义

class CharacterResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    world_setting: Optional[str] = None
    personality: Optional[str] = None  # JSON字符串
    current_state: Optional[str] = None  # JSON字符串
    creation_raw: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# ==================== Conversation Schemas ====================

class ChatRequest(BaseModel):
    character_id: int
    message: str

class ChatResponse(BaseModel):
    id: int
    character_id: int
    user_input: str
    npc_response: str
    emotion: Optional[str] = None
    action: Optional[str] = None
    expression: Optional[str] = None
    director_raw: Optional[str] = None
    actor_raw: Optional[str] = None
    timestamp: datetime
    
    class Config:
        from_attributes = True

# ==================== Memory Schemas ====================

class MemoryResponse(BaseModel):
    id: int
    character_id: int
    content: str
    importance: int = 5
    memory_type: str = "conversation"
    created_at: datetime
    
    class Config:
        from_attributes = True

# ==================== Growth Schemas ====================

class GrowthTriggerRequest(BaseModel):
    character_id: int

class GrowthResponse(BaseModel):
    id: int
    character_id: int
    personality_delta: Optional[str] = None
    event_summary: Optional[str] = None
    new_memories: Optional[str] = None
    growth_raw: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# ==================== Creation Response (Special) ====================

class CreationResponse(BaseModel):
    """Creation Module的完整响应"""
    id: int
    name: str
    world_setting: Optional[str] = None
    personality: Optional[str] = None
    initial_memories: Optional[List[str]] = None
    current_state: Optional[str] = None
    creation_raw: Optional[str] = None
