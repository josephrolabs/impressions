"""Command-line interface for Impressions."""

from __future__ import annotations

import argparse

from impressions import __version__


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

    return parser


def show_version(_args: argparse.Namespace) -> int:
    """Print the current package version."""
    print(f"impressions {__version__}")
    return 0


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
