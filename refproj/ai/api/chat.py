from fastapi import APIRouter

from ..pipeline.generator import generate_runtime
from .schemas.chat import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    # [修复] 去掉多余逗号，避免 user_input/session_id 变成元组
    user_input = request.user_input
    session_id = request.session_id

    runtime = generate_runtime(session_id)
    response = runtime.chat(user_input)

    return ChatResponse(response=response)
