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
# ChatRequest 统一在底部 "ChatSession Schemas" 之后定义（带可选 session_id）

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
    session_id: Optional[int] = None  # ← 新增：返回消息所属 session
    session_title: Optional[str] = None  # ← 新增：方便前端立即更新侧栏

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

# ==================== LLM Settings Schemas ====================

class ProviderMeta(BaseModel):
    """前端下拉选项用的厂商元信息"""
    id: str
    name: str
    needs_key: str  # "true" / "false"（用字符串是因前端 JS 解析方便）


class ProviderConfig(BaseModel):
    """单个 provider 的配置（写入侧：明文 api_key）"""
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


class ProviderConfigMasked(BaseModel):
    """单个 provider 的配置（读取侧：api_key 已脱敏）"""
    api_key: str        # 已脱敏：保留首尾 4 字符
    base_url: str
    model: str


class LLMSettingsResponse(BaseModel):
    """GET /api/settings/llm 的响应体"""
    active_provider: str
    active_provider_name: str
    config: ProviderConfigMasked
    default_temperature: float
    default_max_tokens: int
    providers: dict  # {provider_id: ProviderConfigMasked}
    settings_file_path: str  # 给前端展示用，便于排错


class LLMUpdateRequest(BaseModel):
    """PUT /api/settings/llm 的请求体（部分字段可选）"""
    active_provider: Optional[str] = None       # 切换激活 provider
    active_config: Optional[ProviderConfig] = None  # 修改当前激活 provider 的配置
    default_temperature: Optional[float] = None
    default_max_tokens: Optional[int] = None


class LLMTestRequest(BaseModel):
    """POST /api/settings/llm/test 的请求体（可选覆盖当前配置）"""
    # 不传则用当前激活 provider 的配置测试
    provider_id: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    test_prompt: Optional[str] = "你好，请用一句话自我介绍。"


class LLMTestResponse(BaseModel):
    """POST /api/settings/llm/test 的响应体"""
    success: bool
    message: str
    provider_id: str
    model: str
    response_text: Optional[str] = None
    latency_ms: Optional[int] = None


# ==================== API Test Schemas ====================
# 参考 https://github.com/joker1point/web-tools 的 API 联通测试 Dashboard
# 三大能力：models 列表 / 流式延迟 / 原始请求探针

class TestModelItem(BaseModel):
    """provider /v1/models 返回的单个模型条目"""
    id: str
    owned_by: str = ""
    object: str = "model"


class ModelsListResponse(BaseModel):
    """GET /api/test/models 响应体"""
    provider_id: str
    base_url: str
    models: List[TestModelItem]
    duration_ms: int
    raw_count: int


class LatencyTestRequest(BaseModel):
    """POST /api/test/latency 请求体"""
    provider_id: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    test_message: Optional[str] = "Hi"
    max_tokens: Optional[int] = 16


class LatencyTestResponse(BaseModel):
    """POST /api/test/latency 响应体"""
    provider_id: str
    model: str
    status: int
    ttft_ms: Optional[int] = None      # Time To First Token
    total_ms: Optional[int] = None     # 完整响应耗时
    content: str = ""
    chunks: int = 0
    error: Optional[str] = None


class ProbeRequest(BaseModel):
    """POST /api/test/probe 请求体（debug 模式）"""
    provider_id: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    test_message: Optional[str] = "Hi"
    max_tokens: Optional[int] = 16


class ProbeResponse(BaseModel):
    """POST /api/test/probe 响应体（含完整 request/response，密钥脱敏）"""
    provider_id: str
    model: str
    base_url: str
    request: dict
    response: dict
    error: Optional[str] = None


# ==================== ChatSession Schemas ====================
# 参考 https://github.com/ChatGPTNextWeb/NextChat 的会话管理
# 提供：list / create / rename / delete / get-detail（带 messages）/ search

class ChatSessionCreate(BaseModel):
    """POST /api/sessions 请求体"""
    character_id: int
    title: Optional[str] = None  # 缺省时用"新对话"占位


class ChatSessionUpdate(BaseModel):
    """PATCH /api/sessions/{id} 请求体（目前只支持改 title）"""
    title: str


class ChatSessionInfo(BaseModel):
    """会话概要（列表用）"""
    id: int
    character_id: int
    title: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    message_count: int = 0

    class Config:
        from_attributes = True


class ChatSessionWithMessages(ChatSessionInfo):
    """会话详情（含所有消息）"""
    messages: List["ConversationRow"] = []


class ConversationRow(BaseModel):
    """单条对话（与数据库行 1:1）"""
    id: int
    session_id: Optional[int] = None
    character_id: int
    user_input: str
    npc_response: Optional[str] = None
    emotion: Optional[str] = None
    action: Optional[str] = None
    expression: Optional[str] = None
    director_raw: Optional[str] = None
    actor_raw: Optional[str] = None
    timestamp: Optional[str] = None

    class Config:
        from_attributes = True


# ChatRequest 增加可选的 session_id（向后兼容：None 时自动创建新 session）
class ChatRequest(BaseModel):
    character_id: int
    message: str
    session_id: Optional[int] = None  # ← 新增


# 解决 ChatSessionWithMessages 中 ConversationRow 的前向引用
ChatSessionWithMessages.model_rebuild()
