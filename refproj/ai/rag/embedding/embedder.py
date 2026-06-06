## 载入api key
from dotenv import load_dotenv
import os

load_dotenv()
##

# 用户输入文本转换为向量的模块，使用OpenAI的API进行文本嵌入
from openai import OpenAI
from typing import List

class Embedder:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),  
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.model = "text-embedding-v4"

    # 文本转换向量
    def embed(self, text: str) -> List[float]:
        response = self.client.embeddings.create(
            model=self.model,
            input=text
        )
        return response.data[0].embedding

    # 批量转换向量
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        responses = self.client.embeddings.create(
            model=self.model,
            input=texts
        )
        return [item.embedding for item in responses.data]



