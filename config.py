from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./g4med.db"
    
    # Security
    SECRET_KEY: str = "g4med-secret-key-change-in-production-2025"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 horas
    
    # API
    API_TITLE: str = "G4med API"
    API_VERSION: str = "0.2.0"
    CORS_ORIGINS: List[str] = ["*"]
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # Business Rules
    MAX_BID_AMOUNT: float = 1_000_000.0
    MIN_BID_AMOUNT: float = 100.0
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

