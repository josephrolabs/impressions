"""Construct configured model clients without coupling providers to TOML loading."""

from __future__ import annotations

import os
from collections.abc import Mapping

from impressions.core.config import ConfigError, ProjectConfig
from impressions.core.model_client import ModelClient
from impressions.core.openai_client import OpenAIModelClient


def create_model_client(
    config: ProjectConfig, environment: Mapping[str, str] | None = None
) -> ModelClient:
    """Create the configured provider client using its referenced environment key."""
    environment = os.environ if environment is None else environment
    api_key = environment.get(config.credentials.api_key_env)
    if api_key is None or not api_key.strip():
        raise ConfigError(
            "Missing API key environment variable "
            f"{config.credentials.api_key_env!r} for model provider "
            f"{config.model.provider!r}."
        )

    if config.model.provider == "openai":
        return OpenAIModelClient(
            api_key=api_key,
            model=config.model.model,
            timeout=config.model.timeout,
        )

    # Configuration validation prevents this path; retain the guard for callers
    # that construct ProjectConfig directly.
    raise ConfigError(f"Unsupported model provider: {config.model.provider!r}.")
