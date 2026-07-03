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
class ProjectConfig:
    """Validated Impressions project configuration."""

    root: Path
    file_path: Path
    version: int
    paths: ProjectPaths


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

    return ProjectConfig(
        root=project_root,
        file_path=config_path,
        version=version,
        paths=ProjectPaths(tasks=tasks, reports=reports),
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
