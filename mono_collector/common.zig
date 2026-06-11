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

//! Helpers shared by the mono and il2cpp backends.
const std = @import("std");
const resolver = @import("resolver.zig");
const Encoder = @import("msgpack.zig").Encoder;

// x86 WINE also uses cdecl.
pub const CC: std.builtin.CallingConvention = if (resolver.win64_abi) .winapi else .c;
pub const CStr = [*:0]const u8;

pub inline fn cspan(p: ?CStr) []const u8 {
    return if (p) |s| std.mem.span(s) else "";
}

pub inline fn eql(a: []const u8, b: []const u8) bool {
    return std.mem.eql(u8, a, b);
}

// Resolve a symbol through the bound module (dlsym natively, PE export under WINE).
pub inline fn req(comptime T: type, mod: resolver.Module, name: [*:0]const u8) !T {
    const p = mod.lookup(name) orelse return error.SymbolMissing;
    return @ptrCast(p);
}
pub inline fn opt(comptime T: type, mod: resolver.Module, name: [*:0]const u8) ?T {
    const p = mod.lookup(name) orelse return null;
    return @ptrCast(p);
}

// MONO_TYPE_* / Il2CppTypeEnum -> our wire type tag (the two runtimes share these numeric values).
// "unsupported" = a type we can't marshal yet.
pub inline fn typeTag(t: c_int) []const u8 {
    return switch (t) {
        0x01 => "void",
        0x02 => "bool",
        0x03 => "char",
        0x04 => "i1",
        0x05 => "u1",
        0x06 => "i2",
        0x07 => "u2",
        0x08 => "i4",
        0x09 => "u4",
        0x0a => "i8",
        0x0b => "u8",
        0x0c => "r4",
        0x0d => "r8",
        0x0e => "str",
        0x0f, 0x18, 0x19 => if (@sizeOf(usize) == 8) "u8" else "u4", // PTR, I, U
        0x12, 0x14, 0x1c, 0x1d => "object", // CLASS, ARRAY, OBJECT, SZARRAY
        else => "unsupported",
    };
}

pub inline fn typeWidth(tag: []const u8) usize {
    if (eql(tag, "i1") or eql(tag, "u1") or eql(tag, "bool")) return 1;
    if (eql(tag, "i2") or eql(tag, "u2") or eql(tag, "char")) return 2;
    if (eql(tag, "i4") or eql(tag, "u4") or eql(tag, "r4")) return 4;
    return 8;
}

pub inline fn emitBits(e: *Encoder, tag: []const u8, bits: u64) !void {
    try e.mapHeader(2);
    try e.str("tag");
    try e.str(tag);
    try e.str("bits");
    try e.uint(bits);
}
