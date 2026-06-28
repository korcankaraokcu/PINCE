// Copyright (C) 2026 brkzlr <brksys@icloud.com>
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

//! Entry + worker thread + request server + op dispatch.
//! The worker attaches to the Mono domain and serves frames over a socket.
const std = @import("std");
const linux = std.os.linux;
const common = @import("common.zig");
const rt = @import("runtime.zig");
const msgpack = @import("msgpack.zig");
const Encoder = msgpack.Encoder;
const eql = common.eql;

const EINTR = -@as(isize, @intFromEnum(linux.E.INTR));
const ws = std.os.windows.ws2_32;

var started = std.atomic.Value(bool).init(false);

// Transport: ELF uses a raw syscall abstract Unix socket while the PE DLL uses Winsock TCP on 127.0.0.1,
// because WINE's seccomp filter kills direct Linux syscalls from PE code (SIGSYS).
const Sock = if (common.is_windows) usize else i32;

var wine_port: u16 = 0;
comptime {
    if (common.is_windows) @export(&wine_port, .{ .name = "pince_mono_port" });
}

const win = if (common.is_windows) struct {
    extern "ws2_32" fn WSAStartup(version: u16, data: *anyopaque) callconv(.winapi) c_int;
    extern "ws2_32" fn socket(af: c_int, kind: c_int, protocol: c_int) callconv(.winapi) usize;
    extern "ws2_32" fn bind(s: usize, name: *const anyopaque, namelen: c_int) callconv(.winapi) c_int;
    extern "ws2_32" fn listen(s: usize, backlog: c_int) callconv(.winapi) c_int;
    extern "ws2_32" fn accept(s: usize, addr: ?*anyopaque, addrlen: ?*c_int) callconv(.winapi) usize;
    extern "ws2_32" fn getsockname(s: usize, name: *anyopaque, namelen: *c_int) callconv(.winapi) c_int;
    extern "ws2_32" fn setsockopt(s: usize, level: c_int, optname: c_int, optval: [*]const u8, optlen: c_int) callconv(.winapi) c_int;
    extern "ws2_32" fn recv(s: usize, buf: [*]u8, len: c_int, flags: c_int) callconv(.winapi) c_int;
    extern "ws2_32" fn send(s: usize, buf: [*]const u8, len: c_int, flags: c_int) callconv(.winapi) c_int;
    extern "ws2_32" fn closesocket(s: usize) callconv(.winapi) c_int;
} else struct {};

fn setupListener() ?Sock {
    if (common.is_windows) {
        var wsadata: [512]u8 = undefined;
        if (win.WSAStartup(0x0202, &wsadata) != 0) return null; // request Winsock 2.2
        const s = win.socket(ws.AF.INET, ws.SOCK.STREAM, ws.IPPROTO.TCP);
        if (s == std.math.maxInt(usize)) return null;
        var addr = ws.sockaddr.in{
            .port = 0, // kernel-assigned free port
            .addr = std.mem.nativeToBig(u32, 0x7F00_0001), // 127.0.0.1, loopback only
        };
        if (win.bind(s, &addr, @sizeOf(ws.sockaddr.in)) != 0 or win.listen(s, 1) != 0) {
            _ = win.closesocket(s);
            return null;
        }
        var slen: c_int = @sizeOf(ws.sockaddr.in);
        if (win.getsockname(s, &addr, &slen) != 0) {
            _ = win.closesocket(s);
            return null;
        }
        wine_port = std.mem.bigToNative(u16, addr.port);
        return s;
    }
    const rc = linux.socket(linux.AF.UNIX, linux.SOCK.STREAM, 0);
    if (@as(isize, @bitCast(rc)) < 0) return null;
    const fd: i32 = @intCast(rc);
    var namebuf: [64]u8 = undefined;
    const name = std.fmt.bufPrint(&namebuf, "pince-mono-{d}", .{linux.getpid()}) catch {
        _ = linux.close(fd);
        return null;
    };
    var addr = std.mem.zeroes(linux.sockaddr.un);
    addr.family = linux.AF.UNIX;
    addr.path[0] = 0; // leading NUL -> abstract namespace
    @memcpy(addr.path[1 .. 1 + name.len], name);
    const addrlen: linux.socklen_t = @intCast(@offsetOf(linux.sockaddr.un, "path") + 1 + name.len);
    if (linux.bind(fd, @ptrCast(&addr), addrlen) != 0 or linux.listen(fd, 1) != 0) {
        _ = linux.close(fd);
        return null;
    }
    return fd;
}

fn startWorker() void {
    if (started.swap(true, .seq_cst)) return;
    // PE build must spawn a real WINE thread so Mono's GC can suspend it.
    (std.Thread.spawn(.{}, workerMain, .{}) catch return).detach();
}

// PE entry point loaded via kernel32!LoadLibraryW.
pub fn DllMain(
    _: std.os.windows.HINSTANCE,
    reason: std.os.windows.DWORD,
    _: std.os.windows.LPVOID,
) callconv(.winapi) std.os.windows.BOOL {
    if (reason == 1) startWorker(); // DLL_PROCESS_ATTACH
    return .TRUE;
}

fn ctor() callconv(.c) void {
    startWorker();
}
const ctor_ptr: *const fn () callconv(.c) void = &ctor;
comptime {
    if (!common.is_windows) @export(&ctor_ptr, .{ .name = "_pince_mono_ctor", .section = ".init_array" });
}

fn readN(s: Sock, buf: []u8) !void {
    var off: usize = 0;
    while (off < buf.len) {
        const n = if (common.is_windows)
            win.recv(s, buf[off..].ptr, @intCast(buf.len - off), 0)
        else blk: {
            const rc: isize = @bitCast(linux.read(s, buf[off..].ptr, buf.len - off));
            if (rc == EINTR) continue;
            break :blk rc;
        };
        if (n < 0) return error.ReadError;
        if (n == 0) return error.Eof;
        off += @intCast(n);
    }
}

fn writeN(s: Sock, buf: []const u8) !void {
    var off: usize = 0;
    while (off < buf.len) {
        const n = if (common.is_windows)
            win.send(s, buf[off..].ptr, @intCast(buf.len - off), 0)
        else blk: {
            const rc: isize = @bitCast(linux.write(s, buf[off..].ptr, buf.len - off));
            if (rc == EINTR) continue;
            break :blk rc;
        };
        if (n < 0) return error.WriteError;
        if (n == 0) return error.Closed;
        off += @intCast(n);
    }
}

fn dispatch(allocator: std.mem.Allocator, backend: *const rt.Backend, req_bytes: []const u8, out: *Encoder) !void {
    var dec = msgpack.Decoder{ .data = req_bytes };
    const n = dec.mapLen() catch return writeErr(out, "bad request");

    var op: []const u8 = "";
    var image: u64 = 0;
    var klass: u64 = 0;
    var field: u64 = 0;
    var method: u64 = 0;
    var obj: u64 = 0;
    var args_buf: [32]rt.Arg = undefined;
    var args_len: usize = 0;

    for (0..n) |_| {
        const key = dec.str() catch return writeErr(out, "bad key");
        if (eql(key, "op")) {
            op = dec.str() catch return writeErr(out, "bad op");
        } else if (eql(key, "image")) {
            image = dec.uint() catch return writeErr(out, "bad image");
        } else if (eql(key, "klass")) {
            klass = dec.uint() catch return writeErr(out, "bad klass");
        } else if (eql(key, "field")) {
            field = dec.uint() catch return writeErr(out, "bad field");
        } else if (eql(key, "method")) {
            method = dec.uint() catch return writeErr(out, "bad method");
        } else if (eql(key, "obj")) {
            obj = dec.uint() catch return writeErr(out, "bad obj");
        } else if (eql(key, "args")) {
            const count = dec.arrayLen() catch return writeErr(out, "bad args");
            args_len = 0;
            for (0..count) |_| {
                if (args_len >= args_buf.len) return writeErr(out, "too many args");
                if ((dec.arrayLen() catch return writeErr(out, "bad arg")) != 2) return writeErr(out, "bad arg");
                const tag = dec.str() catch return writeErr(out, "bad arg tag");
                var a = rt.Arg{ .tag = tag };
                if (eql(tag, "str") or eql(tag, "struct")) {
                    a.str = dec.str() catch return writeErr(out, "bad arg str"); // struct: raw value bytes
                } else {
                    a.bits = dec.uint() catch return writeErr(out, "bad arg val");
                }
                args_buf[args_len] = a;
                args_len += 1;
            }
        } else {
            return writeErr(out, "unknown key"); // PINCE should only send known keys
        }
    }

    // Run the op into a temp buffer and then wrap success/failure afterwards.
    var tmp: std.ArrayList(u8) = .empty;
    defer tmp.deinit(allocator);
    var tenc = Encoder{ .list = &tmp, .allocator = allocator };

    const result: anyerror!void = if (eql(op, "assemblies"))
        backend.assemblies(&tenc)
    else if (eql(op, "classes"))
        backend.classes(image, &tenc)
    else if (eql(op, "fields"))
        backend.fields(klass, &tenc)
    else if (eql(op, "methods"))
        backend.methods(klass, &tenc)
    else if (eql(op, "compile"))
        backend.compile(method, &tenc)
    else if (eql(op, "static_addr"))
        backend.staticAddr(klass, field, &tenc)
    else if (eql(op, "class_info"))
        backend.classInfo(klass, &tenc)
    else if (eql(op, "type_klass"))
        backend.typeKlass(field, &tenc)
    else if (eql(op, "instance_marker"))
        backend.instanceMarker(klass, &tenc)
    else if (eql(op, "invoke"))
        backend.invoke(method, obj, args_buf[0..args_len], &tenc)
    else if (eql(op, "signature"))
        backend.signature(method, &tenc)
    else
        error.UnknownOp;

    if (result) |_| {
        try out.mapHeader(2);
        try out.str("ok");
        try out.boolean(true);
        try out.str("data");
        try out.raw(tmp.items);
    } else |err| {
        try writeErr(out, @errorName(err));
    }
}

fn writeErr(out: *Encoder, msg: []const u8) !void {
    out.list.clearRetainingCapacity();
    try out.mapHeader(2);
    try out.str("ok");
    try out.boolean(false);
    try out.str("error");
    try out.str(msg);
}

fn handleConn(allocator: std.mem.Allocator, backend: *const rt.Backend, conn: Sock) void {
    defer {
        if (common.is_windows) _ = win.closesocket(conn) else _ = linux.close(conn);
    }
    while (true) {
        var len_buf: [4]u8 = undefined;
        readN(conn, &len_buf) catch return;
        const len = std.mem.readInt(u32, &len_buf, .big);
        if (len > (16 * 1024 * 1024)) return;

        const req_bytes = allocator.alloc(u8, len) catch return;
        defer allocator.free(req_bytes);
        readN(conn, req_bytes) catch return;

        var out: std.ArrayList(u8) = .empty;
        defer out.deinit(allocator);

        var enc = Encoder{ .list = &out, .allocator = allocator };
        dispatch(allocator, backend, req_bytes, &enc) catch {
            writeErr(&enc, "internal") catch return;
        };
        std.mem.writeInt(u32, &len_buf, @intCast(out.items.len), .big);
        writeN(conn, &len_buf) catch return;
        writeN(conn, out.items) catch return;
    }
}

fn workerMain() void {
    // The PE build links no libc, so use the libc-free general allocator there.
    const allocator = if (common.is_windows) std.heap.smp_allocator else std.heap.c_allocator;
    const backend = (rt.detectAndLoad(allocator) catch return) orelse return;

    const listener = setupListener() orelse return;
    while (true) {
        const conn = if (common.is_windows) blk: {
            const c = win.accept(listener, null, null);
            if (c == std.math.maxInt(usize)) continue;
            const one: u32 = 1; // TCP_NODELAY: our frames are a 4 bytes header + body, so avoid Nagle delays
            _ = win.setsockopt(c, ws.IPPROTO.TCP, ws.TCP.NODELAY, std.mem.asBytes(&one), @sizeOf(u32));
            break :blk c;
        } else blk: {
            const c = linux.accept(listener, null, null);
            if (@as(isize, @bitCast(c)) < 0) continue;
            break :blk @as(i32, @intCast(c));
        };
        handleConn(allocator, &backend, conn);
    }
}
