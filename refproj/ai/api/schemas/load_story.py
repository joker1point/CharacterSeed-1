from pydantic import BaseModel


class LoadStoryRequest(BaseModel):
    file_path: str


class LoadStoryResponse(BaseModel):
    message: str
    # [优化] 返回向量文件路径，便于前端绑定到会话检索范围
    vector_path: str = ""
