"""
Конфигурация приложения TestOps Copilot
"""
import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Настройки приложения"""

    # Настройки приложения
    APP_NAME: str = "TestOps Copilot"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    SECRET_KEY: str = Field(default="your-secret-key-here", env="SECRET_KEY")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    # Настройки CORS
    ALLOWED_ORIGINS: List[str] = Field(default=["*"], env="ALLOWED_ORIGINS")

    # Настройки LLM Cloud.ru (OpenAI-совместимый API)
    LLM_API_KEY: Optional[str] = Field(default=None, env="LLM_API_KEY")
    LLM_BASE_URL: str = Field(
        default="https://llm.api.cloud.ru/v1",
        env="LLM_BASE_URL"
    )
    LLM_MODEL: str = Field(
        default="openai/gpt-oss-120b",
        env="LLM_MODEL"
    )

    # Настройки Evolution Compute API
    COMPUTE_API_URL: str = Field(
        default="https://compute.api.cloud.ru",
        env="COMPUTE_API_URL"
    )
    COMPUTE_API_TOKEN: Optional[str] = Field(
        default=None,
        env="COMPUTE_API_TOKEN"
    )
    COMPUTE_PROJECT_ID: Optional[str] = Field(
        default=None,
        env="COMPUTE_PROJECT_ID"
    )

    # Настройки GitLab
    GITLAB_URL: str = Field(default="https://gitlab.com", env="GITLAB_URL")
    GITLAB_TOKEN: Optional[str] = Field(default=None, env="GITLAB_TOKEN")
    GITLAB_PROJECT_ID: Optional[str] = Field(default=None, env="GITLAB_PROJECT_ID")

    # Настройки хранилища (без Redis - используем in-memory)
    STORAGE_PATH: str = Field(
        default="./storage",
        env="STORAGE_PATH"
    )

    # Настройки временных файлов
    TEMP_PATH: str = Field(
        default="./temp",
        env="TEMP_PATH"
    )

    # Таймауты
    LLM_TIMEOUT: int = Field(default=120, env="LLM_TIMEOUT")
    API_TIMEOUT: int = Field(default=30, env="API_TIMEOUT")
    JOB_TIMEOUT: int = Field(default=600, env="JOB_TIMEOUT")  # 10 минут

    # Лимиты
    MAX_TESTCASES_PER_JOB: int = Field(default=100, env="MAX_TESTCASES_PER_JOB")
    MAX_FILE_SIZE: int = Field(default=10 * 1024 * 1024, env="MAX_FILE_SIZE")  # 10MB

    # LLM параметры генерации
    LLM_TEMPERATURE: float = Field(default=0.7, env="LLM_TEMPERATURE")
    LLM_MAX_TOKENS: int = Field(default=4096, env="LLM_MAX_TOKENS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# Создание экземпляра настроек
settings = Settings()


# Создание директорий при необходимости
def create_directories():
    """Создание необходимых директорий"""
    directories = [
        settings.STORAGE_PATH,
        settings.TEMP_PATH,
        f"{settings.STORAGE_PATH}/jobs",
        f"{settings.STORAGE_PATH}/testcases",
        f"{settings.STORAGE_PATH}/autotests",
        f"{settings.STORAGE_PATH}/reports"
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)


# Инициализация при запуске
create_directories()


def get_settings() -> Settings:
    """
    Получение настроек приложения (для dependency injection)

    Returns:
        Экземпляр настроек
    """
    return settings
