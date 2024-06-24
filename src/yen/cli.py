"""CLI interface for yen."""

from __future__ import annotations

import argparse
import os.path
import sys
from typing import Literal

from yen import (
    PACKAGE_INSTALLS_PATH,
    ExecutableDoesNotExist,
    check_path,
    create_symlink,
    create_venv,
    ensure_python,
    install_package,
    run_package,
)
from yen.github import NotAvailable, list_pythons


class YenArgs:
    # TODO: add ensurepath, by bundling userpath library (so rust can call it too)
    command: Literal["list", "create", "install", "run", "use"]
    python: str
    venv_path: str
    package_name: str
    binary: str | None
    module: str | None
    force_reinstall: bool
    run_args: list[str]


def cli() -> int:
    """CLI interface."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list")

    create_parser = subparsers.add_parser("create")
    create_parser.add_argument("venv_path", type=os.path.abspath)
    create_parser.add_argument("-p", "--python", required=True)

    install_parser = subparsers.add_parser("install")
    install_parser.add_argument("package_name")
    install_parser.add_argument("-p", "--python", default="3.12")
    install_parser.add_argument(
        "--binary",
        help="Name of command installed by package. Defaults to package name itself.",
    )
    install_parser.add_argument(
        "--module",
        help="Use if package should be run as a module, i.e. `python -m <module_name>`",
    )
    install_parser.add_argument("--force-reinstall", action="store_true")

    # TODO: add long help texts to each subparser
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("package_name")
    run_parser.add_argument("-p", "--python", default="3.12")
    run_parser.add_argument(
        "run_args",
        help="Arguments to pass to the command invocation",
        nargs="*",
    )

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

        if os.path.exists(args.venv_path):
            print(f"\033[1;31mError:\033[m {args.venv_path} already exists.")
            return 2

        create_venv(python_bin_path, args.venv_path)
        print(f"Created \033[1m{args.venv_path}\033[m with Python {python_version} ✨")

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

        if args.module is not None and args.binary is not None:
            print(
                "Error: cannot pass `--binary-name` and `--module-name` together.",
                file=sys.stderr,
            )
            return 1

        # TODO: add yaspin?
        executable_name = args.module or args.binary or args.package_name
        is_module = args.module is not None
        try:
            already_installed = install_package(
                args.package_name,
                python_bin_path,
                executable_name,
                is_module=is_module,
                force_reinstall=args.force_reinstall,
            )
        except ExecutableDoesNotExist:
            print(
                f"Error: package {args.package_name} doesn't contain a binary named"
                f" {executable_name}. Consider passing `--binary` or `--module` flags.",
                file=sys.stderr,
            )
            return 4

        if already_installed:
            print(f"Package \033[1m{args.package_name}\033[m is already installed.")
        else:
            print(
                f"Installed package \033[1m{args.package_name}\033[m"
                f" with Python {python_version} ✨"
            )

        check_path(PACKAGE_INSTALLS_PATH)

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
        try:
            already_installed = install_package(
                args.package_name,
                python_bin_path,
                executable_name=args.package_name,
            )
        except ExecutableDoesNotExist:
            print(
                f"Error: package {args.package_name} doesn't contain a binary named"
                f" {executable_name}. Consider passing `--binary` or `--module` flags.",
                file=sys.stderr,
            )
            return 4

        run_package(args.package_name, args.run_args)

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
