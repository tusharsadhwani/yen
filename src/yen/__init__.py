"""yen - Yet another Python environment manager."""

from __future__ import annotations

import hashlib
import os
import os.path
import platform
import subprocess
import sys
import tarfile

from yen.downloader import download, read_url
from yen.github import resolve_python_version

PYTHON_INSTALLS_PATH = os.getenv(
    "YEN_PYTHONS_PATH", os.path.expanduser("~/.yen_pythons")
)
PACKAGE_INSTALLS_PATH = os.getenv(
    "YEN_PACKAGES_PATH", os.path.expanduser("~/.yen_packages")
)


def check_path(path: str) -> None:
    """Ensure that given path is in PATH."""
    if path not in os.environ["PATH"].split(os.pathsep):
        print(
            "\033[33m\n"
            "Warning: The executable just installed is not in PATH.\n"
            "Add the following line to your shell's configuration file:\n"
            "\033[0;1m"
            f"export PATH={path}:$PATH"
            "\033[m",
            file=sys.stderr,
        )


def ensure_python(python_version: str) -> tuple[str, str]:
    """Checks if given Python version exists locally. If not, downloads it."""
    os.makedirs(PYTHON_INSTALLS_PATH, exist_ok=True)

    python_version, download_link = resolve_python_version(python_version)
    download_directory = os.path.join(PYTHON_INSTALLS_PATH, python_version)

    if os.name == "nt":
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


def create_venv(python_bin_path: str, venv_path: str, exists_ok: bool = False) -> bool:
    """if `exist_ok` is True, Returns False if venv already existed."""
    if os.path.exists(venv_path) and not exists_ok:
        print(f"\033[1;31mError:\033[m {venv_path} already exists.")
        raise SystemExit(2)

    subprocess.run([python_bin_path, "-m", "venv", venv_path], check=True)


def _venv_binary_path(binary_name: str, venv_path: str) -> str:
    is_windows = platform.system() == "Windows"
    venv_bin_path = os.path.join(venv_path, "Scripts" if is_windows else "bin")
    binary_path = os.path.join(
        venv_bin_path, f"{binary_name}.exe" if is_windows else binary_name
    )
    return binary_path


def install_package(package_name: str, python_bin_path: str) -> tuple[str, bool]:
    # TODO: add `force` arg to manually remove the venv if it exists
    # TODO: add `--spec` equivalent from pipx
    # TODO: maybe add a `--module` flag that runs it as `python -m package_name` instead
    os.makedirs(PACKAGE_INSTALLS_PATH, exist_ok=True)
    venv_name = f"venv_{package_name}"
    venv_path = os.path.join(PACKAGE_INSTALLS_PATH, venv_name)
    venv_created = create_venv(python_bin_path, venv_path, exists_ok=True)

    if not venv_created:
        return venv_path, True  # True as in already existed

    venv_python_path = _venv_binary_path("python", venv_path)
    subprocess.run([venv_python_path, "-m", "pip", "install", package_name], check=True)
    package_bin_path = _venv_binary_path(package_name, venv_path)
    os.symlink(package_bin_path, os.path.join(PACKAGE_INSTALLS_PATH, package_name))

    check_path(PACKAGE_INSTALLS_PATH)
    return venv_path, False


def run_package(package_name: str, venv_path: str, args: list[str]) -> None:
    # TODO: add `--spec` equivalent from pipx
    # TODO: maybe add a `--module` flag that runs it as `python -m package_name` instead
    package_bin_path = _venv_binary_path(package_name, venv_path)
    subprocess.run([package_bin_path, *args])


def create_symlink(python_bin_path: str, python_version: str) -> None:
    python_version = "python" + ".".join(python_version.split(".")[:2])
    symlink_path = os.path.join(PYTHON_INSTALLS_PATH, python_version)

    if os.path.exists(symlink_path):
        os.remove(symlink_path)

    os.symlink(python_bin_path, symlink_path)
    check_path(PYTHON_INSTALLS_PATH)
