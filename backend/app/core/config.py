"""应用配置管理

使用 pydantic-settings 管理环境变量配置。
"""

import os
from pathlib import Path
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用配置
    APP_NAME: str = "Skill-Know"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # 数据目录
    DATA_DIR: str = Field(default="data", description="数据存储目录")

    # 数据库配置（SQLite）
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///data/skill_know.db",
        description="数据库连接 URL",
    )

    # LLM 配置
    LLM_PROVIDER: str = Field(default="openai", description="LLM 提供商")
    LLM_API_KEY: str = Field(default="", description="LLM API Key")
    LLM_BASE_URL: str = Field(
        default="https://api.openai.com/v1",
        description="LLM API Base URL",
    )
    LLM_CHAT_MODEL: str = Field(default="gpt-4o-mini", description="聊天模型")

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS 配置
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    def ensure_data_dir(self) -> Path:
        """确保数据目录存在"""
        data_path = Path(self.DATA_DIR)
        data_path.mkdir(parents=True, exist_ok=True)
        return data_path

    @property
    def database_path(self) -> Path:
        """获取数据库文件路径"""
        if "sqlite" in self.DATABASE_URL:
            # 从 URL 中提取路径
            db_path = self.DATABASE_URL.split("///")[-1]
            return Path(db_path)
        return Path(self.DATA_DIR) / "skill_know.db"


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
