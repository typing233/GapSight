from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    SEMANTIC_SCHOLAR_API_KEY: Optional[str] = None
    SEMANTIC_SCHOLAR_BASE_URL: str = "https://api.semanticscholar.org/graph/v1"
    MAX_PAPERS: int = 100
    DEFAULT_YEARS_BACK: int = 5
    SCISPACY_MODEL: str = "en_core_sci_sm"
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
