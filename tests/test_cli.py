import json

import pytest

from impressions.core.execution import ExecutionResult
from impressions.core.model_client import ModelResponse

from impressions import __version__
from impressions.cli import main


def test_help_command(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "usage: impressions" in captured.out
    assert "version" in captured.out


def test_no_command_shows_help(capsys):
    exit_code = main([])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "usage: impressions" in captured.out


def test_version_command(capsys):
    exit_code = main(["version"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.strip() == f"impressions {__version__}"


def test_init_command_creates_project_scaffold(tmp_path, capsys):
    exit_code = main(["init", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Initialized Impressions project" in captured.out
    assert (tmp_path / "impressions.toml").is_file()
    assert "version = 1" in (tmp_path / "impressions.toml").read_text(
        encoding="utf-8"
    )
    assert "[paths]" in (tmp_path / "impressions.toml").read_text(
        encoding="utf-8"
    )
    assert (tmp_path / "tasks" / "example.yaml").is_file()
    assert (tmp_path / "reports").is_dir()


def test_init_command_does_not_overwrite_without_confirmation(
    tmp_path, monkeypatch, capsys
):
    config = tmp_path / "impressions.toml"
    config.write_text("custom = true\n", encoding="utf-8")
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")

    exit_code = main(["init", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Initialization cancelled." in captured.out
    assert config.read_text(encoding="utf-8") == "custom = true\n"


def test_init_command_overwrites_with_confirmation(tmp_path, monkeypatch):
    config = tmp_path / "impressions.toml"
    config.write_text("custom = true\n", encoding="utf-8")
    monkeypatch.setattr("builtins.input", lambda _prompt: "yes")

    exit_code = main(["init", str(tmp_path)])

    assert exit_code == 0
    assert "[paths]" in config.read_text(encoding="utf-8")
    assert (tmp_path / "tasks" / "example.yaml").is_file()
    assert (tmp_path / "reports").is_dir()


def test_init_command_force_overwrites_existing_files(tmp_path):
    example = tmp_path / "tasks" / "example.yaml"
    example.parent.mkdir()
    example.write_text("custom: true\n", encoding="utf-8")

    exit_code = main(["init", "--force", str(tmp_path)])

    assert exit_code == 0
    assert "name: example-task" in example.read_text(encoding="utf-8")


def test_init_command_rejects_incompatible_paths(tmp_path, capsys):
    reports = tmp_path / "reports"
    reports.write_text("not a directory\n", encoding="utf-8")

    exit_code = main(["init", "--force", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "incompatible types" in captured.out
    assert reports.read_text(encoding="utf-8") == "not a directory\n"


def test_config_show_displays_loaded_configuration(tmp_path, monkeypatch, capsys):
    main(["init", str(tmp_path)])
    capsys.readouterr()
    monkeypatch.chdir(tmp_path)

    exit_code = main(["config", "show"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Project Configuration" in captured.out
    assert "Configuration file:" in captured.out
    assert "impressions.toml" in captured.out
    assert "Paths" in captured.out
    assert "tasks: tasks/" in captured.out
    assert "reports: reports/" in captured.out


def test_config_show_reports_missing_configuration(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    exit_code = main(["config", "show"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Missing configuration file" in captured.out
    assert "impressions.toml" in captured.out


def test_tasks_list_displays_discovered_tasks(tmp_path, monkeypatch, capsys):
    main(["init", str(tmp_path)])
    capsys.readouterr()
    tasks_dir = tmp_path / "tasks"
    (tasks_dir / "summarize.yaml").write_text(
        task_yaml("summarize"),
        encoding="utf-8",
    )
    (tasks_dir / "classify.yaml").write_text(
        task_yaml("classify"),
        encoding="utf-8",
    )
    (tasks_dir / ".hidden.yaml").write_text(
        task_yaml("hidden"),
        encoding="utf-8",
    )
    (tasks_dir / "notes.txt").write_text("not a task\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    exit_code = main(["tasks", "list"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.splitlines() == [
        "Discovered 3 validated task(s)",
        "",
        "- classify",
        "- example-task",
        "- summarize",
    ]


def test_tasks_list_reports_discovery_error(tmp_path, monkeypatch, capsys):
    main(["init", str(tmp_path)])
    capsys.readouterr()
    for task_file in (tmp_path / "tasks").iterdir():
        task_file.unlink()
    monkeypatch.chdir(tmp_path)

    exit_code = main(["tasks", "list"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "No task definition files found" in captured.out


def test_tasks_list_reports_validation_error(tmp_path, monkeypatch, capsys):
    main(["init", str(tmp_path)])
    capsys.readouterr()
    (tmp_path / "tasks" / "example.yaml").write_text(
        "version: 1\nname: broken\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    exit_code = main(["tasks", "list"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Invalid task definition" in captured.out
    assert "description: Missing required field." in captured.out


def test_tasks_validate_reports_all_task_statuses(tmp_path, monkeypatch, capsys):
    main(["init", str(tmp_path)])
    capsys.readouterr()
    tasks_dir = tmp_path / "tasks"
    (tasks_dir / "valid.yaml").write_text(task_yaml("valid"), encoding="utf-8")
    (tasks_dir / "invalid.yaml").write_text(
        "version: 1\nname: invalid\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    exit_code = main(["tasks", "validate"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "[ok] example.yaml" in captured.out
    assert "[ok] valid.yaml" in captured.out
    assert "[error] invalid.yaml" in captured.out
    assert "description: Missing required field." in captured.out
    assert "1 task(s) failed validation." in captured.out


def test_tasks_validate_reports_success(tmp_path, monkeypatch, capsys):
    main(["init", str(tmp_path)])
    capsys.readouterr()
    monkeypatch.chdir(tmp_path)

    exit_code = main(["tasks", "validate"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "[ok] example.yaml" in captured.out
    assert "1 task(s) validated successfully." in captured.out


def test_evaluate_command_displays_successful_evaluation_results(
    tmp_path, monkeypatch, capsys
):
    main(["init", str(tmp_path)])
    capsys.readouterr()
    tasks_dir = tmp_path / "tasks"
    (tasks_dir / "summarize.yaml").write_text(
        task_yaml("summarize"),
        encoding="utf-8",
    )
    (tasks_dir / "classify.yaml").write_text(
        task_yaml("classify"),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    exit_code = main(["evaluate"])

    captured = capsys.readouterr()

    assert exit_code == 0
    lines = captured.out.splitlines()
    assert len(lines) == 8
    assert lines[:7] == [
        "Evaluation complete.",
        "",
        "3 attempt(s) evaluated",
        "0 succeeded",
        "",
        "Results written to:",
        "",
    ]
    assert lines[7].startswith("reports/")
    assert lines[7].endswith("/")

    run_path = tmp_path / lines[7].removeprefix("reports/").rstrip("/")
    run_path = tmp_path / "reports" / run_path.name
    assert (run_path / "run.json").is_file()
    assert (run_path / "config.json").is_file()
    assert (run_path / "summary.json").is_file()

    run = json.loads((run_path / "run.json").read_text(encoding="utf-8"))
    assert run["metadata"] == {
        "command": "evaluate",
        "evaluator": "echo",
        "task_count": 3,
        "attempts_per_task": 1,
        "pass_at_k": 1,
        "metrics": {
            "task_count": 3,
            "first_attempt_success_rate": 0.0,
            "observed_pass_at_k": 0.0,
            "mean_attempts_to_success": None,
            "attempts_per_task": 1,
            "pass_at_k": 1,
        },
    }
    assert [result["task"]["name"] for result in run["results"]] == [
        "classify",
        "example-task",
        "summarize",
    ]

    summary = json.loads((run_path / "summary.json").read_text(encoding="utf-8"))
    assert summary == {
        "failed": 3,
        "succeeded": 0,
        "tasks_evaluated": 3,
    }


def test_run_command_prints_task_status_and_persists_run(tmp_path, monkeypatch, capsys):
    main(["init", str(tmp_path)])
    capsys.readouterr()
    monkeypatch.chdir(tmp_path)

    assert main(["run"]) == 0

    output = capsys.readouterr().out
    assert "[failed] example-task" in output
    assert "1 attempt(s) evaluated" in output
    assert "Results written to:" in output


def test_run_command_rejects_k_greater_than_configured_attempts(tmp_path, monkeypatch, capsys):
    main(["init", str(tmp_path)])
    capsys.readouterr()
    monkeypatch.chdir(tmp_path)

    assert main(["run", "--k", "2"]) == 1

    assert "must be a positive integer" in capsys.readouterr().out


def test_run_command_exercises_model_grader_pipeline(tmp_path, monkeypatch, capsys):
    main(["init", str(tmp_path)])
    capsys.readouterr()
    (tmp_path / "tasks" / "example.yaml").write_text(
        "\n".join([
            "version: 1", "name: add", "description: Add.", "input:",
            "  prompt: Write add.", "expected:", "  type: code", "execution:",
            "  entrypoint: solution.py", "  tests: tests/test_solution.py",
            "  timeout_seconds: 30", "",
        ]), encoding="utf-8"
    )
    tests_dir = tmp_path / "tasks" / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_solution.py").write_text("def test_add(): assert True\n", encoding="utf-8")
    config_path = tmp_path / "impressions.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8")
        .replace("attempts = 1\npass_at_k = 1", "attempts = 2\npass_at_k = 2"),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("impressions.cli.create_model_client", lambda config: FakeClient())
    monkeypatch.setattr("impressions.cli.DockerPythonExecutor", lambda **kwargs: SequenceExecutor())

    assert main(["run"]) == 0
    output = capsys.readouterr().out
    assert "[passed] add" in output
    run_path = next((tmp_path / "reports").iterdir())
    run = json.loads((run_path / "run.json").read_text(encoding="utf-8"))
    assert run["metadata"]["evaluator"] == "llm-pytest"
    assert len(run["results"]) == 2
    assert run["results"][0]["metadata"]["attempt"] == 1
    assert run["results"][0]["metadata"]["failure_classification"]["category"] == "test_failure"
    assert run["results"][1]["metadata"]["passed"] is True
    assert run["metadata"]["metrics"]["observed_pass_at_k"] == 1.0
    config = json.loads((run_path / "config.json").read_text(encoding="utf-8"))
    assert config["model"]["provider"] == "openai"


def test_report_command_reads_persisted_run_without_evaluating(tmp_path, monkeypatch, capsys):
    main(["init", str(tmp_path)])
    capsys.readouterr()
    monkeypatch.chdir(tmp_path)
    assert main(["evaluate"]) == 0
    capsys.readouterr()
    run_path = next((tmp_path / "reports").iterdir())
    monkeypatch.setattr(
        "impressions.cli.create_model_client",
        lambda _config: pytest.fail("report must not create a model client"),
    )

    assert main(["report", str(run_path)]) == 0

    output = capsys.readouterr().out
    assert f"Run: {run_path.name}" in output
    assert "Tasks:" in output
    assert "Summary:" in output
    assert "Pass@1: 0.0" in output


def test_report_command_reports_missing_artifact(tmp_path, capsys):
    assert main(["report", str(tmp_path / "missing")]) == 1

    assert "Run path is not a directory" in capsys.readouterr().out


def test_compare_command_reads_persisted_runs_without_evaluating(tmp_path, monkeypatch, capsys):
    main(["init", str(tmp_path)])
    capsys.readouterr()
    monkeypatch.chdir(tmp_path)
    assert main(["evaluate"]) == 0
    capsys.readouterr()
    first_run = next((tmp_path / "reports").iterdir())
    assert main(["evaluate"]) == 0
    capsys.readouterr()
    second_run = max((tmp_path / "reports").iterdir())
    monkeypatch.setattr(
        "impressions.cli.create_model_client",
        lambda _config: pytest.fail("compare must not create a model client"),
    )

    assert main(["compare", str(first_run), str(second_run)]) == 0

    output = capsys.readouterr().out
    assert f"Baseline:\n  Run: {first_run.name}" in output
    assert f"Candidate:\n  Run: {second_run.name}" in output
    assert "Metric deltas" in output


class FakeClient:
    def generate(self, request):
        return ModelResponse(text="def add(a, b): return a + b", model="fake")


class SequenceExecutor:
    def __init__(self):
        self.results = iter([
            ExecutionResult("1 failed", "", 1, False),
            ExecutionResult("1 passed", "", 0, False),
        ])

    def execute(self, code, **kwargs):
        return next(self.results)


def task_yaml(name: str) -> str:
    return f"""\
version: 1
name: {name}
description: Test task.
input:
  prompt: Say hello.
expected:
  type: text
"""
