import uuid
from pathlib import Path

from ..config import vector_path_for_source
from ..rag.chunk import textChunker
from ..rag.vector_store import vectorStore
from ..rag.embedding import embedder
from ..utils.load_file import textLoader
from ..rag.chunk.chunk import Chunk


class EmbeddingRuntime:

    def __init__(self, source_path: str):
        self.source_path = source_path

        self.textChunker = textChunker
        self.vectorStore = vectorStore
        self.embedder = embedder
        self.fileLoader = self.choose_fileloader()

        # [优化] 向量文件路径由 config 统一推导
        self.vector_store_path = vector_path_for_source(source_path)
        self.vectorStore.path = str(self.vector_store_path)

    def process_file(self):
        text = self.fileLoader.load(self.source_path)
        chunk_texts = self.textChunker.paragraph_split(text)

        # [优化] 批量 embedding，减少 API 调用次数
        batch_size = 16
        for start in range(0, len(chunk_texts), batch_size):
            batch = chunk_texts[start : start + batch_size]
            vectors = self.embedder.embed_batch(batch)

            for offset, (chunk_text, chunk_vector) in enumerate(zip(batch, vectors)):
                index = start + offset
                chunk = Chunk(
                    chunk_id=str(uuid.uuid4()),
                    text=chunk_text,
                    vector=chunk_vector,
                    metadata={
                        "file_path": self.source_path,
                        "index": index,
                    },
                )
                self.vectorStore.add_to_buffer(chunk)

        self.vectorStore.flush()
        return str(self.vector_store_path)

    def choose_fileloader(self):
        if self.source_path.endswith(".txt"):
            return textLoader
        # 其它类型待实现
