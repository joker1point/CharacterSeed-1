from .prompt import Prompt

# 保留工厂方法，避免外部直接依赖已废弃的全局单例
def create_prompt() -> Prompt:
    return Prompt()
