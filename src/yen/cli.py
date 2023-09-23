"""CLI interface for yen."""
import argparse

from yen import ensure_python, create_venv
from yen.github import list_pythons


def cli() -> None:
    """CLI interface."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list")

    create_parser = subparsers.add_parser("create")
    create_parser.add_argument("venv_path")
    create_parser.add_argument("-p", "--python")

    args = parser.parse_args()

    if args.command == "list":
        versions = list(list_pythons())
        print("Available Pythons:")
        for version in versions:
            print(version)

    elif args.command == "create":
        python_version, python_bin_path = ensure_python(args.python)
        create_venv(python_version, python_bin_path, args.venv_path)
