"""Task definition discovery."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from impressions.core.config import ProjectConfig, load_project_config


SUPPORTED_TASK_EXTENSIONS = frozenset({".yaml", ".yml"})


class TaskDiscoveryError(Exception):
    """Raised when task definitions cannot be discovered."""


@dataclass(frozen=True)
class TaskDefinition:
    """A discovered task definition file."""

    path: Path

    @property
    def name(self) -> str:
        """Return the task definition file name."""
        return self.path.name


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


def _is_supported_task_file(path: Path) -> bool:
    return (
        path.is_file()
        and not path.name.startswith(".")
        and path.suffix.lower() in SUPPORTED_TASK_EXTENSIONS
    )
