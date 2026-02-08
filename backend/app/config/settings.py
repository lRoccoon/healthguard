"""
Configuration Settings.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # App info
    app_name: str = "HealthGuard AI"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # Security
    secret_key: str = "your-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    
    # Storage
    storage_type: str = "local"  # local, s3, oss
    local_storage_path: str = "./data"
    
    # AI/LLM settings
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    web_search_api_key: Optional[str] = None
    
    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
