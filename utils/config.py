from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    pb_url: str
    openai_api_key: str
    openai_model: str
    domain_blocklist: str = "tempmail.com,10minutemail.net,mailinator.com"
    backend_cors_origins: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()