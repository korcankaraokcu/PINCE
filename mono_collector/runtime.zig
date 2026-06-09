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
    // Made intentionally null for the TODO further down.
    invokeFn: ?*const fn (*anyopaque, u64, u64, []const u64, *Encoder) anyerror!void = null,

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
    pub fn invoke(self: *const Backend, method: u64, obj: u64, params: []const u64, e: *Encoder) !void {
        // TODO BRK: Implement the invoke logic once we have functional reading.
        const f = self.invokeFn orelse return error.Unsupported;
        return f(self.ctx, method, obj, params, e);
    }
};

/// TODO BRK: Use detected kind and branch off once we have functional il2cpp impl.
pub fn detectAndLoad(allocator: std.mem.Allocator) !?Backend {
    return @import("mono_api.zig").load(allocator);
}
