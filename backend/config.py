import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    APP_NAME: str = "Orchestra AI"
    DEBUG: bool = True

    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'data' / 'orchestra.db'}"
    VECTOR_STORE_PATH: str = str(BASE_DIR / "data" / "vector_store")
    PROJECTS_DIR: str = str(BASE_DIR / "projects")
    PROMPTS_DIR: str = str(BASE_DIR / "prompts")

    LM_STUDIO_BASE_URL: str = "http://127.0.0.1:1234/v1"
    LM_STUDIO_MODEL: str = "codellama-7b-instruct"
    LLM_TIMEOUT: int = 120
    LLM_MAX_TOKENS: int = 2048
    LLM_TEMPERATURE: float = 0.7

    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    DOCKER_SANDBOX_IMAGE: str = "orchestra-sandbox"
    DOCKER_TIMEOUT: int = 60

    GIT_AUTHOR_NAME: str = "Orchestra AI"
    GIT_AUTHOR_EMAIL: str = "orchestra@local"

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"

settings = Settings()

os.makedirs(BASE_DIR / "data" / "vector_store", exist_ok=True)
os.makedirs(BASE_DIR / "projects", exist_ok=True)
