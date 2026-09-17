from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"

    database_url: str = "sqlite:///../data/db/legal_lens.db"
    vector_store_dir: str = "../data/vector_store"
    evidence_store_dir: str = "../data/evidence"

    # CLAUDE.md §18's encryption-at-rest design, scoped to evidence files (see
    # app/encryption.py): a Fernet key, base64-encoded per the `cryptography`
    # library's own format. Left unset by default and auto-generated with a
    # loud warning on first use in that case — key management itself (env var
    # vs. secrets manager vs. KMS) is deliberately NOT resolved here, same as
    # the original design note; this only makes local/dev usable without
    # requiring the operator to generate one by hand first.
    evidence_encryption_key: str = ""


settings = Settings()
