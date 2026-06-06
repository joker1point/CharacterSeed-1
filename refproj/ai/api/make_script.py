from fastapi import APIRouter

from ..config import vector_path_for_source
from ..pipeline.generator import generate_runtime
from .schemas.make_script import MakeScriptRequest, MakeScriptResponse

router = APIRouter()


@router.post("/make_script", response_model=MakeScriptResponse)
def make_script(request: MakeScriptRequest) -> MakeScriptResponse:
    # [修复] file_path 是资料文本路径，不应作为 script_path 传入
    session_id = "make_script_session"
    vector_path = str(vector_path_for_source(request.file_path))

    runtime = generate_runtime(session_id, vector_paths=[vector_path])
    result = runtime.make_script(request.file_path, request.user_input)

    return MakeScriptResponse(
        message=result["message"],
        script_path=result.get("script_path"),
    )
