from pathlib import Path
from pydantic_settings import BaseSettings,SettingsConfigDict
from typing import Literal

ROOT_DIR=Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    CHAT_SERVICE:Literal["ollama","deepseek"]="ollama"
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_CHAT_MODEL: str = "qwen3.5:9b"

    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-flash"
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
    )

settings=Settings()

if __name__=="__main__":
    print("模型地址：", settings.OLLAMA_BASE_URL)
    print("聊天模型：", settings.OLLAMA_CHAT_MODEL)