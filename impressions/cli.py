"""Command-line interface for Impressions."""

from __future__ import annotations

import argparse
from pathlib import Path

from impressions import __version__


DEFAULT_CONFIG = """\
[project]
name = "my-impressions-project"

[tasks]
directory = "tasks"

[reports]
directory = "reports"
"""

EXAMPLE_TASK = """\
id: example_task
title: Example string reversal
difficulty: easy
category: function_generation
timeout_seconds: 10
entrypoint: solution.py
prompt: |
  Write a function named reverse_text that returns the input string reversed.
starter_code: |
  def reverse_text(value: str) -> str:
      pass
tests: |
  from solution import reverse_text


  def test_reverse_text():
      assert reverse_text("impressions") == "snoisserpmi"
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
