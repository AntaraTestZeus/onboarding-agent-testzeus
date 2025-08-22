# backend/utils/config.py
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    pb_url: str
    openai_api_key: str
    openai_model: str
    domain_blocklist: str = "tempmail.com,10minutemail.net,mailinator.com"
    backend_cors_origins: str

    model_config = {
        "env_file": str(Path(__file__).parent.parent.parent / ".env"),
        "env_file_encoding": "utf-8"
    }

settings = Settings()