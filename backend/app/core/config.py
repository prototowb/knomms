from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # database
    database_url: str = "postgresql+asyncpg://kc:kc@localhost:5432/knomms"
    database_sync_url: str = "postgresql://kc:kc@localhost:5432/knomms"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # redis
    redis_url: str = "redis://localhost:6379/0"

    # minio
    minio_endpoint: str = "http://localhost:9000"
    minio_access_key: str = "kc-admin"
    minio_secret_key: str = "change-me"
    minio_bucket: str = "knomms-media"

    # ollama (not used in M0)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral:7b-instruct"
    ollama_embed_model: str = "nomic-embed-text"
    max_concurrent_generations: int = 2
    # Read timeout for Ollama generation requests.
    # CPU inference requires ~120s prefill for a 1200-token RAG context;
    # set higher for GPU (where prefill is <1s and this is just a safety net).
    ollama_read_timeout: float = 300.0
    # Number of chunks retrieved per Q&A query.
    # CPU default=3 (~1200 input tokens, ~2min TTFT on a 4-core machine).
    # Set to 10 for GPU deployments where prefill is fast.
    retrieval_top_k: int = 3

    # auth
    secret_key: str = "insecure-dev-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30


settings = Settings()
