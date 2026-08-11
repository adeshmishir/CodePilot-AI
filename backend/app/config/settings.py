from pydantic import model_validator
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
    "https://code-pilot-ai-puce.vercel.app",
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
    INDEX_BATCH_SIZE: int = 8
    MAX_INDEX_FILE_SIZE_MB: float = 1.0

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_persistent_vector_store(self):
        in_memory = not self.QDRANT_URL.strip() or self.QDRANT_URL.strip() == ":memory:"

        if not self.DEBUG and in_memory:
            raise ValueError(
                "QDRANT_URL must point to a persistent Qdrant instance "
                "when DEBUG=False. Refusing to fall back to an in-memory "
                "vector store in production."
            )

        return self


settings = Settings()