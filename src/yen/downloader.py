"""Taken from https://github.com/textualize/rich/blob/ec91917/examples/downloader.py"""

from __future__ import annotations

from http.client import HTTPResponse
import os.path
import signal
from functools import partial
from threading import Event
from urllib.request import urlopen

from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

SUFFIX_32BIT = "_32bit"

PROGRESS = Progress(
    TextColumn("[bold blue]{task.fields[display_name]}"),
    BarColumn(bar_width=None),
    "[progress.percentage]{task.percentage:>3.1f}%",
    "•",
    DownloadColumn(),
    "•",
    TransferSpeedColumn(),
    "•",
    TimeRemainingColumn(),
)


DONE = Event()


def handle_sigint(_: object, __: object) -> None:
    DONE.set()


signal.signal(signal.SIGINT, handle_sigint)


def read_url(url: str) -> str:
    """Reads the contents of the URL."""
    response: HTTPResponse = urlopen(url)
    return response.read().decode()


def download(url: str, display_name: str, directory: str, is_32bit: bool) -> str:
    """Downloads file to the given directory. Returns path to downloaded file."""
    with PROGRESS:
        filename = url.split("/")[-1]
        if is_32bit:
            filename += SUFFIX_32BIT

        filepath = os.path.join(directory, filename)
        task_id = PROGRESS.add_task("download", display_name=display_name, start=False)
        response = urlopen(url)

        # This will break if the response doesn't contain content length
        PROGRESS.update(task_id, total=int(response.info()["Content-length"]))
        with open(filepath, "wb") as file:
            PROGRESS.start_task(task_id)
            for data in iter(partial(response.read, 32768), b""):
                file.write(data)
                PROGRESS.update(task_id, advance=len(data))

    return filepath
