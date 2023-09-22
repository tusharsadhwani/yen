"""CLI interface for yen."""
import argparse

from yen import ensure_python, create_venv


def cli() -> None:
    """CLI interface."""
    parser = argparse.ArgumentParser()
    parser.add_argument("venv_path")
    args = parser.parse_args()

    python_bin_path = ensure_python()
    create_venv(python_bin_path, args.venv_path)
