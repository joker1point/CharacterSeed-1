import json
from openai import OpenAI
from backend.config import settings
from typing import Optional

class LLMService:
    """LLM服务封装类"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        )
        self.model = "deepseek-chat"  # DeepSeek-V3模型
    
    def call(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        response_format: Optional[dict] = None
    ) -> str:
        """
        调用LLM
        
        Args:
            prompt: 用户prompt
            system_prompt: 系统prompt（可选）
            temperature: 温度参数（0-1）
            max_tokens: 最大token数
            response_format: 响应格式约束（可选，例如 {"type": "json_object"}）。
                           默认 None 即不约束格式，由调用方按需传入。
            
        Returns:
            LLM的响应文本
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            kwargs = dict(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if response_format is not None:
                kwargs["response_format"] = response_format
            
            response = self.client.chat.completions.create(**kwargs)
            
            content = response.choices[0].message.content
            return content
            
        except Exception as e:
            print(f"LLM调用失败: {e}")
            raise
    
    def parse_json_response(self, response: str) -> dict:
        """
        解析LLM的JSON响应
        
        Args:
            response: LLM返回的字符串
            
        Returns:
            解析后的字典
        """
        try:
            # 尝试直接解析
            return json.loads(response)
        except json.JSONDecodeError:
            # 如果失败，尝试提取JSON部分
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                raise ValueError(f"无法解析LLM响应为JSON: {response}")

    @staticmethod
    def validate_creation_schema(data: dict) -> dict:
        """
        轻量级 schema 校验：验证 Creation LLM 输出的必要字段与类型。
        
        校验内容：
        1. 顶层必填字段：name, world_setting, personality, current_state
        2. personality 子字段：optimism, courage, empathy, loyalty,
           intelligence, sociability（要求为 0-100 整数值）
        3. current_state 子字段：location, activity, mood
        
        Args:
            data: 解析后的字典
            
        Returns:
            校验通过后的字典（personality 数值已转为 int）
            
        Raises:
            ValueError: 缺少必要字段或类型错误时
        """
        # 1. 顶层必填字段
        required_top = ["name", "world_setting", "personality", "current_state"]
        for field in required_top:
            if field not in data or data[field] is None:
                raise ValueError(f"LLM响应缺少必填字段: '{field}'")

        # 2. personality 子字段校验 + 类型强制转换
        personality = data["personality"]
        if not isinstance(personality, dict):
            raise ValueError("'personality' 必须是 JSON 对象")

        personality_fields = [
            "optimism", "courage", "empathy",
            "loyalty", "intelligence", "sociability"
        ]
        for field in personality_fields:
            if field not in personality:
                raise ValueError(f"personality 缺少字段: '{field}'")
            try:
                val = int(personality[field])
                if val < 0 or val > 100:
                    raise ValueError(
                        f"personality.{field} 值 {val} 超出范围 [0, 100]"
                    )
                personality[field] = val
            except (ValueError, TypeError):
                raise ValueError(
                    f"personality.{field} 值 '{personality[field]}' 无法转换为 0-100 的整数"
                )

        # 3. current_state 子字段校验
        current_state = data["current_state"]
        if not isinstance(current_state, dict):
            raise ValueError("'current_state' 必须是 JSON 对象")

        for field in ["location", "activity", "mood"]:
            if field not in current_state:
                raise ValueError(f"current_state 缺少字段: '{field}'")

        return data

    @staticmethod
    def validate_director_schema(data: dict) -> dict:
        """
        轻量级 schema 校验：验证 Director LLM 输出的必要字段与类型。

        校验内容：
        1. 顶层必填字段：emotion, focus_memories, goal, style（均为 string 或 list）
        2. focus_memories 必须是 list[str] 类型，最多 3 条
        3. 所有字符串字段不能为空

        设计考量：
          - 不做 emotion 枚举约束，给 LLM 自由发挥空间（"悲喜交加"、"怅然若失"等复合情绪）
          - focus_memories 截断到 3 条，作为 prompt 工程之外的兜底保护

        Args:
            data: 解析后的字典

        Returns:
            校验通过后的字典

        Raises:
            ValueError: 缺少必要字段或类型错误时
        """
        # 1. 顶层必填字段
        required_top = ["emotion", "focus_memories", "goal", "style"]
        for field in required_top:
            if field not in data or data[field] is None:
                raise ValueError(f"Director 输出缺少必填字段: '{field}'")

        # 2. emotion - 非空字符串
        emotion = data["emotion"]
        if not isinstance(emotion, str) or not emotion.strip():
            raise ValueError(f"Director.emotion 必须是非空字符串")

        # 3. focus_memories - 必须为列表，元素为字符串，截断到 3 条
        focus_memories = data["focus_memories"]
        if not isinstance(focus_memories, list):
            raise ValueError(f"Director.focus_memories 必须是数组")
        # 过滤非字符串元素 + 去空 + 截断
        focus_memories = [
            str(m) for m in focus_memories if m and str(m).strip()
        ][:3]
        data["focus_memories"] = focus_memories

        # 4. goal - 非空字符串
        goal = data["goal"]
        if not isinstance(goal, str) or not goal.strip():
            raise ValueError(f"Director.goal 必须是非空字符串")

        # 5. style - 非空字符串
        style = data["style"]
        if not isinstance(style, str) or not style.strip():
            raise ValueError(f"Director.style 必须是非空字符串")

        return data

    @staticmethod
    def validate_actor_schema(data: dict) -> dict:
        """
        轻量级 schema 校验：验证 Actor LLM 输出的必要字段与类型。

        校验内容：
        1. 顶层必填字段：action, expression, speech（均为非空字符串）
        2. speech 做最小长度校验（>= 1 字符）以防止空回复

        设计考量：
          - Actor 输出结构简单（3 个字符串），校验逻辑轻薄
          - speech 不做最大长度限制，给 LLM 充分的表达空间
          - 不做 OOC 检测（超出角色设定的回复），这是 prompt 层面的责任

        Args:
            data: 解析后的字典

        Returns:
            校验通过后的字典

        Raises:
            ValueError: 缺少必要字段或类型错误时
        """
        required_top = ["action", "expression", "speech"]
        for field in required_top:
            if field not in data or data[field] is None:
                raise ValueError(f"Actor 输出缺少必填字段: '{field}'")

        # action - 非空字符串
        action = data["action"]
        if not isinstance(action, str) or not action.strip():
            raise ValueError(f"Actor.action 必须是非空字符串")

        # expression - 非空字符串
        expression = data["expression"]
        if not isinstance(expression, str) or not expression.strip():
            raise ValueError(f"Actor.expression 必须是非空字符串")

        # speech - 非空字符串
        speech = data["speech"]
        if not isinstance(speech, str) or not speech.strip():
            raise ValueError(f"Actor.speech 必须是非空字符串")

        return data

    @staticmethod
    def validate_growth_schema(data: dict) -> dict:
        """
        轻量级 schema 校验：验证 Growth LLM 输出的必要字段与类型。

        校验内容：
        1. 顶层必填字段：personality_delta (dict), new_memories (list), event_summary (str)
        2. personality_delta 子字段：6 个人格维度，值域 [-30, 30]
        3. new_memories 数组元素：每条含 content(str) + importance(int 1-10)，最多 3 条
        4. event_summary 为非空字符串

        设计考量：
          - delta 范围限制在 [-30, 30]：防止 LLM 一次输出极端变化（如 optimism 直接 -90）
          - new_memories 截断到 3 条：prompt 已要求 ≤3 条，但 schema 层二次兜底
          - 不对事件摘要做最大长度限制：给 LLM 充分的叙事空间

        Args:
            data: 解析后的字典

        Returns:
            校验通过后的字典（personality_delta 数值已转为 int）

        Raises:
            ValueError: 缺少必要字段或类型/范围错误时
        """
        # 1. 顶层必填字段
        required_top = ["personality_delta", "new_memories", "event_summary"]
        for field in required_top:
            if field not in data or data[field] is None:
                raise ValueError(f"Growth 输出缺少必填字段: '{field}'")

        # 2. personality_delta 子字段校验
        #    只有 6 个固定的人格维度，不变属性名
        personality_delta = data["personality_delta"]
        if not isinstance(personality_delta, dict):
            raise ValueError("'personality_delta' 必须是 JSON 对象")

        personality_fields = [
            "optimism", "courage", "empathy",
            "loyalty", "intelligence", "sociability"
        ]
        for field in personality_fields:
            if field not in personality_delta:
                raise ValueError(
                    f"personality_delta 缺少字段: '{field}'"
                )
            try:
                val = int(personality_delta[field])
                # 限制变化范围在 [-30, 30]，防止 LLM 输出极端值
                if val < -30 or val > 30:
                    raise ValueError(
                        f"personality_delta.{field} 值 {val} "
                        f"超出范围 [-30, 30]"
                    )
                personality_delta[field] = val
            except (ValueError, TypeError):
                raise ValueError(
                    f"personality_delta.{field} 值 "
                    f"'{personality_delta[field]}' 无法转换为整数"
                )

        # 3. new_memories 数组校验
        new_memories = data["new_memories"]
        if not isinstance(new_memories, list):
            raise ValueError("'new_memories' 必须是数组")

        validated_memories = []
        for i, mem in enumerate(new_memories):
            if not isinstance(mem, dict):
                continue
            # content 必须是非空字符串
            content = mem.get("content", "")
            if not isinstance(content, str) or not content.strip():
                continue
            # importance 必须在 1-10 范围内
            try:
                importance = int(mem.get("importance", 5))
                if importance < 1 or importance > 10:
                    importance = 5  # 范围外则回退到默认值
            except (ValueError, TypeError):
                importance = 5
            validated_memories.append({
                "content": content.strip(),
                "importance": importance
            })

        # 截断到最多 3 条（prompt 已要求 ≤3，此处为兜底）
        data["new_memories"] = validated_memories[:3]

        # 4. event_summary 非空字符串
        event_summary = data["event_summary"]
        if not isinstance(event_summary, str) or not event_summary.strip():
            raise ValueError("'event_summary' 必须是非空字符串")

        return data
