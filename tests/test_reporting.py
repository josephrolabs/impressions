import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

from impressions.core import RunRegistry as PublicRunRegistry
from impressions.core import RunRegistryError as PublicRunRegistryError
from impressions.core import RunMetadata as PublicRunMetadata
from impressions.core import RunSummary as PublicRunSummary
from impressions.core.evaluation import EvaluationResult
from impressions.core.reporting import (
    RunMetadata,
    RunRegistry,
    RunRegistryError,
    RunSummary,
)
from impressions.core.tasks import Task, TaskExpected, TaskInput


def test_run_registry_writes_timestamped_artifacts(tmp_path):
    registry = RunRegistry(tmp_path, clock=fixed_clock)
    task = make_task("summarize")

    run_path = registry.write(
        metadata=RunMetadata(command="evaluate", evaluator="echo", task_count=1),
        results=[EvaluationResult(task=task, output="Say hello.")],
        summary=RunSummary(tasks_evaluated=1, succeeded=1),
        config={"paths": {"tasks": tmp_path / "tasks"}},
    )

    assert run_path == tmp_path / "2026-07-18_001"
    assert (run_path / "run.json").is_file()
    assert (run_path / "config.json").is_file()
    assert (run_path / "summary.json").is_file()

    run = read_json(run_path / "run.json")
    assert run["schema_version"] == 1
    assert run["run_id"] == "2026-07-18_001"
    assert run["created_at"] == "2026-07-18T12:30:00+00:00"
    assert run["metadata"] == {
        "command": "evaluate",
        "evaluator": "echo",
        "task_count": 1,
    }
    assert run["results"][0]["task"]["path"] == "tasks/summarize.yaml"
    assert run["results"][0]["task"]["name"] == "summarize"
    assert run["results"][0]["output"] == "Say hello."

    config = read_json(run_path / "config.json")
    assert config == {"paths": {"tasks": str(tmp_path / "tasks")}}

    summary = read_json(run_path / "summary.json")
    assert summary == {
        "failed": 0,
        "succeeded": 1,
        "tasks_evaluated": 1,
    }


def test_run_registry_allocates_next_available_run_id(tmp_path):
    (tmp_path / "2026-07-18_001").mkdir()
    registry = RunRegistry(tmp_path, clock=fixed_clock)

    run_path = registry.write(
        metadata={"command": "evaluate"},
        results=[],
        summary={"tasks_evaluated": 0, "succeeded": 0},
    )

    assert run_path == tmp_path / "2026-07-18_002"


def test_run_registry_wraps_json_serialization_errors(tmp_path):
    registry = RunRegistry(tmp_path, clock=fixed_clock)

    with pytest.raises(RunRegistryError, match="JSON serializable"):
        registry.write(
            metadata={"bad": object()},
            results=[],
            summary={"tasks_evaluated": 0, "succeeded": 0},
        )


def test_run_registry_serializes_nested_dataclasses(tmp_path):
    registry = RunRegistry(tmp_path, clock=fixed_clock)

    run_path = registry.write(
        metadata={"custom": Nested(path=Path("example.txt"))},
        results=[],
        summary={"tasks_evaluated": 0, "succeeded": 0},
    )

    run = read_json(run_path / "run.json")
    assert run["metadata"]["custom"] == {"path": "example.txt"}


def test_reporting_api_exports_from_core_package():
    assert PublicRunRegistry is RunRegistry
    assert PublicRunRegistryError is RunRegistryError
    assert PublicRunMetadata is RunMetadata
    assert PublicRunSummary is RunSummary


@dataclass(frozen=True)
class Nested:
    path: Path


def fixed_clock() -> datetime:
    return datetime(2026, 7, 18, 12, 30, tzinfo=timezone.utc)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def make_task(name: str) -> Task:
    return Task(
        path=Path(f"tasks/{name}.yaml"),
        version=1,
        name=name,
        description="Test task.",
        input=TaskInput(prompt="Say hello."),
        expected=TaskExpected(type="text"),
    )
