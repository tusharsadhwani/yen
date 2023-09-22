"""CLI interface for yen."""
import argparse

from yen import ensure_python, create_venv


def cli() -> None:
    """CLI interface."""
    parser = argparse.ArgumentParser()
    parser.add_argument("venv_path")
    args = parser.parse_args()

    ensure_python()
    create_venv(args.venv_path)
