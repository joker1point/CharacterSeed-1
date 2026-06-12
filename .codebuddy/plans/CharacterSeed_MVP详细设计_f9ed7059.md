---
name: CharacterSeed MVP详细设计
overview: 为校园AI创业赛设计一个4天可完成的MVP demo，聚焦角色创建、智能交互、成长迭代三大核心功能，采用FastAPI+Streamlit+SQLite的极简技术栈
design:
  architecture:
    framework: html
  styleKeywords:
    - Minimalism
    - Clean
    - Functional
  fontSystem:
    fontFamily: "\"Times New Roman\", Times, serif"
    heading:
      size: 24px
      weight: 600
    subheading:
      size: 18px
      weight: 500
    body:
      size: 14px
      weight: 100
  colorSystem:
    primary:
      - "#6595a4"
      - "#e5eff5"
    background:
      - "#FFFFFF"
      - "#F5F5F5"
    text:
      - "#212121"
      - "#757575"
    functional:
      - "#bdc7f9"
      - "#fbf8b1"
      - "#f1bcbc"
todos:
  - id: day1-setup
    content: 搭建项目结构，配置FastAPI+Streamlit+SQLite环境
    status: completed
  - id: day1-database
    content: 设计并实现数据库Schema（4张表）和ORM模型
    status: completed
    dependencies:
      - day1-setup
  - id: day1-creation
    content: 实现Creation Module（角色创建LLM调用和解析）
    status: completed
    dependencies:
      - day1-database
  - id: day2-director
    content: 实现Director LLM（注意力聚焦逻辑和prompt设计）
    status: completed
    dependencies:
      - day1-creation
  - id: day2-actor
    content: 实现Actor LLM（动作/表情/语言生成和prompt设计）
    status: completed
    dependencies:
      - day2-director
  - id: day2-interaction-api
    content: 实现对话交互API（POST /api/chat）和集成测试
    status: completed
    dependencies:
      - day2-actor
  - id: day3-memory
    content: 实现Memory Module简化版（记忆存储和检索）
    status: completed
    dependencies:
      - day2-interaction-api
  - id: day3-growth
    content: 实现Growth Module（成长LLM调用和人格演化）
    status: completed
    dependencies:
      - day3-memory
  - id: day4-frontend
    content: 实现Streamlit前端（三个页面：创建/对话/状态）
    status: completed
    dependencies:
      - day3-growth
  - id: day4-integration
    content: 前后端集成测试和Demo脚本准备
    status: completed
    dependencies:
      - day4-frontend
---

## 用户需求分析

### 用户背景

软件工程专业学生，初次参与完整软件系统实现，需要完成校园AI创业赛的MVP demo演示。

### 核心约束

- 开发时间：4天
- 技术栈：Python FastAPI + Streamlit + SQLite + DeepSeek API
- 演示目标：校园AI创业赛，需展示核心创新功能
- 非功能性约束：单用户演示，无需登录、并发等复杂功能

### 功能范围（MVP裁剪结果）

基于原方案的9个系统，激进裁剪为3个核心功能：

1. **Creation System（角色创建系统）**

- 功能：支持"一句话生成角色"和"故事导入生成角色"
- 创新点：自动解析生成角色的世界观、人格、初始记忆、生活状态
- LLM调用：1次（Creation LLM）

2. **Interaction Runtime（交互运行时）**

- 功能：玩家与NPC对话，NPC能根据记忆、人格、场景做出合理回复
- 创新点：Director聚焦注意力 + Actor生成动作/表情/语言
- LLM调用：2次（Director LLM + Actor LLM）

3. **Growth System（成长系统）**

- 功能：日期切换时，NPC根据昨日经历演化人格、积累记忆
- 创新点：时间驱动的人格演化，而非静态人设
- LLM调用：1次（Growth LLM）

### 简化策略（设计理由）

- **World System简化**：用文本字段存储世界设定，不构建复杂世界模型
- **Memory System简化**：用时间线列表存储记忆，不使用时序数据库或向量检索
- **Life System简化**：用状态字段存储当前活动，不构建复杂日程系统
- **Personality System简化**：用数值属性存储人格特征，不构建复杂人格模型

### 用户期望

- "最偷懒易懂但最有效体现核心的技术方案"
- 4天能完成一个能跑、能演示、体现核心创新点的原型
- 代码易于理解和后续扩展

## 技术选型（设计理由）

### 1. 技术栈选择

**后端框架：Python FastAPI**

- 理由：轻量级，快速开发，自动生成API文档，适合原型开发
- 替代方案：Flask（更轻量但缺少自动文档），Django（过重）
- 决策：FastAPI（开发效率和功能完整性最佳平衡）

**前端框架：Streamlit**

- 理由：最简单的前端方案，纯Python编写，无需前端知识，适合demo演示
- 替代方案：React（需要前端技能），Gradio（类似但Streamlit更灵活）
- 决策：Streamlit（对学生最友好，1天内可完成前端）

**数据库：SQLite**

- 理由：无需配置，单文件存储，适合单用户demo，后续易迁移到PostgreSQL
- 替代方案：PostgreSQL（过重），MongoDB（需要额外配置）
- 决策：SQLite（最符合4天开发约束）

**LLM服务：DeepSeek API**

- 理由：用户已有API Key，成本低，API兼容OpenAI格式
- 决策：使用openai库调用DeepSeek API（兼容模式）

### 2. 架构设计（设计理由）

**整体架构：单体模块化架构**

- 理由：4天时间不适合微服务，单体架构最简单，模块化便于后续拆分
- 架构图：

```
┌─────────────────────────────────────────┐
│         Streamlit Frontend              │
│    (角色创建+对话界面+状态展示)          │
└──────────────┬──────────────────────────┘
               │ HTTP API
┌──────────────▼──────────────────────────┐
│         FastAPI Backend                 │
│  ┌────────────┐  ┌────────────┐        │
│  │  Creation  │  │ Interaction│        │
│  │  Module    │  │  Module    │        │
│  └────────────┘  └────────────┘        │
│  ┌────────────┐  ┌────────────┐        │
│  │   Growth   │  │  LLM       │        │
│  │   Module   │  │  Service   │        │
│  └────────────┘  └────────────┘        │
└──────────────┬──────────────────────────┘
               │ SQLAlchemy ORM
┌──────────────▼──────────────────────────┐
│         SQLite Database                 │
│  (characters, conversations,           │
│   memories, growth_logs)               │
└─────────────────────────────────────────┘
```

**模块划分（设计理由）**

1. **Creation Module**（角色创建模块）

- 职责：解析用户输入（一句话/故事），调用LLM生成角色完整信息
- 输入：用户描述（文本）
- 输出：角色对象（世界设定、人格属性、初始记忆、生活状态）
- 设计理由：将复杂的Creation System简化为一个LLM调用 + 解析逻辑

2. **Interaction Module**（交互模块）

- 职责：处理玩家输入，调用Director聚焦注意力，调用Actor生成回复
- 流程：

```
玩家输入 → 获取角色状态 → Director LLM（聚焦） → Actor LLM（生成） → 返回结果
```

- 设计理由：保留双LLM架构体现创新，但简化输入为关键字段拼接

3. **Growth Module**（成长模块）

- 职责：日期切换时，分析昨日对话，演化人格，积累记忆
- 流程：

```
触发成长 → 获取昨日对话 → Growth LLM（分析） → 更新角色状态 → 返回结果
```

- 设计理由：简化成长为"对话后反思"，而非复杂的后台模拟

4. **LLM Service**（LLM服务封装）

- 职责：封装DeepSeek API调用，处理prompt组装、响应解析
- 设计理由：统一LLM调用接口，便于后续切换模型

5. **Data Access Layer**（数据访问层）

- 职责：使用SQLAlchemy ORM操作SQLite数据库
- 设计理由：ORM简化数据库操作，便于后续迁移

### 3. 数据库Schema设计（设计理由）

**核心实体关系图（ER图文字描述）**

```
┌─────────────┐
│  Character  │
│  (角色表)   │
└──────┬──────┘
       │ 1:N
       │
┌──────▼──────┐  ┌─────────────┐  ┌─────────────┐
│Conversation │  │   Memory    │  │ GrowthLog   │
│  (对话表)   │  │  (记忆表)   │  │ (成长记录表) │
└─────────────┘  └─────────────┘  └─────────────┘
```

**表结构设计**

1. **characters表（角色表）**

- id: Integer, 主键, 自增
- name: String(100), 角色名称
- description: Text, 角色描述（用户原始输入）
- world_setting: Text, 世界设定（LLM生成）
- personality: Text, 人格属性（JSON格式存储，如{"optimism": 70, "courage": 80}）
- current_state: Text, 当前状态（JSON格式，如{"location": "酒馆", "activity": "工作"}）
- created_at: DateTime, 创建时间
- updated_at: DateTime, 更新时间
- 设计理由：将复杂的World/Personality/Life System简化为字段存储，用JSON格式保留扩展性

2. **conversations表（对话表）**

- id: Integer, 主键, 自增
- character_id: Integer, 外键(characters.id)
- user_input: Text, 玩家输入
- npc_response: Text, NPC回复
- emotion: String(50), 情绪状态（Director输出）
- action: Text, 动作描述（Actor输出）
- timestamp: DateTime, 对话时间
- 设计理由：存储完整对话历史，用于记忆积累和成长分析

3. **memories表（记忆表）**

- id: Integer, 主键, 自增
- character_id: Integer, 外键(characters.id)
- content: Text, 记忆内容
- importance: Integer, 重要性（1-10）
- memory_type: String(50), 记忆类型（"conversation", "event", "growth"）
- created_at: DateTime, 记忆时间
- 设计理由：简化记忆系统为时间线列表，用importance字段模拟记忆重要性

4. **growth_logs表（成长记录表）**

- id: Integer, 主键, 自增
- character_id: Integer, 外键(characters.id)
- personality_delta: Text, 人格变化（JSON格式）
- event_summary: Text, 事件摘要
- new_memories: Text, 新增记忆（JSON数组）
- created_at: DateTime, 成长时间
- 设计理由：记录每次成长的详细过程，便于演示和调试

### 4. API设计（设计理由）

**RESTful API设计**

1. **POST /api/characters/create**

- 功能：创建角色
- 输入：{"description": "落魄贵族少女"}
- 输出：{"id": 1, "name": "艾琳", ...}
- 设计理由：最简单的创建接口，一句话生成角色

2. **POST /api/chat**

- 功能：与角色对话
- 输入：{"character_id": 1, "message": "你好"}
- 输出：{"response": "你好，旅行者...", "emotion": "friendly", "action": "微笑"}
- 设计理由：核心交互接口，展示Director+Actor双LLM架构

3. **GET /api/characters/{character_id}**

- 功能：获取角色状态
- 输出：{"name": "艾琳", "personality": {...}, "memories": [...], ...}
- 设计理由：展示角色当前状态，用于演示成长效果

4. **POST /api/growth/trigger**

- 功能：触发角色成长
- 输入：{"character_id": 1}
- 输出：{"personality_delta": {...}, "new_memories": [...]}
- 设计理由：手动触发成长，便于demo演示（实际应自动触发）

**API设计理由总结**

- 最小化API数量（4个接口覆盖核心功能）
- 使用RESTful风格，易于理解
- 输入输出的JSON格式便于Streamlit调用

### 5. 前端设计（Streamlit）

**页面结构**

1. **角色创建页面**

- 输入框：输入角色描述（一句话或故事）
- 按钮：生成角色
- 展示区：显示生成的角色信息（名称、人格、世界设定等）

2. **对话交互页面**

- 角色选择：下拉框选择已创建的角色
- 对话区：显示对话历史（类似聊天界面）
- 输入区：输入框 + 发送按钮
- 状态区：显示角色当前情绪、动作

3. **角色状态页面**

- 角色选择：下拉框选择角色
- 展示区：显示角色人格属性（数值条）、记忆时间线、成长历史
- 按钮：触发成长（手动）

**前端设计理由**

- Streamlit最适合快速原型开发
- 三个页面覆盖核心功能
- 无需前端知识，纯Python编写

### 6. 关键流程图描述

**流程1：角色创建流程**

```
用户输入描述
    ↓
调用Creation LLM（prompt：解析描述，生成角色完整信息）
    ↓
解析LLM响应（JSON格式）
    ↓
存储到characters表
    ↓
初始化memories表（初始记忆）
    ↓
返回角色信息
```

**流程2：对话交互流程**

```
玩家输入消息
    ↓
获取角色状态（personality, memories, current_state）
    ↓
调用Director LLM（prompt：根据角色状态+玩家输入，聚焦注意力）
    ↓
解析Director输出（emotion, focus_memories, goal, style）
    ↓
调用Actor LLM（prompt：根据Director输出，生成动作/表情/语言）
    ↓
解析Actor输出（action, expression, speech）
    ↓
存储对话到conversations表
    ↓
存储重要记忆到memories表
    ↓
返回结果给前端
```

**流程3：成长流程**

```
触发成长（手动或自动）
    ↓
获取昨日对话历史（conversations表）
    ↓
调用Growth LLM（prompt：分析对话，生成人格演化和新记忆）
    ↓
解析Growth输出（personality_delta, new_memories）
    ↓
更新characters表（personality字段）
    ↓
存储新记忆到memories表
    ↓
存储成长记录到growth_logs表
    ↓
返回成长结果
```

### 7. 目录结构设计（设计理由）

```
CharacterSeed/
├── backend/
│   ├── main.py              # FastAPI入口文件
│   ├── config.py            # 配置文件（DeepSeek API Key等）
│   ├── database.py          # 数据库连接和ORM配置
│   ├── models.py            # SQLAlchemy模型定义
│   ├── schemas.py           # Pydantic schemas（请求/响应格式）
│   ├── crud/
│   │   ├── __init__.py
│   │   ├── character.py     # 角色CRUD操作
│   │   ├── conversation.py  # 对话CRUD操作
│   │   └── memory.py       # 记忆CRUD操作
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── creation.py      # Creation Module（角色创建）
│   │   ├── interaction.py   # Interaction Module（对话交互）
│   │   └── growth.py        # Growth Module（成长系统）
│   ├── services/
│   │   ├── __init__.py
│   │   └── llm_service.py   # LLM Service（DeepSeek API封装）
│   └── prompts/
│       ├── creation.txt     # Creation LLM的prompt模板
│       ├── director.txt     # Director LLM的prompt模板
│       ├── actor.txt        # Actor LLM的prompt模板
│       └── growth.txt       # Growth LLM的prompt模板
├── frontend/
│   └── app.py               # Streamlit前端应用
├── data/
│   └── character_seed.db    # SQLite数据库文件（自动生成）
├── requirements.txt         # Python依赖
└── README.md                # 项目说明
```

**目录结构设计理由**

- 清晰的模块分离：crud（数据访问）、modules（业务逻辑）、services（外部服务）
- prompts单独存放：便于调试和优化prompt
- 扁平化结构：适合小项目，降低复杂度
- 符合FastAPI最佳实践：models/schemas/crud分离

### 8. 实现注意事项（设计理由）

**性能优化**

- LLM调用使用同步方式（简单，适合demo）
- 后续可优化为异步调用
- SQLite适合单用户，无需连接池

**错误处理**

- LLM调用失败时的降级策略（返回默认回复）
- 数据库操作使用transaction保证一致性
- 输入验证使用Pydantic schemas

**可扩展性**

- JSON字段存储复杂数据，便于后续结构化
- 模块化设计，便于后续拆分为微服务
- SQLAlchemy ORM便于迁移到PostgreSQL

**Demo演示优化**

- 添加详细日志，便于展示系统运行过程
- Streamlit界面添加"调试模式"，显示LLM原始输入输出
- 准备预设角色和对话脚本，确保demo流畅

### 9. 4天开发计划（精确到天）

**Day 1（项目初始化 + Creation System）**

- 上午：项目结构搭建，FastAPI + Streamlit + SQLite环境配置
- 下午：数据库Schema设计和ORM模型实现，Creation Module实现
- 晚上：测试Creation System，调试prompt

**Day 2（Interaction Runtime）**

- 上午：Director LLM实现，prompt设计
- 下午：Actor LLM实现，prompt设计
- 晚上：集成测试，调试对话交互流程

**Day 3（Growth System + Memory）**

- 上午：Memory Module简化实现
- 下午：Growth Module实现，prompt设计
- 晚上：集成测试，调试成长流程

**Day 4（前端 + 集成 + Demo准备）**

- 上午：Streamlit前端实现（三个页面）
- 下午：前后端集成，端到端测试
- 晚上：Demo脚本准备，演讲PPT准备

**每天的具体任务拆解（详见todolist）**

### 10. Prompt设计（设计理由）

**Creation Prompt模板**

```
你是一个角色创建助手。根据用户描述，生成一个完整的角色设定。

用户描述：{user_description}

请生成以下信息（JSON格式）：
1. name - 角色名称
2. world_setting - 世界设定（200字以内）
3. personality - 人格属性（JSON对象，包含optimism, courage, empathy, loyalty等属性，值域0-100）
4. initial_memories - 初始记忆（数组，每个记忆包含content和importance）
5. current_state - 当前状态（JSON对象，包含location, activity, mood）

输出格式：严格的JSON，不要包含```json```标记。
```

**Director Prompt模板**

```
你是一个角色注意力聚焦系统。根据角色当前状态和玩家输入，决定角色应该关注什么。

角色名称：{character_name}
人格属性：{personality}
当前状态：{current_state}
最近记忆：{recent_memories}
玩家输入：{user_input}

请分析并输出（JSON格式）：
1. emotion - 当前情绪（happy, sad, angry, surprised, neutral, friendly等）
2. focus_memories - 应该回忆的记忆（数组，最多3条）
3. goal - 当前对话目标（简短描述）
4. style - 回复风格（简短描述，如"热情的", "冷漠的"等）

输出格式：严格的JSON，不要包含```json```标记。
```

**Actor Prompt模板**

```
你是一个角色行为生成系统。根据角色状态和聚焦结果，生成角色的动作、表情和语言。

角色名称：{character_name}
人格属性：{personality}
当前情绪：{emotion}
聚焦记忆：{focus_memories}
对话目标：{goal}
回复风格：{style}
玩家输入：{user_input}

请生成（JSON格式）：
1. action - 动作描述（如"拿起酒杯", "站起身来"等）
2. expression - 表情描述（如"微笑", "皱眉"等）
3. speech - 语言回复（符合角色人格和当前情境的回复）

输出格式：严格的JSON，不要包含```json```标记。
```

**Growth Prompt模板**

```
你是一个角色成长分析系统。根据角色昨日经历，分析人格演化和重要记忆。

角色名称：{character_name}
当前人格：{current_personality}
昨日对话历史：{yesterday_conversations}

请分析并输出（JSON格式）：
1. personality_delta - 人格变化（JSON对象，每个属性是变化量，正值增加负值减少）
2. new_memories - 新增记忆（数组，每个记忆包含content和importance）
3. event_summary - 事件摘要（简短描述昨日发生了什么）

输出格式：严格的JSON，不要包含```json```标记。
```

**Prompt设计理由**

- 结构化输出：要求LLM输出JSON，便于解析
- 上下文注入：将角色状态、记忆等注入prompt
- 简化输入：只注入最关键的信息，避免token过长
- 可调试性：prompt单独存放，便于优化

## 设计风格

由于使用Streamlit作为前端框架，界面设计受限于Streamlit的默认组件样式。但可以通过Streamlit的主题配置和自定义CSS来实现简洁美观的界面。

## 设计思路

1. **角色创建页面**：简洁的输入和展示，突出"一句话生成角色"的创新点
2. **对话交互页面**：类聊天界面，清晰展示对话历史和角色状态
3. **角色状态页面**：时间线展示记忆和成长，突出"生命模拟"的创新点

## 界面布局（Streamlit实现）

### 页面1：角色创建

- 顶部标题："CharacterSeed - AI生命模拟系统"
- 输入区：st.text_area（输入角色描述）
- 按钮：st.button（"生成角色"）
- 展示区：
- st.expander（"角色信息"，展开显示名称、人格雷达图、世界设定）
- st.expander（"初始记忆"，展开显示记忆时间线）

### 页面2：对话交互

- 左侧：角色选择（st.selectbox）
- 中间：对话历史（st.container，循环显示对话气泡）
- 右侧：角色状态（st.json或st.markdown显示情绪、动作）
- 底部：输入框和发送按钮（st.text_input + st.button）

### 页面3：角色状态

- 顶部：角色选择（st.selectbox）
- 左侧：人格属性（st.progress_bar或自定义雷达图）
- 右侧：记忆时间线（st.timeline或st.markdown列表）
- 底部：成长历史（st.dataframe显示growth_logs）

## 视觉优化

- 使用Streamlit的主题配置（config.toml）设置主色调
- 通过st.markdown + HTML/CSS实现简单的样式定制
- 使用plotly（Streamlit内置）绘制人格雷达图

## 设计理由

- Streamlit不适合高度定制化的UI设计，重点应放在功能实现
- 简洁的界面反而更适合demo演示，突出技术创新而非界面华丽
- Streamlit的组件足以支撑核心功能的展示