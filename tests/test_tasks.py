from pathlib import Path

import pytest

from impressions.core.config import load_project_config
from impressions.core.tasks import (
    ParsedTask,
    TaskDefinition,
    TaskDiscoveryError,
    TaskExpected,
    TaskInput,
    TaskValidationError,
    discover_tasks,
    discover_tasks_from_config,
    load_task,
    load_tasks,
    parse_task_data,
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


def test_load_task_parses_valid_yaml_task_definition(tmp_path):
    task_path = tmp_path / "summarize.yaml"
    task_path.write_text(valid_task_yaml("summarize-article"), encoding="utf-8")

    task = load_task(task_path)

    assert task == ParsedTask(
        path=task_path,
        version=1,
        name="summarize-article",
        description="Test task.",
        input=TaskInput(prompt="Say hello."),
        expected=TaskExpected(type="text"),
    )


def test_load_tasks_discovers_and_parses_valid_task_definitions(tmp_path):
    write_config(tmp_path)
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "summarize.yaml").write_text(
        valid_task_yaml("summarize"),
        encoding="utf-8",
    )
    (tasks_dir / "classify.yml").write_text(
        valid_task_yaml("classify"),
        encoding="utf-8",
    )

    tasks = load_tasks(tmp_path)

    assert [task.name for task in tasks] == ["classify", "summarize"]


def test_parse_task_data_reports_missing_required_fields(tmp_path):
    with pytest.raises(TaskValidationError) as exc_info:
        parse_task_data({"version": 1, "name": "missing"}, tmp_path / "task.yaml")

    errors = exc_info.value.errors

    assert errors == [
        field_error("description", "Missing required field."),
        field_error("input", "Missing required field."),
        field_error("expected", "Missing required field."),
    ]
    assert "task.yaml" in str(exc_info.value)
    assert "description: Missing required field." in str(exc_info.value)


def test_parse_task_data_reports_field_type_errors(tmp_path):
    with pytest.raises(TaskValidationError) as exc_info:
        parse_task_data(
            {
                "version": "1",
                "name": 10,
                "description": "",
                "input": {"prompt": ["hello"]},
                "expected": {"type": "image"},
            },
            tmp_path / "task.yaml",
        )

    errors = exc_info.value.errors

    assert errors == [
        field_error("version", "Expected an integer."),
        field_error("name", "Expected a string."),
        field_error("description", "Expected a non-empty string."),
        field_error("input.prompt", "Expected a string."),
        field_error(
            "expected.type",
            "Unsupported expected type 'image'. Supported values: text.",
        ),
    ]


def test_parse_task_data_reports_nested_mapping_type_errors(tmp_path):
    with pytest.raises(TaskValidationError) as exc_info:
        parse_task_data(
            {
                "version": 1,
                "name": "task",
                "description": "Task.",
                "input": "prompt",
                "expected": "text",
            },
            tmp_path / "task.yaml",
        )

    errors = exc_info.value.errors

    assert errors == [
        field_error("input", "Expected a mapping."),
        field_error("expected", "Expected a mapping."),
    ]


def test_parse_task_data_reports_unsupported_schema_version(tmp_path):
    data = {
        "version": 2,
        "name": "task",
        "description": "Task.",
        "input": {"prompt": "Say hello."},
        "expected": {"type": "text"},
    }

    with pytest.raises(TaskValidationError) as exc_info:
        parse_task_data(data, tmp_path / "task.yaml")

    assert exc_info.value.errors == [
        field_error("version", "Unsupported task schema version 2. Expected 1."),
    ]


def test_parse_task_data_rejects_non_mapping_document(tmp_path):
    with pytest.raises(TaskValidationError) as exc_info:
        parse_task_data(["not", "a", "mapping"], tmp_path / "task.yaml")

    assert exc_info.value.errors == [
        field_error("<document>", "Expected a YAML mapping."),
    ]


def test_load_task_reports_yaml_syntax_error(tmp_path):
    task_path = tmp_path / "broken.yaml"
    task_path.write_text("version: [\n", encoding="utf-8")

    with pytest.raises(TaskValidationError) as exc_info:
        load_task(task_path)

    assert exc_info.value.errors[0].field == "<document>"
    assert "Invalid YAML syntax" in exc_info.value.errors[0].message


def field_error(field: str, message: str):
    from impressions.core.tasks import TaskFieldError

    return TaskFieldError(field, message)


def valid_task_yaml(name: str) -> str:
    return f"""\
version: 1
name: {name}
description: Test task.
input:
  prompt: Say hello.
expected:
  type: text
"""
