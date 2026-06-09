# -*- coding: utf-8 -*-
"""
Copyright (C) 2026 brkzlr <brksys@icloud.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import socket
import struct
import pickle
import shelve
from dataclasses import dataclass
from time import sleep
from typing import Any

import msgpack

from . import debugcore, utils, typedefs
from .utils import logger

# The active collector connection for the current process or None.
_client: "MonoClient | None" = None

_RUNTIME_PATTERNS = [
    ("mono", "sysv", r"libmono(sgen|bdwgc)?-2\.0\.so"),
    ("mono", "win64", r"mono-2\.0-bdwgc\.dll"),
    ("il2cpp", "sysv", r"libil2cpp\.so"),
    ("il2cpp", "win64", r"GameAssembly\.dll"),
]


@dataclass
class RuntimeInfo:
    kind: str  # "mono" || "il2cpp"
    abi: str  # "sysv" || "win64"
    load_bias: int
    module_path: str


class MonoError(Exception):
    """Raised when the collector returns an error response."""


def detect_runtime(pid: int) -> RuntimeInfo | None:
    """Detect the managed runtime mapped into the given process

    Args:
        pid (int): PID of the process

    Returns:
        RuntimeInfo: kind/abi/load_bias/module_path of the detected runtime
        None: If no supported managed runtime is mapped
    """
    for kind, abi, pattern in _RUNTIME_PATTERNS:
        module = utils.get_module_load_bias(pid, pattern)
        if module is not None:
            load_bias, path = module
            return RuntimeInfo(kind, abi, load_bias, path)
    return None


def _collector_path() -> str:
    """Returns the collector .so path for the current inferior's arch."""
    base = os.path.join(os.path.dirname(__file__), "libmono_collector")
    if debugcore.inferior_arch == typedefs.INFERIOR_ARCH.ARCH_32:
        return os.path.join(base, "mono_collector_x86.so")
    return os.path.join(base, "mono_collector_x64.so")


def _abstract_address(pid: int) -> bytes:
    """Abstract namespace Unix socket address that the agent binds to."""
    return b"\x00pince-mono-" + str(pid).encode("ascii")


def _try_connect(pid: int, retries: int = 1, delay: float = 0.05) -> "MonoClient | None":
    """Attempts to connect to an already running collector agent."""
    address = _abstract_address(pid)
    for _ in range(retries):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(address)
            return MonoClient(sock)
        except OSError:
            sock.close()
            sleep(delay)
    return None


def init_mono() -> bool:
    """Ensure a collector agent is injected and connected for the current process

    Reuses an existing connection/agent if present.
    Only acts on native Linux Mono targets for now

    Returns:
        bool: True if a connected MonoClient is ready, False otherwise
    """
    global _client
    pid = debugcore.currentpid
    if pid == -1:
        return False

    # Agent may already be resident from a previous attach.
    client = _try_connect(pid, retries=1)
    if client is None:
        info = detect_runtime(pid)
        if info is None or info.kind != "mono" or info.abi != "sysv":
            return False  # GUI decides the message
        so_path = _collector_path()
        if not os.path.exists(so_path):
            logger.error(f"Mono collector not built: {so_path}")
            return False
        if not debugcore.inject_so(so_path):
            logger.error("Failed to inject Mono collector!")
            return False
        client = _try_connect(pid, retries=40, delay=0.05)
        if client is None:
            # Fallback: explicitly invoke the exported init in case the ctor didn't fire.
            debugcore.call_function_from_inferior("pince_mono_init()")
            client = _try_connect(pid, retries=40, delay=0.05)
        if client is None:
            logger.error("Mono collector did not come up!")
            return False

    _client = client
    return True


def get_client() -> "MonoClient | None":
    """Returns the active MonoClient or None if init_mono() hasn't succeeded."""
    return _client


class MonoClient:
    """Msgpack request/response client to the collector agent."""

    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock

    def _recv_exact(self, n: int) -> bytes:
        chunks = []
        got = 0
        while got < n:
            chunk = self.sock.recv(n - got)
            if not chunk:
                raise MonoError("connection closed")
            chunks.append(chunk)
            got += len(chunk)
        return b"".join(chunks)

    def request(self, op: str, **args: Any) -> Any:
        """Send one request frame, return the decoded "data" (or raise MonoError)"""
        payload = msgpack.packb({"op": op, **args}, use_bin_type=False)
        self.sock.sendall(struct.pack(">I", len(payload)) + payload)
        (length,) = struct.unpack(">I", self._recv_exact(4))
        response = msgpack.unpackb(self._recv_exact(length), raw=False)
        if not response.get("ok"):
            raise MonoError(response.get("error", "unknown error"))
        return response.get("data")

    def hello(self) -> dict:
        return self.request("hello")

    def assemblies(self) -> list[dict]:
        return self.request("assemblies")

    def classes(self, image: int) -> list[dict]:
        return self.request("classes", image=image)

    def fields(self, klass: int) -> list[dict]:
        return self.request("fields", klass=klass)

    def methods(self, klass: int) -> list[dict]:
        return self.request("methods", klass=klass)

    def compile_method(self, method: int) -> int:
        return self.request("compile", method=method)["native_addr"]

    def static_field_address(self, klass: int, field: int) -> int:
        return self.request("static_addr", klass=klass, field=field)["address"]

    def find_class(self, image: int, namespace: str, name: str) -> int:
        return self.request("find_class", image=image, namespace=namespace, name=name)["klass"]

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass


def _write_status(pid: int, current: int, total: int) -> None:
    try:
        with open(utils.get_mono_status_file(pid), "wb") as handle:
            pickle.dump((current, total), handle)
    except OSError:
        pass


def get_status() -> tuple[int, int]:
    """Returns (assemblies_done, assemblies_total) for the GUI progress bar."""
    try:
        with open(utils.get_mono_status_file(debugcore.currentpid), "rb") as handle:
            return pickle.load(handle)
    except Exception:
        return 0, 0


def dissect_mono() -> bool:
    """Enumerate assemblies + their classes and persist to the shelve cache.

    Fields/methods are fetched lazily by the GUI on expansion.
    Mirrors the debugcore.dissect_code() persistence pattern.

    Returns:
        bool: True on success, False if the collector isn't ready
    """
    if _client is None:
        return False
    pid = debugcore.currentpid
    if pid == -1:
        return False

    assemblies = _client.assemblies()
    with shelve.open(utils.get_mono_data_file(pid)) as db:
        db["assemblies"] = assemblies
        total = len(assemblies)
        for index, assembly in enumerate(assemblies):
            _write_status(pid, index, total)
            db[f"img:{assembly['image']}"] = _client.classes(assembly["image"])
        _write_status(pid, total, total)
    return True
