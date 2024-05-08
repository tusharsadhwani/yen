from __future__ import annotations

import json
import os.path
import platform
import re
import urllib.error
from typing import Any
from urllib.request import urlopen

MACHINE_SUFFIX = {
    "Darwin": {
        "arm64": "aarch64-apple-darwin-install_only.tar.gz",
        "x86_64": "x86_64-apple-darwin-install_only.tar.gz",
    },
    "Linux": {
        "aarch64": {
            "glibc": "aarch64-unknown-linux-gnu-install_only.tar.gz",
            # musl doesn't exist
        },
        "x86_64": {
            "glibc": "x86_64_v3-unknown-linux-gnu-install_only.tar.gz",
            "musl": "x86_64_v3-unknown-linux-musl-install_only.tar.gz",
        },
    },
    "Windows": {"AMD64": "x86_64-pc-windows-msvc-shared-install_only.tar.gz"},
}

GITHUB_API_URL = (
    "https://api.github.com/repos/indygreg/python-build-standalone/releases/latest"
)
PYTHON_VERSION_REGEX = re.compile(r"cpython-(\d+\.\d+\.\d+)")


def fallback_release_data() -> dict[str, Any]:
    """Returns the fallback release data, for when GitHub API gives an error."""
    print("\033[33mWarning: GitHub unreachable. Using fallback release data.\033[m")
    data_file = os.path.join(os.path.dirname(__file__), "fallback_release_data.json")
    with open(data_file) as data:
        return json.load(data)


class NotAvailable(Exception):
    """Raised when the asked Python version is not available."""


def get_latest_python_releases() -> list[str]:
    """Returns the list of python download links from the latest github release."""
    try:
        with urlopen(GITHUB_API_URL) as response:
            release_data = json.load(response)

    except urllib.error.URLError:
        # raise
        release_data = fallback_release_data()

    return [asset["browser_download_url"] for asset in release_data["assets"]]


def list_pythons() -> dict[str, str]:
    """Returns available python versions for your machine and their download links."""
    system, machine = platform.system(), platform.machine()
    download_link_suffix = MACHINE_SUFFIX[system][machine]
    # linux suffixes are nested under glibc or musl builds
    if system == "Linux":
        # fallback to musl if libc version is not found
        libc_version = platform.libc_ver()[0] or "musl"
        download_link_suffix = download_link_suffix[libc_version]

    python_releases = get_latest_python_releases()

    available_python_links = [
        link for link in python_releases if link.endswith(download_link_suffix)
    ]

    python_versions: dict[str, str] = {}
    for link in available_python_links:
        match = PYTHON_VERSION_REGEX.search(link)
        assert match is not None
        python_version = match[1]
        python_versions[python_version] = link

    sorted_python_versions = {
        version: python_versions[version]
        for version in sorted(
            python_versions,
            # sort by semver
            key=lambda version: [int(k) for k in version.split(".")],
            reverse=True,
        )
    }
    return sorted_python_versions


def _parse_python_version(version: str) -> tuple[int, ...]:
    return tuple(int(k) for k in version.split("."))


def resolve_python_version(requested_version: str | None) -> None:
    pythons = list_pythons()

    if requested_version is None:
        sorted_pythons = sorted(
            pythons.items(),
            key=lambda version_link: _parse_python_version(version_link[0]),
            reverse=True,
        )
        latest_version, download_link = sorted_pythons[0]
        return latest_version, download_link

    for version, version_download_link in pythons.items():
        if version.startswith(requested_version):
            python_version = version
            download_link = version_download_link
            break
    else:
        raise NotAvailable

    return python_version, download_link
