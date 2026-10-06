"""Construct configured model clients without coupling providers to TOML loading."""

from __future__ import annotations

import os
from collections.abc import Mapping

from impressions.core.anthropic_client import AnthropicModelClient
from impressions.core.config import SUPPORTED_PROVIDERS, ConfigError, ProjectConfig
from impressions.core.gemini_client import GeminiModelClient
from impressions.core.meta_client import MetaModelClient
from impressions.core.model_client import EchoModelClient, ModelClient
from impressions.core.openai_client import OpenAIModelClient


def create_model_client(
    config: ProjectConfig, environment: Mapping[str, str] | None = None
) -> ModelClient:
    """Create the configured provider client using its referenced environment key.

    When the referenced API key variable is unset or empty, return the
    deterministic :class:`EchoModelClient` fallback instead of raising, so
    ``impressions run`` works end to end without provider credentials.
    """
    environment = os.environ if environment is None else environment
    api_key = environment.get(config.credentials.api_key_env)
    if api_key is None or not api_key.strip():
        return EchoModelClient()

    provider = config.model.provider
    if provider == "openai":
        return OpenAIModelClient(
            api_key=api_key,
            model=config.model.model,
            timeout=config.model.timeout,
        )
    if provider == "anthropic":
        return AnthropicModelClient(
            api_key=api_key,
            model=config.model.model,
            timeout=config.model.timeout,
        )
    if provider == "gemini":
        return GeminiModelClient(
            api_key=api_key,
            model=config.model.model,
            timeout=config.model.timeout,
        )
    if provider == "meta":
        return MetaModelClient(
            api_key=api_key,
            model=config.model.model,
            timeout=config.model.timeout,
        )

    # Configuration validation prevents this path; retain the guard for callers
    # that construct ProjectConfig directly.
    raise ConfigError(
        f"Unsupported model provider: {provider!r}. "
        f"Supported providers: {', '.join(SUPPORTED_PROVIDERS)}."
    )
