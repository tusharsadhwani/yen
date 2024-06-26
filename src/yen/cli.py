"""CLI interface for yen."""

from __future__ import annotations

import argparse
import os.path
import subprocess
import sys
from typing import Literal

from yen import (
    DEFAULT_PYTHON_VERSION,
    PACKAGE_INSTALLS_PATH,
    ExecutableDoesNotExist,
    check_path,
    create_venv,
    ensure_python,
    ensurepath,
    install_package,
)
from yen.github import NotAvailable, list_pythons


class YenArgs:
    command: Literal["list", "ensurepath", "create", "install", "run", "exec"]
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
    subparsers.add_parser("ensurepath")

    create_parser = subparsers.add_parser("create")
    create_parser.add_argument("venv_path", type=os.path.abspath)
    create_parser.add_argument("-p", "--python", required=True)

    install_parser = subparsers.add_parser("install")
    install_parser.add_argument("package_name")
    install_parser.add_argument("-p", "--python", default=DEFAULT_PYTHON_VERSION)
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
    run_parser.add_argument("-p", "--python", default=DEFAULT_PYTHON_VERSION)
    run_parser.add_argument(
        "run_args",
        help="Arguments to pass to the command invocation",
        nargs="*",
    )

    exec_parser = subparsers.add_parser("exec")
    exec_parser.add_argument("-p", "--python", default=DEFAULT_PYTHON_VERSION)

    args = parser.parse_args(namespace=YenArgs)

    if args.command == "list":
        versions = list(list_pythons())
        print("Available Pythons:", file=sys.stderr)
        for version in versions:
            print(version)

    if args.command == "ensurepath":
        ensurepath()
        print(
            f"`{PACKAGE_INSTALLS_PATH}` is now present in your PATH."
            " Restart your shell for it to take effect."
        )

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
        if args.module is not None and args.binary is not None:
            print(
                "Error: cannot pass `--binary` and `--module` together.",
                file=sys.stderr,
            )
            return 1

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
        executable_name = args.module or args.binary or args.package_name
        is_module = args.module is not None
        try:
            _, already_installed = install_package(
                args.package_name,
                python_bin_path,
                executable_name,
                is_module=is_module,
                force_reinstall=args.force_reinstall,
            )
        except ExecutableDoesNotExist:
            error_message = (
                f"Error: package {args.package_name} doesn't contain a binary named"
                f" {executable_name}."
            )
            if not (args.module or args.binary):
                error_message += " Consider passing `--binary` or `--module` flags."
            print(error_message, file=sys.stderr)
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
            shim_path, _ = install_package(
                args.package_name,
                python_bin_path,
                executable_name=args.package_name,
            )
        except ExecutableDoesNotExist:
            print(
                f"Error: package {args.package_name} doesn't contain a binary named"
                f" {args.package_name}.",
                file=sys.stderr,
            )
            return 4

        return subprocess.call([shim_path, *args.run_args])

    elif args.command == "exec":
        try:
            python_version, python_bin_path = ensure_python(args.python)
        except NotAvailable:
            print(
                "Error: requested Python version is not available."
                " Use 'yen list' to get list of available Pythons.",
                file=sys.stderr,
            )
            return 1

        return subprocess.call([python_bin_path])

    return 0
