# 组装 embedding 和 vector store 模块
from pathlib import Path
from typing import List, Optional, Union

from .embedding import embedder
from .vector_store import vectorStore


def retrieve_context(
    text: str,
    top_k: int = 10,
    vector_paths: Optional[List[Union[str, Path]]] = None,
):
    # [优化] vector_paths 限定检索范围，避免扫全库
    query_vector = embedder.embed(text)

    context = vectorStore.retrieve_vectors(
        query_vector,
        top_k,
        vector_paths=vector_paths,
    )

    return context
