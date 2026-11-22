"""`aegissoc` command-line entrypoint (stdlib argparse). Subcommands arrive in S1-T10."""

import argparse
from collections.abc import Sequence

from aegissoc import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aegissoc", description="AegisSOC administration CLI.")
    parser.add_argument("--version", action="version", version=f"aegissoc {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    build_parser().parse_args(argv)
    return 0
