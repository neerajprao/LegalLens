from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM provider (CLAUDE.md §19): switched twice on 2026-08-26 — Anthropic Claude API ->
    # Google Gemini's free tier (API credit blocker) -> a fully local model via Ollama (user's
    # explicit request to remove the API/network dependency entirely). No API key at all is
    # needed for this configuration — everything runs on-device. Requires the Ollama app/daemon
    # running locally (default port 11434) with the configured model already pulled.
    # This keeps every agent's _call_model() call shape unchanged (see app/agents/base.py), so
    # only the client construction changed, not any agent's logic.
    #
    # Swapped 2026-09-16: qwen3.5:9b-q4_K_M -> qwen2.5:7b-instruct, at the user's request for a
    # faster model. Warm-call latency dropped from ~15-25s to ~3-4s on the same M3 Pro hardware
    # for a comparable fact-extraction call, verified live. qwen2.5 is not a reasoning model, so
    # base.py's "think": false field is simply ignored by Ollama for it rather than doing
    # anything — harmless no-op, confirmed live, left in place since it's still needed if a
    # reasoning model is configured again later.
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b-instruct"

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
