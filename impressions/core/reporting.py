"""Run artifact persistence for evaluation reports."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping


REPORT_SCHEMA_VERSION = 1


class RunRegistryError(Exception):
    """Raised when a run artifact cannot be written."""


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

    if isinstance(value, Mapping):
        return {str(key): _to_json_data(item) for key, item in value.items()}

    if isinstance(value, tuple | list):
        return [_to_json_data(item) for item in value]

    return value
