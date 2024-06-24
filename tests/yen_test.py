from __future__ import annotations

import os.path
import platform
import shutil
import subprocess
import sys
from textwrap import dedent
from typing import Iterator

import pytest


PACKAGES_INSTALL_PATH = os.path.join(os.path.dirname(__file__), "yen_packages")


@pytest.fixture(autouse=True)
def patch_yen_packages_path(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Ensures that YEN_PACKAGES_PATH is set up correctly and cleaned up."""
    monkeypatch.setenv("YEN_PACKAGES_PATH", PACKAGES_INSTALL_PATH)
    yield
    shutil.rmtree(PACKAGES_INSTALL_PATH, ignore_errors=True)


def is_in_venv() -> bool:
    bin_folder = os.path.dirname(sys.executable)
    bin_parent_folder = os.path.dirname(bin_folder)
    return os.path.isfile(os.path.join(bin_parent_folder, "pyvenv.cfg"))


def yen_python_and_rust_path() -> list[str]:
    yen_paths: list[tuple[str]] = []
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


def run(
    command: list[str],
    *,
    combined_output: bool = False,
    cwd: str | None = None,
) -> str:
    if not os.path.isabs(command[0]):
        command[0] = os.path.abspath(os.path.join(cwd or ".", command[0]))

    if platform.system() == "Windows" and not command[0].endswith(".exe"):
        command[0] += ".exe"

    try:
        output = subprocess.check_output(
            command,
            stderr=subprocess.STDOUT if combined_output else subprocess.PIPE,
            env={**os.environ, "PYTHONUTF8": "1"},
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"Subprocess stdout: {exc.stdout}\nstderr: {exc.stderr}")
        raise

    return output


@parametrize_python_and_rust_path
def test_yen_list(yen_path: str) -> None:
    output = run([yen_path, "list"], combined_output=True)
    assert "Available Pythons:"
    assert "\n3.12." in output
    assert "\n3.11." in output
    assert "\n3.10." in output
    assert "\n3.9." in output


@parametrize_python_and_rust_path
def test_yen_create(yen_path: str) -> None:
    try:
        output = run([yen_path, "create", "-p3.11", "testvenv"])
        assert "Created" in output
        assert "testvenv" in output
        assert "Python 3.11" in output
    finally:
        shutil.rmtree("testvenv", ignore_errors=True)


@parametrize_python_and_rust_path
def test_yen_install(yen_path: str) -> None:
    output = run([yen_path, "install", "-p3.10", "meowsay"])
    assert "Installed" in output
    assert "meowsay" in output
    assert "Python 3.10" in output

    meowsay_output = run(["meowsay", "hi"], cwd=PACKAGES_INSTALL_PATH)
    assert meowsay_output == dedent(
        r"""
         ____
        < hi >
         ----
                \      |\---/|
                 \     | ,_, |
                        \_`_/-..----.
                     ___/ `   ' ,\"\"+ \  sk
                    (__...'   __\    |`.___.';
                      (_,...'(_,.`__)/'.....+
        """.rstrip("\n")
    )

    output = run([yen_path, "install", "meowsay"])
    assert "meowsay" in output
    assert "already installed" in output


@parametrize_python_and_rust_path
def test_yen_install_with_binary_name(yen_path: str) -> None:
    package_name = "python-leetcode-runner"
    output = run([yen_path, "install", package_name, "--binary", "pyleet"])
    assert "Installed" in output
    assert package_name in output

    code = dedent(
        """
        class Solution:
            def add(self, x, y):
                return x + y

        tests = [((2, 2), 4), ((4, -1), 3)]  # quick maths
        """
    )
    with open("./foo.py", "w") as file:
        file.write(code)

    pyleet_output = run(
        ["python-leetcode-runner", "./foo.py"], cwd=PACKAGES_INSTALL_PATH
    )
    os.remove(file.name)

    assert "Test 1 - (2, 2)" in pyleet_output
    assert "PASSED" in pyleet_output
    assert "Test 2 - (4, -1)" in pyleet_output
    assert "All cases passed!" in pyleet_output


@parametrize_python_and_rust_path
def test_yen_install_module(yen_path: str) -> None:
    output = run([yen_path, "install", "-p3.9", "astmath", "--module", "astmath"])
    assert "Installed" in output
    assert "astmath" in output
    assert "Python 3.9" in output

    if platform.system() != "Windows":
        # Ensure the module runner file got created
        executable_path = os.path.join(PACKAGES_INSTALL_PATH, "astmath")
        with open(executable_path) as executable:
            executable_code = executable.read()

        assert '-m astmath "$@"' in executable_code

    astmath_output = run(["astmath", "'foo' * 3"], cwd=PACKAGES_INSTALL_PATH)
    assert astmath_output == "foofoofoo\n"


@parametrize_python_and_rust_path
def test_yen_run(yen_path: str) -> None:
    output = run([yen_path, "run", "astmath", "--module", "astmath", "--args", "3 * 3"])
    assert output == "9\n"

    if platform.system() != "Windows":
        # Ensure the module runner file got created
        executable_path = os.path.join(PACKAGES_INSTALL_PATH, "astmath")
        with open(executable_path) as executable:
            executable_code = executable.read()

        assert "-m astmath" in executable_code

    executable_output = run(["astmath", "2 * 3"], cwd=PACKAGES_INSTALL_PATH)
    assert executable_output == "6\n"

    repeat_output = run([yen_path, "run", "astmath", "--args", "9 + 10"])
    assert repeat_output == "19\n"

    install_output = run([yen_path, "install", "astmath"])
    assert "astmath" in install_output
    assert "already installed" in install_output
