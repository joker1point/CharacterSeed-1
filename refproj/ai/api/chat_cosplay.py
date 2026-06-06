from fastapi import APIRouter

from ..pipeline.generator import generate_runtime
from .schemas.chat_cosplay import ChatCosplayRequest, ChatCosplayResponse

router = APIRouter()


@router.post("/chat_cosplay", response_model=ChatCosplayResponse)
def chat_cosplay(request: ChatCosplayRequest) -> ChatCosplayResponse:
    # [修复] 使用 chat_cosplay + script_path 传入 generate_runtime，而非错误的 chat(..., script_path=)
    runtime = generate_runtime(
        request.session_id,
        script_path=request.script_path,
    )
    response = runtime.chat_cosplay(request.user_input)

    return ChatCosplayResponse(response=response)
