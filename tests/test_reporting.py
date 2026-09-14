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
    load_persisted_run,
    render_terminal_report,
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


def test_load_and_render_persisted_run(tmp_path):
    registry = RunRegistry(tmp_path, clock=fixed_clock)
    run_path = registry.write(
        metadata={
            "task_count": 1,
            "attempts_per_task": 2,
            "metrics": {
                "first_attempt_success_rate": 0.0,
                "observed_pass_at_k": 1.0,
                "mean_attempts_to_success": 2.0,
            },
        },
        results=[
            {
                "task": {"name": "add"},
                "metadata": {
                    "attempt": 1,
                    "passed": False,
                    "passed_tests": 0,
                    "total_tests": 1,
                    "failure_classification": {"category": "test_failure"},
                },
            },
            {"task": {"name": "add"}, "metadata": {"attempt": 2, "passed": True}},
        ],
        summary={"tasks_evaluated": 2, "succeeded": 1},
        config={"model": {"provider": "openai", "model": "test-model"}},
    )

    report = render_terminal_report(load_persisted_run(run_path))

    assert report == "\n".join([
        "Run: 2026-07-18_001",
        "Timestamp: 2026-07-18T12:30:00+00:00",
        "Model: openai / test-model",
        "Tasks: 1",
        "Attempts per task: 2",
        "",
        "Tasks:",
        "  [failed] add (attempt 1) — tests 0/1, failure test_failure",
        "  [passed] add (attempt 2)",
        "",
        "Summary:",
        "  Passed attempts: 1 / 2",
        "  Pass@1: 0.0",
        "  Observed pass@k: 1.0",
        "  Mean attempts to success: 2.0",
    ])


def test_load_persisted_run_rejects_malformed_artifacts(tmp_path):
    run_path = tmp_path / "broken"
    run_path.mkdir()
    (run_path / "run.json").write_text("not-json", encoding="utf-8")
    (run_path / "config.json").write_text("{}", encoding="utf-8")
    (run_path / "summary.json").write_text("{}", encoding="utf-8")

    with pytest.raises(RunRegistryError, match="Unable to read run artifact"):
        load_persisted_run(run_path)


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
