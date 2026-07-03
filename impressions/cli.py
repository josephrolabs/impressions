"""Command-line interface for Impressions."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import List

from impressions import __version__


def build_parsers() -> argparse.ArgumentParser:
    """Create the top-level CLI parser."""
    parser = argparse.ArgumentParser(
        prog="impressions",
        description=(
            "Evaluation harness for measuring AI-generated code."
        ),
    )

    subparsers = parser.add_subparsers(dest="command")

    # version
    version_parser = subparsers.add_parser("version", help="Show the installed Impressions version.")
    version_parser.set_defaults(handler=show_version)

    # init
    init_parser = subparsers.add_parser("init", help="Bootstrap a new Impressions project in the current directory.")
    init_parser.add_argument("--force", "-f", action="store_true", help="Overwrite existing files without prompting.")
    init_parser.set_defaults(handler=handle_init)

    return parser


def show_version(_args: argparse.Namespace) -> int:
    """Print the current package version."""
    print(f"impressions {__version__}")
    return 0


DEFAULT_TOML = """# impressions configuration

[project]
name = "impressions-project"
"""

DEFAULT_EXAMPLE_TASK = """# Example task for Impressions
id: example_task
title: Example task
category: example
"""


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _confirm_overwrite(path: Path) -> bool:
    resp = input(f"{path} already exists. Overwrite? [y/N]: ")
    return resp.strip().lower().startswith("y")


def handle_init(args: argparse.Namespace) -> int:
    """Create a standard project layout and example files.

    The layout created is:
      - impressions.toml
      - tasks/example.yaml
      - reports/ (empty dir)

    Existing files are not overwritten unless --force is passed or the user confirms.
    """
    cwd = Path.cwd()
    created = []

    # impressions.toml
    toml_path = cwd / "impressions.toml"
    if toml_path.exists() and not args.force:
        if not _confirm_overwrite(toml_path):
            print(f"Skipping {toml_path}")
        else:
            _write_file(toml_path, DEFAULT_TOML)
            created.append(str(toml_path))
    else:
        _write_file(toml_path, DEFAULT_TOML)
        created.append(str(toml_path))

    # tasks/example.yaml
    task_path = cwd / "tasks" / "example.yaml"
    if task_path.exists() and not args.force:
        if not _confirm_overwrite(task_path):
            print(f"Skipping {task_path}")
        else:
            _write_file(task_path, DEFAULT_EXAMPLE_TASK)
            created.append(str(task_path))
    else:
        _write_file(task_path, DEFAULT_EXAMPLE_TASK)
        created.append(str(task_path))

    # reports directory
    reports_dir = cwd / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    created.append(str(reports_dir))

    print("Created:")
    for p in created:
        print(f" - {p}")

    return 0


def main(argv: List[str] | None = None) -> int:
    parser = build_parsers()
    args = parser.parse_args(argv)

    # When argparse prints help it will raise SystemExit; mimic previous behavior.
    if hasattr(args, "handler"):
        return args.handler(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
