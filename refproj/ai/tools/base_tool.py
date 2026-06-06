class BaseTool:

    name = ""

    description = ""

    parameters = {}

    # [优化] 工具通过 execute(prompt=...) 接收当前会话 Prompt，不再依赖全局单例
    def execute(self, prompt=None, **kwargs):
        raise NotImplementedError("Subclasses must implement this method")
