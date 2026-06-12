"""
CharacterSeed Frontend — API Client 模块
==========================================

设计理念（Why this module exists）：
  将全部 HTTP 调用逻辑集中在单一模块中，UI 层（app.py）不涉及 URL 拼接、
  requests 参数构造、异常捕获细节。

核心设计决策：
  1. 同步 requests 而非异步 aiohttp
     —— Streamlit 内部以同步方式运行脚本（每次 rerun 从头执行），
        使用同步 requests 在语义上完全匹配，且无需 asyncio 事件循环管理。
  2. 每个 API 函数独立封装
     —— 8 个端点 = 8 个函数，一一对应。
        避免用一个"通用调用函数"导致类型安全丢失和参数歧义。
  3. 异常统一转换为 dict 结果
     —— 不向上抛异常，而是返回 {"error": True, "detail": "..."} 字典。
        Streamlit 页面代码只需检查 "error" key，无需 try/except 样板。
  4. 文件上传使用 requests.post(files=...)
     —— 后端端点 require UploadFile via Form，对应 requests 的 files 参数。
        文件名推断从 file_uploader 返回的 BytesIO 对象获取。
"""

import requests
import json
from typing import Optional, List, Dict, Any


# ============================================================
# 配置常量
# ============================================================
# 为何硬编码而非从配置文件读取：
#   本地 Demo 场景，前端和后端在 localhost 上固定端口运行。
#   生产环境可通过环境变量覆盖，但 Demo 阶段的确定性比灵活性更重要。
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api"
TIMEOUT_SECONDS = 120  # LLM 调用可能耗时较长（Creation 可达 60s+）


# ============================================================
# 内部辅助函数
# ============================================================

def _build_url(path: str) -> str:
    """拼接完整 URL。不暴露给外部，所有 URL 逻辑集中在此。"""
    return f"{BASE_URL}{path}"


def _handle_response(response: requests.Response) -> Dict[str, Any]:
    """
    统一处理 HTTP 响应。

    设计考量：
      - 200/201 → 返回 JSON 数据（dict 或 list）
      - 4xx/5xx → 返回 {"error": True, "detail": "..."}
      - 连接错误 → 在调用函数处通过 except 捕获并转换

    为何不在此函数中捕获 ConnectionError：
      此函数只处理"已得到响应"的情况。连接的建立/失败在调用方捕获，
      因为不同 API 的 ConnectionError 可能有不同的用户提示。
    """
    if response.ok:
        return response.json()
    else:
        return {
            "error": True,
            "detail": f"HTTP {response.status_code}: {response.text[:500]}"
        }


# ============================================================
# 角色 API (4 个端点)
# ============================================================

def create_character_text(description: str) -> Dict[str, Any]:
    """
    通过文本描述创建角色。
    端点: POST /api/characters/create (Form data)

    Args:
        description: 用户输入的角色描述文本

    Returns:
        成功: CharacterResponse dict (含 id/name/personality 等)
        失败: {"error": True, "detail": "..."}

    为何用 Form data 而非 JSON body：
      后端端点 design 将 description 定义为 Form(...)，与 story_file
      的 UploadFile 共存于同一端点。使用 data= 而非 json= 匹配 Form 语义。
    """
    try:
        response = requests.post(
            _build_url(f"{API_PREFIX}/characters/create"),
            data={"description": description},
            timeout=TIMEOUT_SECONDS,
        )
        return _handle_response(response)
    except requests.ConnectionError:
        return {"error": True, "detail": "无法连接后端，请确认 uvicorn 已启动在 :8000"}
    except requests.Timeout:
        return {"error": True, "detail": "请求超时，LLM 生成可能耗时过长，请重试"}


def create_character_file(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    通过 TXT 文件上传创建角色。
    端点: POST /api/characters/create (multipart/form-data)

    Args:
        file_bytes: 文件内容的字节数据
        filename: 原始文件名（用于推断 content-type）

    Returns:
        成功: CharacterResponse dict
        失败: {"error": True, "detail": "..."}

    为何分离 text 和 file 两个函数而非用一个统一函数：
      requests 的 data= 和 files= 参数语义不同。
      Streamlit 的 st.file_uploader 返回 BytesIO，需要额外提取 bytes。
      两个独立函数让调用方明确知道自己在做什么，避免参数误传。
    """
    try:
        response = requests.post(
            _build_url(f"{API_PREFIX}/characters/create"),
            files={"story_file": (filename, file_bytes, "text/plain")},
            timeout=TIMEOUT_SECONDS,
        )
        return _handle_response(response)
    except requests.ConnectionError:
        return {"error": True, "detail": "无法连接后端，请确认 uvicorn 已启动在 :8000"}
    except requests.Timeout:
        return {"error": True, "detail": "请求超时，LLM 生成可能耗时过长，请重试"}


def get_characters(skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """
    获取角色列表。
    端点: GET /api/characters

    Returns:
        成功: List[CharacterResponse]
        失败: 空列表 []（并 st.error 显示错误）
    """
    try:
        response = requests.get(
            _build_url(f"{API_PREFIX}/characters"),
            params={"skip": skip, "limit": limit},
            timeout=10,
        )
        result = _handle_response(response)
        if isinstance(result, list):
            return result
        return []
    except (requests.ConnectionError, requests.Timeout):
        return []


def get_character(character_id: int) -> Dict[str, Any]:
    """
    获取单个角色详情。
    端点: GET /api/characters/{character_id}

    Returns:
        成功: CharacterResponse dict（personality/current_state 为 JSON 字符串）
        失败: {"error": True, "detail": "..."}
    """
    try:
        response = requests.get(
            _build_url(f"{API_PREFIX}/characters/{character_id}"),
            timeout=10,
        )
        return _handle_response(response)
    except requests.ConnectionError:
        return {"error": True, "detail": "无法连接后端"}
    except requests.Timeout:
        return {"error": True, "detail": "请求超时"}


# ============================================================
# 对话 API (1 个端点)
# ============================================================

def send_message(character_id: int, message: str) -> Dict[str, Any]:
    """
    发送玩家消息，获取 NPC 回复（Director + Actor 双 LLM 管线）。
    端点: POST /api/chat (JSON body)

    Args:
        character_id: 目标角色 ID
        message:      玩家输入的消息文本

    Returns:
        成功: ChatResponse dict
              {id, character_id, user_input, npc_response,
               emotion, action, expression, director_raw, actor_raw, timestamp}
        失败: {"error": True, "detail": "..."}

    为何使用 JSON body 而非 Form：
      ChatRequest 是一个 Pydantic BaseModel（character_id + message），
      后端通过请求体解析。requests.post(json=...) 自动设置
      Content-Type: application/json。
    """
    try:
        response = requests.post(
            _build_url(f"{API_PREFIX}/chat"),
            json={"character_id": character_id, "message": message},
            timeout=TIMEOUT_SECONDS,
        )
        return _handle_response(response)
    except requests.ConnectionError:
        return {"error": True, "detail": "无法连接后端，请确认 uvicorn 已启动"}
    except requests.Timeout:
        return {"error": True, "detail": "对话请求超时，请重试"}


# ============================================================
# 成长 API (1 个端点)
# ============================================================

def trigger_growth(character_id: int) -> Dict[str, Any]:
    """
    触发角色成长（Growth LLM 管线）。
    端点: POST /api/growth/trigger (JSON body)

    管线流程（后端执行）：
      1. 读取角色当前人格 + 最近 10 条对话
      2. Growth LLM 分析 → personality_delta / new_memories / event_summary
      3. 计算新人格 = 旧人格 + delta（钳位 [0, 100]）
      4. 持久化 growth_log + memories + 更新 character.personality

    Returns:
        成功: GrowthResponse dict
              {id, character_id, personality_delta, event_summary,
               new_memories, growth_raw, created_at}
        失败: {"error": True, "detail": "..."}

    注意：Growth 是异步触发接口，不存在降级策略。
          LLM 失败时直接返回错误，调用方可自行决定是否重试。
    """
    try:
        response = requests.post(
            _build_url(f"{API_PREFIX}/growth/trigger"),
            json={"character_id": character_id},
            timeout=TIMEOUT_SECONDS,
        )
        return _handle_response(response)
    except requests.ConnectionError:
        return {"error": True, "detail": "无法连接后端"}
    except requests.Timeout:
        return {"error": True, "detail": "成长分析请求超时，请重试"}


# ============================================================
# 数据查询 API (3 个端点)
# ============================================================

def get_memories(
    character_id: int,
    memory_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    获取角色记忆列表。
    端点: GET /api/characters/{character_id}/memories?memory_type=...

    Args:
        character_id: 角色 ID
        memory_type:  可选筛选（"conversation" / "event" / "growth" / None=all）
        skip/limit:   分页参数

    Returns:
        成功: List[MemoryResponse]
             每条: {id, character_id, content, importance, memory_type, created_at}
        失败: 空列表 []

    为何返回空列表而非抛异常：
      记忆查询是展示型操作，失败时不影响核心流程。
      空列表在 UI 上自然表现为"暂无数据"，不需要额外的错误态处理。
    """
    try:
        params = {"skip": skip, "limit": limit}
        if memory_type:
            params["memory_type"] = memory_type
        response = requests.get(
            _build_url(f"{API_PREFIX}/characters/{character_id}/memories"),
            params=params,
            timeout=10,
        )
        result = _handle_response(response)
        if isinstance(result, list):
            return result
        return []
    except (requests.ConnectionError, requests.Timeout):
        return []


def get_conversations(
    character_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    获取角色对话历史。
    端点: GET /api/characters/{character_id}/conversations

    Returns:
        成功: List[ChatResponse 风格 dict]
        失败: 空列表 []
    """
    try:
        response = requests.get(
            _build_url(f"{API_PREFIX}/characters/{character_id}/conversations"),
            params={"skip": skip, "limit": limit},
            timeout=10,
        )
        result = _handle_response(response)
        if isinstance(result, list):
            return result
        return []
    except (requests.ConnectionError, requests.Timeout):
        return []


def get_growth_logs(
    character_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    获取角色成长记录。
    端点: GET /api/characters/{character_id}/growth-logs

    Returns:
        成功: List[GrowthResponse 风格 dict]
        失败: 空列表 []
    """
    try:
        response = requests.get(
            _build_url(f"{API_PREFIX}/characters/{character_id}/growth-logs"),
            params={"skip": skip, "limit": limit},
            timeout=10,
        )
        result = _handle_response(response)
        if isinstance(result, list):
            return result
        return []
    except (requests.ConnectionError, requests.Timeout):
        return []


# ============================================================
# 健康检查
# ============================================================

def check_backend_health() -> bool:
    """
    检查后端是否可达。
    终点: GET /

    在 Streamlit 首次渲染时调用，确定是否展示"后端未启动"警告。
    """
    try:
        response = requests.get(
            _build_url("/"),
            timeout=3,
        )
        return response.ok
    except (requests.ConnectionError, requests.Timeout):
        return False
