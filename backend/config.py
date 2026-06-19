from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Literal

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"  # 允许 .env 中存在未声明字段
    )

    # LLM Provider Selection: deepseek | qwen | zhipu | ollama | openai | agnes
    LLM_PROVIDER: str = "agnes"
    
    # DeepSeek API Configuration
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    
    # 通义千问 (Qwen) Configuration
    QWEN_API_KEY: str = ""
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_MODEL: str = "qwen-turbo"
    
    # 智谱 GLM Configuration
    ZHIPU_API_KEY: str = ""
    ZHIPU_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    ZHIPU_MODEL: str = "glm-4-flash"
    
    # Ollama (本地模型) Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Agnes AI (OpenAI 兼容) Configuration
    AGNES_API_KEY: str = ""
    AGNES_BASE_URL: str = "https://apihub.agnes-ai.com/v1"
    AGNES_MODEL: str = "agnes-1.5-flash"

    # Database Configuration
    DATABASE_URL: str = "sqlite:///./data/character_seed.db"
    
    # Application Settings
    DEBUG: bool = False
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "CharacterSeed"
    
    def get_llm_config(self) -> dict:
        """根据 LLM_PROVIDER 返回对应的配置"""
        provider_configs = {
            "deepseek": {
                "api_key": self.DEEPSEEK_API_KEY,
                "base_url": self.DEEPSEEK_BASE_URL,
                "model": self.DEEPSEEK_MODEL
            },
            "qwen": {
                "api_key": self.QWEN_API_KEY,
                "base_url": self.QWEN_BASE_URL,
                "model": self.QWEN_MODEL
            },
            "zhipu": {
                "api_key": self.ZHIPU_API_KEY,
                "base_url": self.ZHIPU_BASE_URL,
                "model": self.ZHIPU_MODEL
            },
            "ollama": {
                "api_key": "ollama",  # Ollama 不需要真实 API Key
                "base_url": self.OLLAMA_BASE_URL,
                "model": self.OLLAMA_MODEL
            },
            "openai": {
                "api_key": self.OPENAI_API_KEY,
                "base_url": self.OPENAI_BASE_URL,
                "model": self.OPENAI_MODEL
            },
            "agnes": {
                "api_key": self.AGNES_API_KEY,
                "base_url": self.AGNES_BASE_URL,
                "model": self.AGNES_MODEL
            }
        }
        return provider_configs.get(self.LLM_PROVIDER, provider_configs["deepseek"])

settings = Settings()
