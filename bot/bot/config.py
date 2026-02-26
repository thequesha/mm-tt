from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "mysql+pymysql://app:apppassword@db:3306/carsensor"
    TELEGRAM_BOT_TOKEN: str = ""
    GEMINI_API_KEY: str = ""
    BACKEND_API_BASE_URL: str = "http://backend:8000"
    BOT_FRESH_WAIT_SECONDS: int = 12
    BOT_STATUS_POLL_INTERVAL_SECONDS: int = 2

    class Config:
        env_file = ".env"


settings = Settings()
