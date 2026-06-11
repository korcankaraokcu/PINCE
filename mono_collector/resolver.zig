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

//! Runtime module symbol resolution.
//!
//! Native ELF builds resolve mono_*/il2cpp_* via dlopen/dlsym.
//! The WINE/Proton variant (built with -Dwine) parses the mapped runtime DLL's PE export directory instead.
//! WINE maps the DLL as an image but does NOT register its exports with the glibc dynamic linker, so dlsym can't see them.
const std = @import("std");
const build_options = @import("build_options");

pub const is_wine = build_options.wine;

/// On x86 both native and WINE use cdecl (".c"), so backends select ".winapi" only when this is set.
pub const win64_abi = is_wine and @import("builtin").cpu.arch == .x86_64;

pub const Module = if (is_wine) WINEModule else NativeModule;

/// Find + bind the runtime module and confirm "core" resolves through it.
/// - core: a symbol that must exist (proves it is the expected runtime).
/// - substr: identifies the mapped module file in /proc/self/maps.
/// - path_buf/path_len: receives the bound module path.
/// Returns null when the module isn't present or isn't the expected runtime.
pub fn open(
    allocator: std.mem.Allocator,
    core: [*:0]const u8,
    substr: []const u8,
    path_buf: []u8,
    path_len: *usize,
) ?Module {
    return if (is_wine)
        openWINE(allocator, core, substr, path_buf, path_len)
    else
        openNative(allocator, core, substr, path_buf, path_len);
}

// native (ELF)
const NativeModule = struct {
    handle: ?*anyopaque,

    pub fn lookup(self: NativeModule, name: [*:0]const u8) ?*anyopaque {
        return std.c.dlsym(self.handle, name);
    }
};

// Find the path of the mapped module whose maps line contains "substr", NUL-terminated in "buf".
fn findModulePath(allocator: std.mem.Allocator, substr: []const u8, buf: []u8) ?[:0]const u8 {
    const io = std.Io.Threaded.global_single_threaded.io();
    const f = std.Io.Dir.openFileAbsolute(io, "/proc/self/maps", .{}) catch return null;
    defer f.close(io);

    var contents: std.ArrayList(u8) = .empty;
    defer contents.deinit(allocator);
    var chunk: [1 << 16]u8 = undefined;
    var offset: u64 = 0;
    while (true) {
        const n = f.readPositionalAll(io, &chunk, offset) catch return null;
        if (n == 0) break;
        contents.appendSlice(allocator, chunk[0..n]) catch return null;
        offset += n;
        if (n < chunk.len) break; // short read -> EOF
    }

    var it = std.mem.splitScalar(u8, contents.items, '\n');
    while (it.next()) |line| {
        if (std.mem.indexOf(u8, line, substr) == null) continue;
        const start = std.mem.indexOfScalar(u8, line, '/') orelse continue;
        const path = line[start..];
        if (path.len == 0 or path.len >= buf.len) return null;
        @memcpy(buf[0..path.len], path);
        buf[path.len] = 0;
        return buf[0..path.len :0];
    }
    return null;
}

fn openNative(
    allocator: std.mem.Allocator,
    core: [*:0]const u8,
    substr: []const u8,
    path_buf: []u8,
    path_len: *usize,
) ?NativeModule {
    // Try the global scope first, works when the runtime is linked into the executable or was loaded RTLD_GLOBAL.
    var h = std.c.dlopen(null, std.c.RTLD{ .NOW = true });
    if (std.c.dlsym(h, core) == null) {
        // Unity usually loads its runtime with RTLD_LOCAL so the exports aren't global.
        // Attach to the already mapped copy by path (NOLOAD won't map a second).
        var find_buf: [4096]u8 = undefined;
        const path = findModulePath(allocator, substr, &find_buf) orelse return null;
        h = std.c.dlopen(path.ptr, std.c.RTLD{ .NOW = true, .NOLOAD = true });
        if (h == null or std.c.dlsym(h, core) == null) return null;
    }

    var find_buf: [4096]u8 = undefined;
    if (findModulePath(allocator, substr, &find_buf)) |path| {
        const len = @min(path.len, path_buf.len);
        @memcpy(path_buf[0..len], path[0..len]);
        path_len.* = len;
    }
    return .{ .handle = h };
}

// WINE (PE)
inline fn peRead(comptime T: type, base: [*]const u8, off: usize) T {
    return @as(*align(1) const T, @ptrCast(base + off)).*;
}

const WINEModule = struct {
    base: [*]const u8,
    number_of_names: u32,
    name_rvas: usize, // base relative offset of AddressOfNames[]        (u32 each)
    ordinals: usize, //  base relative offset of AddressOfNameOrdinals[] (u16 each)
    func_rvas: usize, // base relative offset of AddressOfFunctions[]    (u32 each)

    pub fn lookup(self: WINEModule, name: [*:0]const u8) ?*anyopaque {
        const want = std.mem.span(name);
        var i: u32 = 0;
        while (i < self.number_of_names) : (i += 1) {
            const name_rva = peRead(u32, self.base, self.name_rvas + i * 4);
            const sym: [*:0]const u8 = @ptrCast(self.base + name_rva);
            if (std.mem.eql(u8, std.mem.span(sym), want)) {
                // AddressOfNameOrdinals[i] is already the index into AddressOfFunctions (the export Base is NOT added here).
                const ord = peRead(u16, self.base, self.ordinals + i * 2);
                const func_rva = peRead(u32, self.base, self.func_rvas + @as(usize, ord) * 4);
                return @ptrCast(@constCast(self.base + func_rva));
            }
        }
        return null;
    }
};

// Parse a mapped PE image's export directory.
// Returns null if "base" is not a PE image or has no export directory.
fn parsePe(base: [*]const u8) ?WINEModule {
    if (peRead(u16, base, 0x00) != 0x5A4D) return null; // "MZ"
    const e_lfanew: usize = peRead(u32, base, 0x3C);
    if (peRead(u32, base, e_lfanew) != 0x0000_4550) return null; // "PE\0\0"
    // Optional header begins at NT + 0x18.
    // Its DataDirectory starts at +0x60 for PE32 (Magic 0x10B) and +0x70 for PE32+ (Magic 0x20B).
    // ImageBase widens to u64 in PE32+, shifting the fields after it.
    // Export = DataDirectory[0].
    const opt = e_lfanew + 0x18;
    const dd_off: usize = if (peRead(u16, base, opt) == 0x20B) 0x70 else 0x60;
    const export_dir_rva: usize = peRead(u32, base, opt + dd_off);
    if (export_dir_rva == 0) return null; // no export directory
    return WINEModule{
        .base = base,
        .number_of_names = peRead(u32, base, export_dir_rva + 0x18),
        .func_rvas = peRead(u32, base, export_dir_rva + 0x1C),
        .name_rvas = peRead(u32, base, export_dir_rva + 0x20),
        .ordinals = peRead(u32, base, export_dir_rva + 0x24),
    };
}

fn openWINE(
    allocator: std.mem.Allocator,
    core: [*:0]const u8,
    substr: []const u8,
    path_buf: []u8,
    path_len: *usize,
) ?WINEModule {
    const io = std.Io.Threaded.global_single_threaded.io();
    const f = std.Io.Dir.openFileAbsolute(io, "/proc/self/maps", .{}) catch return null;
    defer f.close(io);

    var contents: std.ArrayList(u8) = .empty;
    defer contents.deinit(allocator);
    var chunk: [1 << 16]u8 = undefined;
    var offset: u64 = 0;
    while (true) {
        const n = f.readPositionalAll(io, &chunk, offset) catch return null;
        if (n == 0) break;
        contents.appendSlice(allocator, chunk[0..n]) catch return null;
        offset += n;
        if (n < chunk.len) break;
    }

    // A DLL spans several maps lines (one per PE section).
    // The headers mapping (file offset 0, with the "MZ"/"PE" signatures) is the image base.
    // Try each matching line's start address and keep the one that parses as a PE whose export table actually contains "core".
    var it = std.mem.splitScalar(u8, contents.items, '\n');
    while (it.next()) |line| {
        if (std.mem.indexOf(u8, line, substr) == null) continue;
        const dash = std.mem.indexOfScalar(u8, line, '-') orelse continue;
        const start = std.fmt.parseInt(usize, line[0..dash], 16) catch continue;
        const mod = parsePe(@ptrFromInt(start)) orelse continue;
        if (mod.lookup(core) == null) continue; // exports parsed but not the right runtime
        if (std.mem.indexOfScalar(u8, line, '/')) |s| {
            const path = line[s..];
            const len = @min(path.len, path_buf.len);
            @memcpy(path_buf[0..len], path[0..len]);
            path_len.* = len;
        }
        return mod;
    }
    return null;
}
