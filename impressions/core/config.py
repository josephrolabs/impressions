"""Project configuration loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised only on Python 3.10
    import tomli as tomllib


CONFIG_FILE_NAME = "impressions.toml"
SUPPORTED_CONFIG_VERSION = 1


class ConfigError(Exception):
    """Raised when project configuration cannot be loaded."""


@dataclass(frozen=True)
class ProjectPaths:
    """Configured project resource paths."""

    tasks: Path
    reports: Path


@dataclass(frozen=True)
class ModelConfig:
    """Validated configuration for a language model provider."""

    provider: str
    model: str
    timeout: float | None


@dataclass(frozen=True)
class CredentialsConfig:
    """References to credentials required by configured providers."""

    api_key_env: str


@dataclass(frozen=True)
class EvaluationConfig:
    """Optional reproducible settings for repeated evaluation attempts."""

    attempts: int = 1
    pass_at_k: int = 1


@dataclass(frozen=True)
class PromptConfig:
    variant: str = "baseline"


@dataclass(frozen=True)
class ProjectConfig:
    """Validated Impressions project configuration."""

    root: Path
    file_path: Path
    version: int
    paths: ProjectPaths
    model: ModelConfig
    credentials: CredentialsConfig
    evaluation: EvaluationConfig
    prompt: PromptConfig


def load_project_config(root: str | Path = ".") -> ProjectConfig:
    """Load and validate an Impressions project configuration."""
    project_root = Path(root)
    config_path = project_root / CONFIG_FILE_NAME

    if not config_path.is_file():
        raise ConfigError(
            f"Missing configuration file: {config_path}\n"
            f"Run 'impressions init {project_root}' to create one."
        )

    try:
        with config_path.open("rb") as config_file:
            data = tomllib.load(config_file)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(
            f"Invalid TOML syntax in {config_path}: {exc}"
        ) from exc

    version = _required_int(data, "version", CONFIG_FILE_NAME)
    if version != SUPPORTED_CONFIG_VERSION:
        raise ConfigError(
            f"Unsupported configuration version in {config_path}: {version}. "
            f"Expected version {SUPPORTED_CONFIG_VERSION}."
        )

    paths = _required_table(data, "paths", CONFIG_FILE_NAME)
    tasks = _required_path(paths, "tasks", "[paths]", project_root)
    reports = _required_path(paths, "reports", "[paths]", project_root)
    model = _required_table(data, "model", CONFIG_FILE_NAME)
    provider = _required_non_empty_string(model, "provider", "[model]")
    if provider != "openai":
        raise ConfigError(
            f"Unsupported model provider in {config_path}: {provider!r}. "
            "Supported providers: openai."
        )
    model_name = _required_non_empty_string(model, "model", "[model]")
    timeout = _optional_positive_number(model, "timeout", "[model]")

    credentials = _required_table(data, "credentials", CONFIG_FILE_NAME)
    api_key_env = _required_non_empty_string(
        credentials, "api_key_env", "[credentials]"
    )
    evaluation_data = data.get("evaluation", {})
    if not isinstance(evaluation_data, dict):
        raise ConfigError(f"Expected [evaluation] in {CONFIG_FILE_NAME} to be a TOML table.")
    attempts = _optional_positive_int(evaluation_data, "attempts", "[evaluation]", 1)
    pass_at_k = _optional_positive_int(evaluation_data, "pass_at_k", "[evaluation]", 1)
    if pass_at_k > attempts:
        raise ConfigError("Expected 'pass_at_k' in [evaluation] not to exceed 'attempts'.")
    prompt_data = data.get("prompt", {})
    if not isinstance(prompt_data, dict):
        raise ConfigError(f"Expected [prompt] in {CONFIG_FILE_NAME} to be a TOML table.")
    variant = _optional_non_empty_string(prompt_data, "variant", "[prompt]", "baseline")

    return ProjectConfig(
        root=project_root,
        file_path=config_path,
        version=version,
        paths=ProjectPaths(tasks=tasks, reports=reports),
        model=ModelConfig(provider=provider, model=model_name, timeout=timeout),
        credentials=CredentialsConfig(api_key_env=api_key_env),
        evaluation=EvaluationConfig(attempts=attempts, pass_at_k=pass_at_k),
        prompt=PromptConfig(variant=variant),
    )


def _required_table(data: dict[str, Any], key: str, location: str) -> dict[str, Any]:
    if key not in data:
        raise ConfigError(f"Missing required section [{key}] in {location}.")

    value = data[key]
    if not isinstance(value, dict):
        raise ConfigError(f"Expected [{key}] in {location} to be a TOML table.")

    return value


def _required_int(data: dict[str, Any], key: str, location: str) -> int:
    if key not in data:
        raise ConfigError(f"Missing required value '{key}' in {location}.")

    value = data[key]
    if not isinstance(value, int):
        raise ConfigError(f"Expected '{key}' in {location} to be an integer.")

    return value


def _required_path(
    data: dict[str, Any],
    key: str,
    location: str,
    project_root: Path,
) -> Path:
    if key not in data:
        raise ConfigError(f"Missing required value '{key}' in {location}.")

    value = data[key]
    if not isinstance(value, str):
        raise ConfigError(f"Expected '{key}' in {location} to be a string path.")

    if not value.strip():
        raise ConfigError(f"Expected '{key}' in {location} to be a non-empty path.")

    path = Path(value)
    if path.is_absolute():
        return path

    return project_root / path


def _required_non_empty_string(
    data: dict[str, Any], key: str, location: str
) -> str:
    if key not in data:
        raise ConfigError(f"Missing required value '{key}' in {location}.")

    value = data[key]
    if not isinstance(value, str):
        raise ConfigError(f"Expected '{key}' in {location} to be a string.")
    if not value.strip():
        raise ConfigError(f"Expected '{key}' in {location} to be a non-empty string.")
    return value


def _optional_non_empty_string(data: dict[str, Any], key: str, location: str, default: str) -> str:
    if key not in data:
        return default
    value = data[key]
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"Expected '{key}' in {location} to be a non-empty string.")
    return value


def _optional_positive_number(
    data: dict[str, Any], key: str, location: str
) -> float | None:
    if key not in data:
        return None

    value = data[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"Expected '{key}' in {location} to be a number.")
    if value <= 0:
        raise ConfigError(f"Expected '{key}' in {location} to be greater than zero.")
    return float(value)


def _optional_positive_int(
    data: dict[str, Any], key: str, location: str, default: int
) -> int:
    if key not in data:
        return default
    value = data[key]
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConfigError(f"Expected '{key}' in {location} to be a positive integer.")
    return value
