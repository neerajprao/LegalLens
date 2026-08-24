from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"

    database_url: str = "sqlite:///../data/db/legal_lens.db"
    vector_store_dir: str = "../data/vector_store"
    evidence_store_dir: str = "../data/evidence"


settings = Settings()
