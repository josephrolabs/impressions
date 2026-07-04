"""Task definition discovery, parsing, and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from impressions.core.config import ProjectConfig, load_project_config

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - dependency issue
    raise RuntimeError(
        "PyYAML is required to parse task definition files."
    ) from exc


SUPPORTED_TASK_EXTENSIONS = frozenset({".yaml", ".yml"})
SUPPORTED_TASK_SCHEMA_VERSION = 1
SUPPORTED_EXPECTED_TYPES = frozenset({"text"})


class TaskDiscoveryError(Exception):
    """Raised when task definitions cannot be discovered."""


class TaskValidationError(Exception):
    """Raised when a task definition file fails parsing or validation."""

    def __init__(self, path: Path, errors: list["TaskFieldError"]) -> None:
        self.path = path
        self.errors = errors
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        details = "\n".join(f"  {error.field}: {error.message}" for error in self.errors)
        return f"Invalid task definition: {self.path}\n{details}"


@dataclass(frozen=True)
class TaskFieldError:
    """A validation error for one task definition field."""

    field: str
    message: str


@dataclass(frozen=True)
class TaskDefinition:
    """A discovered task definition file."""

    path: Path

    @property
    def name(self) -> str:
        """Return the task definition file name."""
        return self.path.name


@dataclass(frozen=True)
class TaskInput:
    """Validated task input configuration."""

    prompt: str


@dataclass(frozen=True)
class TaskExpected:
    """Validated expected output configuration."""

    type: str


@dataclass(frozen=True)
class ParsedTask:
    """A parsed and validated task definition."""

    path: Path
    version: int
    name: str
    description: str
    input: TaskInput
    expected: TaskExpected


def discover_tasks(root: str | Path = ".") -> list[TaskDefinition]:
    """Load project configuration and discover task definition files."""
    config = load_project_config(root)
    return discover_tasks_from_config(config)


def discover_tasks_from_config(config: ProjectConfig) -> list[TaskDefinition]:
    """Discover supported task definition files for a loaded project config."""
    tasks_dir = config.paths.tasks

    if not tasks_dir.exists():
        raise TaskDiscoveryError(f"Tasks directory does not exist: {tasks_dir}")

    if not tasks_dir.is_dir():
        raise TaskDiscoveryError(f"Configured tasks path is not a directory: {tasks_dir}")

    tasks = [
        TaskDefinition(path=path)
        for path in tasks_dir.iterdir()
        if _is_supported_task_file(path)
    ]
    tasks.sort(key=lambda task: task.path.name)

    if not tasks:
        supported = ", ".join(sorted(SUPPORTED_TASK_EXTENSIONS))
        raise TaskDiscoveryError(
            f"No task definition files found in {tasks_dir}. "
            f"Supported extensions: {supported}."
        )

    return tasks


def load_task(path: str | Path) -> ParsedTask:
    """Parse and validate a single task definition file."""
    task_path = Path(path)
    try:
        with task_path.open("r", encoding="utf-8") as task_file:
            data = yaml.safe_load(task_file)
    except yaml.YAMLError as exc:
        raise TaskValidationError(
            task_path,
            [TaskFieldError("<document>", f"Invalid YAML syntax: {exc}")],
        ) from exc

    return parse_task_data(data, task_path)


def load_tasks(root: str | Path = ".") -> list[ParsedTask]:
    """Discover, parse, and validate task definition files."""
    config = load_project_config(root)
    return load_tasks_from_config(config)


def load_tasks_from_config(config: ProjectConfig) -> list[ParsedTask]:
    """Parse and validate all task files for a loaded project config."""
    return [load_task(task.path) for task in discover_tasks_from_config(config)]


def parse_task_data(data: Any, path: str | Path) -> ParsedTask:
    """Validate raw YAML data and return a parsed task object."""
    task_path = Path(path)
    errors: list[TaskFieldError] = []

    if not isinstance(data, dict):
        raise TaskValidationError(
            task_path,
            [TaskFieldError("<document>", "Expected a YAML mapping.")],
        )

    version = _required_int(data, "version", errors)
    name = _required_non_empty_str(data, "name", errors)
    description = _required_non_empty_str(data, "description", errors)
    input_data = _required_mapping(data, "input", errors)
    expected_data = _required_mapping(data, "expected", errors)

    prompt = None
    if input_data is not None:
        prompt = _required_non_empty_str(input_data, "prompt", errors, parent="input")

    expected_type = None
    if expected_data is not None:
        expected_type = _required_non_empty_str(
            expected_data,
            "type",
            errors,
            parent="expected",
        )
        if expected_type is not None and expected_type not in SUPPORTED_EXPECTED_TYPES:
            supported = ", ".join(sorted(SUPPORTED_EXPECTED_TYPES))
            errors.append(
                TaskFieldError(
                    "expected.type",
                    f"Unsupported expected type '{expected_type}'. "
                    f"Supported values: {supported}.",
                )
            )

    if version is not None and version != SUPPORTED_TASK_SCHEMA_VERSION:
        errors.append(
            TaskFieldError(
                "version",
                f"Unsupported task schema version {version}. "
                f"Expected {SUPPORTED_TASK_SCHEMA_VERSION}.",
            )
        )

    if errors:
        raise TaskValidationError(task_path, errors)

    return ParsedTask(
        path=task_path,
        version=version,
        name=name,
        description=description,
        input=TaskInput(prompt=prompt),
        expected=TaskExpected(type=expected_type),
    )


def _is_supported_task_file(path: Path) -> bool:
    return (
        path.is_file()
        and not path.name.startswith(".")
        and path.suffix.lower() in SUPPORTED_TASK_EXTENSIONS
    )


def _field_name(key: str, parent: str | None = None) -> str:
    if parent is None:
        return key
    return f"{parent}.{key}"


def _required_mapping(
    data: dict[str, Any],
    key: str,
    errors: list[TaskFieldError],
    parent: str | None = None,
) -> dict[str, Any] | None:
    field = _field_name(key, parent)
    if key not in data:
        errors.append(TaskFieldError(field, "Missing required field."))
        return None

    value = data[key]
    if not isinstance(value, dict):
        errors.append(TaskFieldError(field, "Expected a mapping."))
        return None

    return value


def _required_int(
    data: dict[str, Any],
    key: str,
    errors: list[TaskFieldError],
    parent: str | None = None,
) -> int | None:
    field = _field_name(key, parent)
    if key not in data:
        errors.append(TaskFieldError(field, "Missing required field."))
        return None

    value = data[key]
    if not isinstance(value, int):
        errors.append(TaskFieldError(field, "Expected an integer."))
        return None

    return value


def _required_non_empty_str(
    data: dict[str, Any],
    key: str,
    errors: list[TaskFieldError],
    parent: str | None = None,
) -> str | None:
    field = _field_name(key, parent)
    if key not in data:
        errors.append(TaskFieldError(field, "Missing required field."))
        return None

    value = data[key]
    if not isinstance(value, str):
        errors.append(TaskFieldError(field, "Expected a string."))
        return None

    if not value.strip():
        errors.append(TaskFieldError(field, "Expected a non-empty string."))
        return None

    return value
