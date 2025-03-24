from __future__ import annotations

import json
import os.path
import platform
import re
import sys
import typing
import urllib.error
from typing import Any, TypedDict
import urllib.parse
from urllib.request import urlopen

LAST_TAG_FOR_I686_LINUX = "118809599"  # tag name: "20230826"

MACHINE_SUFFIX: dict[str, dict[str, Any]] = {
    "Darwin": {
        "arm64": ["aarch64-apple-darwin-install_only.tar.gz"],
        "x86_64": ["x86_64-apple-darwin-install_only.tar.gz"],
    },
    "Linux": {
        "aarch64": {
            "glibc": ["aarch64-unknown-linux-gnu-install_only.tar.gz"],
            # musl doesn't exist
        },
        "x86_64": {
            "glibc": [
                "x86_64_v3-unknown-linux-gnu-install_only.tar.gz",
                "x86_64-unknown-linux-gnu-install_only.tar.gz",
            ],
            "musl": ["x86_64_v3-unknown-linux-musl-install_only.tar.gz"],
        },
        "i686": {
            "glibc": ["i686-unknown-linux-gnu-install_only.tar.gz"],
            # musl doesn't exist
        },
    },
    "Windows": {
        "AMD64": ["x86_64-pc-windows-msvc-install_only.tar.gz"],
        "i686": ["i686-pc-windows-msvc-install_only.tar.gz"],
    },
}

GITHUB_API_RELEASES_URL = (
    "https://api.github.com/repos/astral-sh/python-build-standalone/releases/"
)
PYTHON_VERSION_REGEX = re.compile(r"cpython-(\d+\.\d+\.\d+)")


class GitHubReleaseData(TypedDict):
    id: int
    html_url: str
    assets: list[GitHubAsset]


class GitHubAsset(TypedDict):
    browser_download_url: str


def trim_github_release_data(release_data: dict[str, Any]) -> GitHubReleaseData:
    return {
        "id": release_data["id"],
        "html_url": release_data["html_url"],
        "assets": [
            {"browser_download_url": asset["browser_download_url"]}
            for asset in release_data["assets"]
        ],
    }


def fallback_release_data() -> GitHubReleaseData:
    """Returns the fallback release data, for when GitHub API gives an error."""
    print(
        "\033[33mWarning: GitHub unreachable. Using fallback release data.\033[m",
        file=sys.stderr,
    )
    data_file = os.path.join(os.path.dirname(__file__), "fallback_release_data.json")
    with open(data_file) as data:
        return typing.cast(GitHubReleaseData, json.load(data))


class NotAvailable(Exception):
    """Raised when the asked Python version is not available."""


def get_latest_python_releases(is_linux_i686: bool) -> GitHubReleaseData:
    """Returns the list of python download links from the latest github release."""
    # They stopped shipping for 32 bit linux since after the 20230826 tag
    if is_linux_i686:
        data_file = os.path.join(os.path.dirname(__file__), "linux_i686_release.json")
        with open(data_file) as data:
            return typing.cast(GitHubReleaseData, json.load(data))

    latest_release_url = urllib.parse.urljoin(GITHUB_API_RELEASES_URL, "latest")
    try:
        with urlopen(latest_release_url) as response:
            release_data = typing.cast(GitHubReleaseData, json.load(response))

    except urllib.error.URLError:
        release_data = fallback_release_data()

    return release_data


def list_pythons() -> dict[str, str]:
    """Returns available python versions for your machine and their download links."""
    system, machine = platform.system(), platform.machine()
    download_link_suffixes = MACHINE_SUFFIX[system][machine]
    # linux suffixes are nested under glibc or musl builds
    if system == "Linux":
        # fallback to musl if libc version is not found
        libc_version = platform.libc_ver()[0] or "musl"
        download_link_suffixes = download_link_suffixes[libc_version]

    is_linux_i686 = system == "Linux" and machine == "i686"
    releases = get_latest_python_releases(is_linux_i686)
    python_releases = [asset["browser_download_url"] for asset in releases["assets"]]

    available_python_links = [
        link
        # Suffixes are in order of preference.
        for download_link_suffix in download_link_suffixes
        for link in python_releases
        if link.endswith(download_link_suffix)
    ]

    python_versions: dict[str, str] = {}
    for link in available_python_links:
        match = PYTHON_VERSION_REGEX.search(link)
        assert match is not None
        python_version = match[1]
        # Don't override already found versions, as they are in order of preference
        if python_version in python_versions:
            continue

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


def resolve_python_version(requested_version: str | None) -> tuple[str, str]:
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
