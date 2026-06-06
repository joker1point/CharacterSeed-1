from .tools import (
    UpdateMemoryTool,
    UpdateSessionSummaryTool,
    UpdateEmotionTool,
    RetrieveContextTool,
    MakeScriptTool,
)


class ToolRegistry:
    def __init__(self):
        self.tools = {
            UpdateMemoryTool.name: UpdateMemoryTool(),
            UpdateSessionSummaryTool.name: UpdateSessionSummaryTool(),
            UpdateEmotionTool.name: UpdateEmotionTool(),
            RetrieveContextTool.name: RetrieveContextTool(),
            MakeScriptTool.name: MakeScriptTool()
        }
        # [优化] 每次对话前由 AIRuntime 绑定当前会话的 Prompt 与向量检索范围
        self._bound_prompt = None
        self._vector_paths = None

    def bind_prompt(self, prompt):
        self._bound_prompt = prompt

    def bind_vector_paths(self, vector_paths):
        self._vector_paths = vector_paths

    def execute_tool(self, tool_name, **kwargs):
        tool = self.tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")
        if self._bound_prompt is None:
            raise RuntimeError("ToolRegistry 未绑定 Prompt，请先调用 bind_prompt()")

        if tool_name == "Retrieve_Context":
            kwargs["vector_paths"] = self._vector_paths

        return tool.execute(prompt=self._bound_prompt, **kwargs)

    def get_tools(self):
        result = []
        for tool in self.tools.values():
            result.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            })
        return result