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

//! Minimal MessagePack implementation.
//! Some things are omitted as they're not relevant to PINCE, like int decoding (but we encode to prevent issues while serializing)
//! Msgpack is better than JSON for our specific needs:
//! - Tiny implementation and no dependency on JSON libraries which can be beefy.
//! - Much more compact structure, useful for enumerating thousands of classes and fields in Mono.
//! - Good integration with msgpack Python lib.
//! Encoder writes into a std.ArrayList(u8).
//! Decoder reads from a byte slice.
const std = @import("std");

pub const Encoder = struct {
    list: *std.ArrayList(u8),
    allocator: std.mem.Allocator,

    fn byte(self: *Encoder, b: u8) !void {
        try self.list.append(self.allocator, b);
    }
    fn beN(self: *Encoder, comptime T: type, v: T) !void {
        var tmp: [@sizeOf(T)]u8 = undefined;
        std.mem.writeInt(T, &tmp, v, .big);
        try self.list.appendSlice(self.allocator, &tmp);
    }

    pub fn nil(self: *Encoder) !void {
        try self.byte(0xc0);
    }
    pub fn boolean(self: *Encoder, v: bool) !void {
        try self.byte(if (v) 0xc3 else 0xc2);
    }
    pub fn uint(self: *Encoder, v: u64) !void {
        if (v < 0x80) {
            try self.byte(@intCast(v));
        } else if (v <= 0xff) {
            try self.byte(0xcc);
            try self.byte(@intCast(v));
        } else if (v <= 0xffff) {
            try self.byte(0xcd);
            try self.beN(u16, @intCast(v));
        } else if (v <= 0xffffffff) {
            try self.byte(0xce);
            try self.beN(u32, @intCast(v));
        } else {
            try self.byte(0xcf);
            try self.beN(u64, v);
        }
    }
    pub fn int(self: *Encoder, v: i64) !void {
        if (v >= 0) return self.uint(@intCast(v));
        // negative: use int64 form for simplicity
        try self.byte(0xd3);
        try self.beN(i64, v);
    }
    pub fn str(self: *Encoder, s: []const u8) !void {
        const n = s.len;
        if (n < 32) {
            try self.byte(0xa0 | @as(u8, @intCast(n)));
        } else if (n <= 0xff) {
            try self.byte(0xd9);
            try self.byte(@intCast(n));
        } else if (n <= 0xffff) {
            try self.byte(0xda);
            try self.beN(u16, @intCast(n));
        } else {
            try self.byte(0xdb);
            try self.beN(u32, @intCast(n));
        }
        try self.list.appendSlice(self.allocator, s);
    }
    pub fn arrayHeader(self: *Encoder, n: usize) !void {
        if (n < 16) {
            try self.byte(0x90 | @as(u8, @intCast(n)));
        } else if (n <= 0xffff) {
            try self.byte(0xdc);
            try self.beN(u16, @intCast(n));
        } else {
            try self.byte(0xdd);
            try self.beN(u32, @intCast(n));
        }
    }
    pub fn mapHeader(self: *Encoder, n: usize) !void {
        if (n < 16) {
            try self.byte(0x80 | @as(u8, @intCast(n)));
        } else if (n <= 0xffff) {
            try self.byte(0xde);
            try self.beN(u16, @intCast(n));
        } else {
            try self.byte(0xdf);
            try self.beN(u32, @intCast(n));
        }
    }
    pub fn bin(self: *Encoder, bytes: []const u8) !void {
        const n = bytes.len;
        if (n <= 0xff) {
            try self.byte(0xc4);
            try self.byte(@intCast(n));
        } else if (n <= 0xffff) {
            try self.byte(0xc5);
            try self.beN(u16, @intCast(n));
        } else {
            try self.byte(0xc6);
            try self.beN(u32, @intCast(n));
        }
        try self.list.appendSlice(self.allocator, bytes);
    }
    pub fn raw(self: *Encoder, bytes: []const u8) !void {
        try self.list.appendSlice(self.allocator, bytes);
    }
};

pub const Decoder = struct {
    data: []const u8,
    pos: usize = 0,

    fn take(self: *Decoder) !u8 {
        if (self.pos >= self.data.len) return error.Eof;
        const b = self.data[self.pos];
        self.pos += 1;
        return b;
    }
    fn beN(self: *Decoder, comptime T: type) !T {
        const sz = @sizeOf(T);
        if (self.pos + sz > self.data.len) return error.Eof;
        const v = std.mem.readInt(T, self.data[self.pos..][0..sz], .big);
        self.pos += sz;
        return v;
    }
    pub fn mapLen(self: *Decoder) !usize {
        const b = try self.take();
        if (b & 0xf0 == 0x80) return b & 0x0f;
        if (b == 0xde) return try self.beN(u16);
        if (b == 0xdf) return try self.beN(u32);
        return error.NotMap;
    }
    pub fn arrayLen(self: *Decoder) !usize {
        const b = try self.take();
        if (b & 0xf0 == 0x90) return b & 0x0f;
        if (b == 0xdc) return try self.beN(u16);
        if (b == 0xdd) return try self.beN(u32);
        return error.NotArray;
    }
    pub fn str(self: *Decoder) ![]const u8 {
        const b = try self.take();
        var n: usize = undefined;
        if (b & 0xe0 == 0xa0) {
            n = b & 0x1f;
        } else if (b == 0xd9) {
            n = try self.take();
        } else if (b == 0xda) {
            n = try self.beN(u16);
        } else if (b == 0xdb) {
            n = try self.beN(u32);
        } else return error.NotStr;
        if (self.pos + n > self.data.len) return error.Eof;
        const s = self.data[self.pos .. self.pos + n];
        self.pos += n;
        return s;
    }
    pub fn uint(self: *Decoder) !u64 {
        const b = try self.take();
        if (b < 0x80) return b;
        if (b == 0xcc) return try self.take();
        if (b == 0xcd) return try self.beN(u16);
        if (b == 0xce) return try self.beN(u32);
        if (b == 0xcf) return try self.beN(u64);
        return error.NotUint;
    }
};
