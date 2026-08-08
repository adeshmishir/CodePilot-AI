from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str
    APP_VERSION: str
    DEBUG: bool

    HOST: str
    PORT: int

    GROQ_API_KEY: str = ""
    GITHUB_TOKEN: str = ""
    DATABASE_URL: str = ""
    QDRANT_URL: str = ":memory:"
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()