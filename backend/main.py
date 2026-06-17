from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List

from backend.database import engine, get_db, Base
from backend.models import Character, Conversation, Memory, GrowthLog
from backend.schemas import (
    CharacterCreate, CharacterResponse,
    ChatRequest, ChatResponse,
    MemoryResponse,
    GrowthTriggerRequest, GrowthResponse
)
from backend.crud import character as character_crud
from backend.crud import memory as memory_crud
from backend.crud import conversation as conversation_crud
from backend.crud import growth as growth_crud
from backend.modules.creation import CreationModule
from backend.modules.interaction import InteractionPipeline
from backend.modules.growth import GrowthModule
from backend.modules.enhanced_interaction import EnhancedInteractionPipeline
from backend.api.memory_router import router as memory_router

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 创建FastAPI应用
app = FastAPI(
    title="CharacterSeed API",
    description="AI NPC生命模拟系统",
    version="0.1.0"
)

# ==================== 启动事件 ====================
@app.on_event("startup")
def startup_event():
    """应用启动时执行"""
    print("=" * 50)
    print("CharacterSeed API 启动成功！")
    print("访问 http://localhost:8000/docs 查看API文档")
    print("=" * 50)

# ==================== 注册记忆系统路由 ====================
app.include_router(memory_router)

# ==================== 全局实例 ====================
# 增强版管线（集成三层记忆）
enhanced_pipeline = EnhancedInteractionPipeline(enable_memory=True)

# ==================== Character Endpoints ====================

@app.post("/api/characters/create", response_model=CharacterResponse)
async def create_character(
    description: Optional[str] = Form(None),
    story_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    创建角色（支持一句话描述或TXT文件上传）
    
    - description: 一句话描述（可选）
    - story_file: TXT故事文件（可选，与description二选一）
    """
    # 确定输入类型和内容
    if story_file:
        # 读取文件内容
        content = await story_file.read()
        user_input = content.decode("utf-8")
        input_type = "file"
    elif description:
        user_input = description
        input_type = "text"
    else:
        raise HTTPException(status_code=400, detail="必须提供description或story_file")
    
    # 调用Creation Module
    try:
        creation_module = CreationModule()
        parsed_data, raw_response = creation_module.run(user_input, input_type)
        
        # 提取数据（personality/current_state 以 dict 形式传入 CRUD，
        # 由 CRUD 层统一完成 JSON 序列化，消除调用方重复的 json.dumps）
        name = parsed_data.get("name", "未命名角色")
        world_setting = parsed_data.get("world_setting")
        personality = parsed_data.get("personality", {})
        current_state = parsed_data.get("current_state", {})
        initial_memories = parsed_data.get("initial_memories", [])
        
        # 保存到数据库（CRUD 层自动将 dict 序列化为 JSON 字符串）
        db_character = character_crud.create_character(
            db=db,
            name=name,
            description=user_input[:500],  # 限制长度
            world_setting=world_setting,
            personality=personality,
            current_state=current_state,
            creation_raw=raw_response
        )
        
        # Day 3：保存初始记忆到 memories 表
        # 初始记忆来自 Creation LLM 的输出，每条含 content + importance 字段
        for mem in initial_memories:
            if isinstance(mem, dict):
                memory_crud.create_memory(
                    db=db,
                    character_id=db_character.id,
                    content=mem.get("content", ""),
                    importance=mem.get("importance", 5),
                    memory_type="event"  # 初始记忆标记为 event 类型
                )
        
        return db_character
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"角色创建失败: {str(e)}")

@app.get("/api/characters", response_model=List[CharacterResponse])
def get_characters(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取角色列表"""
    characters = character_crud.get_characters(db, skip=skip, limit=limit)
    return characters

@app.get("/api/characters/{character_id}", response_model=CharacterResponse)
def get_character(character_id: int, db: Session = Depends(get_db)):
    """获取单个角色详情"""
    character = character_crud.get_character(db, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    return character

# ==================== Chat Endpoints（Day 2实现） ====================

@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    与角色对话（Day 2 实现：Director + Actor 双 LLM 管线）

    管线流程:
      1. 从数据库获取角色、最近记忆
      2. Director.analyze()  → emotion / focus_memories / goal / style
      3. Actor.generate()    → action / expression / speech
      4. 持久化对话记录到 conversations 表
      5. 返回 ChatResponse
    """
    try:
        pipeline = InteractionPipeline()
        result = pipeline.run(
            character_id=request.character_id,
            user_message=request.message,
            db=db,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"对话处理失败: {str(e)}")


@app.post("/api/chat/enhanced", response_model=ChatResponse)
def chat_enhanced(
    request: ChatRequest,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    与角色对话（增强版 - 集成三层记忆系统）

    在基础管线之上：
    - 自动维护短期记忆（LangChain Window）
    - 自动记录长期记忆（Mem0）
    - 自动检索相关知识（Cognee RAG）
    - 返回响应中包含 memory_stats 字段

    Args:
        request: 包含 character_id 和 message
        user_id: 用户 ID（可选，用于多用户隔离）
    """
    try:
        # 使用全局增强管线实例
        result = enhanced_pipeline.run(
            character_id=request.character_id,
            user_message=request.message,
            db=db,
            user_id=user_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"增强对话失败: {str(e)}")

# ==================== Growth Endpoints（Day 3实现） ====================

@app.post("/api/growth/trigger", response_model=GrowthResponse)
def trigger_growth(request: GrowthTriggerRequest, db: Session = Depends(get_db)):
    """
    触发角色成长（Day 3 实现：Growth LLM 管线）

    管线流程:
      1. 从数据库获取角色、昨日最近对话
      2. GrowthModule.run() → personality_delta / new_memories / event_summary
      3. 计算新人格 = 旧人格 + delta
      4. 持久化 growth_log + memories + 更新 character.personality
      5. 返回 GrowthResponse

    注意：Growth 是异步触发接口，不设降级策略——LLM 失败时直接抛异常，
          调用方可自行决定何时重试。
    """
    try:
        growth_module = GrowthModule()
        result = growth_module.run(
            character_id=request.character_id,
            db=db,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"成长处理失败: {str(e)}")

# ==================== Memory Endpoints（Day 3实现） ====================

@app.get("/api/characters/{character_id}/memories", response_model=List[MemoryResponse])
def get_character_memories(
    character_id: int,
    memory_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取角色记忆列表"""
    memories = memory_crud.get_character_memories(
        db, character_id, memory_type=memory_type, skip=skip, limit=limit
    )
    return memories


@app.get("/api/characters/{character_id}/conversations")
def get_character_conversations(
    character_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取角色对话历史"""
    conversations = conversation_crud.get_character_conversations(
        db, character_id, skip=skip, limit=limit
    )
    return conversations


@app.get("/api/characters/{character_id}/growth-logs")
def get_character_growth_logs(
    character_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取角色成长记录列表"""
    logs = growth_crud.get_character_growth_logs(
        db, character_id, skip=skip, limit=limit
    )
    return logs


# ==================== 根路径 ====================

@app.get("/")
def root():
    return {
        "message": "CharacterSeed API is running!",
        "docs": "http://localhost:8000/docs",
        "version": "0.1.0"
    }
