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
    
    # LLM Provider settings
    llm_provider: str = "openai"  # "openai" or "volcengine"
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None  # uses provider default if not set
    llm_base_url: Optional[str] = None  # uses provider default if not set
    llm_api_mode: str = "chat"  # "chat" (chat/completions) or "responses"

    # Legacy keys (still accepted)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # Web search
    web_search_api_key: Optional[str] = None
    web_search_provider: str = "tavily"
    
    # Feishu (Lark) Bot settings
    feishu_app_id: Optional[str] = None
    feishu_app_secret: Optional[str] = None
    feishu_verification_token: Optional[str] = None
    feishu_encrypt_key: Optional[str] = None
    
    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
    ]

    # Logging configuration
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_file_path: str = "./logs/healthguard.log"
    log_file_enabled: bool = True
    log_console_enabled: bool = True
    log_json_format: bool = True  # JSON format for files, human-readable for console
    log_api_requests: bool = True  # Log all API requests/responses
    log_llm_calls: bool = True  # Log all LLM calls with token usage

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
