"""Run artifact persistence for evaluation reports."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping


REPORT_SCHEMA_VERSION = 1


class RunRegistryError(Exception):
    """Raised when a run artifact cannot be written or read."""


@dataclass(frozen=True)
class RunMetadata:
    """Metadata describing an evaluation run."""

    command: str
    evaluator: str
    task_count: int


@dataclass(frozen=True)
class RunSummary:
    """Summary counts for an evaluation run."""

    tasks_evaluated: int
    succeeded: int
    failed: int = 0


@dataclass(frozen=True)
class PersistedRun:
    """Validated, immutable view of the artifacts produced for one evaluation run."""

    path: Path
    run: Mapping[str, Any]
    config: Mapping[str, Any]
    summary: Mapping[str, Any]


@dataclass(frozen=True)
class RunRegistry:
    """Persist evaluation runs as timestamped report artifacts."""

    report_dir: Path | str
    clock: Callable[[], datetime] | None = None

    def write(
        self,
        *,
        metadata: RunMetadata | Mapping[str, Any],
        results: Iterable[Any],
        summary: RunSummary | Mapping[str, Any],
        config: Mapping[str, Any] | None = None,
    ) -> Path:
        """Write a run directory and return its path."""
        created_at = self._now()
        run_path = self._create_run_path(created_at)
        result_data = [_to_json_data(result) for result in results]

        run_payload = {
            "schema_version": REPORT_SCHEMA_VERSION,
            "run_id": run_path.name,
            "created_at": created_at.isoformat(),
            "metadata": _to_json_data(metadata),
            "results": result_data,
        }

        try:
            _write_json(run_path / "run.json", run_payload)
            _write_json(run_path / "config.json", _to_json_data(config or {}))
            _write_json(run_path / "summary.json", _to_json_data(summary))
        except OSError as exc:
            raise RunRegistryError(f"Failed to write run artifacts: {exc}") from exc
        except TypeError as exc:
            raise RunRegistryError(f"Run artifacts are not JSON serializable: {exc}") from exc

        return run_path

    def _now(self) -> datetime:
        if self.clock is None:
            return datetime.now(timezone.utc)

        value = self.clock()
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    def _create_run_path(self, created_at: datetime) -> Path:
        report_dir = Path(self.report_dir)
        prefix = created_at.strftime("%Y-%m-%d")

        try:
            report_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise RunRegistryError(f"Failed to create report directory: {exc}") from exc

        for index in range(1, 1000):
            run_path = report_dir / f"{prefix}_{index:03d}"
            try:
                run_path.mkdir()
            except FileExistsError:
                continue
            except OSError as exc:
                raise RunRegistryError(f"Failed to create run directory: {exc}") from exc
            return run_path

        raise RunRegistryError(
            f"Unable to allocate a run ID for {prefix}; tried 999 run directories."
        )


def load_persisted_run(path: Path | str) -> PersistedRun:
    """Load and validate the three immutable artifacts for a persisted run."""
    run_path = Path(path)
    if not run_path.is_dir():
        raise RunRegistryError(f"Run path is not a directory: {run_path}")

    run = _read_json_object(run_path / "run.json")
    config = _read_json_object(run_path / "config.json")
    summary = _read_json_object(run_path / "summary.json")
    if run.get("schema_version") != REPORT_SCHEMA_VERSION:
        raise RunRegistryError(
            f"Unsupported run schema version in {run_path / 'run.json'}: "
            f"{run.get('schema_version')!r}."
        )
    for field in ("run_id", "created_at"):
        if not isinstance(run.get(field), str):
            raise RunRegistryError(f"Run artifact is missing a string {field!r} field.")
    if not isinstance(run.get("metadata"), Mapping):
        raise RunRegistryError("Run artifact is missing a metadata object.")
    if not isinstance(run.get("results"), list):
        raise RunRegistryError("Run artifact is missing a results list.")
    return PersistedRun(path=run_path, run=run, config=config, summary=summary)


def render_terminal_report(persisted_run: PersistedRun) -> str:
    """Render a deterministic, read-only terminal report for one persisted run."""
    run = persisted_run.run
    metadata = run["metadata"]
    model = persisted_run.config.get("model", {})
    metrics = metadata.get("metrics", {})
    if not isinstance(model, Mapping):
        model = {}
    if not isinstance(metrics, Mapping):
        metrics = {}

    lines = [
        f"Run: {run['run_id']}",
        f"Timestamp: {run['created_at']}",
        f"Model: {model.get('provider', 'unknown')} / {model.get('model', 'unknown')}",
        f"Tasks: {metadata.get('task_count', persisted_run.summary.get('tasks_evaluated', 0))}",
        f"Attempts per task: {metadata.get('attempts_per_task', 'unknown')}",
        "",
        "Tasks:",
    ]
    for result in run["results"]:
        if not isinstance(result, Mapping):
            raise RunRegistryError("Run artifact contains a non-object result.")
        task = result.get("task", {})
        result_metadata = result.get("metadata", {})
        if not isinstance(task, Mapping) or not isinstance(result_metadata, Mapping):
            raise RunRegistryError("Run artifact contains a result with invalid task or metadata.")
        status = "passed" if result_metadata.get("passed") is True else "failed"
        name = task.get("name", "unknown")
        attempt = result_metadata.get("attempt", 1)
        detail = _result_detail(result_metadata)
        lines.append(f"  [{status}] {name} (attempt {attempt}){detail}")

    lines.extend([
        "",
        "Summary:",
        f"  Passed attempts: {persisted_run.summary.get('succeeded', 0)} / {persisted_run.summary.get('tasks_evaluated', 0)}",
        f"  Pass@1: {_format_metric(metrics.get('first_attempt_success_rate'))}",
        f"  Observed pass@k: {_format_metric(metrics.get('observed_pass_at_k'))}",
        f"  Mean attempts to success: {_format_metric(metrics.get('mean_attempts_to_success'))}",
    ])
    return "\n".join(lines)


def _read_json_object(path: Path) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RunRegistryError(f"Run artifact is missing: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise RunRegistryError(f"Unable to read run artifact {path}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise RunRegistryError(f"Run artifact must contain a JSON object: {path}")
    return payload


def _result_detail(metadata: Mapping[str, Any]) -> str:
    passed = metadata.get("passed_tests")
    total = metadata.get("total_tests")
    details: list[str] = []
    if isinstance(passed, int) and isinstance(total, int):
        details.append(f"tests {passed}/{total}")
    classification = metadata.get("failure_classification")
    if isinstance(classification, Mapping) and isinstance(classification.get("category"), str):
        details.append(f"failure {classification['category']}")
    return f" — {', '.join(details)}" if details else ""


def _format_metric(value: Any) -> str:
    return "n/a" if value is None else str(value)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        f"{json.dumps(payload, indent=2, sort_keys=True)}\n",
        encoding="utf-8",
    )


def _to_json_data(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _to_json_data(asdict(value))

    if isinstance(value, Path):
        return value.as_posix()

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, Mapping):
        return {str(key): _to_json_data(item) for key, item in value.items()}

    if isinstance(value, tuple | list):
        return [_to_json_data(item) for item in value]

    return value
