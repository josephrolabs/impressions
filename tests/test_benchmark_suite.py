"""Integrity checks for the curated MVP benchmark assets."""

from collections import Counter
from pathlib import Path
import shutil
import subprocess
import sys

from impressions.core.tasks import load_task


BENCHMARK_ROOT = Path(__file__).parents[1] / "benchmarks" / "mvp"


def test_mvp_benchmark_composition_and_metadata():
    tasks = [load_task(path) for path in sorted((BENCHMARK_ROOT / "tasks").glob("*.yaml"))]

    assert len(tasks) == 9
    assert Counter(task.metadata.difficulty for task in tasks) == {"easy": 3, "medium": 4, "hard": 2}
    assert {task.metadata.category for task in tasks} >= {
        "function_generation", "bug_fix", "error_handling", "refactor", "test_writing", "multi_file_repair",
    }
    assert all(task.execution is not None and (task.path.parent / task.execution.tests).is_file() for task in tasks)


def test_all_canonical_solutions_pass_their_task_local_pytest_suites(tmp_path):
    for task in [load_task(path) for path in sorted((BENCHMARK_ROOT / "tasks").glob("*.yaml"))]:
        work = tmp_path / task.name
        work.mkdir()
        reference = BENCHMARK_ROOT / "reference_solutions" / f"{task.path.stem}.py"
        entrypoint = work / task.execution.entrypoint
        entrypoint.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(reference, entrypoint)
        test_path = work / task.execution.tests
        test_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(task.path.parent / task.execution.tests, test_path)
        for relative_path in task.execution.files:
            destination = work / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(task.path.parent / relative_path, destination)
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", task.execution.tests],
            cwd=work, text=True, capture_output=True, check=False,
        )
        assert completed.returncode == 0, f"{task.name}: {completed.stdout}\n{completed.stderr}"


def test_incorrect_fixture_fails_a_benchmark_suite(tmp_path):
    task = load_task(BENCHMARK_ROOT / "tasks" / "reverse_words.yaml")
    (tmp_path / "solution.py").write_text("def solve(text): return text\n", encoding="utf-8")
    shutil.copy(task.path.parent / task.execution.tests, tmp_path / "test_solution.py")

    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "test_solution.py"],
        cwd=tmp_path, text=True, capture_output=True, check=False,
    )
    assert completed.returncode != 0


def test_refactor_reference_explicitly_uses_the_supplied_legacy_fixture():
    reference = (BENCHMARK_ROOT / "reference_solutions" / "lru_cache.py").read_text(encoding="utf-8")

    assert "class LRUCache(LegacyCache)" in reference
