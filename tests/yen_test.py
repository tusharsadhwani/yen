from __future__ import annotations

import os.path
import platform
import shutil
import subprocess
import sys

import pytest


def is_in_venv() -> bool:
    bin_folder = os.path.dirname(sys.executable)
    bin_parent_folder = os.path.dirname(bin_folder)
    return os.path.isfile(os.path.join(bin_parent_folder, "pyvenv.cfg"))


def yen_python_and_rust_path() -> list[str]:
    yen_paths: list[str] = []
    assert is_in_venv()
    yen_python_path = os.path.join(
        os.path.dirname(sys.executable),
        "yen.exe" if platform.system() == "Windows" else "yen",
    )

    yen_paths.append((yen_python_path,))
    if yen_rust_path := os.getenv("YEN_RUST_PATH"):
        yen_paths.append((yen_rust_path,))

    return yen_paths


yen_paths = yen_python_and_rust_path()
parametrize_python_and_rust_path = pytest.mark.parametrize(("yen_path",), yen_paths)


@parametrize_python_and_rust_path
def test_yen_list(yen_path: str) -> None:
    output = subprocess.check_output(
        [yen_path, "list"],
        stderr=subprocess.STDOUT,
    ).decode()
    assert "\n3.12." in output
    assert "\n3.11." in output
    assert "\n3.10." in output
    assert "\n3.9." in output


@parametrize_python_and_rust_path
def test_yen_create(yen_path: str) -> None:
    try:
        output = subprocess.check_output(
            [yen_path, "create", "-p3.11", "testvenv"],
            stderr=subprocess.STDOUT,
        ).decode()
        assert "Created" in output
        assert "testvenv" in output
        assert "Python 3.11" in output
    finally:
        shutil.rmtree("testvenv", ignore_errors=True)
