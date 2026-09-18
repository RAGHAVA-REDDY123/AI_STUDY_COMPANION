from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Study Companion"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "dev-secret-key-ai-study-companion-prototype"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # PostgreSQL + pgvector Database Configuration (Mandatory, no SQLite fallback)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/ai_study_companion"
    
    # Redis & Celery Background Queue
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_ALWAYS_EAGER: bool = False
    
    # LLM Provider: Gemini 2.5 Flash
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    # AI Observability, Retries & Cost Tracking
    AI_MAX_RETRIES: int = 3
    AI_REQUEST_TIMEOUT: float = 45.0
    AI_COST_TRACKING_ENABLED: bool = True
    AI_LOGGING_ENABLED: bool = True
    AI_EVALUATION_ENABLED: bool = True
    
    # Prompt & Retrieval Versioning
    PROMPT_VERSION_TUTOR: str = "tutor_v1.0"
    PROMPT_VERSION_QUIZ: str = "quiz_gen_v2.0"
    PROMPT_VERSION_EVAL: str = "assessment_rubric_v1.0"
    RETRIEVAL_VERSION: str = "hybrid_rrf_v1.0_bge384"
    
    # Embedding Provider: BGE-small (Strict 384 Dimensions)
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIMENSION: int = 384
    EMBEDDING_BATCH_SIZE: int = 32

    # Semantic Chunking Safety Limits
    CHUNK_TARGET_SIZE: int = 400
    CHUNK_MIN_SIZE: int = 80
    CHUNK_MAX_SIZE: int = 1000
    CHUNK_OVERLAP: int = 50
    
    # File Storage
    STORAGE_DIR: str = "storage/uploads"
    
    # Seed Admin
    FIRST_SUPERUSER_EMAIL: str = "admin@aiprof.com"
    FIRST_SUPERUSER_PASSWORD: str = "AdminPassword123!"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
