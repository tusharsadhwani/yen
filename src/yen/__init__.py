"""yen - Yet another Python environment manager."""

from __future__ import annotations

import hashlib
import os
import os.path
import subprocess
import tarfile

from yen.downloader import download, read_url
from yen.github import NotAvailable, resolve_python_version

PYTHON_INSTALLS_PATH = os.getenv("YEN_PYTHONS_PATH") or os.path.expanduser(
    "~/.yen_pythons"
)


def check_path() -> None:
    """Ensure that PYTHON_INSTALLS_PATH is in PATH."""
    if PYTHON_INSTALLS_PATH not in os.environ["PATH"]:
        print(
            "\033[33m\n"
            "Warning: PYTHON_INSTALLS_PATH is not in PATH.\n"
            "Add the following line to your shell's configuration file:\n"
            "\033[0;1m"
            f"export PATH={PYTHON_INSTALLS_PATH}:$PATH"
            "\033[m"
        )


def ensure_python(python_version: str) -> tuple[str, str]:
    """Checks if given Python version exists locally. If not, downloads it."""
    os.makedirs(PYTHON_INSTALLS_PATH, exist_ok=True)

    try:
        python_version, download_link = resolve_python_version(python_version)
    except NotAvailable:
        print(
            "Error: requested Python version is not available."
            " Use 'yen list' to get list of available Pythons."
        )

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
        print(f"\033[1;31mError:\033[m Checksum did not match!")
        os.remove(downloaded_filepath)
        raise SystemExit(1)

    with tarfile.open(downloaded_filepath, mode="r:gz") as tar:
        tar.extractall(download_directory)

    os.remove(downloaded_filepath)
    assert os.path.exists(python_bin_path)

    return python_version, python_bin_path


def create_venv(python_version: str, python_bin_path: str, venv_path: str) -> None:
    if os.path.exists(venv_path):
        print(f"\033[1;31mError:\033[m {venv_path} already exists.")
        raise SystemExit(2)

    subprocess.run([python_bin_path, "-m", "venv", venv_path], check=True)
    print(f"Created \033[1m{venv_path}\033[m with Python {python_version} ✨")


def create_symlink(python_bin_path: str, python_version: str) -> None:
    python_major_minor = "python" + ".".join(python_version.split(".")[:2])
    symlink_path = os.path.join(PYTHON_INSTALLS_PATH, python_major_minor)

    if os.path.exists(symlink_path):
        os.remove(symlink_path)

    os.symlink(python_bin_path, symlink_path)
    print(f"\033[1m{python_major_minor}\033[m created in {PYTHON_INSTALLS_PATH} 🐍")
    check_path()
