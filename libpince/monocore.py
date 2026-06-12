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
    ("mono", "sysv", r"^mono-sgen$|^mono-boehm$|^mono$"),
    ("mono", "win64", r"mono-2\.0-bdwgc\.dll"),
    ("il2cpp", "sysv", r"GameAssembly\.so"),
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


def _collector_path(wine: bool = False) -> str:
    """Returns the collector .so path for the current inferior's arch / ABI.

    Four variants: native Linux and WINE/Proton, both x64 and x86.
    If AppImage, the .so is inside a FUSE mount that the target process cannot access,
    so we copy it to /tmp first.
    """
    base = os.path.join(os.path.dirname(__file__), "libmono_collector")
    arch32 = debugcore.inferior_arch == typedefs.INFERIOR_ARCH.ARCH_32
    if wine:
        src = os.path.join(base, "mono_collector_wine_x86.so" if arch32 else "mono_collector_wine_x64.so")
    elif arch32:
        src = os.path.join(base, "mono_collector_x86.so")
    else:
        src = os.path.join(base, "mono_collector_x64.so")

    appdir = os.environ.get("APPDIR")
    if appdir and os.path.commonpath([src, appdir]) == appdir:
        import shutil
        import tempfile

        dst = os.path.join(tempfile.gettempdir(), os.path.basename(src))
        if not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst):
            shutil.copy2(src, dst)
            os.chmod(dst, 0o755)
        return dst
    return src


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
    Acts on native Linux Mono/IL2CPP (sysv) and Wine/Proton (win64) targets, both x64 and x86.

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
        if info is None or info.kind not in ("mono", "il2cpp") or info.abi not in ("sysv", "win64"):
            return False  # GUI decides the message
        so_path = _collector_path(info.abi == "win64")
        if not os.path.exists(so_path):
            logger.error(f"Mono collector not built: {so_path}")
            return False
        try:
            if not debugcore.inject_so(so_path):
                logger.error("Failed to inject Mono collector!")
                return False
            client = _try_connect(pid, retries=80, delay=0.05)
        except typedefs.GDBInitializeException:
            logger.error("GDB became unavailable while injecting the Mono collector")
            return False
        if client is None:
            logger.error("Mono collector did not come up!")
            return False

    _client = client
    return True


def get_client() -> "MonoClient | None":
    """Returns the active MonoClient or None if init_mono() hasn't succeeded."""
    return _client


# Invoke argument marshalling.
# Value type args/returns travel as a type tag + raw bit pattern (a uint) but the collector
# writes/reads the native bytes.
# Mirrors the tags emitted by the collector's signature op (see mono_api.zig typeTag).
_INT_WIDTH = {"i1": 1, "u1": 1, "i2": 2, "u2": 2, "char": 2, "i4": 4, "u4": 4, "i8": 8, "u8": 8}


def _arg_to_bits(tag: str, value: Any) -> int:
    """Encode a Python value into the raw bit pattern the collector expects for tag."""
    if tag == "nil":
        return 0
    if tag == "object":
        return int(value) & 0xFFFFFFFFFFFFFFFF
    if tag == "bool":
        return 1 if value else 0
    if tag == "r4":
        return struct.unpack("<I", struct.pack("<f", float(value)))[0]
    if tag == "r8":
        return struct.unpack("<Q", struct.pack("<d", float(value)))[0]
    if tag == "char" and isinstance(value, str):
        value = ord(value[0]) if value else 0
    width = _INT_WIDTH.get(tag)
    if width is None:
        raise MonoError(f"unsupported argument type {tag}")
    return int(value) & ((1 << (8 * width)) - 1)


def _bits_to_value(tag: str, bits: int) -> Any:
    """Reinterpret a raw bit pattern from the collector back into a Python value."""
    if tag == "r4":
        return struct.unpack("<f", struct.pack("<I", bits & 0xFFFFFFFF))[0]
    if tag == "r8":
        return struct.unpack("<d", struct.pack("<Q", bits & 0xFFFFFFFFFFFFFFFF))[0]
    if tag == "bool":
        return bool(bits & 1)
    if tag == "char":
        return chr(bits & 0xFFFF)
    width = _INT_WIDTH.get(tag)
    if width is None:
        return bits  # object / native pointer
    value = bits & ((1 << (8 * width)) - 1)
    if tag.startswith("i") and value >= (1 << (8 * width - 1)):
        value -= 1 << (8 * width)
    return value


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

    def class_info(self, klass: int) -> dict:
        """Return {namespace, name, parent} for a class handle."""
        return self.request("class_info", klass=klass)

    def type_klass(self, field: int) -> int:
        """Return the klass handle of a field's declared type or 0 if unresolvable."""
        return self.request("type_klass", field=field)["klass"]

    def signature(self, method: int) -> dict:
        """Return {ret:{tag,name}, params:[{name,tag,type}]} for a method handle."""
        return self.request("signature", method=method)

    def invoke(self, method: int, obj: int = 0, args: list[tuple[str, Any]] | None = None) -> dict:
        """Invoke a managed method. args is a list of (type_tag, value) pairs.

        Returns {"result": <decoded value or None>, "tag": <type tag or None>, "exception": <ptr>}.
        """
        wire_args = [[tag, value if tag == "str" else _arg_to_bits(tag, value)] for tag, value in (args or [])]
        response = self.request("invoke", method=method, obj=obj, args=wire_args)
        result = response.get("result")
        decoded, tag = None, None
        if result is not None:
            tag = result.get("tag")
            decoded = result.get("val") if tag == "str" else _bits_to_value(tag, result.get("bits", 0))
        return {"result": decoded, "tag": tag, "exception": response.get("exception", 0)}

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass
