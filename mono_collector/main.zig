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

//! Entry + worker thread + Unix-socket server + op dispatch.
//! The worker attaches to the Mono domain, binds an abstract Unix socket "\0pince-mono-<pid>" and serves frames.
const std = @import("std");
const linux = std.os.linux;
const rt = @import("runtime.zig");
const msgpack = @import("msgpack.zig");
const Encoder = msgpack.Encoder;
const Decoder = msgpack.Decoder;

const AF_UNIX: u32 = 1;
const SOCK_STREAM: u32 = 1;

var started = std.atomic.Value(bool).init(false);

fn startWorker() void {
    if (started.swap(true, .seq_cst)) return;
    const t = std.Thread.spawn(.{}, workerMain, .{}) catch return;
    t.detach();
}

// Just in case our constructor auto-attach fails.
export fn pince_mono_init() callconv(.c) void {
    startWorker();
}

fn ctor() callconv(.c) void {
    startWorker();
}
export const _pince_mono_ctor: *const fn () callconv(.c) void linksection(".init_array") = &ctor;

fn readN(fd: i32, buf: []u8) !void {
    var off: usize = 0;
    while (off < buf.len) {
        const n = linux.read(fd, buf[off..].ptr, buf.len - off);
        if (n == 0) return error.Eof;
        if (@as(isize, @bitCast(n)) < 0) return error.ReadError;
        off += n;
    }
}

fn writeN(fd: i32, buf: []const u8) !void {
    var off: usize = 0;
    while (off < buf.len) {
        const n = linux.write(fd, buf[off..].ptr, buf.len - off);
        if (n == 0) return error.Closed;
        if (@as(isize, @bitCast(n)) < 0) return error.WriteError;
        off += n;
    }
}

fn readFrame(allocator: std.mem.Allocator, fd: i32) ![]u8 {
    var len_buf: [4]u8 = undefined;
    try readN(fd, &len_buf);

    const len = std.mem.readInt(u32, &len_buf, .big);
    if (len > (16 * 1024 * 1024)) return error.FrameTooBig;

    const buf = try allocator.alloc(u8, len);
    errdefer allocator.free(buf);
    try readN(fd, buf);
    return buf;
}

fn writeFrame(fd: i32, payload: []const u8) !void {
    var len_buf: [4]u8 = undefined;
    std.mem.writeInt(u32, &len_buf, @intCast(payload.len), .big);
    try writeN(fd, &len_buf);
    try writeN(fd, payload);
}

inline fn eql(a: []const u8, b: []const u8) bool {
    return std.mem.eql(u8, a, b);
}

fn dispatch(allocator: std.mem.Allocator, backend: *const rt.Backend, req_bytes: []const u8, out: *Encoder) !void {
    var dec = Decoder{ .data = req_bytes };
    const n = dec.mapLen() catch return writeErr(out, "bad request");

    var op: []const u8 = "";
    var image: u64 = 0;
    var klass: u64 = 0;
    var field: u64 = 0;
    var method: u64 = 0;
    var obj: u64 = 0;
    var args_buf: [32]rt.Arg = undefined;
    var args_len: usize = 0;
    var ns: []const u8 = "";
    var name: []const u8 = "";
    var i: usize = 0;

    while (i < n) : (i += 1) {
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
        } else if (eql(key, "namespace")) {
            ns = dec.str() catch return writeErr(out, "bad ns");
        } else if (eql(key, "name")) {
            name = dec.str() catch return writeErr(out, "bad name");
        } else if (eql(key, "args")) {
            const count = dec.arrayLen() catch return writeErr(out, "bad args");
            args_len = 0;
            var p: usize = 0;
            while (p < count) : (p += 1) {
                if (args_len >= args_buf.len) return writeErr(out, "too many args");
                if ((dec.arrayLen() catch return writeErr(out, "bad arg")) != 2) return writeErr(out, "bad arg");
                const tag = dec.str() catch return writeErr(out, "bad arg tag");
                var a = rt.Arg{ .tag = tag };
                if (eql(tag, "str")) {
                    a.str = dec.str() catch return writeErr(out, "bad arg str");
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

    const result: anyerror!void = if (eql(op, "hello"))
        backend.hello(&tenc)
    else if (eql(op, "assemblies"))
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
    else if (eql(op, "find_class"))
        backend.findClass(image, ns, name, &tenc)
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

fn handleConn(allocator: std.mem.Allocator, backend: *const rt.Backend, fd: i32) void {
    defer _ = linux.close(fd);
    while (true) {
        const req_bytes = readFrame(allocator, fd) catch return;
        defer allocator.free(req_bytes);

        var out: std.ArrayList(u8) = .empty;
        defer out.deinit(allocator);

        var enc = Encoder{ .list = &out, .allocator = allocator };
        dispatch(allocator, backend, req_bytes, &enc) catch {
            out.clearRetainingCapacity();
            writeErr(&enc, "internal") catch return;
        };
        writeFrame(fd, out.items) catch return;
    }
}

fn workerMain() void {
    const allocator = std.heap.c_allocator;
    var backend = (rt.detectAndLoad(allocator) catch return) orelse return;

    const fd = @as(i32, @intCast(linux.socket(AF_UNIX, SOCK_STREAM, 0)));
    if (fd < 0) return;

    const pid = std.c.getpid();
    var namebuf: [64]u8 = undefined;
    const name = std.fmt.bufPrint(&namebuf, "pince-mono-{d}", .{pid}) catch return;

    var addr = std.mem.zeroes(linux.sockaddr.un);
    addr.family = AF_UNIX;
    addr.path[0] = 0; // leading NUL -> abstract namespace
    @memcpy(addr.path[1 .. 1 + name.len], name);
    const addrlen: linux.socklen_t = @intCast(@offsetOf(linux.sockaddr.un, "path") + 1 + name.len);

    if (linux.bind(fd, @ptrCast(&addr), addrlen) != 0) return;
    if (linux.listen(fd, 1) != 0) return;

    while (true) {
        const cfd = @as(i32, @intCast(linux.accept(fd, null, null)));
        if (cfd < 0) continue;
        handleConn(allocator, &backend, cfd);
    }
}
