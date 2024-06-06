"""CLI interface for yen."""

from __future__ import annotations

import argparse
import sys
from typing import Literal

from yen import create_symlink, create_venv, ensure_python
from yen.github import NotAvailable, list_pythons


class YenArgs:
    command: Literal["list", "create", "use"]
    python: str
    venv_path: str


def cli() -> int:
    """CLI interface."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list")

    create_parser = subparsers.add_parser("create")
    create_parser.add_argument("venv_path")
    create_parser.add_argument("-p", "--python", required=True)

    create_parser = subparsers.add_parser("use")
    create_parser.add_argument("-p", "--python", required=True)

    args = parser.parse_args(namespace=YenArgs)

    if args.command == "list":
        versions = list(list_pythons())
        print("Available Pythons:", file=sys.stderr)
        for version in versions:
            print(version)

    elif args.command == "create":
        try:
            python_version, python_bin_path = ensure_python(args.python)
            create_venv(python_version, python_bin_path, args.venv_path)
        except NotAvailable:
            print(
                "Error: requested Python version is not available."
                " Use 'yen list' to get list of available Pythons.",
                file=sys.stderr,
            )
            return 1

    elif args.command == "use":
        try:
            python_version, python_bin_path = ensure_python(args.python)
            create_symlink(python_bin_path, python_version)
        except NotAvailable:
            print(
                "Error: requested Python version is not available."
                " Use 'yen list' to get list of available Pythons."
            )
            return 1

    return 0
