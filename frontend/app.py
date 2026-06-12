"""
CharacterSeed Frontend — Streamlit 三页面应用
==============================================

架构设计（Why single-file multi-page）：
  Streamlit 支持两种多页面方案：
    A. pages/ 目录（每个文件一个页面）—— 需要共享 session_state 的 hack
    B. st.sidebar.radio 手动切换 —— 所有页面共享同一个 session_state

  选择方案 B 的原因：
    - 三个页面需要共享 selected_character_id 状态
    - 跨文件 session_state 在 st 1.29 中仍然不完美
    - 单个 app.py 更适合 Demo 场景：一键启动、零配置、代码量可控

页面切换设计：
  st.sidebar.radio 返回当前选中的页面名（str），
  主函数根据返回值 dispatch 到对应的 render 函数。
  每次 rerun 都会重新执行整个脚本，所以 st.cache_data 用于缓存
  不变数据（如角色列表）。

状态管理设计：
  st.session_state 中持久化的 key：
    - selected_character_id: int | None  ← 跨页面共享的角色选择
    - chat_history: list[dict]           ← 当前会话的对话气泡缓存
    - creation_result: dict | None       ← 最近一次创建结果（用于页面1展示）

运行方式：
  cd CharacterSeed
  streamlit run frontend/app.py
"""

import sys
import os
import json
import time

# 确保项目根目录在 path 中（本地开发时 streamlit run 的 cwd 是项目根）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from frontend.api_client import (
    check_backend_health,
    create_character_text,
    create_character_file,
    get_characters,
    get_character,
    send_message,
    trigger_growth,
    get_memories,
    get_conversations,
    get_growth_logs,
)

# ============================================================
# 页面配置（必须是第一个 st 调用）
# ============================================================
st.set_page_config(
    page_title="CharacterSeed — AI NPC 生命模拟",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 人格维度常量
# ============================================================
# 为何在此处重新定义而非从 backend 导入：
#   frontend 包与 backend 包逻辑隔离。重新定义使前端零后端依赖，
#   即使后端重构/移动文件也不影响前端。6 个维度名是不变的业务常量。
PERSONALITY_DIMS = [
    ("optimism", "乐观"),
    ("courage", "勇气"),
    ("empathy", "同理心"),
    ("loyalty", "忠诚"),
    ("intelligence", "智慧"),
    ("sociability", "社交"),
]
PERSONALITY_KEYS = [k for k, _ in PERSONALITY_DIMS]


# ============================================================
# 工具函数
# ============================================================

def safe_parse_json(raw: str | None) -> dict:
    """
    安全解析 JSON 字符串为 dict。

    为何需要此函数：
      CharacterResponse.personality 和 current_state 在 API 返回中
      是 JSON 字符串。Streamlit UI 渲染需要 dict 形式。
      如果 JSON 格式异常（极少情况），返回空 dict 而非崩溃。
    """
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def format_personality_progress(personality_dict: dict) -> list:
    """
    将人格 dict {optimism: 75, ...} 转为有序的 (英文key, 中文名, 值) 三元组。

    为何需要排序：
      进度条展示时，固定顺序给用户一致的视觉参照。
      随机顺序会降低可读性。
    """
    result = []
    for key, cn_name in PERSONALITY_DIMS:
        val = personality_dict.get(key, 50)  # 默认 50 分
        result.append((key, cn_name, val))
    return result


def display_personality_bars(personality_dict: dict, prefix: str = ""):
    """
    渲染 6 维人格进度条。

    设计考量：
      - st.progress 接受 0.0-1.0 的浮点数，而人格值是 0-100 的整数
      - 直接除以 100 转换
      - 每行显示：中文名 | 进度条 | 数值
      - 为何分两列：三列各 2 条，减少纵向滚动，提升信息密度
    """
    items = format_personality_progress(personality_dict)
    mid = 3
    col1, col2 = st.columns(2)

    with col1:
        for key, cn_name, val in items[:mid]:
            pct = val / 100.0
            st.caption(f"{cn_name} ({key})")
            st.progress(pct, text=f"{val}/100")
    with col2:
        for key, cn_name, val in items[mid:]:
            pct = val / 100.0
            st.caption(f"{cn_name} ({key})")
            st.progress(pct, text=f"{val}/100")


def render_character_selector(key_prefix: str = "") -> int | None:
    """
    渲染角色下拉选择器并返回选中的 character_id。

    为何作为独立函数：
      页面2和页面3都需要角色选择器，代码复用避免重复。
      key_prefix 参数确保不同页面的 st.selectbox 使用不同的 widget key，
      避免 Streamlit 报 "DuplicateWidgetID" 错误。
    """
    characters = get_characters()
    if not characters:
        st.info("📭 暂无角色，请先去「角色创建」页面创建")
        return None

    options = {f"[{c['id']}] {c['name']}": c["id"] for c in characters}
    labels = list(options.keys())

    # 尝试恢复之前的选中状态
    default_idx = 0
    if "selected_character_id" in st.session_state and st.session_state.selected_character_id:
        for i, c in enumerate(characters):
            if c["id"] == st.session_state.selected_character_id:
                default_idx = i
                break

    selected_label = st.selectbox(
        "👤 选择角色",
        labels,
        index=min(default_idx, len(labels) - 1),
        key=f"{key_prefix}_char_selector",
    )
    char_id = options[selected_label]
    st.session_state.selected_character_id = char_id
    return char_id


# ============================================================
# 页面 1：角色创建
# ============================================================

def render_page_create():
    """
    角色创建页面。

    UI 布局（自上而下）：
      ┌────────────────────────────────────┐
      │  标题：🌱 创建新角色               │
      │  模式切换：文本描述 | 文件上传      │
      │  ┌──────────────────────────┐      │
      │  │ 输入区（text_area 或      │      │
      │  │ file_uploader）           │      │
      │  └──────────────────────────┘      │
      │  [ 🔮 生成角色 ]                   │
      │  ┌──────────────────────────┐      │
      │  │ 结果区（角色卡片）        │      │
      │  │ - 名称 + 世界设定         │      │
      │  │ - 6维人格进度条           │      │
      │  │ - 初始状态                │      │
      │  │ - 初始记忆表              │      │
      │  │ - LLM 原始响应展开        │      │
      │  └──────────────────────────┘      │
      └────────────────────────────────────┘

    交互流程：
      1. 用户选择输入模式（文本 / 文件）
      2. 输入描述或上传 TXT 文件
      3. 点击「生成角色」→ 调用 POST /api/characters/create
      4. 展示生成结果卡片
      5. 自动将新角色 ID 写入 session_state 供其他页面使用
    """
    st.title("🌱 创建新角色")
    st.markdown("输入一段描述或上传 TXT 故事文件，让 AI 为你创造一个鲜活的 NPC 角色。")

    # ---- 模式选择 ----
    # 为何用 radio 而非 tabs：
    #   radio 的状态切换更直观，且 Streamlit 1.29 中 radio 的 horizontal 模式
    #   提供了清晰的视觉分组
    input_mode = st.radio(
        "📥 输入模式",
        ["📝 文本描述", "📄 文件上传 (.txt)"],
        horizontal=True,
        key="create_input_mode",
    )

    user_input_text = ""
    file_content_bytes = None
    file_name = ""

    # ---- 输入区 ----
    if input_mode == "📝 文本描述":
        user_input_text = st.text_area(
            "角色描述",
            placeholder=(
                "用一段话描述你想要的角色...\n\n"
                "示例：「一位在雪山中修炼十年的剑客，性格孤傲但内心善良，\n"
                "师父临终前将一把古剑托付给他...」"
            ),
            height=200,
            key="create_text_input",
        )
    else:
        uploaded_file = st.file_uploader(
            "上传 TXT 故事文件",
            type=["txt"],
            accept_multiple_files=False,
            key="create_file_uploader",
            help="选择一个 .txt 文件，文件内容将作为角色故事描述",
        )
        if uploaded_file is not None:
            file_content_bytes = uploaded_file.getvalue()
            file_name = uploaded_file.name
            # 预览文件前 500 字符
            preview = file_content_bytes.decode("utf-8", errors="replace")[:500]
            st.text_area("📋 文件预览", preview, height=100, disabled=True)

    # ---- 生成按钮 ----
    # 为何用 button 而非 form_submit_button：
    #   button 更灵活，不需要包装在 st.form 中。
    #   生成操作是幂等的（每次点击创建新角色），不需要 form 的"确认"语义。
    col_btn, col_spacer = st.columns([1, 3])
    with col_btn:
        generate_clicked = st.button(
            "🔮 生成角色",
            type="primary",
            use_container_width=True,
            key="create_generate_btn",
            disabled=(input_mode == "📝 文本描述" and not user_input_text.strip())
            or (input_mode == "📄 文件上传 (.txt)" and file_content_bytes is None),
        )

    if generate_clicked:
        with st.spinner("⏳ 正在调用 Creation LLM 生成角色..."):
            if input_mode == "📝 文本描述":
                result = create_character_text(user_input_text.strip())
            else:
                result = create_character_file(file_content_bytes, file_name)

        if result.get("error"):
            st.error(f"❌ 创建失败：{result['detail']}")
        else:
            # 创建成功 → 写入 session_state + 展示结果
            st.session_state.creation_result = result
            st.session_state.selected_character_id = result["id"]
            st.success(f"✅ 角色「{result['name']}」创建成功！(ID: {result['id']})")
            st.balloons()

    # ---- 结果展示区 ----
    # 为何同时检查 creation_result 和 result：
    #   如果用户刚点击生成 → generation_result 已写入
    #   如果用户刷新页面（翻到别的 tab 再回来）→ 从 session_state 恢复
    if "creation_result" in st.session_state and st.session_state.creation_result:
        result = st.session_state.creation_result
        personality = safe_parse_json(result.get("personality"))
        current_state = safe_parse_json(result.get("current_state"))

        st.divider()
        st.subheader(f"🎭 {result['name']}")

        # 世界设定
        if result.get("world_setting"):
            with st.expander("🌍 世界设定", expanded=True):
                st.markdown(result["world_setting"])

        # 人格属性
        st.subheader("📊 人格属性")
        if personality:
            display_personality_bars(personality)
        else:
            st.info("暂无初始人格数据")

        # 当前状态
        if current_state:
            st.subheader("📍 当前状态")
            cols = st.columns(3)
            cols[0].metric("位置", current_state.get("location", "未知"))
            cols[1].metric("活动", current_state.get("activity", "空闲"))
            cols[2].metric("心情", current_state.get("mood", "平静"))

        # 初始记忆
        st.subheader("🧠 初始记忆")
        # 从后端获取该角色的记忆列表
        memories = get_memories(result["id"], memory_type="event", limit=50)
        if memories:
            mem_data = []
            for m in memories:
                mem_data.append({
                    "内容": m.get("content", ""),
                    "重要性": m.get("importance", 5),
                    "类型": m.get("memory_type", "event"),
                })
            st.dataframe(mem_data, use_container_width=True, hide_index=True)
        else:
            st.info("暂无初始记忆数据")

        # LLM 原始响应（折叠，供调试）
        if result.get("creation_raw"):
            with st.expander("🔍 Creation LLM 原始响应 (Raw JSON)", expanded=False):
                try:
                    raw_parsed = json.loads(result["creation_raw"])
                    st.json(raw_parsed)
                except json.JSONDecodeError:
                    st.text(result["creation_raw"])

        # 清除按钮
        if st.button("🔄 清除结果，重新创建", key="create_clear_btn"):
            st.session_state.creation_result = None
            st.rerun()


# ============================================================
# 页面 2：对话交互
# ============================================================

def render_page_chat():
    """
    对话交互页面。

    UI 布局：
      ┌────────────────────────────────────┐
      │  标题：💬 角色对话                 │
      │  [角色选择器]                       │
      │  角色信息栏（名称/人格摘要）        │
      │  ┌──────────────────────────┐      │
      │  │ 对话气泡区               │      │
      │  │ 用户消息 (右)            │      │
      │  │ NPC 回复 (左) + 标签     │      │
      │  │   emotion / action /     │      │
      │  │   expression             │      │
      │  └──────────────────────────┘      │
      │  [消息输入框 chat_input]            │
      │  ──── 侧栏 ────                    │
      │  [🌱 触发成长] [🗑️ 清空对话]      │
      └────────────────────────────────────┘

    交互流程（Director + Actor 双 LLM 管线）：
      1. 用户输入消息 → POST /api/chat
      2. 后端执行 Director.analyze() → emotion/focus_memories/goal/style
      3. 后端执行 Actor.generate()  → action/expression/speech
      4. 前端展示回复气泡 + 标签

    为何用 st.chat_message 而非手写 HTML：
      Streamlit 1.29 内置的聊天组件提供了与 ChatGPT 一致的交互体验。
      原生支持 user/assistant 两种角色，自动处理 CSS 样式和对齐。
      手写 st.markdown + HTML 会增加大量非语义化的样式代码。
    """
    st.title("💬 角色对话")
    st.markdown("选择一名角色，开始对话。AI 将通过 Director+Actor 双管线生成角色的反应。")

    # ---- 角色选择 ----
    char_id = render_character_selector(key_prefix="chat")
    if char_id is None:
        return

    # ---- 角色信息栏 ----
    char_detail = get_character(char_id)
    if char_detail.get("error"):
        st.error(f"无法加载角色信息：{char_detail['detail']}")
        return

    personality = safe_parse_json(char_detail.get("personality"))
    current_state = safe_parse_json(char_detail.get("current_state"))

    # 人格摘要（一行文本，用最极端的人格维度描述角色）
    if personality:
        top_trait = max(personality.items(), key=lambda x: x[1]) if personality else (None, 0)
        bottom_trait = min(personality.items(), key=lambda x: x[1]) if personality else (None, 0)
        trait_summary = (
            f"**{char_detail['name']}** · "
            f"最突出: {dict(PERSONALITY_DIMS).get(top_trait[0], top_trait[0])} ({top_trait[1]}) · "
            f"最薄弱: {dict(PERSONALITY_DIMS).get(bottom_trait[0], bottom_trait[0])} ({bottom_trait[1]})"
        )
    else:
        trait_summary = char_detail.get("name", "未知角色")

    st.markdown(trait_summary)
    if current_state:
        st.caption(
            f"📍 {current_state.get('location', '未知')} · "
            f"🔄 {current_state.get('activity', '空闲')} · "
            f"😊 {current_state.get('mood', '平静')}"
        )

    st.divider()

    # ---- 对话历史初始化 ----
    # 为何用 session_state 缓存而非每次从后端加载：
    #   对话是实时交互，session_state 保存当前会话的上下文
    #   刷新页面时清空缓存（从后端重新加载最近的对话记录），
    #   避免数据冗余和状态不一致。
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # 从后端加载最近对话并追加到 chat_history（仅在首次或刷新时）
    if "chat_loaded_char_id" not in st.session_state or st.session_state.chat_loaded_char_id != char_id:
        conversations = get_conversations(char_id, limit=50)
        st.session_state.chat_history = []
        for conv in conversations:
            # 用户消息
            st.session_state.chat_history.append({
                "role": "user",
                "content": conv.get("user_input", ""),
                "timestamp": conv.get("timestamp", ""),
            })
            # NPC 回复
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": conv.get("npc_response", ""),
                "emotion": conv.get("emotion", ""),
                "action": conv.get("action", ""),
                "expression": conv.get("expression", ""),
                "director_raw": conv.get("director_raw", ""),
                "actor_raw": conv.get("actor_raw", ""),
                "timestamp": conv.get("timestamp", ""),
            })
        st.session_state.chat_loaded_char_id = char_id

    # ---- 渲染对话气泡 ----
    # 为何用两层嵌套渲染：
    #   外层遍历 chat_history，内层对每条消息调用 st.chat_message()。
    #   st.chat_message 必须直接作为上下文管理器使用，
    #   每一条调用会在 UI 上追加一个气泡。不支持"收集→批量渲染"模式。
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            # NPC 消息额外交互标签
            if msg["role"] == "assistant":
                tags = []
                if msg.get("emotion"):
                    tags.append(f"😶 {msg['emotion']}")
                if msg.get("expression"):
                    tags.append(f"🎭 {msg['expression']}")
                if msg.get("action"):
                    tags.append(f"🏃 {msg['action']}")
                if tags:
                    st.caption(" · ".join(tags))

    # ---- 消息输入 ----
    # 为何用 st.chat_input 而非 st.text_input + button：
    #   chat_input 是 Streamlit 1.29 为聊天场景优化的组件。
    #   它始终固定在页面底部，左对齐输入框 + 发送按钮。
    #   用户体验与 ChatGPT/微信一致。
    user_msg = st.chat_input("输入消息...", key="chat_input_box")

    if user_msg:
        # 追加用户消息到历史
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_msg,
        })

        # 调用后端对话 API
        with st.spinner("💭 角色正在思考..."):
            chat_result = send_message(char_id, user_msg)

        if chat_result.get("error"):
            st.error(f"对话失败：{chat_result['detail']}")
            # 移除刚追加的用户消息（因为发送失败）
            st.session_state.chat_history.pop()
        else:
            # 追加 NPC 回复到历史
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": chat_result.get("npc_response", ""),
                "emotion": chat_result.get("emotion", ""),
                "action": chat_result.get("action", ""),
                "expression": chat_result.get("expression", ""),
                "director_raw": chat_result.get("director_raw", ""),
                "actor_raw": chat_result.get("actor_raw", ""),
                "timestamp": str(chat_result.get("timestamp", "")),
            })

            # ---- 展示 LLM 原始响应（折叠，供调试） ----
            # 为何展示 raw 响应：
            #   Director/Actor 的原始 JSON 输出提供了角色的"思考过程"
            #   对于开发者/Demo 观众而言，这是系统可解释性的关键窗口
            if chat_result.get("director_raw") or chat_result.get("actor_raw"):
                with st.expander("🔍 LLM 管线内部响应 (调试)", expanded=False):
                    if chat_result.get("director_raw"):
                        st.markdown("**Director（注意力聚焦）原始输出：**")
                        try:
                            st.json(json.loads(chat_result["director_raw"]))
                        except json.JSONDecodeError:
                            st.text(chat_result["director_raw"])
                    if chat_result.get("actor_raw"):
                        st.markdown("**Actor（行为生成）原始输出：**")
                        try:
                            st.json(json.loads(chat_result["actor_raw"]))
                        except json.JSONDecodeError:
                            st.text(chat_result["actor_raw"])

        st.rerun()

    # ---- 侧边操作 ----
    st.divider()
    col_grow, col_clear = st.columns(2)

    with col_grow:
        if st.button("🌱 触发角色成长", use_container_width=True, key="chat_growth_btn"):
            with st.spinner("⏳ Growth LLM 正在分析角色成长..."):
                growth_result = trigger_growth(char_id)

            if growth_result.get("error"):
                st.error(f"成长触发失败：{growth_result['detail']}")
            else:
                st.success(f"✅ 成长分析完成！")

                # 展示成长摘要
                st.markdown(f"**事件摘要：** {growth_result.get('event_summary', '无')}")

                # 展示人格变化
                delta_raw = growth_result.get("personality_delta", "{}")
                delta = safe_parse_json(delta_raw)
                if delta:
                    st.markdown("**人格变化 (Δ)：**")
                    for key, cn_name in PERSONALITY_DIMS:
                        dv = delta.get(key, 0)
                        if dv != 0:
                            arrow = "↑" if dv > 0 else "↓"
                            color = "green" if dv > 0 else "red"
                            st.markdown(f"  {cn_name}: :{color}[{arrow}{abs(dv)}]")

                # 新记忆
                new_memories_raw = growth_result.get("new_memories", "[]")
                new_memories = safe_parse_json(new_memories_raw) if isinstance(new_memories_raw, str) else new_memories_raw
                if new_memories:
                    with st.expander("🧠 新增记忆", expanded=True):
                        for nm in new_memories:
                            if isinstance(nm, dict):
                                st.markdown(f"- [{nm.get('importance', 5)}/10] {nm.get('content', '')}")

                # Growth LLM 原始响应
                if growth_result.get("growth_raw"):
                    with st.expander("🔍 Growth LLM 原始响应", expanded=False):
                        try:
                            st.json(json.loads(growth_result["growth_raw"]))
                        except json.JSONDecodeError:
                            st.text(growth_result["growth_raw"])

    with col_clear:
        if st.button("🗑️ 清空当前对话显示", use_container_width=True, key="chat_clear_btn"):
            st.session_state.chat_history = []
            st.session_state.chat_loaded_char_id = None
            st.rerun()


# ============================================================
# 页面 3：角色状态面板
# ============================================================

def render_page_dashboard():
    """
    角色状态面板页面。

    UI 布局：
      ┌────────────────────────────────────┐
      │  标题：📊 角色状态面板             │
      │  [角色选择器]                       │
      │  ┌─────────────┬─────────────┐     │
      │  │ 人格面板    │ 当前状态    │     │
      │  │ 6个进度条   │ 位置/活动/  │     │
      │  │             │ 心情        │     │
      │  └─────────────┴─────────────┘     │
      │  ┌─────────────┬─────────────┐     │
      │  │ 记忆面板    │ 对话历史    │     │
      │  │ [类型筛选]  │ dataframe   │     │
      │  │ dataframe   │             │     │
      │  └─────────────┴─────────────┘     │
      │  ┌──────────────────────────┐      │
      │  │ 成长记录 (expander)      │      │
      │  │ - event_summary          │      │
      │  │ - personality_delta      │      │
      │  │ - new_memories           │      │
      │  └──────────────────────────┘      │
      └────────────────────────────────────┘

    为何将四个面板放在同一页面而非拆分：
      这是角色的"控制面板"——一次性展示所有维度的数据。
      分页会增加用户的认知负担，降低信息获取效率。
      通过 expander 折叠成长记录，避免信息过载。
    """
    st.title("📊 角色状态面板")
    st.markdown("选择一个角色查看其完整状态，包括人格属性、记忆、对话历史和成长记录。")

    # ---- 角色选择 ----
    char_id = render_character_selector(key_prefix="dashboard")
    if char_id is None:
        return

    # ---- 加载角色数据 ----
    char_detail = get_character(char_id)
    if char_detail.get("error"):
        st.error(f"无法加载角色信息：{char_detail['detail']}")
        return

    personality = safe_parse_json(char_detail.get("personality"))
    current_state = safe_parse_json(char_detail.get("current_state"))

    # ---- 上半部分：人格 + 当前状态 ----
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📊 人格属性")
        if personality:
            display_personality_bars(personality)
        else:
            st.info("暂无数据")

    with col_right:
        st.subheader("📍 当前状态")
        if current_state:
            st.metric("位置", current_state.get("location", "未知"))
            st.metric("活动", current_state.get("activity", "空闲"))
            st.metric("心情", current_state.get("mood", "平静"))
        else:
            st.info("暂无数据")

        # 角色基本信息
        st.subheader("📋 基本信息")
        st.markdown(f"**名称：** {char_detail.get('name', '未知')}")
        st.markdown(f"**ID：** {char_detail.get('id', 'N/A')}")
        if char_detail.get("world_setting"):
            with st.expander("🌍 世界设定", expanded=False):
                st.markdown(char_detail["world_setting"])
        if char_detail.get("description"):
            st.caption(f"原始描述: {char_detail['description'][:200]}...")

    st.divider()

    # ---- 下半部分：记忆 + 对话历史 ----
    col_left2, col_right2 = st.columns(2)

    with col_left2:
        st.subheader("🧠 记忆列表")

        # 记忆类型筛选
        # 为何提供筛选：
        #   记忆有三种类型（conversation/event/growth），
        #   不同类型的记忆有不同的语义。筛选让用户快速聚焦。
        mem_type = st.selectbox(
            "筛选类型",
            ["全部", "对话记忆", "事件记忆", "成长记忆"],
            key="dashboard_mem_filter",
        )
        mem_type_map = {
            "全部": None,
            "对话记忆": "conversation",
            "事件记忆": "event",
            "成长记忆": "growth",
        }
        api_mem_type = mem_type_map.get(mem_type)

        memories = get_memories(char_id, memory_type=api_mem_type, limit=100)
        if memories:
            mem_df_data = []
            for m in memories:
                mem_df_data.append({
                    "ID": m.get("id"),
                    "内容": m.get("content", "")[:80] + ("..." if len(m.get("content", "")) > 80 else ""),
                    "重要度": m.get("importance", 5),
                    "类型": m.get("memory_type", "unknown"),
                    "创建时间": str(m.get("created_at", ""))[:19],
                })
            st.dataframe(mem_df_data, use_container_width=True, hide_index=True)
            st.caption(f"共 {len(memories)} 条记忆")
        else:
            st.info("暂无记忆记录")

    with col_right2:
        st.subheader("💬 对话历史")

        conversations = get_conversations(char_id, limit=50)
        if conversations:
            conv_data = []
            for c in conversations:
                conv_data.append({
                    "ID": c.get("id"),
                    "玩家": c.get("user_input", "")[:60] + ("..." if len(c.get("user_input", "")) > 60 else ""),
                    "NPC": c.get("npc_response", "")[:60] + ("..." if len(c.get("npc_response", "")) > 60 else ""),
                    "情绪": c.get("emotion", ""),
                    "时间": str(c.get("timestamp", ""))[:19],
                })
            st.dataframe(conv_data, use_container_width=True, hide_index=True)
            st.caption(f"共 {len(conversations)} 条对话")
        else:
            st.info("暂无对话记录")

    st.divider()

    # ---- 成长记录面板 ----
    st.subheader("📈 成长记录")
    growth_logs = get_growth_logs(char_id, limit=50)
    if growth_logs:
        for idx, gl in enumerate(growth_logs):
            with st.expander(
                f"🌱 成长 #{gl.get('id')} — {gl.get('event_summary', '无摘要')[:60]}..."
                f" | {str(gl.get('created_at', ''))[:19]}",
                expanded=(idx == 0),  # 第一条默认展开
            ):
                # 事件摘要
                st.markdown("**📝 事件摘要：**")
                st.markdown(gl.get("event_summary", "无"))

                # 人格变化
                delta = safe_parse_json(gl.get("personality_delta"))
                if delta:
                    st.markdown("**📊 人格变化 (Δ)：**")
                    delta_cols = st.columns(3)
                    for i, (key, cn_name) in enumerate(PERSONALITY_DIMS):
                        dv = delta.get(key, 0)
                        if dv != 0:
                            arrow = "↑" if dv > 0 else "↓"
                            color = "green" if dv > 0 else "red"
                            delta_cols[i % 3].markdown(f"{cn_name}: :{color}[{arrow}{abs(dv)}]")
                        else:
                            delta_cols[i % 3].markdown(f"{cn_name}: 0")

                # 新增记忆
                new_memories_raw = gl.get("new_memories", "[]")
                new_memories = safe_parse_json(new_memories_raw) if isinstance(new_memories_raw, str) else new_memories_raw
                if new_memories:
                    st.markdown("**🧠 新增记忆：**")
                    for nm in new_memories:
                        if isinstance(nm, dict):
                            st.markdown(f"- [{nm.get('importance', 5)}/10] {nm.get('content', '')}")

                # Growth LLM 原始响应
                if gl.get("growth_raw"):
                    with st.expander("🔍 Growth LLM 原始响应", expanded=False):
                        try:
                            st.json(json.loads(gl["growth_raw"]))
                        except json.JSONDecodeError:
                            st.text(gl["growth_raw"])

        st.caption(f"共 {len(growth_logs)} 条成长记录")
    else:
        st.info("暂无成长记录（请先在对话页触发角色成长）")


# ============================================================
# 主入口 + 侧边栏
# ============================================================

def main():
    """
    主函数：渲染侧边栏导航 → 分发到对应页面。

    为何不使用 Streamlit 的 pages/ 自动导航：
      pages/ 方案要求每个页面一个文件，三个页面需要共享
      selected_character_id 状态。在 st 1.29 中，跨页面
      session_state 共享有时不稳定，尤其在 rerun 时。
      手动 sidebar.radio 控制页面切换，所有组件在同一
      脚本上下文中，session_state 天然共享。
    """

    # ---- 侧边栏 ----
    with st.sidebar:
        # 直接使用 emoji 字符以避免 Streamlit magic 机制误判。
        st.markdown("# 🌱")
        st.title("CharacterSeed")

        # 后端健康检查
        # 为何每次 rerun 都检查一次：
        #   后端可能在中途崩溃或重启。实时检查比"启动时检查一次"更可靠。
        #   使用 st.cache_data(ttl=30) 缓存 30 秒，避免过度频繁的请求。
        @st.cache_data(ttl=30)
        def _cached_health_check():
            return check_backend_health()

        backend_ok = _cached_health_check()
        if backend_ok:
            st.success("🟢 后端连接正常")
        else:
            st.error(
                "🔴 后端未启动！\n\n"
                "请在另一个终端运行：\n"
                "```bash\n"
                "uvicorn backend.main:app --reload --port 8000\n"
                "```"
            )

        st.divider()

        # 页面导航
        # 为何用 radio 而非 selectbox：
        #   radio 让所有选项始终可见，用户一目了然有三个页面。
        #   selectbox 需要点击展开，对首次使用的用户不够友好。
        page = st.radio(
            "📂 功能导航",
            ["🌱 角色创建", "💬 对话交互", "📊 角色状态"],
            key="nav_radio",
        )

        st.divider()

        # 应用统计信息
        characters = get_characters()
        st.caption(f"📦 数据库中有 **{len(characters)}** 个角色")

        if st.session_state.get("selected_character_id"):
            st.caption(f"当前选中角色 ID: **{st.session_state.selected_character_id}**")

    # ---- 页面分发 ----
    if page == "🌱 角色创建":
        render_page_create()
    elif page == "💬 对话交互":
        render_page_chat()
    elif page == "📊 角色状态":
        render_page_dashboard()


if __name__ == "__main__":
    main()
