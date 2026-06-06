import json
from .base_tool import BaseTool

from ..prompt.script import save_script, script_path_for_name
from ..rag.rag import retrieve_context


class UpdateMemoryTool(BaseTool):
    name = "Update_Memory"
    description = "更新长期记忆，确保AI能够记住重要信息并在未来的对话中使用它。"

    parameters = {
        "type": "object",
        "properties": {
            "new_memory": {
                "type": "string",
                "description": "加入新的长期记忆内容，格式为{\"标签\": \"内容\"}",
            }
        },
        "required": ["new_memory"],
    }

    def execute(self, prompt=None, new_memory=None, **_kwargs):
        # [修复] 写入当前会话绑定的 prompt，而非模块级全局单例
        prompt.update_memory(new_memory)
        return "成功更新长期记忆"


class UpdateSessionSummaryTool(BaseTool):
    name = "Update_Session_Summary"
    description = "更新会话总结，确保AI能够跟踪对话的主题和进展。"

    parameters = {
        "type": "object",
        "properties": {
            "new_summary": {
                "type": "string",
                "description": "新的当前会话总结内容"
            }
        },
        "required": ["new_summary"],
    }

    def execute(self, prompt=None, new_summary=None, **_kwargs):
        prompt.update_session_summary(new_summary)
        return "会话总结已更新"


class UpdateEmotionTool(BaseTool):
    name = "Update_Emotion"
    description = "更新当前会话的情绪，确保AI能够适应当前的环境。"

    parameters = {
        "type": "object",
        "properties": {
            "label": {
                "type": "string",
                "description": "情绪标签，例如 happy, sad, angry, neutral, anxious",
            },
            "score": {
                "type": "number",
                "description": "情绪强度，范围 0 到 1",
            },
        },
        "required": ["label", "score"],
    }

    def execute(self, prompt=None, label=None, score=None, **_kwargs):
        prompt.update_emotion_curve(label, score)
        return "当前会话的情绪已更新"


class RetrieveContextTool(BaseTool):
    name = "Retrieve_Context"
    description = "检索相关的上下文信息，确保AI能够获取必要的信息来生成更准确的回复。"

    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "检索上下文信息的查询语句",
            }
        },
        "required": ["query"],
    }

    def execute(self, prompt=None, query=None, vector_paths=None, **_kwargs):
        # [优化] 支持限定向量文件范围，避免跨故事检索污染
        return retrieve_context(query, vector_paths=vector_paths)


class MakeScriptTool(BaseTool):
    name = "Make_Script"
    description = "生成角色互动脚本，确保AI能够生成符合角色设定的回复。"

    parameters = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "角色名字"},
            "age": {"type": "integer", "description": "角色年龄"},
            "gender": {
                "type": "string",
                "enum": ["male", "female", "other"],
                "description": "角色性别",
            },
            "occupation": {"type": "string", "description": "角色职业"},
            "background": {
                "type": "array",
                "items": {"type": "string"},
                "description": "角色背景经历",
            },
            "personality": {
                "type": "object",
                "properties": {
                    "extroversion": {"type": "number", "minimum": 0, "maximum": 1},
                    "kindness": {"type": "number", "minimum": 0, "maximum": 1},
                    "humor": {"type": "number", "minimum": 0, "maximum": 1},
                    "emotional": {"type": "number", "minimum": 0, "maximum": 1},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["extroversion", "kindness", "humor", "emotional", "confidence"],
            },
            "speaking_style": {
                "type": "array",
                "items": {"type": "string"},
                "description": "角色说话风格",
            },
            "values": {
                "type": "array",
                "items": {"type": "string"},
                "description": "角色价值观",
            },
            "habits": {
                "type": "array",
                "items": {"type": "string"},
                "description": "角色习惯",
            },
            "relationship": {
                "type": "object",
                "properties": {
                    "user": {"type": "string", "description": "角色与用户的关系"}
                },
            },
            "events": {
                "type": "array",
                "items": {"type": "string"},
                "description": "角色与用户的故事",
            },
        },
        "required": [
            "name", "age", "gender", "occupation", "background", "personality",
            "speaking_style", "values", "habits", "relationship", "events",
        ],
    }

    def execute(
        self,
        prompt=None,
        name=None,
        age=None,
        gender=None,
        occupation=None,
        background=None,
        personality=None,
        speaking_style=None,
        values=None,
        habits=None,
        relationship=None,
        events=None,
        **_kwargs,
    ):
        script = {
            "name": name,
            "age": age,
            "gender": gender,
            "occupation": occupation,
            "background": background,
            "personality": personality,
            "speaking_style": speaking_style,
            "values": values,
            "habits": habits,
            "relationship": relationship,
            "events": events,
        }
        # [修复] 返回剧本保存路径，供 make_script API 响应
        path = save_script(name, script)
        return {"message": "角色互动脚本已生成并保存", "script_path": str(path)}
