"""CLI interface for yen."""

from __future__ import annotations

import argparse
import sys
from typing import Literal

from yen import create_symlink, create_venv, ensure_python, install_package, run_package
from yen.github import NotAvailable, list_pythons


class YenArgs:
    command: Literal["list", "create", "install", "run", "use"]
    python: str
    venv_path: str
    package_name: str
    command_args: list[str]


def cli() -> int:
    """CLI interface."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list")

    create_parser = subparsers.add_parser("create")
    create_parser.add_argument("venv_path")
    create_parser.add_argument("-p", "--python", required=True)

    install_parser = subparsers.add_parser("install")
    install_parser.add_argument("package_name")
    install_parser.add_argument("-p", "--python", default="3.12")

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("package_name")
    run_parser.add_argument("-p", "--python", default="3.12")
    run_parser.add_argument("command_args", nargs="+")

    use_parser = subparsers.add_parser("use")
    use_parser.add_argument("-p", "--python", required=True)

    args = parser.parse_args(namespace=YenArgs)

    if args.command == "list":
        versions = list(list_pythons())
        print("Available Pythons:", file=sys.stderr)
        for version in versions:
            print(version)

    elif args.command == "create":
        try:
            python_version, python_bin_path = ensure_python(args.python)
        except NotAvailable:
            print(
                "Error: requested Python version is not available."
                " Use 'yen list' to get list of available Pythons.",
                file=sys.stderr,
            )
            return 1

        create_venv(python_bin_path, args.venv_path)
        print(
            f"Created \033[1m{args.venv_path}\033[m" f" with Python {python_version} ✨"
        )

    elif args.command == "install":
        try:
            python_version, python_bin_path = ensure_python(args.python)
        except NotAvailable:
            print(
                "Error: requested Python version is not available."
                " Use 'yen list' to get list of available Pythons.",
                file=sys.stderr,
            )
            return 1

        # TODO: add yaspin?
        already_installed = install_package(args.package_name, python_bin_path)
        if already_installed:
            print(f"Package \033[1m{args.package_name}\033[m is already installed.")
        else:
            print(
                f"Installed package \033[1m{args.package_name}\033[m"
                f" with Python {python_version} ✨"
            )

    elif args.command == "run":
        try:
            _, python_bin_path = ensure_python(args.python)
        except NotAvailable:
            print(
                "Error: requested Python version is not available."
                " Use 'yen list' to get list of available Pythons.",
                file=sys.stderr,
            )
            return 1

        # TODO: add yaspin?
        venv_path, _ = install_package(args.package_name, python_bin_path)
        run_package(args.package_name, venv_path, args.command_args)

    elif args.command == "use":
        try:
            python_version, python_bin_path = ensure_python(args.python)
        except NotAvailable:
            print(
                "Error: requested Python version is not available."
                " Use 'yen list' to get list of available Pythons.",
                file=sys.stderr,
            )
            return 1

        create_symlink(python_bin_path, python_version)
        print(f"\033[1m{python_version}\033[m created 🐍")

    return 0
