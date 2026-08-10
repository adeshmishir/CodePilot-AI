from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str
    APP_VERSION: str
    DEBUG: bool

    HOST: str
    PORT: int

    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    GROQ_API_KEY: str = ""
    GITHUB_TOKEN: str = ""
    DATABASE_URL: str = ""
    QDRANT_URL: str = ":memory:"
    QDRANT_API_KEY: str = ""
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    RAG_CONTEXT_MAX_CHARS: int = 8000
    AGENT_MAX_STEPS: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()