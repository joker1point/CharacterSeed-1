from typing import Optional

from pydantic import BaseModel


class MakeScriptRequest(BaseModel):
    file_path: str
    user_input: str


class MakeScriptResponse(BaseModel):
    message: str
    # [修复] 返回生成的剧本文件路径
    script_path: Optional[str] = None
