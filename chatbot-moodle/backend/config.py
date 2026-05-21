from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")

    jwt_secret: str = "change-me"
    database_url: str = "sqlite:///./chatbot.db"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    daily_message_limit: int = 50
    max_history_messages: int = 10
    llm_timeout: int = 30


settings = Settings()
