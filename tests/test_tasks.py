from pathlib import Path

import pytest

from impressions.core.config import load_project_config
from impressions.core.tasks import (
    TaskDefinition,
    TaskDiscoveryError,
    discover_tasks,
    discover_tasks_from_config,
)


def write_config(root: Path, tasks_path: str = "tasks") -> None:
    (root / "impressions.toml").write_text(
        f"""\
version = 1

[paths]
tasks = "{tasks_path}"
reports = "reports"
""",
        encoding="utf-8",
    )


def test_discover_tasks_returns_supported_files_in_deterministic_order(tmp_path):
    write_config(tmp_path)
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "summarize.yaml").write_text("id: summarize\n", encoding="utf-8")
    (tasks_dir / "classify.yaml").write_text("id: classify\n", encoding="utf-8")
    (tasks_dir / "sentiment.yml").write_text("id: sentiment\n", encoding="utf-8")

    tasks = discover_tasks(tmp_path)

    assert tasks == [
        TaskDefinition(path=tasks_dir / "classify.yaml"),
        TaskDefinition(path=tasks_dir / "sentiment.yml"),
        TaskDefinition(path=tasks_dir / "summarize.yaml"),
    ]
    assert [task.name for task in tasks] == [
        "classify.yaml",
        "sentiment.yml",
        "summarize.yaml",
    ]


def test_discover_tasks_ignores_hidden_and_unsupported_files(tmp_path):
    write_config(tmp_path)
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "valid.yaml").write_text("id: valid\n", encoding="utf-8")
    (tasks_dir / ".hidden.yaml").write_text("id: hidden\n", encoding="utf-8")
    (tasks_dir / "notes.txt").write_text("not a task\n", encoding="utf-8")
    (tasks_dir / "nested.yaml").mkdir()

    tasks = discover_tasks(tmp_path)

    assert [task.name for task in tasks] == ["valid.yaml"]


def test_discover_tasks_from_config_uses_loaded_configuration(tmp_path):
    write_config(tmp_path)
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "example.yaml").write_text("id: example\n", encoding="utf-8")
    config = load_project_config(tmp_path)

    tasks = discover_tasks_from_config(config)

    assert [task.path for task in tasks] == [tasks_dir / "example.yaml"]


def test_discover_tasks_reports_missing_tasks_directory(tmp_path):
    write_config(tmp_path)

    with pytest.raises(TaskDiscoveryError, match="Tasks directory does not exist"):
        discover_tasks(tmp_path)


def test_discover_tasks_reports_tasks_path_that_is_not_directory(tmp_path):
    write_config(tmp_path)
    (tmp_path / "tasks").write_text("not a directory\n", encoding="utf-8")

    with pytest.raises(TaskDiscoveryError, match="not a directory"):
        discover_tasks(tmp_path)


def test_discover_tasks_reports_no_supported_task_files(tmp_path):
    write_config(tmp_path)
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "notes.txt").write_text("not a task\n", encoding="utf-8")

    with pytest.raises(TaskDiscoveryError, match="No task definition files found"):
        discover_tasks(tmp_path)
