import json
from typing import Callable, List, Optional

from ..config import vector_path_for_source
from ..prompt.prompt import Prompt
from ..prompt.prompt_store import load, save
from ..prompt.script import load_script

from ..utils.load_file import textLoader


class AIRuntime:

    def __init__(
        self,
        agent,
        prompt,
        tool_registry,
        session_id: str,
        script_path: str = None,
        vector_paths: Optional[List[str]] = None,
    ):
        self.agent = agent
        self.tool_registry = tool_registry
        self.session_id = session_id

        # [修复] 从磁盘恢复时使用独立实例，不再与全局 prompt 混用
        data = load(session_id)
        if data:
            self.prompt = Prompt.from_dict(data)
        else:
            self.prompt = prompt

        if script_path:
            self.prompt.script = load_script(script_path)

        if vector_paths:
            self.vector_paths = [str(p) for p in vector_paths]
        else:
            self.vector_paths = None

    def _bind_tools(self):
        self.tool_registry.bind_prompt(self.prompt)
        self.tool_registry.bind_vector_paths(self.vector_paths)

    @staticmethod
    def _serialize_tool_result(result) -> str:
        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False)

    @staticmethod
    def _assistant_message_dict(message) -> dict:
        payload = {
            "role": "assistant",
            "content": message.content or "",
        }
        if message.tool_calls:
            payload["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ]
        return payload

    def _run_turn(self, build_prompt_fn: Callable[[], str], user_input: str) -> str:
        """[优化] 抽取 chat / chat_cosplay 公共逻辑，统一工具调用与多轮 messages。"""
        self.prompt.user_input = user_input
        self._bind_tools()

        tools = self.tool_registry.get_tools()
        messages = [{"role": "user", "content": build_prompt_fn()}]

        max_rounds = 3
        message = None

        for _ in range(max_rounds):
            response = self.agent.chat(messages=messages, tools=tools)
            message = response.choices[0].message

            if not message.tool_calls:
                break

            messages.append(self._assistant_message_dict(message))

            needs_regenerate = False
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                result = self.tool_registry.execute_tool(tool_name, **tool_args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": self._serialize_tool_result(result),
                })

                if tool_name == "Retrieve_Context":
                    self.prompt.update_retrieval_history(result)
                    needs_regenerate = True

            if needs_regenerate:
                messages = [{"role": "user", "content": build_prompt_fn()}]
                continue

            # 非检索类工具已更新 prompt 状态，用新上下文再请求一轮
            messages.append({"role": "user", "content": build_prompt_fn()})

        assistant_reply = message.content if message else ""
        self.prompt.update_chat_history(user_input, assistant_reply)
        save(self.session_id, self.prompt.to_dict())

        return assistant_reply

    def chat(self, user_input: str):
        return self._run_turn(self.prompt.build_prompt, user_input)

    def chat_cosplay(self, user_input: str):
        return self._run_turn(self.prompt.build_prompt_cosplay, user_input)

    def make_script(self, file_path: str, user_input: str) -> dict:
        text = textLoader.load(file_path)
        self.prompt.user_input = user_input
        self._bind_tools()

        messages = [{"role": "user", "content": self.prompt.build_script(text)}]
        tools = self.tool_registry.get_tools()

        response = self.agent.chat(messages=messages, tools=tools)
        message = response.choices[0].message

        script_path = None
        tool_message = "剧本生成完成"

        if message.tool_calls:
            messages.append(self._assistant_message_dict(message))

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                result = self.tool_registry.execute_tool(tool_name, **tool_args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": self._serialize_tool_result(result),
                })

                if tool_name == "Make_Script" and isinstance(result, dict):
                    script_path = result.get("script_path")
                    tool_message = result.get("message", tool_message)

        # [修复] 返回结构化结果，供 API 使用
        return {
            "message": message.content or tool_message,
            "script_path": script_path,
        }

    def set_vector_paths_for_source(self, source_path: str):
        """[优化] 根据故事源文件绑定对应向量库路径。"""
        path = vector_path_for_source(source_path)
        self.vector_paths = [str(path)]
        self.tool_registry.bind_vector_paths(self.vector_paths)
