"""yen - Yet another Python environment manager."""
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

    os.makedirs(download_directory)
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
        print(f"Error: Checksum did not match!")
        os.remove(downloaded_filepath)
        raise SystemExit(1)

    print("Checksum matched!")

    with tarfile.open(downloaded_filepath, mode="r:gz") as tar:
        tar.extractall(download_directory)

    os.remove(downloaded_filepath)
    assert os.path.exists(python_bin_path)

    return python_version, python_bin_path


def create_venv(python_version: str, python_bin_path: str, venv_path: str) -> None:
    if os.path.exists(venv_path):
        print(f"Error: {venv_path} already exists.")
        raise SystemExit(2)

    subprocess.run([python_bin_path, "-m", "venv", venv_path])
    print(f"Created {venv_path} with Python {python_version} ✨")
