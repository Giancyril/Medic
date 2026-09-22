from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "Incident Response Agent"
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str = "sqlite+aiosqlite:///./incident_agent.db"
    PROMETHEUS_URL: str = "http://localhost:9090"
    KUBERNETES_IN_CLUSTER: bool = False
    SIMULATION_MODE: bool = True
    LLM_MODEL: str = "gemini-1.5-pro"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    SLACK_WEBHOOK_URL: str = ""
    PAGERDUTY_ROUTING_KEY: str = ""
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000", "*"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
