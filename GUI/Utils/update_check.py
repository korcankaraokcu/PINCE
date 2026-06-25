import hashlib
import json
import os
import ssl
import sys
import urllib.request
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

from PyQt6.QtCore import QThread


class UpdateCheckStatus(Enum):
    UPDATE_AVAILABLE = auto()
    UP_TO_DATE = auto()
    ERROR = auto()


@dataclass(frozen=True)
class UpdateCheckResult:
    status: UpdateCheckStatus
    message: str = ""


class UpdateCheckThread(QThread):
    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.result = UpdateCheckResult(UpdateCheckStatus.ERROR, "Update check did not finish")

    def run(self) -> None:
        self.result = check_for_update()


def check_for_update() -> UpdateCheckResult:
    try:
        appimage_path = os.environ.get("APPIMAGE")
        if not appimage_path or not os.path.isfile(appimage_path):
            raise RuntimeError("Not running from an AppImage")
        config = _read_config()
        if config.get("type") != "zsync":
            raise ValueError("Unsupported update check config")
        zsync_url = config["url"]
        zsync_headers = _fetch_zsync_headers(zsync_url)
        remote_sha1 = zsync_headers.get("sha-1")
        if remote_sha1:
            with open(appimage_path, "rb") as appimage:
                local_sha1 = hashlib.file_digest(appimage, "sha1").hexdigest()
            return _get_result(local_sha1.lower() != remote_sha1.lower())
        remote_length = zsync_headers.get("length")
        if remote_length:
            return _get_result(os.path.getsize(appimage_path) != int(remote_length))
        raise ValueError("The update metadata does not contain a comparable file hash or size")
    except Exception as exc:
        return UpdateCheckResult(UpdateCheckStatus.ERROR, str(exc))


def _get_result(update_available: bool) -> UpdateCheckResult:
    status = UpdateCheckStatus.UPDATE_AVAILABLE if update_available else UpdateCheckStatus.UP_TO_DATE
    return UpdateCheckResult(status)


def _read_config() -> dict[str, Any]:
    with open(os.path.join(sys.path[0], "update-check.json"), encoding="utf-8") as config_file:
        config = json.load(config_file)
    if not isinstance(config, dict):
        raise ValueError("Update config must be a JSON object")
    return config


def _fetch_zsync_headers(url: str) -> dict[str, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "PINCE update checker"})
    with urllib.request.urlopen(request, timeout=10, context=_get_ssl_context()) as response:
        data = response.read(65536)
    text = data.decode("utf-8", errors="replace")
    headers: dict[str, str] = {}
    for line in text.splitlines():
        if not line:
            break
        key, sep, value = line.partition(":")
        if sep:
            headers[key.strip().lower()] = value.strip()
    return headers


def _get_ssl_context() -> ssl.SSLContext:
    cafile = os.path.join(os.environ.get("APPDIR", ""), "usr/conda/ssl/cacert.pem")
    if os.path.isfile(cafile):
        return ssl.create_default_context(cafile=cafile)
    return ssl.create_default_context()
