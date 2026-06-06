from dataclasses import dataclass

@dataclass
class Chunk:
    chunk_id: str
    text: str
    vector: list[float]
    
    metadata: dict
    #metadata格式：{
    #   "source_file": str,
    #   "index": int
    #}