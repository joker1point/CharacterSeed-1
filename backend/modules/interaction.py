"""
Day 2 — 交互运行时（Interaction Runtime）

设计理念：采用"注意力聚焦 + 行为生成"双 LLM 管路。
    Director.analyze() → 角色"感知"世界，决定该关注什么
    Actor.generate()   → 角色"表达"自我，生成动作/表情/语言

该架构的核心优势：
  - 可解释性：Director 的中间输出（emotion / focus_memories / goal）
              可独立可视化，让观察者看到"角色的思考过程"
  - 可调试性：两个 LLM 独立调试 prompt 与温度参数，互不干扰
  - 鲁棒性：  每个 LLM 调用点都有独立降级策略，任一失败不影响管线完整性

温度参数选择依据：
  - Director temperature=0.5：注意力聚焦需要逻辑一致性，偏低减少随机性
  - Actor temperature=0.8：  行为/语言生成需要创造性，偏高避免千篇一律
"""

import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from sqlalchemy.orm import Session

from backend.services.llm_service import LLMService
from backend.services.observability import observe_safe, update_current_trace
from backend.crud import character as character_crud
from backend.crud import memory as memory_crud
from backend.crud import conversation as conversation_crud

logger = logging.getLogger(__name__)


# ============================================================================
# 降级常量：当 LLM 调用失败时，保证管线不崩溃
# 设计考量：降级值采用"中立/保守"策略——
#   宁可返回一个 bland but correct 的回复，也不返回空值或报错
# ============================================================================

FALLBACK_DIRECTOR_OUTPUT: Dict[str, Any] = {
    "emotion": "平静",
    "focus_memories": [],
    "goal": "与玩家进行友好交谈",
    "style": "温和有礼的",
}

FALLBACK_ACTOR_OUTPUT: Dict[str, Any] = {
    "action": "站在原地，注视着玩家",
    "expression": "表情平静",
    "speech": "（角色暂时无法回应）",
}


# ============================================================================
# Director：注意力聚焦模块
# ============================================================================

class DirectorModule:
    """
    注意力聚焦模块（Director）

    职责：给定角色状态 + 玩家输入，决定角色"该关注什么"。
    ——这是双 LLM 管路的第一阶段，模拟人类的"感知→关注"认知过程。

    输入 → 输出链路：
        character_name + personality + current_state
        + recent_memories + user_input
            ↓  一次 LLM 调用 (temperature=0.5, response_format=json_object)
        emotion + focus_memories + goal + style
    """

    def __init__(self):
        self.llm_service = LLMService()
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """加载 Director prompt 模板文件"""
        with open("backend/prompts/director.txt", "r", encoding="utf-8") as f:
            return f.read()

    @observe_safe("director.analyze", as_type="generation")
    def analyze(
        self,
        character_name: str,
        personality: Dict[str, Any],
        current_state: Dict[str, Any],
        recent_memories: List[str],
        user_input: str,
        history_messages: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[Dict[str, Any], str]:
        """
        执行注意力聚焦分析。

        Args:
            character_name:  角色名称
            personality:     人格属性字典（如 {"optimism": 70, ...}）
            current_state:   当前状态字典（如 {"location": "酒馆", ...}）
            recent_memories: 最近记忆内容列表（字符串，最多5条）
            user_input:      玩家输入文本
            history_messages: 可选的历史对话消息列表。
                传入时启用多轮模式 ——
                messages 数组会按 [system, ...history, current_user(prompt)] 顺序组装，
                LLM 能感知完整对话上下文。
                传 None 或空列表则回退到单轮（system + user）模式。

        Returns:
            (parsed_data, raw_response) 元组
            - parsed_data: 校验通过后的字典 {emotion, focus_memories, goal, style}
            - raw_response: LLM 原始 JSON 字符串

        降级策略：
            LLM 调用异常 → 返回 FALLBACK_DIRECTOR_OUTPUT + 错误日志
        """
        # --- 步骤 1：组装 prompt ---
        personality_str = json.dumps(personality, ensure_ascii=False)
        current_state_str = json.dumps(current_state, ensure_ascii=False)
        memories_str = "\n".join(
            f"  - {mem}" for mem in (recent_memories or [])
        ) or "  （无最近记忆）"

        prompt = self.prompt_template.format(
            character_name=character_name,
            personality=personality_str,
            current_state=current_state_str,
            recent_memories=memories_str,
            user_input=user_input,
        )

        # --- 步骤 2：调用 LLM ---
        # temperature=0.5 的设计考量：
        #   注意力聚焦是"决策型"任务，需要偏确定的逻辑推导。
        #   过高的温度会导致情绪标签与实际情况不匹配。
        system_prompt = (
            "你是一个专业的角色行为分析师，"
            "擅长根据上下文推导角色的心理状态和注意力焦点。"
        )

        if history_messages:
            # 多轮模式：system + 历史 user/assistant 交替 + 当前 user(prompt)
            messages: List[Dict[str, str]] = [
                {"role": "system", "content": system_prompt}
            ]
            messages.extend(history_messages)
            messages.append({"role": "user", "content": prompt})

            raw_response = self.llm_service.call_with_messages(
                messages=messages,
                temperature=0.5,
                response_format={"type": "json_object"},
            )
        else:
            # 单轮模式（向后兼容）
            raw_response = self.llm_service.call(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.5,
                response_format={"type": "json_object"},
            )

        # --- 步骤 3：解析并校验 ---
        parsed = self.llm_service.parse_json_response(raw_response)
        parsed = LLMService.validate_director_schema(parsed)

        return parsed, raw_response

    def analyze_with_fallback(
        self,
        character_name: str,
        personality: Dict[str, Any],
        current_state: Dict[str, Any],
        recent_memories: List[str],
        user_input: str,
        history_messages: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        带降级的注意力分析。

        与 analyze() 的区别：捕获异常后不向上抛，而是返回降级值。
        这是管线中的"安全网"节点，确保 Director 的失败不会阻塞 Actor。

        history_messages 透传给 analyze()，语义与 analyze() 一致。

        Returns:
            (parsed_data, raw_response_or_None)
            成功时 raw_response 为 LLM 原始 JSON 字符串
            降级时 raw_response 为 None
        """
        try:
            return self.analyze(
                character_name, personality, current_state,
                recent_memories, user_input,
                history_messages=history_messages,
            )
        except Exception as e:
            logger.warning(
                "Director LLM 调用失败，使用降级输出: %s", e
            )
            return dict(FALLBACK_DIRECTOR_OUTPUT), None


# ============================================================================
# Actor：行为生成模块
# ============================================================================

class ActorModule:
    """
    行为生成模块（Actor）

    职责：根据 Director 聚焦结果，生成角色的具体动作/表情/语言。
    ——这是双 LLM 管路的第二阶段，模拟人类的"关注→表达"行为过程。

    输入 → 输出链路：
        character_name + personality
        + emotion + focus_memories + goal + style  ← 来自 Director
        + user_input
            ↓  一次 LLM 调用 (temperature=0.8, response_format=json_object)
        action + expression + speech
    """

    def __init__(self):
        self.llm_service = LLMService()
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """加载 Actor prompt 模板文件"""
        with open("backend/prompts/actor.txt", "r", encoding="utf-8") as f:
            return f.read()

    @observe_safe("actor.generate", as_type="generation")
    def generate(
        self,
        character_name: str,
        personality: Dict[str, Any],
        emotion: str,
        focus_memories: List[str],
        goal: str,
        style: str,
        user_input: str,
        history_messages: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[Dict[str, Any], str]:
        """
        生成角色行为（动作 + 表情 + 语言）。

        Args:
            character_name:  角色名称
            personality:     人格属性字典
            emotion:         Director 输出的情绪标签
            focus_memories:  Director 筛选的关键记忆
            goal:            Director 设定的对话目标
            style:           Director 确定的回复风格
            user_input:      玩家输入文本
            history_messages: 可选的历史对话消息列表。
                传入时启用多轮模式 ——
                messages 数组会按 [system, ...history, current_user(prompt)] 顺序组装，
                让 LLM 在生成回复时能感知到完整对话上下文（不仅是 Director 提供的摘要）。
                传 None 或空列表则回退到单轮（system + user）模式。

        Returns:
            (parsed_data, raw_response) 元组
            - parsed_data: 校验通过后的字典 {action, expression, speech}
            - raw_response: LLM 原始 JSON 字符串

        降级策略：
            LLM 调用异常 → 返回 FALLBACK_ACTOR_OUTPUT + 错误日志
        """
        # --- 步骤 1：组装 prompt ---
        personality_str = json.dumps(personality, ensure_ascii=False)
        memories_str = "\n".join(
            f"  - {mem}" for mem in (focus_memories or [])
        ) or "  （无特殊关注的记忆）"

        # 注意：prompt 模板使用 {} 占位符但 Director 输出中可能含 {}，
        # 故使用 format_map + defaultdict 的安全替换方式，避免 KeyError
        import collections
        safe_dict = collections.defaultdict(str, {
            "character_name": character_name,
            "personality": personality_str,
            "emotion": emotion,
            "focus_memories": memories_str,
            "goal": goal,
            "style": style,
            "user_input": user_input,
        })

        # 使用 string.Template 风格安全性建 prompt
        prompt = self.prompt_template
        for key, val in safe_dict.items():
            prompt = prompt.replace("{" + key + "}", val)

        # --- 步骤 2：调用 LLM ---
        # temperature=0.8 的设计考量：
        #   行为生成是"创意型"任务，需要一定的随机性来产生多样的回复。
        #   但也不宜超过 0.9，否则可能产生不符合角色设定的内容。
        system_prompt = (
            "你是一个沉浸式角色扮演系统，"
            "你能精准地根据角色的情绪、记忆和目标生成自然的动作和对话。"
        )

        if history_messages:
            # 多轮模式：system + 历史 user/assistant 交替 + 当前 user(prompt)
            messages: List[Dict[str, str]] = [
                {"role": "system", "content": system_prompt}
            ]
            messages.extend(history_messages)
            messages.append({"role": "user", "content": prompt})

            raw_response = self.llm_service.call_with_messages(
                messages=messages,
                temperature=0.8,
                response_format={"type": "json_object"},
            )
        else:
            # 单轮模式（向后兼容）
            raw_response = self.llm_service.call(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.8,
                response_format={"type": "json_object"},
            )

        # --- 步骤 3：解析并校验 ---
        parsed = self.llm_service.parse_json_response(raw_response)
        parsed = LLMService.validate_actor_schema(parsed)

        return parsed, raw_response

    def generate_with_fallback(
        self,
        character_name: str,
        personality: Dict[str, Any],
        emotion: str,
        focus_memories: List[str],
        goal: str,
        style: str,
        user_input: str,
        history_messages: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        带降级的行为生成。

        history_messages 透传给 generate()，语义与 generate() 一致。

        Returns:
            (parsed_data, raw_response_or_None)
            成功时 raw_response 为 LLM 原始 JSON 字符串
            降级时 raw_response 为 None
        """
        try:
            return self.generate(
                character_name, personality, emotion,
                focus_memories, goal, style, user_input,
                history_messages=history_messages,
            )
        except Exception as e:
            logger.warning(
                "Actor LLM 调用失败，使用降级输出: %s", e
            )
            return dict(FALLBACK_ACTOR_OUTPUT), None


# ============================================================================
# InteractionPipeline：对话管线编排层
# ============================================================================

class InteractionPipeline:
    """
    对话管线编排层

    职责：
      1. 数据库读取（角色 → 记忆 → 历史对话）
      2. 数据组装（字典反序列化、列表提取）
      3. 串联 Director → Actor 两步 LLM 调用
      4. 持久化对话记录到数据库
      5. 返回完整 ChatResponse

    管线节点依赖图（→ 表示数据流方向）：

        character_crud.get_character ────┐
        memory_crud.get_character_memories ─┤──□ Director.analyze()
        conversation_crud.get_character_conversations ─┘     │
                                                             ▼
                                                      Actor.generate()
                                                             │
                                                             ▼
                                            conversation_crud.create()

    设计考量：
      - Pipeline 本身不调用 LLM，LLM 调用封装在 Director/Actor 中
      - Pipeline 仅负责"读数据 → 协调调用 → 写数据"的编排逻辑
      - 这样保证了单一职责：模块内聚 LLM 调用，管线负责流程
    """

    def __init__(self):
        """初始化 Director 和 Actor 实例（两个 LLM 子模块）"""
        self.director = DirectorModule()
        self.actor = ActorModule()

    @staticmethod
    def _safe_load_json(raw: Optional[str]) -> dict:
        """安全地将数据库中的 JSON 字符串转为 dict"""
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}

    @staticmethod
    def _build_history_messages(
        conversations: List[Any],
        max_turns: int = 10,
    ) -> List[Dict[str, str]]:
        """
        把数据库中最近 N 条对话记录组装为 OpenAI 风格的 messages 数组。

        数据结构（OpenAI 格式）：
            [
              {"role": "user",      "content": <user_input>},
              {"role": "assistant", "content": <npc_response>},
              ... 交替 ...
            ]

        Args:
            conversations: Conversation ORM 对象列表（按时间升序）。
                          调用方需自行做"取最近 N 条"的截断。
            max_turns: 最多保留多少轮（每轮 = 1 user + 1 assistant）。
                       截断采用"保留最近 N 轮"策略：取列表尾部而非头部，
                       避免最早的对话覆盖最近的语义。

        Returns:
            OpenAI 风格 messages 数组（不含 system，由调用方追加在最前）。
            空列表表示无历史。

        健壮性设计：
          - 一轮对话必须 user_input *和* npc_response 都非空才保留。
            原因：OpenAI messages 必须 user/assistant 严格交替，
            若只保留一侧会导致连续同角色消息，触发 API 报错或语义混乱。
          - 跳过"半轮"（任一字段为空）—— 在脏数据或部分写入失败时保护 LLM 调用。
        """
        if not conversations or max_turns <= 0:
            return []

        # 截断到最近 N 轮
        recent = conversations[-max_turns:]

        history: List[Dict[str, str]] = []
        for conv in recent:
            user_text = (conv.user_input or "").strip()
            npc_text = (conv.npc_response or "").strip()
            # 严格成对：两端都有非空内容才纳入 messages
            if user_text and npc_text:
                history.append({"role": "user", "content": user_text})
                history.append({"role": "assistant", "content": npc_text})
        return history

    @observe_safe("interaction.run", as_type="span")
    def run(
        self,
        character_id: int,
        user_message: str,
        db: Session,
        history_turns: int = 10,
        session_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        运行完整的对话管线。

        Args:
            character_id:  角色 ID
            user_message:  玩家输入文本
            db:            SQLAlchemy 数据库会话
            history_turns: 注入到 LLM messages 的最近对话轮数。
                           默认 10 轮 = 20 条消息；
                           设为 0 即可禁用多轮模式（回退到单轮）。
            session_id:    会话 ID（None → 自动创建新 session 并用首条消息做标题）

        Returns:
            字典，包含以下字段，可直接用于 ChatResponse schema：
            {
                "id": int,               # 对话记录 ID
                "character_id": int,
                "user_input": str,
                "npc_response": str,     # 角色的语言回复
                "emotion": str,          # Director 输出的情绪
                "action": str,           # Actor 输出的动作
                "expression": str,       # Actor 输出的表情
                "director_raw": str|None,# Director LLM 原始响应
                "actor_raw": str|None,   # Actor LLM 原始响应
                "timestamp": datetime,
                "session_id": int,       # 新增：所属会话
                "session_title": str,    # 新增：会话标题（前端可立即更新侧栏）
            }

        Raises:
            ValueError: 角色不存在时抛出
        """
        # ---- 节点 1：获取角色基础数据 ----
        character = character_crud.get_character(db, character_id)
        if not character:
            raise ValueError(f"角色不存在: id={character_id}")

        personality = self._safe_load_json(character.personality)
        current_state = self._safe_load_json(character.current_state)

        # ---- 节点 2：获取最近记忆（最多 5 条） ----
        # 设计考量：限制 5 条是 prompt token 预算与上下文丰富度之间的平衡点。
        # 5 条记忆 + 其他变量 ≈ 总 token < 2000，确保在模型上下文限制内安全。
        recent_memories = memory_crud.get_character_memories(
            db, character_id, limit=5
        )
        memory_texts = [mem.content for mem in recent_memories]

        # ---- 节点 2.4：获取/创建会话（多轮消息的容器） ----
        #   - session_id 传了就复用（角色不匹配时降级为创建新 session）
        #   - 没传就创建一个新 session，标题取首条消息前 30 字
        #   - 必须在"取历史消息"之前完成，否则会把"上一会话"的内容串味到新会话
        from backend.services import chat_session_crud
        session = chat_session_crud.get_or_create_session(
            db, session_id=session_id, character_id=character_id,
            first_user_message=user_message,
        )
        session_id = session.id
        session_title = session.title

        # ---- 节点 2.6：给 Langfuse 当前 trace 打元数据 ----
        #   - session_id: 关联到 ChatSession.id，UI 可按会话筛选
        #   - user_id:    当前是匿名版（"anonymous"），未来接登录后换成实际用户
        #   - tags:       方便按管线类型筛选
        update_current_trace(
            user_id="anonymous",
            session_id=str(session_id),
            tags=["interaction", "director+actor", f"character_id={character_id}"],
            metadata={
                "character_id": character_id,
                "character_name": character.name,
                "session_id": session_id,
                "session_title": session_title,
                "history_turns": history_turns,
                "user_message_length": len(user_message),
            },
        )

        # ---- 节点 2.5：组装多轮历史消息 ----
        #   从当前 session 取最近 N 轮对话，按时间升序拼接为 OpenAI 风格 messages。
        #   重要：必须在持久化新对话 *之前* 取历史，否则会把"当前轮"也塞回去造成重复。
        history_messages: List[Dict[str, str]] = []
        if history_turns and history_turns > 0:
            # 优先用 session 级历史（更聚焦），但若 session 为空且没有显式 session_id
            # 则退回到角色级历史，避免首次进入"默认会话"时空白
            recent_conversations = conversation_crud.get_session_conversations(
                db, session_id=session_id, limit=history_turns,
            )
            if not recent_conversations and session_id is None:
                recent_conversations = conversation_crud.get_character_conversations(
                    db, character_id, skip=0, limit=history_turns,
                )
            history_messages = self._build_history_messages(
                recent_conversations, max_turns=history_turns,
            )
            if history_messages:
                logger.info(
                    "InteractionPipeline: 注入 %d 条历史消息（%d 轮）",
                    len(history_messages), len(history_messages) // 2,
                )

        # ---- 节点 3：执行 Director 注意力聚焦 ----
        # 使用带降级的版本，确保 LLM 失败时管线不崩溃
        director_data, director_raw = self.director.analyze_with_fallback(
            character_name=character.name,
            personality=personality,
            current_state=current_state,
            recent_memories=memory_texts,
            user_input=user_message,
            history_messages=history_messages or None,
        )

        # ---- 节点 4：执行 Actor 行为生成 ----
        # Actor 接收 Director 的完整输出作为上下文
        actor_data, actor_raw = self.actor.generate_with_fallback(
            character_name=character.name,
            personality=personality,
            emotion=director_data["emotion"],
            focus_memories=director_data["focus_memories"],
            goal=director_data["goal"],
            style=director_data["style"],
            user_input=user_message,
            history_messages=history_messages or None,
        )

        # ---- 节点 5：持久化对话记录（带 session_id） ----
        conversation = conversation_crud.create_conversation(
            db=db,
            character_id=character_id,
            user_input=user_message,
            npc_response=actor_data["speech"],
            emotion=director_data["emotion"],
            action=actor_data["action"],
            expression=actor_data["expression"],
            director_raw=director_raw,
            actor_raw=actor_raw,
            session_id=session_id,
        )

        # 刷新 session.updated_at，让活跃会话在侧栏里排前面
        chat_session_crud.touch_session(db, session_id)

        # ---- 节点 6：返回结果 ----
        return {
            "id": conversation.id,
            "character_id": character_id,
            "user_input": user_message,
            "npc_response": actor_data["speech"],
            "emotion": director_data["emotion"],
            "action": actor_data["action"],
            "expression": actor_data["expression"],
            "director_raw": director_raw,
            "actor_raw": actor_raw,
            "timestamp": conversation.timestamp,
            "session_id": session_id,
            "session_title": session_title,
        }
