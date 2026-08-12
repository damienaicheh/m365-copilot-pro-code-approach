"""Centralized, validated application settings.

All environment variables consumed by the app (MS_FOUNDRY_*, AZURE_SEARCH_*,
bot/auth settings, misc toggles, ...) are declared here as a single
`pydantic_settings.BaseSettings` schema. This gives us:

  * Validation at process startup instead of opaque `KeyError` /
    `os.environ[...]` crashes deep inside request handling.
  * One place to see every environment variable the app depends on,
    with types, defaults, and descriptions.
  * A clear, actionable error message listing every missing/invalid
    variable at once instead of failing on the first one encountered.

Usage:
    from bootstrap.settings import get_settings
    settings = get_settings()
    settings.ms_foundry_project_endpoint
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import AnyHttpUrl, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Schema for every environment variable read by the application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Azure AI Foundry ──
    ms_foundry_project_endpoint: AnyHttpUrl = Field(
        ...,
        description="Azure AI Foundry project endpoint (required).",
    )
    ms_foundry_orchestrator_model_deployment_name: str = Field(
        ...,
        min_length=1,
        description="Foundry model deployment name used by the orchestrator agent (required).",
    )

    # ── Azure AI Search ──
    azure_search_endpoint: str = Field(
        default="",
        description="Azure AI Search endpoint. Optional: search is disabled if empty.",
    )
    azure_search_index: str = Field(
        default="secure-docs",
        description="Azure AI Search index name.",
    )
    azure_search_semantic_config_name: str = Field(
        default="default-semantic-config",
        description="Azure AI Search semantic configuration name (used by ingestion).",
    )
    azure_search_api_key: str | None = Field(
        default=None,
        description="Azure AI Search API key. If unset, DefaultAzureCredential is used instead.",
    )

    # ── Azure AI Foundry embeddings (data ingestion) ──
    azure_ai_foundry_embedding_deployment: str = Field(
        default="text-embedding-3-small",
        description="Foundry embedding model deployment name (used by ingestion).",
    )
    azure_ai_foundry_api_version: str = Field(
        default="2024-06-01",
        description="Azure OpenAI-compatible API version (used by ingestion).",
    )

    # ── Bot / identity ──
    bot_client_id: str | None = Field(
        default=None,
        description="Managed identity client id used for DefaultAzureCredential. "
        "Empty means the ambient/az-login identity is used.",
    )

    # ── Misc toggles ──
    enable_diag_logs: bool = Field(
        default=True,
        description="Enable verbose diagnostic logging.",
    )
    port: int = Field(
        default=3978,
        ge=1,
        le=65535,
        description="HTTP port the aiohttp server listens on.",
    )

    # ── Contoso demo/test data ──
    contoso_group_restricted_docs_id: str | None = Field(
        default=None,
        description="Entra group id used for the restricted-docs POC (optional).",
    )

    def azure_search_configured(self) -> bool:
        """Whether Azure AI Search should be wired up (endpoint provided)."""
        return bool(self.azure_search_endpoint.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide validated settings singleton.

    Raises a `SystemExit` with a readable, aggregated error message (rather
    than letting a `pydantic.ValidationError` traceback bubble up) so
    startup failures are obvious and actionable in logs/console.
    """
    try:
        return Settings()  # type: ignore[call-arg]
    except ValidationError as exc:
        errors = "\n".join(
            f"  - {'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
            for err in exc.errors()
        )
        raise SystemExit(
            "Invalid or missing environment variables detected at startup:\n"
            f"{errors}\n\n"
            "Check your .env file (see .env.template) and required Azure resources."
        ) from exc
