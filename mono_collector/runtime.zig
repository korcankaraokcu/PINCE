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

//! Runtime backend interface.
//! The Mono implementation lives in mono_api.zig.
//! Each *fn writes exactly one MessagePack value (the response "data") into enc.
const std = @import("std");
const Encoder = @import("msgpack.zig").Encoder;

pub const RuntimeKind = enum { mono, il2cpp };

/// One marshalled argument for "invoke".
/// "tag" is the wire type tag ("i4","r4","str",…).
/// Value types carry their raw bit pattern in "bits".
/// Strings carry UTF-8 in "str".
pub const Arg = struct { tag: []const u8, bits: u64 = 0, str: []const u8 = "" };

pub const Backend = struct {
    ctx: *anyopaque,
    kind: RuntimeKind,

    helloFn: *const fn (*anyopaque, *Encoder) anyerror!void,
    assembliesFn: *const fn (*anyopaque, *Encoder) anyerror!void,
    classesFn: *const fn (*anyopaque, u64, *Encoder) anyerror!void,
    fieldsFn: *const fn (*anyopaque, u64, *Encoder) anyerror!void,
    methodsFn: *const fn (*anyopaque, u64, *Encoder) anyerror!void,
    compileFn: *const fn (*anyopaque, u64, *Encoder) anyerror!void,
    staticAddrFn: *const fn (*anyopaque, u64, u64, *Encoder) anyerror!void,
    findClassFn: *const fn (*anyopaque, u64, []const u8, []const u8, *Encoder) anyerror!void,
    invokeFn: *const fn (*anyopaque, u64, u64, []const Arg, *Encoder) anyerror!void,
    signatureFn: *const fn (*anyopaque, u64, *Encoder) anyerror!void,

    pub fn hello(self: *const Backend, e: *Encoder) !void {
        return self.helloFn(self.ctx, e);
    }
    pub fn assemblies(self: *const Backend, e: *Encoder) !void {
        return self.assembliesFn(self.ctx, e);
    }
    pub fn classes(self: *const Backend, image: u64, e: *Encoder) !void {
        return self.classesFn(self.ctx, image, e);
    }
    pub fn fields(self: *const Backend, klass: u64, e: *Encoder) !void {
        return self.fieldsFn(self.ctx, klass, e);
    }
    pub fn methods(self: *const Backend, klass: u64, e: *Encoder) !void {
        return self.methodsFn(self.ctx, klass, e);
    }
    pub fn compile(self: *const Backend, method: u64, e: *Encoder) !void {
        return self.compileFn(self.ctx, method, e);
    }
    pub fn staticAddr(self: *const Backend, klass: u64, field: u64, e: *Encoder) !void {
        return self.staticAddrFn(self.ctx, klass, field, e);
    }
    pub fn findClass(self: *const Backend, image: u64, ns: []const u8, name: []const u8, e: *Encoder) !void {
        return self.findClassFn(self.ctx, image, ns, name, e);
    }
    pub fn invoke(self: *const Backend, method: u64, obj: u64, args: []const Arg, e: *Encoder) !void {
        return self.invokeFn(self.ctx, method, obj, args, e);
    }
    pub fn signature(self: *const Backend, method: u64, e: *Encoder) !void {
        return self.signatureFn(self.ctx, method, e);
    }
};

/// We don't need fancy checking and switching because we can just try to import each backend
/// and see which is the first one that's valid.
pub fn detectAndLoad(allocator: std.mem.Allocator) !?Backend {
    if (try @import("mono_api.zig").load(allocator)) |b| return b;
    if (try @import("il2cpp_api.zig").load(allocator)) |b| return b;
    return null;
}
