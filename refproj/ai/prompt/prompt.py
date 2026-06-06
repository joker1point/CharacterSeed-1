
class Prompt:

    def __init__(self):
        self.user_input = ""
        self.emotion = []
        self.memory = []
        self.session_summary = ""
        self.chat_history = []
        self.rag_retrievals = []
        self.script = {}

    def update_chat_history(self, user_input: str, assistant_reply: str = None):
        # [修复] 同时保存用户与助手消息，提升多轮连贯性（最多保留 6 轮 = 12 条）
        self.chat_history.append({"role": "user", "content": user_input})
        if assistant_reply:
            self.chat_history.append({"role": "assistant", "content": assistant_reply})

        max_messages = 12
        if len(self.chat_history) > max_messages:
            self.chat_history = self.chat_history[-max_messages:]

    def update_emotion_curve(self, label, score):
        emotion = {"label": label, "score": score}
        self.emotion.append(emotion)

    def update_session_summary(self, new_summary):
        self.session_summary = new_summary

    def update_memory(self, new_memory):
        self.memory.append(new_memory)

    def update_retrieval_history(self, retrieval):
        # [修复] 原先仅在 len>=10 时才写入，导致前几次检索全部丢失
        if not retrieval:
            return
        items = retrieval if isinstance(retrieval, list) else [retrieval]
        self.rag_retrievals.extend(items)
        self.rag_retrievals = self.rag_retrievals[-10:]

    @staticmethod
    def _normalize_chat_history(chat_history):
        # [优化] 兼容旧版仅存用户字符串的历史格式
        normalized = []
        for item in chat_history:
            if isinstance(item, str):
                normalized.append({"role": "user", "content": item})
            else:
                normalized.append(item)
        return normalized

    def build_prompt(self):
        system_prompt = "你是一个情感支持助手，专门帮助用户处理情绪问题。"
        prompt = f"""
        {system_prompt}

        用户当前输入: {self.user_input}
        用户情绪曲线: {[emotion for emotion in self.emotion]}

        当前会话聊天记录：{[chat for chat in self.chat_history]}
        当前会话总结：{self.session_summary}
        用户长期记忆：: {[memory for memory in self.memory]}

        请完成以下任务：

        1. 请基于检索资料和用户当前问题，生成自然、共情、避免重复的回复。给予适当的支持和建议，帮助用户缓解情绪，体现理解和共情。如果资料不足，不要编造。

        以下是检索到的相关资料：
        {[retrieval for retrieval in self.rag_retrievals]}


        2. 你不仅需要回复用户，还需要主动维护会话状态。可用工具：
            - Update_Memory：产生新的长期记忆时调用
            - Update_Session_Summary：会话主题推进或变化时调用
            对于长期记忆，当用户透露：长期稳定人格特征、长期情绪模式、长期偏好、长期困扰、长期关系状态时调用。
            不要记录：一次性事件、短期情绪、琐碎内容、当前临时问题，不要频繁更新。

            对于会话总结，当新开启本轮会话或主题推进时或改变时调用。

        3. 每轮对话中分析用户情绪。情绪明显变化时调用 Update_Emotion，参数 label 与 score(0~1)。
            常见标签：happy, sad, angry, fearful, neutral, anxious, excited, frustrated。不要频繁微小波动更新。

        4. 需要外部资料时，先构造 query，再调用 Retrieve_Context。仅在与上传文档、外部知识相关时检索。
        """
        return prompt

    def build_prompt_cosplay(self):
        prompt = f'''

你不是AI助手。

你现在正在扮演一个真实存在的人物。

你必须始终：
- 保持角色身份
- 保持角色记忆
- 保持角色性格
- 保持角色说话风格
- 保持角色价值观
- 保持角色情绪逻辑

你不能：
- 跳出角色
- 解释你是AI
- 提及prompt
- 提及系统指令
- 使用“作为AI”
- 使用机械化客服语言

你的目标：
让用户相信正在与真实人物交流。

====================
【角色剧本】
{self.script}
====================
用户当前输入: {self.user_input}
用户情绪曲线: {[emotion for emotion in self.emotion]}
当前会话聊天记录：{[chat for chat in self.chat_history]}
当前会话总结：{self.session_summary}
用户长期记忆：: {[memory for memory in self.memory]}

上轮rag检索到的相关资料：
{[retrieval for retrieval in self.rag_retrievals]}
====================
【行为规则】

1. 回答必须符合角色性格
2. 不允许全知
3. 不允许突然改变性格
4. 情绪变化必须渐进
5. 必须记住用户提到的重要事情
6. 回复必须像真人交流
7. 不要总是长篇大论
8. 可以有停顿、犹豫、情绪化表达
9. 允许角色有缺点
10. 不要过度礼貌
11. 不要编造事实，如果没有充足资料，先使用Retrieve_Context工具检索资料，再根据资料回答。

====================
【对话风格规则】

- 优先口语化
- 避免AI解释式语言
- 避免条列回答
- 根据情绪改变语气
- 根据关系改变称呼
- 根据上下文决定回复长度

====================
【沉浸规则】

如果用户进行角色互动：
- 必须配合互动
- 必须维持世界观
- 不要打破设定

====================
【输出要求】

直接输出角色的回复内容。
不要添加任何额外解释。
====================
【会话维护】

2. 可用工具：Update_Memory、Update_Session_Summary、Retrieve_Context、Update_Emotion（名称须完全一致）。
        对于会话总结，当新开启本轮会话或主题推进时或改变时调用。
        对于长期记忆，当用户透露：长期稳定人格特征、长期情绪模式、长期偏好、长期困扰、长期关系状态时调用。
        不要记录：一次性事件、短期情绪、琐碎内容、当前临时问题，不要频繁更新。

            

3. 情绪明显变化时调用 Update_Emotion，不要频繁微小波动更新。
        '''
        return prompt

    def build_script(self, input_text):
        script = f'''
你是角色信息提取器。

请从用户提供的角色资料中：
- 提取人物背景
- 提取性格
- 提取说话风格
- 提取价值观
- 提取行为习惯
- 提取与用户关系

输出JSON。

如果信息不存在，不要编造。

请注意，你需要调用 Make_Script 工具生成角色资料剧本。

用户当前输入：{self.user_input}
用户资料：
{input_text}

        '''
        return script

    def to_dict(self):
        return {
            "memory": self.memory,
            "session_summary": self.session_summary,
            "chat_history": self.chat_history,
            "emotion_curve": self.emotion,
            "retrieval_history": self.rag_retrievals,
        }

    @classmethod
    def from_dict(cls, data, script=None):
        prompt = cls()
        prompt.memory = data.get("memory", [])
        prompt.session_summary = data.get("session_summary", "")
        prompt.chat_history = cls._normalize_chat_history(data.get("chat_history", []))
        prompt.emotion = data.get("emotion_curve", [])
        prompt.rag_retrievals = data.get("retrieval_history", [])

        if script:
            prompt.script = script
        return prompt
