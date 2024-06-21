import os.path
import platform
import subprocess
import sys
from typing import Any

import pytest


def is_in_venv() -> bool:
    bin_folder = os.path.dirname(sys.executable)
    bin_parent_folder = os.path.dirname(bin_folder)
    if platform.system() == "Windows":
        return os.path.basename(bin_folder) == "Scripts" and os.path.isfile(
            os.path.join(bin_parent_folder, "pyvenv.cfg")
        )

    return os.path.basename(bin_folder) == "bin" and os.path.isfile(
        os.path.join(bin_parent_folder, "pyvenv.cfg")
    )


def parametrize_python_and_rust_path() -> Any:
    yen_paths: list[str] = []
    assert is_in_venv()
    yen_python_path = os.path.join(
        os.path.dirname(sys.executable),
        "yen.exe" if platform.system() == "Windows" else "yen",
    )

    yen_paths.append((yen_python_path,))
    return pytest.mark.parametrize(("yen_path",), yen_paths)


@parametrize_python_and_rust_path()
def test_yen_list(yen_path: str) -> None:
    yen_output = subprocess.check_output(
        [yen_path, "list"],
        stderr=subprocess.STDOUT,
    ).decode()
    assert "\n3.12." in yen_output
    assert "\n3.11." in yen_output
    assert "\n3.10." in yen_output
    assert "\n3.9." in yen_output


@parametrize_python_and_rust_path()
def test_yen_create(yen_path: str) -> None:
    pass  # TODO
