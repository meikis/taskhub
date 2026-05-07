from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "TaskHub"
    DATABASE_URL: str = "sqlite:///e:/source/taskhub/backend/taskhub.db"
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALGORITHM: str = "HS256"
    CORS_ORIGINS: list[str] = ["http://localhost:8000", "http://127.0.0.1:8000", "http://0.0.0.0:8000", "http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]

settings = Settings()