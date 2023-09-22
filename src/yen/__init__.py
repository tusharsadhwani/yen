"""yen - Yet another Python environment manager."""
import os.path
import platform
import shutil
import tarfile
import venv

from yen.downloader import download

PYTHON_INSTALLS_PATH = os.path.expanduser("~/.yen_pythons")

DOWNLOAD_LINKS = {
    "Darwin": {
        "arm64": "https://github.com/indygreg/python-build-standalone/releases/download/20230826/cpython-3.11.5+20230826-aarch64-apple-darwin-install_only.tar.gz",
        "x86_64": "https://github.com/indygreg/python-build-standalone/releases/download/20230826/cpython-3.11.5+20230826-x86_64-apple-darwin-install_only.tar.gz",
    },
    "Linux": {
        "arm64": {
            "glibc": "https://github.com/indygreg/python-build-standalone/releases/download/20230826/cpython-3.11.5+20230826-aarch64-unknown-linux-gnu-install_only.tar.gz",
            # musl doesn't exist
        },
        "x86_64": {
            "glibc": "https://github.com/indygreg/python-build-standalone/releases/download/20230826/cpython-3.11.5+20230826-x86_64_v3-unknown-linux-gnu-install_only.tar.gz",
            "musl": "https://github.com/indygreg/python-build-standalone/releases/download/20230826/cpython-3.11.5+20230826-x86_64_v2-unknown-linux-musl-install_only.tar.gz",
        },
    },
}


# TODO: take version
def download_python() -> None:
    """Downloads a Python version. The version can be something like '3.11.5'."""
    download_link = DOWNLOAD_LINKS[platform.system()][platform.machine()]
    # linux links are nested under glibc or musl builds
    libc_version = platform.libc_ver()[0]
    if libc_version:
        download_link = download_link[libc_version]

    downloaded_filepath = download(
        download_link,
        "Downloading Python 3.11.5",
        PYTHON_INSTALLS_PATH,
    )

    with tarfile.open(downloaded_filepath, mode="r:gz") as tar:
        # TODO: give version as path
        tar.extractall(PYTHON_INSTALLS_PATH)


# TODO: take version
def ensure_python() -> None:
    """Checks if given Python version exists locally. If not, downloads it."""
    os.makedirs(PYTHON_INSTALLS_PATH, exist_ok=True)

    python_bin_path = os.path.join(PYTHON_INSTALLS_PATH, "python/bin/python3")
    if os.path.exists(python_bin_path):
        # already installed
        return

    download_python()

    assert os.path.exists(python_bin_path)
    return python_bin_path


def create_venv(venv_path: str) -> None:
    venv_name = os.path.basename(venv_path)

    if os.path.exists(venv_path):
        print("Error: path already exists.")
        return

    venv.create(venv_path, prompt=venv_name)
    print("Created", venv_path)
