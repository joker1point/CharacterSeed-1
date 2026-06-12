from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # DeepSeek API Configuration
    DEEPSEEK_API_KEY: str
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    
    # Database Configuration
    DATABASE_URL: str = "sqlite:///./data/character_seed.db"
    
    # Application Settings
    DEBUG: bool = False
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "CharacterSeed"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
