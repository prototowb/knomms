from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # database
    database_url: str = "postgresql+asyncpg://kc:kc@localhost:5432/knowledge_commons"
    database_sync_url: str = "postgresql://kc:kc@localhost:5432/knowledge_commons"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # redis
    redis_url: str = "redis://localhost:6379/0"

    # minio
    minio_endpoint: str = "http://localhost:9000"
    minio_access_key: str = "kc-admin"
    minio_secret_key: str = "change-me"
    minio_bucket: str = "knowledge-commons-media"

    # ollama (not used in M0)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral:7b-instruct"
    ollama_embed_model: str = "nomic-embed-text"
    max_concurrent_generations: int = 2

    # auth
    secret_key: str = "insecure-dev-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30


settings = Settings()
