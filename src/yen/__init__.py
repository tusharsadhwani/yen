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
from urllib.request import urlretrieve

from yen.downloader import download, read_url
from yen.github import resolve_python_version

YEN_BIN_PATH = os.path.abspath(
    os.getenv("YEN_BIN_PATH", os.path.expanduser("~/.yen/bin"))
)
PYTHON_INSTALLS_PATH = os.path.abspath(
    os.getenv("YEN_PYTHONS_PATH", os.path.expanduser("~/.yen_pythons"))
)
PACKAGE_INSTALLS_PATH = os.path.abspath(
    os.getenv("YEN_PACKAGES_PATH", os.path.expanduser("~/.yen_packages"))
)

USERPATH_PATH = os.path.join(YEN_BIN_PATH, "userpath.pyz")
MICROVENV_PATH = os.path.join(YEN_BIN_PATH, "microvenv.py")

DEFAULT_PYTHON_VERSION = "3.12"


class ExecutableDoesNotExist(Exception): ...


def check_path(path: str) -> None:
    """Check if given path is in PATH, and inform the user otherwise."""
    if platform.system() == "Windows":
        _ensure_userpath()
        python_bin_path = find_or_download_python()
        process = subprocess.run([python_bin_path, USERPATH_PATH, "check", path])
        path_exists = process.returncode == 0
    else:
        path_exists = path in os.environ["PATH"].split(os.pathsep)

    if not path_exists:
        print(
            "\033[33m"
            "Warning: The executable just installed is not in PATH.\n"
            "Run `yen ensurepath` to add it to your PATH."
            "\033[m",
            file=sys.stderr,
        )


def _ensure_userpath() -> None:
    """Downloads `userpath.pyz`, if it doesn't exist in `YEN_BIN_PATH`."""
    if os.path.exists(USERPATH_PATH):
        return

    os.makedirs(YEN_BIN_PATH, exist_ok=True)
    urlretrieve("http://yen.tushar.lol/userpath.pyz", filename=USERPATH_PATH)


def _ensure_microvenv() -> None:
    """Downloads `microvenv.py`, if it doesn't exist in `YEN_BIN_PATH`."""
    if os.path.exists(MICROVENV_PATH):
        return

    os.makedirs(YEN_BIN_PATH, exist_ok=True)
    urlretrieve("http://yen.tushar.lol/microvenv.py", filename=MICROVENV_PATH)


def find_or_download_python() -> str:
    """
    Finds and returns any Python binary from `PYTHON_INSTALLS_PATH`.
    If no Pythons exist, downloads the default version and returns that.
    """
    for python_folder_name in os.listdir(PYTHON_INSTALLS_PATH):
        python_folder = os.path.join(PYTHON_INSTALLS_PATH, python_folder_name)
        python_bin_path = _python_bin_path(python_folder)
        if os.path.isfile(python_bin_path):
            return python_bin_path

    # No Python binary found. Download one.
    _, python_bin_path = ensure_python(DEFAULT_PYTHON_VERSION)
    return python_bin_path


def ensurepath() -> None:
    """Ensures that PACKAGE_INSTALLS_PATH is in PATH."""
    _ensure_userpath()
    python_bin_path = find_or_download_python()
    subprocess.run(
        [python_bin_path, USERPATH_PATH, "append", PACKAGE_INSTALLS_PATH],
        check=True,
    )


def _python_bin_path(python_directory: str) -> str:
    """Return the python binary path in a downloaded and extracted Python."""
    if platform.system() == "Windows":
        return os.path.join(python_directory, "python", "python.exe")
    else:
        return os.path.join(python_directory, "python", "bin", "python3")


def ensure_python(python_version: str) -> tuple[str, str]:
    """Checks if given Python version exists locally. If not, downloads it."""
    os.makedirs(PYTHON_INSTALLS_PATH, exist_ok=True)

    for python_folder_name in os.listdir(PYTHON_INSTALLS_PATH):
        python_folder = os.path.join(PYTHON_INSTALLS_PATH, python_folder_name)
        if python_folder_name.startswith(python_version):
            # already installed
            python_bin_path = _python_bin_path(python_folder)
            return python_folder_name, python_bin_path

    python_version, download_link = resolve_python_version(python_version)
    download_directory = os.path.join(PYTHON_INSTALLS_PATH, python_version)

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
    print("Checksum verified!")

    with tarfile.open(downloaded_filepath, mode="r:gz") as tar:
        tar.extractall(download_directory)

    os.remove(downloaded_filepath)

    python_bin_path = _python_bin_path(download_directory)
    assert os.path.exists(python_bin_path)
    return python_version, python_bin_path


def create_venv(python_bin_path: str, venv_path: str) -> None:
    # if platform.system() == "Windows":
    subprocess.run([python_bin_path, "-m", "venv", venv_path], check=True)
    return

    # _ensure_microvenv()
    # subprocess.run([python_bin_path, MICROVENV_PATH, venv_path], check=True)
    # venv_python_path = _venv_binary_path("python", venv_path)
    # subprocess.run(
    #     [venv_python_path, "-m", "ensurepip"],
    #     check=True,
    #     capture_output=True,
    # )


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
) -> tuple[str, bool]:
    is_windows = platform.system() == "Windows"
    shim_path = os.path.join(PACKAGE_INSTALLS_PATH, package_name)
    if is_windows:
        # This is somewhat of a hack.
        # For the condition where shim_path exists and we do `yen run`,
        # `is_module` is false but we still want to return early.
        # But for the condition where we try to create the module the first time,
        # `is_module` will be true, and in that case we want to use `.bat` as well
        if is_module or os.path.exists(shim_path + ".bat"):
            shim_path += ".bat"
        else:
            shim_path += ".exe"

    venv_name = f"venv_{package_name}"
    venv_path = os.path.join(PACKAGE_INSTALLS_PATH, venv_name)
    if os.path.exists(shim_path):
        if not force_reinstall:
            return shim_path, True  # True as in package already existed
        else:
            os.remove(shim_path)
            shutil.rmtree(venv_path, ignore_errors=True)

    create_venv(python_bin_path, venv_path)

    venv_python_path = _venv_binary_path("python", venv_path)
    subprocess.run(
        [venv_python_path, "-m", "pip", "install", package_name],
        check=True,
        capture_output=True,
    )

    if is_module:
        with open(shim_path, "w") as file:
            if is_windows:
                file.write(f"@echo off\n{venv_python_path} -m {package_name} %*")
            else:
                file.write(f'#!/bin/sh\n{venv_python_path} -m {package_name} "$@"')

        os.chmod(shim_path, 0o777)
    else:
        executable_path = _venv_binary_path(executable_name, venv_path)
        if not os.path.exists(executable_path):
            # cleanup the venv created
            shutil.rmtree(venv_path)
            raise ExecutableDoesNotExist

        # the created binary is always moveable
        shutil.move(executable_path, shim_path)

    return shim_path, False  # False as in package didn't exist and was just installed
