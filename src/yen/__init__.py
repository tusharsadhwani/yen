"""yen - Yet another Python environment manager."""

from __future__ import annotations

import hashlib
import os
import os.path
import platform
import shutil
import subprocess
import sys
import tarfile

from yen.downloader import download, read_url
from yen.github import resolve_python_version

PYTHON_INSTALLS_PATH = os.path.abspath(
    os.getenv("YEN_PYTHONS_PATH", os.path.expanduser("~/.yen_pythons"))
)
PACKAGE_INSTALLS_PATH = os.path.abspath(
    os.getenv("YEN_PACKAGES_PATH", os.path.expanduser("~/.yen_packages"))
)


class ExecutableDoesNotExist(Exception): ...


def check_path(path: str) -> None:
    """Ensure that given path is in PATH."""
    unix_msg = (
        "Run `yen ensurepath`, or add this line to your shell's configuration file:\n"
        "\033[0;1m"
        f"export PATH={path}:$PATH"
        "\033[m"
    )
    windows_msg = "Run `yen ensurepath` to add it to your PATH."

    if path not in os.environ["PATH"].split(os.pathsep):
        print(
            (
                "\033[33m\n"
                "Warning: The executable just installed is not in PATH.\n" + windows_msg
                if platform.system() == "Windows"
                else unix_msg
            ),
            file=sys.stderr,
        )


def ensure_python(python_version: str) -> tuple[str, str]:
    """Checks if given Python version exists locally. If not, downloads it."""
    os.makedirs(PYTHON_INSTALLS_PATH, exist_ok=True)

    python_version, download_link = resolve_python_version(python_version)
    download_directory = os.path.join(PYTHON_INSTALLS_PATH, python_version)

    if platform.system() == "Windows":
        python_bin_path = os.path.join(download_directory, "python/python.exe")
    else:
        python_bin_path = os.path.join(download_directory, "python/bin/python3")
    if os.path.exists(python_bin_path):
        # already installed
        return python_version, python_bin_path

    os.makedirs(download_directory, exist_ok=True)
    downloaded_filepath = download(
        download_link,
        f"Downloading {python_version}",
        download_directory,
    )
    # Calculate checksum
    with open(downloaded_filepath, "rb") as python_zip:
        checksum = hashlib.sha256(python_zip.read()).hexdigest()

    # Validate checksum
    checksum_link = download_link + ".sha256"
    expected_checksum = read_url(checksum_link).rstrip("\n")
    if checksum != expected_checksum:
        print("\033[1;31mError:\033[m Checksum did not match!")
        os.remove(downloaded_filepath)
        raise SystemExit(1)

    with tarfile.open(downloaded_filepath, mode="r:gz") as tar:
        tar.extractall(download_directory)

    os.remove(downloaded_filepath)
    assert os.path.exists(python_bin_path)

    return python_version, python_bin_path


def create_venv(python_bin_path: str, venv_path: str) -> None:
    # TODO: bundle microvenv.pyz as a dependency, venv is genuinely too slow
    # microvenv doesn't support windows, fallback to venv for that. teehee.
    subprocess.run([python_bin_path, "-m", "venv", venv_path], check=True)


def _venv_binary_path(binary_name: str, venv_path: str) -> str:
    is_windows = platform.system() == "Windows"
    venv_bin_path = os.path.join(venv_path, "Scripts" if is_windows else "bin")
    binary_path = os.path.join(
        venv_bin_path, f"{binary_name}.exe" if is_windows else binary_name
    )
    return binary_path


def install_package(
    package_name: str,
    python_bin_path: str,
    executable_name: str,
    *,
    is_module: bool = False,
    force_reinstall: bool = False,
) -> bool:
    os.makedirs(PACKAGE_INSTALLS_PATH, exist_ok=True)

    venv_name = f"venv_{package_name}"
    venv_path = os.path.join(PACKAGE_INSTALLS_PATH, venv_name)
    if os.path.exists(venv_path):
        if not force_reinstall:
            return True  # True as in package already existed
        else:
            shutil.rmtree(venv_path)

    create_venv(python_bin_path, venv_path)

    venv_python_path = _venv_binary_path("python", venv_path)
    subprocess.run(
        [venv_python_path, "-m", "pip", "install", package_name],
        check=True,
        capture_output=True,
    )

    is_windows = platform.system() == "Windows"
    shim_path = os.path.join(PACKAGE_INSTALLS_PATH, package_name)
    if is_windows:
        shim_path += ".exe"

    if is_module and not is_windows:
        with open(shim_path, "w") as file:
            file.write(f'#!/bin/sh\n{venv_python_path} -m {package_name} "$@"')

        os.chmod(shim_path, 0o777)
    else:
        executable_path = _venv_binary_path(executable_name, venv_path)
        if not os.path.exists(executable_path):
            # cleanup the venv created
            shutil.rmtree(venv_path)
            raise ExecutableDoesNotExist

        if is_windows:
            shutil.move(executable_path, shim_path)
        else:
            os.symlink(executable_path, shim_path)

    return False  # False as in package didn't exist and was just installed


def run_package(package_name: str, args: list[str]) -> None:
    shim_path = os.path.join(PACKAGE_INSTALLS_PATH, package_name)
    subprocess.run([shim_path, *args])


def create_symlink(python_bin_path: str, python_version: str) -> None:
    python_version = "python" + ".".join(python_version.split(".")[:2])
    symlink_path = os.path.join(PYTHON_INSTALLS_PATH, python_version)

    if os.path.exists(symlink_path):
        os.remove(symlink_path)

    os.symlink(python_bin_path, symlink_path)
    check_path(PYTHON_INSTALLS_PATH)
