from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./repolens.db"
    redis_url: str = "redis://localhost:6379/0"
    session_secret: str = Field(min_length=32)
    frontend_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"
    analysis_mode: Literal["demo", "live"] = "demo"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    github_token: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    github_callback_url: str = "http://localhost:8000/auth/github/callback"
    allow_demo_login: bool = False
    cookie_secure: bool = False
    max_files: int = Field(default=60, ge=1, le=200)
    max_source_bytes: int = Field(default=300_000, ge=1000, le=1_000_000)
    max_tool_steps: int = Field(default=10, ge=1, le=20)
    max_output_tokens: int = Field(default=2000, ge=200, le=4000)


@lru_cache
def get_settings():
    return Settings()
