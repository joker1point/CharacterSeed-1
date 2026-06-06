from fastapi import APIRouter

from ..pipeline.embedding_runtime import EmbeddingRuntime
from .schemas.load_story import LoadStoryRequest, LoadStoryResponse

router = APIRouter()


@router.post("/load_story", response_model=LoadStoryResponse)
def load_story(request: LoadStoryRequest) -> LoadStoryResponse:
    file_path = request.file_path

    embedding_runtime = EmbeddingRuntime(file_path)
    vector_path = embedding_runtime.process_file()

    return LoadStoryResponse(
        message=f"File '{file_path}' loaded and processed successfully.",
        vector_path=vector_path,
    )
