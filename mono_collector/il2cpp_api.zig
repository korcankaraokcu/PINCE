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

//! IL2CPP embedding API backend.
//! Resolves il2cpp_* via dlsym from the already loaded runtime, attaches the worker thread and implements the runtime.Backend vtable.
//! Unity's IL2CPP exports a C API deliberately modeled on Mono's embedding API.
//! Differences handled here vs mono_api.zig:
//!   - assemblies arrive as an array (il2cpp_domain_get_assemblies), not via a foreach callback.
//!   - classes are enumerated by index (il2cpp_image_get_class), not by metadata token.
//!   - there is NO JIT: the native code pointer is read from MethodInfo.methodPointer (offset 0) which is version-sensitive, see il2cppCompile.
//!   - IL2CPP exposes no public static field base getter, so static_addr is Unsupported here, see il2cppStaticAddr.
//!   - signature enumerates params by index (il2cpp_method_get_param) with staticness from the method flags.
const std = @import("std");
const rt = @import("runtime.zig");
const Encoder = @import("msgpack.zig").Encoder;

const CC: std.builtin.CallingConvention = .c; // Note for later: .x86_64_win for Wine
const CStr = [*:0]const u8;

inline fn cspan(p: ?CStr) []const u8 {
    return if (p) |s| std.mem.span(s) else "";
}

// il2cpp_* function pointer types (taken from il2cpp-api-functions.h)
const FnDomain = *const fn () callconv(CC) ?*anyopaque;
const FnThreadAttach = *const fn (?*anyopaque) callconv(CC) ?*anyopaque;
const FnGetAssemblies = *const fn (?*anyopaque, *usize) callconv(CC) ?[*]const ?*anyopaque;
const FnP_P = *const fn (?*anyopaque) callconv(CC) ?*anyopaque;
const FnP_CStr = *const fn (?*anyopaque) callconv(CC) ?CStr;
const FnImgCount = *const fn (?*anyopaque) callconv(CC) usize;
const FnImgClass = *const fn (?*anyopaque, usize) callconv(CC) ?*anyopaque;
const FnIter = *const fn (?*anyopaque, *?*anyopaque) callconv(CC) ?*anyopaque;
const FnFieldOffset = *const fn (?*anyopaque) callconv(CC) usize;
const FnFieldFlags = *const fn (?*anyopaque) callconv(CC) c_int;
const FnTypeName = *const fn (?*anyopaque) callconv(CC) ?CStr;
const FnParamCount = *const fn (?*anyopaque) callconv(CC) u32;
const FnClassInit = *const fn (?*anyopaque) callconv(CC) void;
const FnFromName = *const fn (?*anyopaque, CStr, CStr) callconv(CC) ?*anyopaque;
const FnFree = *const fn (?*anyopaque) callconv(CC) void;
const FnInvoke = *const fn (?*anyopaque, ?*anyopaque, ?[*]?*anyopaque, *?*anyopaque) callconv(CC) ?*anyopaque;
const FnTypeType = *const fn (?*anyopaque) callconv(CC) c_int;
const FnMethodParam = *const fn (?*anyopaque, u32) callconv(CC) ?*anyopaque;
const FnMethodParamName = *const fn (?*anyopaque, u32) callconv(CC) ?CStr;
const FnStringNew = *const fn (CStr) callconv(CC) ?*anyopaque; // no domain arg, unlike mono_string_new
const FnMethodFlags = *const fn (?*anyopaque, *u32) callconv(CC) u32;

const Il2CppApi = struct {
    allocator: std.mem.Allocator,
    root_domain: ?*anyopaque = null,
    module_buf: [256]u8 = undefined,
    module_len: usize = 0,

    domain_get: FnDomain,
    thread_attach: FnThreadAttach,
    domain_get_assemblies: FnGetAssemblies,
    assembly_get_image: FnP_P,
    image_get_name: FnP_CStr,
    image_get_filename: ?FnP_CStr, // optional because IL2CPP export sets vary by Unity version
    image_get_class_count: FnImgCount,
    image_get_class: FnImgClass,
    class_get_name: FnP_CStr,
    class_get_namespace: FnP_CStr,
    class_get_parent: FnP_P,
    class_get_fields: FnIter,
    field_get_name: FnP_CStr,
    field_get_type: FnP_P,
    type_get_name: FnTypeName,
    field_get_offset: FnFieldOffset,
    field_get_flags: FnFieldFlags,
    class_get_methods: FnIter,
    method_get_name: FnP_CStr,
    method_get_param_count: FnParamCount,
    method_get_param: FnMethodParam,
    method_get_param_name: ?FnMethodParamName,
    method_get_return_type: FnP_P,
    method_get_flags: ?FnMethodFlags,
    type_get_type: FnTypeType,
    string_new: ?FnStringNew,
    string_to_utf8: ?FnP_CStr,
    object_unbox: ?FnP_P,
    runtime_class_init: ?FnClassInit,
    class_from_name: FnFromName,
    free: ?FnFree,
    runtime_invoke: ?FnInvoke = null,
};

// Cast a dlsym result to a typed fn pointer.
fn req(comptime T: type, handle: ?*anyopaque, name: [*:0]const u8) !T {
    const p = std.c.dlsym(handle, name) orelse return error.SymbolMissing;
    return @ptrCast(p);
}
fn opt(comptime T: type, handle: ?*anyopaque, name: [*:0]const u8) ?T {
    const p = std.c.dlsym(handle, name) orelse return null;
    return @ptrCast(p);
}

// Find the path of the mapped IL2CPP runtime in our own maps, NUL-terminated in "buf".
fn findRuntimeModule(allocator: std.mem.Allocator, buf: []u8) ?[:0]const u8 {
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
        if (std.mem.indexOf(u8, line, "GameAssembly") == null) continue;
        // The pathname is the final maps column but can contain spaces (e.g. ".../Total Reload Demo/GameAssembly.so")
        // so we can't take the last space delimited token.
        // This means that for a file backed mapping the path is absolute -> take from the first "/".
        const start = std.mem.indexOfScalar(u8, line, '/') orelse continue;
        const path = line[start..];
        if (path.len == 0 or path.len >= buf.len) return null;
        @memcpy(buf[0..path.len], path);
        buf[path.len] = 0;
        return buf[0..path.len :0];
    }
    return null;
}

pub fn load(allocator: std.mem.Allocator) !?rt.Backend {
    // Resolve a handle through which the il2cpp_* exports are visible.
    // First try dlopen(NULL) which sees the global scope, which is enough for a runtime linked
    // into the executable or loaded thru RTLD_GLOBAL.
    // Most of the time Unity games dlopen GameAssembly.so with RTLD_LOCAL though, which results
    // in the il2cpp_* symbols to not be in the global scope.
    // In that case we'll dlopen the already mapped module by path, where RTLD_NOLOAD attaches to the copy
    // and doesn't load a new one, to get a proper handle.
    var h = std.c.dlopen(null, std.c.RTLD{ .NOW = true });
    if (std.c.dlsym(h, "il2cpp_domain_get") == null) {
        var path_buf: [4096]u8 = undefined;
        const path = findRuntimeModule(allocator, &path_buf) orelse return null;
        h = std.c.dlopen(path.ptr, std.c.RTLD{ .NOW = true, .NOLOAD = true });
        // Not an IL2CPP process or the runtime's symbols are genuinely absent. RIP...
        if (h == null or std.c.dlsym(h, "il2cpp_domain_get") == null) return null;
    }

    const api = try allocator.create(Il2CppApi);
    api.* = .{
        .allocator = allocator,
        .domain_get = try req(FnDomain, h, "il2cpp_domain_get"),
        .thread_attach = try req(FnThreadAttach, h, "il2cpp_thread_attach"),
        .domain_get_assemblies = try req(FnGetAssemblies, h, "il2cpp_domain_get_assemblies"),
        .assembly_get_image = try req(FnP_P, h, "il2cpp_assembly_get_image"),
        .image_get_name = try req(FnP_CStr, h, "il2cpp_image_get_name"),
        .image_get_filename = opt(FnP_CStr, h, "il2cpp_image_get_filename"),
        .image_get_class_count = try req(FnImgCount, h, "il2cpp_image_get_class_count"),
        .image_get_class = try req(FnImgClass, h, "il2cpp_image_get_class"),
        .class_get_name = try req(FnP_CStr, h, "il2cpp_class_get_name"),
        .class_get_namespace = try req(FnP_CStr, h, "il2cpp_class_get_namespace"),
        .class_get_parent = try req(FnP_P, h, "il2cpp_class_get_parent"),
        .class_get_fields = try req(FnIter, h, "il2cpp_class_get_fields"),
        .field_get_name = try req(FnP_CStr, h, "il2cpp_field_get_name"),
        .field_get_type = try req(FnP_P, h, "il2cpp_field_get_type"),
        .type_get_name = try req(FnTypeName, h, "il2cpp_type_get_name"),
        .field_get_offset = try req(FnFieldOffset, h, "il2cpp_field_get_offset"),
        .field_get_flags = try req(FnFieldFlags, h, "il2cpp_field_get_flags"),
        .class_get_methods = try req(FnIter, h, "il2cpp_class_get_methods"),
        .method_get_name = try req(FnP_CStr, h, "il2cpp_method_get_name"),
        .method_get_param_count = try req(FnParamCount, h, "il2cpp_method_get_param_count"),
        .method_get_param = try req(FnMethodParam, h, "il2cpp_method_get_param"),
        .method_get_param_name = opt(FnMethodParamName, h, "il2cpp_method_get_param_name"),
        .method_get_return_type = try req(FnP_P, h, "il2cpp_method_get_return_type"),
        .method_get_flags = opt(FnMethodFlags, h, "il2cpp_method_get_flags"),
        .type_get_type = try req(FnTypeType, h, "il2cpp_type_get_type"),
        .string_new = opt(FnStringNew, h, "il2cpp_string_new"),
        .string_to_utf8 = opt(FnP_CStr, h, "il2cpp_string_to_utf8"),
        .object_unbox = opt(FnP_P, h, "il2cpp_object_unbox"),
        .runtime_class_init = opt(FnClassInit, h, "il2cpp_runtime_class_init"),
        .class_from_name = try req(FnFromName, h, "il2cpp_class_from_name"),
        .free = opt(FnFree, h, "il2cpp_free"),
        .runtime_invoke = opt(FnInvoke, h, "il2cpp_runtime_invoke"),
    };

    api.root_domain = api.domain_get();
    _ = api.thread_attach(api.root_domain);

    // Record the runtime module path for hello's "module" field.
    var module_buf: [4096]u8 = undefined;
    if (findRuntimeModule(allocator, &module_buf)) |path| {
        const len = @min(path.len, api.module_buf.len);
        @memcpy(api.module_buf[0..len], path[0..len]);
        api.module_len = len;
    }

    return rt.Backend{
        .ctx = api,
        .kind = .il2cpp,
        .helloFn = il2cppHello,
        .assembliesFn = il2cppAssemblies,
        .classesFn = il2cppClasses,
        .fieldsFn = il2cppFields,
        .methodsFn = il2cppMethods,
        .compileFn = il2cppCompile,
        .staticAddrFn = il2cppStaticAddr,
        .findClassFn = il2cppFindClass,
        .invokeFn = il2cppInvoke,
        .signatureFn = il2cppSignature,
    };
}

inline fn self(ctx: *anyopaque) *Il2CppApi {
    return @ptrCast(@alignCast(ctx));
}

fn il2cppHello(ctx: *anyopaque, e: *Encoder) !void {
    const m = self(ctx);
    try e.mapHeader(6);
    try e.str("version");
    try e.uint(1);
    try e.str("arch");
    try e.str(if (@sizeOf(usize) == 8) "x64" else "x86");
    try e.str("runtime");
    try e.str("il2cpp");
    try e.str("abi");
    try e.str("sysv");
    try e.str("module");
    try e.str(m.module_buf[0..m.module_len]);
    try e.str("root_domain");
    try e.uint(@intFromPtr(m.root_domain));
}

fn il2cppAssemblies(ctx: *anyopaque, e: *Encoder) !void {
    const m = self(ctx);
    var count: usize = 0;
    const arr = m.domain_get_assemblies(m.root_domain, &count);
    try e.arrayHeader(if (arr == null) 0 else count);
    if (arr) |list| {
        var i: usize = 0;
        while (i < count) : (i += 1) {
            const asm_ptr = list[i];
            const img = m.assembly_get_image(asm_ptr);
            try e.mapHeader(4);
            try e.str("assembly");
            try e.uint(@intFromPtr(asm_ptr));
            try e.str("image");
            try e.uint(@intFromPtr(img));
            try e.str("name");
            try e.str(cspan(m.image_get_name(img)));
            try e.str("filename");
            try e.str(if (m.image_get_filename) |f| cspan(f(img)) else "");
        }
    }
}

fn il2cppClasses(ctx: *anyopaque, image_u: u64, e: *Encoder) !void {
    const m = self(ctx);
    const image: ?*anyopaque = @ptrFromInt(@as(usize, @intCast(image_u)));
    const count = m.image_get_class_count(image);
    try e.arrayHeader(count);

    var i: usize = 0;
    while (i < count) : (i += 1) {
        const klass = m.image_get_class(image, i);
        try e.mapHeader(5);
        try e.str("klass");
        try e.uint(@intFromPtr(klass));
        try e.str("namespace");
        try e.str(cspan(m.class_get_namespace(klass)));
        try e.str("name");
        try e.str(cspan(m.class_get_name(klass)));
        try e.str("parent");
        try e.uint(@intFromPtr(m.class_get_parent(klass)));
        try e.str("token");
        try e.uint(@as(u64, i + 1)); // IL2CPP has no metadata token here (unlike mono) so we'll create a 1-based index for parity
    }
}

const FIELD_ATTRIBUTE_STATIC: u32 = 0x10;
fn il2cppFields(ctx: *anyopaque, klass_u: u64, e: *Encoder) !void {
    const m = self(ctx);
    const klass: ?*anyopaque = @ptrFromInt(@as(usize, @intCast(klass_u)));

    var list: std.ArrayList(u64) = .empty;
    defer list.deinit(m.allocator);
    var iter: ?*anyopaque = null;
    while (m.class_get_fields(klass, &iter)) |fld| try list.append(m.allocator, @intFromPtr(fld));
    try e.arrayHeader(list.items.len);

    for (list.items) |fu| {
        const fld: ?*anyopaque = @ptrFromInt(@as(usize, @intCast(fu)));
        const ftype = m.field_get_type(fld);
        const tname = m.type_get_name(ftype);
        const flags: u32 = @bitCast(m.field_get_flags(fld));
        try e.mapHeader(6);
        try e.str("field");
        try e.uint(fu);
        try e.str("name");
        try e.str(cspan(m.field_get_name(fld)));
        try e.str("type");
        try e.str(cspan(tname));
        try e.str("offset");
        try e.uint(@intCast(m.field_get_offset(fld)));
        try e.str("flags");
        try e.uint(flags);
        try e.str("is_static");
        try e.boolean((flags & FIELD_ATTRIBUTE_STATIC) != 0);
        if (m.free) |fr| if (tname) |p| fr(@ptrCast(@constCast(p)));
    }
}

fn il2cppMethods(ctx: *anyopaque, klass_u: u64, e: *Encoder) !void {
    const m = self(ctx);
    const klass: ?*anyopaque = @ptrFromInt(@as(usize, @intCast(klass_u)));

    var list: std.ArrayList(u64) = .empty;
    defer list.deinit(m.allocator);
    var iter: ?*anyopaque = null;
    while (m.class_get_methods(klass, &iter)) |meth| try list.append(m.allocator, @intFromPtr(meth));
    try e.arrayHeader(list.items.len);

    for (list.items) |mu| {
        // Still not the drug...
        const meth: ?*anyopaque = @ptrFromInt(@as(usize, @intCast(mu)));
        const nm = cspan(m.method_get_name(meth));
        const pc: u64 = m.method_get_param_count(meth);

        try e.mapHeader(4);
        try e.str("method");
        try e.uint(mu);
        try e.str("name");
        try e.str(nm);
        try e.str("full_name");
        try e.str(nm); // IL2CPP exposes no full-signature API so we'll reuse the name (which is less rich than Mono's mono_method_full_name)
        try e.str("param_count");
        try e.uint(pc);
    }
}

fn il2cppCompile(ctx: *anyopaque, method_u: u64, e: *Encoder) !void {
    _ = ctx;
    // IL2CPP is AOT (ahead of time) compilation so there is no JIT/compile step.
    // MethodInfo.methodPointer is the first struct field (offset 0) across known IL2CPP versions,
    // so the native code address is the pointer sized value stored at the MethodInfo handle.
    var addr: u64 = 0;
    if (method_u != 0) {
        const mi: *const usize = @ptrFromInt(@as(usize, @intCast(method_u)));
        addr = mi.*;
    }

    try e.mapHeader(1);
    try e.str("native_addr");
    try e.uint(addr);
}

fn il2cppStaticAddr(ctx: *anyopaque, klass_u: u64, field_u: u64, e: *Encoder) !void {
    _ = ctx;
    _ = klass_u;
    _ = field_u;
    _ = e;
    // IL2CPP exposes no public getter for a static field's absolute address.
    // The base lives in Il2CppClass.static_fields, reachable only by reading the (heavily version dependent) class struct raw.
    return error.Unsupported;
}

fn il2cppFindClass(ctx: *anyopaque, image_u: u64, ns: []const u8, name: []const u8, e: *Encoder) !void {
    const m = self(ctx);
    const image: ?*anyopaque = @ptrFromInt(@as(usize, @intCast(image_u)));

    // il2cpp_class_from_name needs NUL-terminated C strings.
    var ns_buf: [512]u8 = undefined;
    var nm_buf: [512]u8 = undefined;
    if (ns.len >= ns_buf.len or name.len >= nm_buf.len) return error.NameTooLong;
    @memcpy(ns_buf[0..ns.len], ns);
    ns_buf[ns.len] = 0;
    @memcpy(nm_buf[0..name.len], name);
    nm_buf[name.len] = 0;

    const klass = m.class_from_name(image, @ptrCast(&ns_buf), @ptrCast(&nm_buf));

    try e.mapHeader(1);
    try e.str("klass");
    try e.uint(@intFromPtr(klass));
}

inline fn eql(a: []const u8, b: []const u8) bool {
    return std.mem.eql(u8, a, b);
}

// Il2CppTypeEnum -> our wire tag.
// IL2CPP reuses the MONO_TYPE_* values, so this mirrors mono_api.zig typeTag exactly.
fn typeTag(t: c_int) []const u8 {
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
        0x0f, 0x18, 0x19 => if (@sizeOf(usize) == 8) "u8" else "u4", // PTR, I (IntPtr), U (UIntPtr)
        0x12, 0x14, 0x1c, 0x1d => "object", // CLASS, ARRAY, OBJECT, SZARRAY
        else => "unsupported",
    };
}

fn typeWidth(tag: []const u8) usize {
    if (eql(tag, "i1") or eql(tag, "u1") or eql(tag, "bool")) return 1;
    if (eql(tag, "i2") or eql(tag, "u2") or eql(tag, "char")) return 2;
    if (eql(tag, "i4") or eql(tag, "u4") or eql(tag, "r4")) return 4;
    return 8;
}

inline fn encodeTypeRef(m: *Il2CppApi, e: *Encoder, t: ?*anyopaque) !void {
    const tname = m.type_get_name(t);
    try e.mapHeader(2);
    try e.str("tag");
    try e.str(typeTag(m.type_get_type(t)));
    try e.str("name");
    try e.str(cspan(tname));
    if (m.free) |fr| if (tname) |p| fr(@ptrCast(@constCast(p)));
}

// Same wire shape as monoSignature, but IL2CPP enumerates params by index and not an iterator.
// Static-ness is carried in the method flags (no signature object).
fn il2cppSignature(ctx: *anyopaque, method_u: u64, e: *Encoder) !void {
    const m = self(ctx);
    const meth: ?*anyopaque = @ptrFromInt(@as(usize, @intCast(method_u)));
    const pc = m.method_get_param_count(meth);

    var is_static = false;
    if (m.method_get_flags) |gf| {
        var iflags: u32 = 0;
        const flags = gf(meth, &iflags);
        is_static = (flags & 0x10) != 0; // METHOD_ATTRIBUTE_STATIC
    }

    try e.mapHeader(3);
    try e.str("static");
    try e.boolean(is_static);
    try e.str("ret");
    try encodeTypeRef(m, e, m.method_get_return_type(meth));
    try e.str("params");
    try e.arrayHeader(pc);
    var i: u32 = 0;
    while (i < pc) : (i += 1) {
        const ptype = m.method_get_param(meth, i);
        const tname = m.type_get_name(ptype);
        try e.mapHeader(3);
        try e.str("name");
        const pname = if (m.method_get_param_name) |gpn| gpn(meth, i) else null;
        if (pname != null) {
            try e.str(cspan(pname));
        } else {
            var nb: [16]u8 = undefined;
            try e.str(std.fmt.bufPrint(&nb, "arg{d}", .{i}) catch "arg");
        }
        try e.str("tag");
        try e.str(typeTag(m.type_get_type(ptype)));
        try e.str("type");
        try e.str(cspan(tname));
        if (m.free) |fr| if (tname) |p| fr(@ptrCast(@constCast(p)));
    }
}

fn il2cppInvoke(ctx: *anyopaque, method_u: u64, obj_u: u64, args: []const rt.Arg, e: *Encoder) !void {
    const m = self(ctx);
    const invoke = m.runtime_invoke orelse return error.Unsupported;
    const meth: ?*anyopaque = @ptrFromInt(@as(usize, @intCast(method_u)));
    const obj: ?*anyopaque = if (obj_u == 0) null else @ptrFromInt(@as(usize, @intCast(obj_u)));

    const slots = try m.allocator.alloc(u64, args.len);
    defer m.allocator.free(slots);
    const argv = try m.allocator.alloc(?*anyopaque, args.len);
    defer m.allocator.free(argv);

    for (args, 0..) |a, i| {
        if (eql(a.tag, "str")) {
            const sn = m.string_new orelse return error.Unsupported;
            var sbuf: [1024]u8 = undefined;
            if (a.str.len >= sbuf.len) return error.NameTooLong;
            @memcpy(sbuf[0..a.str.len], a.str);
            sbuf[a.str.len] = 0;
            argv[i] = sn(@ptrCast(&sbuf)); // il2cpp_string_new takes no domain (unlike mono)
        } else if (eql(a.tag, "object")) {
            argv[i] = @ptrFromInt(@as(usize, @intCast(a.bits)));
        } else if (eql(a.tag, "nil")) {
            argv[i] = null;
        } else {
            slots[i] = a.bits; // little-endian native, low N bytes are the value
            argv[i] = &slots[i]; // value type: pointer to the value
        }
    }
    const argv_ptr: ?[*]?*anyopaque = if (args.len == 0) null else argv.ptr;

    var exc: ?*anyopaque = null;
    const ret = invoke(meth, obj, argv_ptr, &exc);

    try e.mapHeader(2);
    try e.str("result");
    if (exc != null) {
        try e.nil();
    } else {
        const rtype = m.method_get_return_type(meth);
        const renum: c_int = if (rtype != null) m.type_get_type(rtype) else 0x01; // void if no return type
        const rtag = typeTag(renum);
        if (renum == 0x01 or ret == null) { // void / null
            try e.nil();
        } else if (eql(rtag, "str")) {
            if (m.string_to_utf8) |conv| {
                const c = conv(ret);
                try e.mapHeader(2);
                try e.str("tag");
                try e.str("str");
                try e.str("val");
                try e.str(cspan(c));
                if (m.free) |fr| if (c) |p| fr(@ptrCast(@constCast(p)));
            } else {
                try e.mapHeader(2);
                try e.str("tag");
                try e.str("object");
                try e.str("bits");
                try e.uint(@intFromPtr(ret));
            }
        } else if (eql(rtag, "object")) {
            try e.mapHeader(2);
            try e.str("tag");
            try e.str("object");
            try e.str("bits");
            try e.uint(@intFromPtr(ret));
        } else { // value type: unbox and read its bytes
            const ub = m.object_unbox orelse return error.Unsupported;
            const vp = ub(ret);
            var bits: u64 = 0;
            const w = typeWidth(rtag);
            if (vp) |p| {
                const src: [*]const u8 = @ptrCast(p);
                @memcpy(std.mem.asBytes(&bits)[0..w], src[0..w]);
            }
            try e.mapHeader(2);
            try e.str("tag");
            try e.str(rtag);
            try e.str("bits");
            try e.uint(bits);
        }
    }
    try e.str("exception");
    try e.uint(@intFromPtr(exc));
}
