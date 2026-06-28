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
from .libmemscan.memscan import Libmemscan, DataType, MatchType, ScanLevel

# The active collector connection for the current process or None.
_client: "MonoClient | None" = None

_RUNTIME_PATTERNS = [
    ("mono", "elf", r"libmono(sgen|bdwgc)?-2\.0\.so"),
    ("mono", "elf", r"^mono-sgen$|^mono-boehm$|^mono$"),
    ("mono", "pe", r"mono-2\.0-bdwgc\.dll"),
    ("il2cpp", "elf", r"GameAssembly\.so"),
    ("il2cpp", "pe", r"GameAssembly\.dll"),
]


@dataclass
class RuntimeInfo:
    kind: str  # "mono" || "il2cpp"
    module_format: str  # "elf" || "pe"
    load_bias: int
    module_path: str


class MonoError(Exception):
    """Raised when the collector returns an error response."""


def detect_runtime(pid: int) -> RuntimeInfo | None:
    """Detect the managed runtime mapped into the given process

    Args:
        pid (int): PID of the process

    Returns:
        RuntimeInfo: kind/module_format/load_bias/module_path of the detected runtime
        None: If no supported managed runtime is mapped
    """
    for kind, module_format, pattern in _RUNTIME_PATTERNS:
        module = utils.get_module_load_bias(pid, pattern)
        if module is not None:
            load_bias, path = module
            return RuntimeInfo(kind, module_format, load_bias, path)
    return None


def _collector_path(wine: bool, arch32: bool) -> str:
    """Returns the collector agent path for the given format / bitness."""
    bits = "x86" if arch32 else "x64"
    name = f"mono_collector{'_wine' if wine else ''}_{bits}.{'dll' if wine else 'so'}"
    src = os.path.join(os.path.dirname(__file__), "libmono_collector", name)

    # AppImage FUSE paths may be inaccessible to the target process.
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


def _connect(family: int, address, retries: int = 1, delay: float = 0.05) -> "MonoClient | None":
    """Connects to a resident collector: abstract Unix socket (native) or loopback TCP (WINE/Proton)."""
    for _ in range(retries):
        sock = socket.socket(family, socket.SOCK_STREAM)
        try:
            sock.connect(address)
            if family == socket.AF_INET:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # frames are tiny header + body
            return MonoClient(sock)
        except OSError:
            sock.close()
            sleep(delay)
    return None


def _wine_port_addr(mem, base: int) -> int:
    def u(addr: int, n: int) -> int:
        mem.seek(addr)
        return int.from_bytes(mem.read(n), "little")

    try:
        if u(base, 2) != 0x5A4D:
            return 0
        pe = base + u(base + 0x3C, 4)
        if u(pe, 4) != 0x4550:
            return 0
        opt = pe + 0x18
        dd = opt + (0x70 if u(opt, 2) == 0x20B else 0x60)
        ed_rva, ed_size = u(dd, 4), u(dd + 4, 4)
        if not ed_rva:
            return 0
        ed = base + ed_rva
        funcs, names, ords = (base + u(ed + off, 4) for off in (0x1C, 0x20, 0x24))
        want = b"pince_mono_port\x00"
        for i in range(u(ed + 0x18, 4)):
            mem.seek(base + u(names + i * 4, 4))
            if mem.read(len(want)) == want:
                rva = u(funcs + u(ords + i * 2, 2) * 4, 4)
                return 0 if ed_rva <= rva < ed_rva + ed_size else base + rva
    except (OSError, ValueError):
        pass
    return 0


def _connect_wine(pid: int, retries: int = 1, delay: float = 0.05) -> "MonoClient | None":
    """Locate the WINE/Proton collector via its exported port then connect."""
    for _ in range(retries):
        module = utils.get_module_load_bias(pid, r"mono_collector_wine_(x86|x64)\.dll")
        if module is not None:
            try:
                with debugcore.memory_handle() as mem:
                    port_addr = _wine_port_addr(mem, module[0])
                    if port_addr:
                        mem.seek(port_addr)
                        port = int.from_bytes(mem.read(2), "little")
                        if port:
                            client = _connect(socket.AF_INET, ("127.0.0.1", port), delay=0)
                            if client is not None:
                                return client
            except (OSError, ValueError):
                pass
        sleep(delay)
    return None


def init_mono() -> bool:
    """Ensure a collector agent is injected and connected for the current process

    Reuses an existing connection/agent if present.
    Acts on native Linux Mono/IL2CPP and Wine/Proton targets, both x64 and x86.

    Returns:
        bool: True if a connected MonoClient is ready, False otherwise
    """
    global _client
    pid = debugcore.currentpid
    if pid == -1:
        return False

    info = detect_runtime(pid)
    if info is None:
        return False  # GUI decides the message
    wine = info.module_format == "pe"

    # Agent may already be resident from a previous attach/dissect.
    client = _connect_wine(pid) if wine else _connect(socket.AF_UNIX, _abstract_address(pid))

    if client is None:
        arch32 = debugcore.inferior_arch == typedefs.INFERIOR_ARCH.ARCH_32
        if wine:
            # new-WoW64 can map a 32-bit PE runtime in a 64-bit Linux process.
            # Trust the runtime PE magic and not the inferior_arch.
            try:
                with debugcore.memory_handle() as mem:
                    mem.seek(info.load_bias + 0x3C)
                    mem.seek(info.load_bias + int.from_bytes(mem.read(4), "little") + 0x18)
                    magic = int.from_bytes(mem.read(2), "little")
                    if magic in (0x10B, 0x20B):
                        arch32 = magic == 0x10B
            except (OSError, ValueError):
                pass

        lib_path = _collector_path(wine, arch32)
        if not os.path.exists(lib_path):
            logger.error(f"Mono collector not built: {lib_path}")
            return False
        try:
            injected = debugcore.inject_dll(lib_path) if wine else debugcore.inject_so(lib_path)
            if not injected:
                logger.error("Failed to inject Mono collector!")
                return False
            # LoadLibraryW injection runs after resume, so WINE gets a longer poll window.
            client = _connect_wine(pid, retries=160) if wine else _connect(socket.AF_UNIX, _abstract_address(pid), retries=80)
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


def reset() -> None:
    """Drop the active collector connection.

    Call when the inferior changes/exits so get_client() doesn't hand back a client
    whose socket points at a process that's gone.
    """
    global _client
    if _client is not None:
        _client.close()
        _client = None


# Invoke argument marshalling.
# Value type args/returns travel as a type tag + raw bit pattern (a uint) but the collector
# writes/reads the native bytes.
# Mirrors the tags emitted by the collector's signature op (see mono_api.zig typeTag).
_INT_WIDTH = {"i1": 1, "u1": 1, "i2": 2, "u2": 2, "char": 2, "i4": 4, "u4": 4, "i8": 8, "u8": 8}


def _arg_to_bits(tag: str, value: Any) -> int:
    """Encode a Python value into the raw bit pattern the collector expects for tag."""
    try:
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
    except (TypeError, ValueError, OverflowError, struct.error) as e:
        raise MonoError(f"invalid value for type {tag}: {e}") from e


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


# Struct (value type) marshalling: a struct travels as the raw bytes of its unboxed value.
_PACKABLE_TAGS = set(_INT_WIDTH) | {"r4", "r8", "bool"}


def _value_width(tag: str) -> int:
    if tag == "r4":
        return 4
    if tag == "r8":
        return 8
    if tag == "bool":
        return 1
    width = _INT_WIDTH.get(tag)
    if width is None:
        raise MonoError(f"cannot size value of type {tag}")
    return width


def pack_value(tag: str, value: Any) -> bytes:
    """Little-endian bytes for a primitive value (assembling a struct argument)."""
    return _arg_to_bits(tag, value).to_bytes(_value_width(tag), "little")


def unpack_value(tag: str, raw: bytes) -> Any:
    """A primitive value read back from its little-endian bytes (a struct field)."""
    return _bits_to_value(tag, int.from_bytes(raw, "little"))


def object_header_size() -> int:
    """Bytes of the object header (vtable/klass + sync word) prefixing a boxed value type.
    Value type field offsets from the fields op include it, so subtract it for the unboxed value."""
    ptr = 4 if debugcore.inferior_arch == typedefs.INFERIOR_ARCH.ARCH_32 else 8
    return 2 * ptr


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
        try:
            self.sock.sendall(struct.pack(">I", len(payload)) + payload)
            (length,) = struct.unpack(">I", self._recv_exact(4))
            response = msgpack.unpackb(self._recv_exact(length), raw=False)
        except OSError as e:
            raise MonoError(f"collector connection lost: {e}")
        if not isinstance(response, dict):
            raise MonoError("malformed response from collector")
        if not response.get("ok"):
            raise MonoError(response.get("error", "unknown error"))
        return response.get("data")

    def assemblies(self) -> list[dict]:
        return self.request("assemblies")

    def classes(self, image: int) -> list[dict]:
        return self.request("classes", image=image)

    def fields(self, klass: int) -> list[dict]:
        return self.request("fields", klass=klass)

    def methods(self, klass: int) -> list[dict]:
        return self.request("methods", klass=klass)

    def compile_method(self, method: int) -> int:
        result = self.request("compile", method=method)
        addr = result.get("native_addr") if isinstance(result, dict) else None
        if addr is None:
            raise MonoError("malformed response: missing 'native_addr'")
        return addr

    def static_field_address(self, klass: int, field: int) -> int:
        result = self.request("static_addr", klass=klass, field=field)
        addr = result.get("address") if isinstance(result, dict) else None
        if addr is None:
            raise MonoError("malformed response: missing 'address'")
        return addr

    def class_info(self, klass: int) -> dict:
        """Return {namespace, name, parent} for a class handle."""
        return self.request("class_info", klass=klass)

    def type_klass(self, field: int) -> int:
        """Return the klass handle of a field's declared type or 0 if unresolvable."""
        result = self.request("type_klass", field=field)
        klass = result.get("klass") if isinstance(result, dict) else None
        if klass is None:
            raise MonoError("malformed response: missing 'klass'")
        return klass

    def instance_marker(self, klass: int) -> int:
        """Return the marker every live instance carries in word 0 (Mono: MonoVTable*, IL2CPP: klass)."""
        result = self.request("instance_marker", klass=klass)
        marker = result.get("marker") if isinstance(result, dict) else None
        if marker is None:
            raise MonoError("malformed response: missing 'marker'")
        return marker

    def signature(self, method: int) -> dict:
        """Return {ret:{tag,name}, params:[{name,tag,type}]} for a method handle.
        struct (value-type) params/ret also carry {klass, size} for marshalling.
        """
        return self.request("signature", method=method)

    def struct_fields(self, klass: int) -> list[dict] | None:
        """Instance fields of a value type, offsets relative to the unboxed value.
        None if any field isn't a packable primitive (caller falls back to raw bytes).
        """
        header = object_header_size()
        layout = []
        try:
            for fld in self.fields(klass):
                if fld["is_static"]:
                    continue
                if fld["tag"] not in _PACKABLE_TAGS:
                    return None
                layout.append(
                    {
                        "name": fld["name"],
                        "tag": fld["tag"],
                        "type": fld["type"],
                        "offset": fld["offset"] - header,
                        "width": _value_width(fld["tag"]),
                    }
                )
        except (KeyError, TypeError) as e:
            raise MonoError(f"malformed field in collector response: {e}") from e
        return layout

    def invoke(self, method: int, obj: int = 0, args: list[tuple[str, Any]] | None = None) -> dict:
        """Invoke a managed method. args is a list of (type_tag, value) pairs.
        A "struct" arg's value is the raw bytes of its unboxed value.

        Returns {"result": <decoded value, bytes for a struct, or None>, "tag": <tag or None>, "exception": <ptr>}.
        """
        wire_args = [[tag, value if tag in ("str", "struct") else _arg_to_bits(tag, value)] for tag, value in (args or [])]
        response = self.request("invoke", method=method, obj=obj, args=wire_args)
        result = response.get("result")
        decoded, tag = None, None
        if result is not None:
            tag = result.get("tag")
            if tag == "str":
                decoded = result.get("val")
            elif tag == "struct":
                decoded = result.get("bytes", b"")
            else:
                decoded = _bits_to_value(tag, result.get("bits", 0))
        return {"result": decoded, "tag": tag, "exception": response.get("exception", 0)}

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass


def find_instances(klass: int) -> list[int]:
    """Find live instance addresses of a class.
    Scan target memory for its instance marker (an object's header word) via a private Libmemscan
    so the main window scan is left intact (if any).

    Raises MonoError if the marker can't be resolved.
    Returns [] if none are mapped.
    """
    client = get_client()
    if client is None or debugcore.currentpid == -1:
        return []
    marker = client.instance_marker(klass)
    if not marker:
        raise MonoError("instance marker unavailable")
    arch32 = debugcore.inferior_arch == typedefs.INFERIOR_ARCH.ARCH_32
    so_path = os.path.join(utils.get_libpince_directory(), "libmemscan", "libmemscan.so")
    scanner = Libmemscan(so_path)
    try:
        scanner.attach(debugcore.currentpid)
        scanner.set_data_type(DataType.INTEGER32 if arch32 else DataType.INTEGER64)
        scanner.set_scan_level(ScanLevel.ALL_RW)
        scanner.set_alignment(4 if arch32 else 8)
        scanner.reset()
        scanner.scan(MatchType.MATCHEQUALTO, marker)
        return [match.address for match in scanner.matches()]
    finally:
        scanner.close()
