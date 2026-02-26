from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "mysql+pymysql://app:apppassword@db:3306/carsensor"
    JWT_SECRET: str = "change-me-to-random-string"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    SCRAPE_INTERVAL_MINUTES: int = 60
    SCRAPE_MAX_PAGES: int = 20
    SCRAPE_TARGET_MAX_PAGES: int = 6
    SCRAPE_FALLBACK_MAX_PAGES: int = 20
    MAX_CONCURRENT_SCRAPES: int = 1

    class Config:
        env_file = ".env"


settings = Settings()
