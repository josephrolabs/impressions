"""Command-line interface for Impressions."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from impressions import __version__
from impressions.core.config import ConfigError, load_project_config
from impressions.core.code_evaluator import CodeTaskEvaluator
from impressions.core.docker_executor import DockerPythonExecutor, PYTEST_IMAGE
from impressions.core.evaluation import (
    EchoEvaluator,
    EvaluationEngine,
    EvaluationEngineError,
    EvaluationResult,
)
from impressions.core.llm_evaluator import LLMEvaluator
from impressions.core.model_factory import create_model_client
from impressions.core.prompt_builder import PromptBuilder
from impressions.core.pytest_grader import PytestCodeGrader
from impressions.core.pytest_grader import GradingError
from impressions.core.scoring import MultiAttemptEvaluator, calculate_reliability_metrics
from impressions.core.reporting import (
    RunMetadata,
    RunRegistry,
    RunRegistryError,
    RunSummary,
)
from impressions.core.tasks import (
    TaskDiscoveryError,
    TaskValidationError,
    discover_tasks,
    load_task,
    load_tasks,
    load_tasks_from_config,
)


DEFAULT_CONFIG = """\
version = 1

[paths]
tasks = "tasks"
reports = "reports"

[model]
provider = "openai"
model = "gpt-5"
timeout = 30

[credentials]
api_key_env = "OPENAI_API_KEY"

[evaluation]
attempts = 1
pass_at_k = 1
"""

EXAMPLE_TASK = """\
version: 1

name: example-task
description: Summarize the supplied article.

input:
  prompt: |
    Write a concise summary of the supplied article.

expected:
  type: text
"""


def build_parser() -> argparse.ArgumentParser:
    """Create the top-level CLI parser."""
    parser = argparse.ArgumentParser(
        prog="impressions",
        description="Evaluation harness for measuring AI-generated code.",
    )
    subparsers = parser.add_subparsers(dest="command")

    version_parser = subparsers.add_parser(
        "version",
        help="Show the installed Impressions version.",
    )
    version_parser.set_defaults(handler=show_version)

    init_parser = subparsers.add_parser(
        "init",
        help="Create a new Impressions project scaffold.",
    )
    init_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Directory to initialize. Defaults to the current directory.",
    )
    init_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Overwrite existing scaffold files without prompting.",
    )
    init_parser.set_defaults(handler=init_project)

    config_parser = subparsers.add_parser(
        "config",
        help="Inspect Impressions project configuration.",
    )
    config_subparsers = config_parser.add_subparsers(dest="config_command")

    config_show_parser = config_subparsers.add_parser(
        "show",
        help="Display the loaded project configuration.",
    )
    config_show_parser.set_defaults(handler=show_config)

    tasks_parser = subparsers.add_parser(
        "tasks",
        help="Inspect Impressions task definitions.",
    )
    tasks_subparsers = tasks_parser.add_subparsers(dest="tasks_command")

    tasks_list_parser = tasks_subparsers.add_parser(
        "list",
        help="List discovered task definitions.",
    )
    tasks_list_parser.set_defaults(handler=list_tasks)

    tasks_validate_parser = tasks_subparsers.add_parser(
        "validate",
        help="Validate discovered task definitions.",
    )
    tasks_validate_parser.set_defaults(handler=validate_tasks)

    evaluate_parser = subparsers.add_parser(
        "evaluate",
        help="Evaluate discovered task definitions.",
    )
    evaluate_parser.set_defaults(handler=evaluate_tasks)

    run_parser = subparsers.add_parser(
        "run", help="Run the complete model-to-grading evaluation workflow."
    )
    run_parser.add_argument("--tasks", type=Path, help="Override the configured tasks directory.")
    run_parser.add_argument("--k", type=int, help="Override the configured observed pass@k value.")
    run_parser.set_defaults(handler=run_tasks)

    return parser


def show_version(_args: argparse.Namespace) -> int:
    """Print the current package version."""
    print(f"impressions {__version__}")
    return 0


def init_project(args: argparse.Namespace) -> int:
    """Create the default project scaffold."""
    root = Path(args.path)
    files = {
        root / "impressions.toml": DEFAULT_CONFIG,
        root / "tasks" / "example.yaml": EXAMPLE_TASK,
    }
    directories = [root / "tasks", root / "reports"]

    invalid_paths = [
        path
        for path in [root, *directories]
        if path.exists() and not path.is_dir()
    ]
    invalid_paths.extend(path for path in files if path.exists() and path.is_dir())
    if invalid_paths:
        path_list = "\n".join(f"  - {path}" for path in invalid_paths)
        print("Cannot initialize because these paths have incompatible types:")
        print(path_list)
        return 1

    existing_files = [path for path in files if path.exists()]

    if existing_files and not args.force:
        file_list = "\n".join(f"  - {path}" for path in existing_files)
        print("The following files already exist:")
        print(file_list)
        if not confirm("Overwrite them? [y/N] "):
            print("Initialization cancelled.")
            return 1

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    print(f"Initialized Impressions project in {root.resolve()}")
    return 0


def show_config(_args: argparse.Namespace) -> int:
    """Print the current project configuration."""
    try:
        config = load_project_config()
    except ConfigError as exc:
        print(exc)
        return 1

    print("Project Configuration")
    print()
    print("Configuration file:")
    print(f"  {config.file_path}")
    print()
    print("Paths")
    print(f"  tasks: {_format_directory(config.paths.tasks)}")
    print(f"  reports: {_format_directory(config.paths.reports)}")
    print()
    print("Model")
    print(f"  provider: {config.model.provider}")
    print(f"  model: {config.model.model}")
    print(f"  timeout: {config.model.timeout}")
    print(f"  api_key_env: {config.credentials.api_key_env}")
    print()
    print("Evaluation")
    print(f"  attempts: {config.evaluation.attempts}")
    print(f"  pass_at_k: {config.evaluation.pass_at_k}")
    return 0


def list_tasks(_args: argparse.Namespace) -> int:
    """Print validated task definitions."""
    try:
        tasks = load_tasks()
    except (ConfigError, TaskDiscoveryError, TaskValidationError) as exc:
        print(exc)
        return 1

    print(f"Discovered {len(tasks)} validated task(s)")
    print()
    for task in tasks:
        print(f"- {task.name}")
    return 0


def validate_tasks(_args: argparse.Namespace) -> int:
    """Validate discovered task definitions."""
    try:
        task_files = discover_tasks()
    except (ConfigError, TaskDiscoveryError) as exc:
        print(exc)
        return 1

    validation_errors: list[TaskValidationError] = []
    for task_file in task_files:
        try:
            load_task(task_file.path)
        except TaskValidationError as exc:
            validation_errors.append(exc)
            print(f"[error] {task_file.name}")
            for error in exc.errors:
                print(f"  {error.field}: {error.message}")
        else:
            print(f"[ok] {task_file.name}")

    print()
    if validation_errors:
        print(f"{len(validation_errors)} task(s) failed validation.")
        return 1

    print(f"{len(task_files)} task(s) validated successfully.")
    return 0


def evaluate_tasks(_args: argparse.Namespace) -> int:
    """Run the legacy evaluation command."""
    return _run_workflow(_args, command="evaluate", show_task_status=False)


def run_tasks(args: argparse.Namespace) -> int:
    """Run the primary end-to-end model evaluation workflow."""
    return _run_workflow(args, command="run", show_task_status=True)


def _run_workflow(args: argparse.Namespace, *, command: str, show_task_status: bool) -> int:
    """Evaluate discovered and validated task definitions."""
    try:
        config = load_project_config()
        if getattr(args, "tasks", None) is not None:
            tasks_path = args.tasks if args.tasks.is_absolute() else config.root / args.tasks
            config = replace(config, paths=replace(config.paths, tasks=tasks_path))
        if getattr(args, "k", None) is not None:
            if args.k <= 0 or args.k > config.evaluation.attempts:
                raise ConfigError("--k must be a positive integer not exceeding configured attempts.")
            config = replace(config, evaluation=replace(config.evaluation, pass_at_k=args.k))
        tasks = load_tasks_from_config(config)
        if any(task.execution is not None for task in tasks):
            evaluator = CodeTaskEvaluator(
                llm_evaluator=LLMEvaluator(PromptBuilder(), create_model_client(config)),
                grader=PytestCodeGrader(DockerPythonExecutor(image=PYTEST_IMAGE)),
            )
            evaluator_name = "llm-pytest"
        else:
            evaluator = EchoEvaluator()
            evaluator_name = "echo"
        attempt_results = MultiAttemptEvaluator(
            evaluator, attempts=config.evaluation.attempts
        ).evaluate_all(tasks)
        metrics = calculate_reliability_metrics(
            attempt_results, pass_at_k=config.evaluation.pass_at_k
        )
    except (ConfigError, TaskDiscoveryError, TaskValidationError) as exc:
        print(exc)
        return 1
    except (EvaluationEngineError, GradingError) as exc:
        print(exc)
        return 1
    try:
        results = [
            EvaluationResult(
                task=attempt.result.task,
                output=attempt.result.output,
                metadata={**attempt.result.metadata, "attempt": attempt.attempt, "passed": attempt.succeeded},
            )
            for task_result in attempt_results
            for attempt in task_result.attempts
        ]
        succeeded = sum(attempt.succeeded for task_result in attempt_results for attempt in task_result.attempts)
        run_path = RunRegistry(config.paths.reports).write(
            metadata={
                "command": command,
                "evaluator": evaluator_name,
                "task_count": len(tasks),
                "attempts_per_task": config.evaluation.attempts,
                "pass_at_k": config.evaluation.pass_at_k,
                "metrics": metrics,
            },
            results=results,
            summary=RunSummary(
                tasks_evaluated=len(results),
                succeeded=succeeded,
                failed=len(results) - succeeded,
            ),
            config={
                "file_path": config.file_path,
                "version": config.version,
                "paths": {
                    "tasks": config.paths.tasks,
                    "reports": config.paths.reports,
                },
                "evaluation": {
                    "attempts": config.evaluation.attempts,
                    "pass_at_k": config.evaluation.pass_at_k,
                },
                "model": {
                    "provider": config.model.provider,
                    "model": config.model.model,
                    "timeout": config.model.timeout,
                },
            },
        )
    except RunRegistryError as exc:
        print(exc)
        return 1

    print("Evaluation complete.")
    print()
    if show_task_status:
        for task_result in attempt_results:
            passed = any(attempt.succeeded for attempt in task_result.attempts)
            print(f"[{ 'passed' if passed else 'failed' }] {task_result.task.name}")
        print()
    print(f"{len(results)} attempt(s) evaluated")
    print(f"{succeeded} succeeded")
    print()
    print("Results written to:")
    print()
    print(_format_directory(run_path))
    return 0


def _format_directory(path: Path) -> str:
    value = path.as_posix()
    if not value.endswith("/"):
        value = f"{value}/"
    return value


def confirm(prompt: str) -> bool:
    """Return True when the user confirms an interactive prompt."""
    try:
        response = input(prompt)
    except EOFError:
        return False
    return response.strip().lower() in {"y", "yes"}


def main(argv: list[str] | None = None) -> int:
    """Run the Impressions command-line interface."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "handler"):
        parser.print_help()
        return 0

    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
