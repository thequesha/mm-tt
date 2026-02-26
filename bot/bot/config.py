from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "mysql+pymysql://app:apppassword@db:3306/carsensor"
    TELEGRAM_BOT_TOKEN: str = ""
    GEMINI_API_KEY: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
