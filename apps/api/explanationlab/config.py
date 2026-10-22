"""Environment-driven configuration.

Secrets live here and nowhere else. Nothing in this module is ever serialised
into an API response, a log line, or an experiment record.
"""

from __future__ import annotations

import functools
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", API_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Database ---
    database_url: str = "sqlite+pysqlite:///./explanationlab.sqlite3"

    # --- Provider credentials ---
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # --- Researcher auth ---
    researcher_api_token: str = ""
    explab_allow_insecure_local: bool = True

    # --- Cost and safety controls ---
    max_batch_requests: int = 120
    cost_confirmation_threshold_usd: float = 1.00
    daily_spend_cap_usd: float = 25.00
    provider_timeout_seconds: float = 180.0
    provider_max_retries: int = 2
    max_input_chars: int = 24_000
    enable_response_cache: bool = True

    # --- Jobs ---
    run_worker_in_api: bool = True
    worker_concurrency: int = 3

    # --- CORS (dev convenience; the web app normally proxies server-side) ---
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # --- Derived capability flags ---
    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key.strip())

    @property
    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key.strip())

    @property
    def demo_mode(self) -> bool:
        """True when no live provider credentials are configured.

        In demo mode the app stays fully navigable, every generated response is
        a fixture, and every such row is flagged synthetic for its whole life.
        """
        return not (self.has_openai or self.has_anthropic)

    @property
    def auth_enabled(self) -> bool:
        return bool(self.researcher_api_token.strip())

    def public_status(self) -> dict:
        """Safe-to-expose configuration summary. Contains no secrets."""
        return {
            "demo_mode": self.demo_mode,
            "providers": {
                "openai": {"configured": self.has_openai},
                "anthropic": {"configured": self.has_anthropic},
            },
            "auth_enabled": self.auth_enabled,
            "limits": {
                "max_batch_requests": self.max_batch_requests,
                "cost_confirmation_threshold_usd": self.cost_confirmation_threshold_usd,
                "daily_spend_cap_usd": self.daily_spend_cap_usd,
                "max_input_chars": self.max_input_chars,
            },
            "response_cache_enabled": self.enable_response_cache,
        }


@functools.lru_cache
def get_settings() -> Settings:
    return Settings()
