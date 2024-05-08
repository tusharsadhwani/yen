"""CLI interface for yen."""

from __future__ import annotations

import argparse
from typing import Literal

from yen import create_symlink, ensure_python, create_venv
from yen.github import list_pythons


class YenArgs:
    command: Literal["list", "create", "use"]
    python: str
    venv_path: str


def cli() -> None:
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
        print("Available Pythons:")
        for version in versions:
            print(version)

    elif args.command == "create":
        python_version, python_bin_path = ensure_python(args.python)
        create_venv(python_version, python_bin_path, args.venv_path)

    elif args.command == "use":
        python_version, python_bin_path = ensure_python(args.python)
        create_symlink(python_bin_path, python_version)
