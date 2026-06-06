from ..agent import agent
from ..prompt import create_prompt
from ..tools import toolRegistry
from .runtime import AIRuntime


def generate_runtime(
    session_id: str,
    script_path: str = None,
    vector_paths: list = None,
):
    # [修复] 每个会话使用独立 Prompt 实例，避免多 session 共享全局状态
    runtime = AIRuntime(
        agent=agent,
        prompt=create_prompt(),
        tool_registry=toolRegistry,
        session_id=session_id,
        script_path=script_path,
        vector_paths=vector_paths,
    )
    return runtime
