import os
from openai import OpenAI

#覆盖环境变量，确保使用正确的API密钥
from dotenv import load_dotenv
load_dotenv(override=True)

class Agent:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),  
            base_url="https://api.deepseek.com"
        )
        self.model = "deepseek-v4-pro"

    def chat(self, messages, tools, stream=False, reasoning_effort="high"):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            stream=stream,
            reasoning_effort=reasoning_effort,
            extra_body={"thinking": {"type": "enabled"}}
        )
        return response


