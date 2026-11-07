from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Every value can be overridden by an env var."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # OpenAI-compatible endpoint. Defaults to a local Ollama daemon.
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"
    llm_model: str = "llama3.2"
    llm_timeout: float = 120.0

    system_prompt: str = (
        "You are a helpful assistant. Answer concisely and in the user's language."
    )

    # Comma-separated origins allowed to call the API from a browser.
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
