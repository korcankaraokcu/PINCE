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
//!   - IL2CPP exposes no static field base getter so il2cppStaticAddr auto-calibrates the Il2CppClass.static_fields offset once at load (calibrateStaticFields), returning Unsupported when calibration is ambiguous.
//!   - signature enumerates params by index (il2cpp_method_get_param) with staticness from the method flags.
const std = @import("std");
const rt = @import("runtime.zig");
const Encoder = @import("msgpack.zig").Encoder;
const resolver = @import("resolver.zig");
const common = @import("common.zig");

const CC = common.CC;
const CStr = common.CStr;
const cspan = common.cspan;
const eql = common.eql;
const typeTag = common.typeTag;
const typeWidth = common.typeWidth;
const StructInfo = common.StructInfo;
const structInfo = common.structInfo;
const encodeTypeRef = common.encodeTypeRef;
const req = common.req;
const opt = common.opt;

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
const FnGetCorlib = *const fn () callconv(CC) ?*anyopaque;
const FnFieldFromName = *const fn (?*anyopaque, CStr) callconv(CC) ?*anyopaque;
const FnFieldStaticGet = *const fn (?*anyopaque, *anyopaque) callconv(CC) void;
const FnValueSize = *const fn (?*anyopaque, ?*u32) callconv(CC) c_int;

const Il2CppApi = struct {
    allocator: std.mem.Allocator,
    root_domain: ?*anyopaque = null,
    module_buf: [256]u8 = undefined,
    module_len: usize = 0,
    static_fields_offset: ?usize = null,

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
    class_from_type: ?FnP_P,
    class_value_size: ?FnValueSize,
    free: ?FnFree,
    runtime_invoke: ?FnInvoke = null,
    get_corlib: ?FnGetCorlib,
    class_get_field_from_name: ?FnFieldFromName,
    field_static_get_value: ?FnFieldStaticGet,
};

pub fn load(allocator: std.mem.Allocator) !?rt.Backend {
    // Bind the runtime module using the resolver.
    // ELF -> dlopen/dlsym, PE -> export parsing.
    const substr = if (resolver.is_wine) "GameAssembly.dll" else "GameAssembly";
    var path_buf: [256]u8 = undefined;
    var path_len: usize = 0;
    const mod = resolver.open(allocator, "il2cpp_domain_get", substr, &path_buf, &path_len) orelse return null;

    const api = try allocator.create(Il2CppApi);
    api.* = .{
        .allocator = allocator,
        .domain_get = try req(FnDomain, mod, "il2cpp_domain_get"),
        .thread_attach = try req(FnThreadAttach, mod, "il2cpp_thread_attach"),
        .domain_get_assemblies = try req(FnGetAssemblies, mod, "il2cpp_domain_get_assemblies"),
        .assembly_get_image = try req(FnP_P, mod, "il2cpp_assembly_get_image"),
        .image_get_name = try req(FnP_CStr, mod, "il2cpp_image_get_name"),
        .image_get_filename = opt(FnP_CStr, mod, "il2cpp_image_get_filename"),
        .image_get_class_count = try req(FnImgCount, mod, "il2cpp_image_get_class_count"),
        .image_get_class = try req(FnImgClass, mod, "il2cpp_image_get_class"),
        .class_get_name = try req(FnP_CStr, mod, "il2cpp_class_get_name"),
        .class_get_namespace = try req(FnP_CStr, mod, "il2cpp_class_get_namespace"),
        .class_get_parent = try req(FnP_P, mod, "il2cpp_class_get_parent"),
        .class_get_fields = try req(FnIter, mod, "il2cpp_class_get_fields"),
        .field_get_name = try req(FnP_CStr, mod, "il2cpp_field_get_name"),
        .field_get_type = try req(FnP_P, mod, "il2cpp_field_get_type"),
        .type_get_name = try req(FnTypeName, mod, "il2cpp_type_get_name"),
        .field_get_offset = try req(FnFieldOffset, mod, "il2cpp_field_get_offset"),
        .field_get_flags = try req(FnFieldFlags, mod, "il2cpp_field_get_flags"),
        .class_get_methods = try req(FnIter, mod, "il2cpp_class_get_methods"),
        .method_get_name = try req(FnP_CStr, mod, "il2cpp_method_get_name"),
        .method_get_param_count = try req(FnParamCount, mod, "il2cpp_method_get_param_count"),
        .method_get_param = try req(FnMethodParam, mod, "il2cpp_method_get_param"),
        .method_get_param_name = opt(FnMethodParamName, mod, "il2cpp_method_get_param_name"),
        .method_get_return_type = try req(FnP_P, mod, "il2cpp_method_get_return_type"),
        .method_get_flags = opt(FnMethodFlags, mod, "il2cpp_method_get_flags"),
        .type_get_type = try req(FnTypeType, mod, "il2cpp_type_get_type"),
        .string_new = opt(FnStringNew, mod, "il2cpp_string_new"),
        .string_to_utf8 = opt(FnP_CStr, mod, "il2cpp_string_to_utf8"),
        .object_unbox = opt(FnP_P, mod, "il2cpp_object_unbox"),
        .runtime_class_init = opt(FnClassInit, mod, "il2cpp_runtime_class_init"),
        .class_from_name = try req(FnFromName, mod, "il2cpp_class_from_name"),
        .class_from_type = opt(FnP_P, mod, "il2cpp_class_from_type"),
        .class_value_size = opt(FnValueSize, mod, "il2cpp_class_value_size"),
        .free = opt(FnFree, mod, "il2cpp_free"),
        .runtime_invoke = opt(FnInvoke, mod, "il2cpp_runtime_invoke"),
        .get_corlib = opt(FnGetCorlib, mod, "il2cpp_get_corlib"),
        .class_get_field_from_name = opt(FnFieldFromName, mod, "il2cpp_class_get_field_from_name"),
        .field_static_get_value = opt(FnFieldStaticGet, mod, "il2cpp_field_static_get_value"),
    };

    api.root_domain = api.domain_get();
    _ = api.thread_attach(api.root_domain);
    api.static_fields_offset = calibrateStaticFields(api);

    @memcpy(api.module_buf[0..path_len], path_buf[0..path_len]);
    api.module_len = path_len;

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
        .classInfoFn = il2cppClassInfo,
        .typeKlassFn = il2cppTypeKlass,
        .instanceMarkerFn = il2cppInstanceMarker,
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
        try e.mapHeader(7);
        try e.str("field");
        try e.uint(fu);
        try e.str("name");
        try e.str(cspan(m.field_get_name(fld)));
        try e.str("type");
        try e.str(cspan(tname));
        try e.str("tag");
        try e.str(typeTag(m.type_get_type(ftype)));
        try e.str("offset");
        try e.uint(@intCast(m.field_get_offset(fld)));
        try e.str("flags");
        try e.uint(flags);
        try e.str("is_static");
        try e.boolean((flags & FIELD_ATTRIBUTE_STATIC) != 0);
        if (m.free) |fr| if (tname) |p| fr(@ptrCast(@constCast(p)));
    }
}

inline fn appendName(buf: []u8, off: *usize, s: []const u8) void {
    const n = @min(s.len, buf.len - off.*);
    @memcpy(buf[off.* .. off.* + n], s[0..n]);
    off.* += n;
}

fn formatFullName(m: *Il2CppApi, meth: ?*anyopaque, buf: []u8) []const u8 {
    var off: usize = 0;
    const rname = m.type_get_name(m.method_get_return_type(meth));
    appendName(buf, &off, cspan(rname));
    if (m.free) |fr| if (rname) |p| fr(@ptrCast(@constCast(p)));
    appendName(buf, &off, " ");
    appendName(buf, &off, cspan(m.method_get_name(meth)));
    appendName(buf, &off, "(");
    const pc = m.method_get_param_count(meth);
    var i: u32 = 0;
    while (i < pc) : (i += 1) {
        if (i != 0) appendName(buf, &off, ", ");
        const pname = m.type_get_name(m.method_get_param(meth, i));
        appendName(buf, &off, cspan(pname));
        if (m.free) |fr| if (pname) |p| fr(@ptrCast(@constCast(p)));
    }
    appendName(buf, &off, ")");
    return buf[0..off];
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
        var fnbuf: [512]u8 = undefined;
        try e.str("full_name");
        try e.str(formatFullName(m, meth, &fnbuf));
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

inline fn classWord(klass: ?*anyopaque, off: usize) usize {
    const p: [*]const u8 = @ptrCast(klass);
    return @as(*align(1) const usize, @ptrCast(p + off)).*;
}

// Fault-safe word read via /proc/self/mem so an unmapped address errors instead of faulting.
inline fn calibReadWord(mem: anytype, io: anytype, addr: usize) ?usize {
    var out: usize = 0;
    const n = mem.readPositionalAll(io, std.mem.asBytes(&out), addr) catch return null;
    if (n != @sizeOf(usize)) return null;
    return out;
}

const SF_SCAN_WINDOW: usize = 0x280;
fn calibrateStaticFields(m: *Il2CppApi) ?usize {
    const get_corlib = m.get_corlib orelse return null;
    const get_field = m.class_get_field_from_name orelse return null;
    const static_get = m.field_static_get_value orelse return null;
    const class_init = m.runtime_class_init orelse return null;

    const corlib = get_corlib() orelse return null;
    const str_klass = m.class_from_name(corlib, "System", "String") orelse return null;
    class_init(str_klass);
    const empty = get_field(str_klass, "Empty") orelse return null;
    var empty_val: usize = 0;
    static_get(empty, @ptrCast(&empty_val));
    if (empty_val == 0) return null;
    const empty_off: usize = @intCast(m.field_get_offset(empty));
    const obj_klass = m.class_from_name(corlib, "System", "Object") orelse return null;

    const io = std.Io.Threaded.global_single_threaded.io();
    const mem = std.Io.Dir.openFileAbsolute(io, "/proc/self/mem", .{}) catch return null;
    defer mem.close(io);

    // static_fields offset in Il2CppClass varies by Unity version so we find it at load.
    // No unique match -> leave it null so static_addr never returns a wrong address.
    const str_addr = @intFromPtr(str_klass);
    const obj_addr = @intFromPtr(obj_klass);
    var found: ?usize = null;
    var k: usize = 0;
    while (k <= SF_SCAN_WINDOW) : (k += @sizeOf(usize)) {
        const cand = calibReadWord(mem, io, str_addr + k) orelse break; // ran off the struct
        if (cand == 0) continue;
        const got = calibReadWord(mem, io, cand + empty_off) orelse continue;
        if (got != empty_val) continue;
        const ow = calibReadWord(mem, io, obj_addr + k) orelse continue;
        if (ow != 0) continue;
        if (found != null) return null; // ambiguous
        found = k;
    }
    return found;
}

fn il2cppStaticAddr(ctx: *anyopaque, klass_u: u64, field_u: u64, e: *Encoder) !void {
    const m = self(ctx);
    const sf_off = m.static_fields_offset orelse return error.Unsupported;
    const klass: ?*anyopaque = @ptrFromInt(@as(usize, @intCast(klass_u)));
    const fld: ?*anyopaque = @ptrFromInt(@as(usize, @intCast(field_u)));

    if (m.runtime_class_init) |ci| ci(klass);
    const base: u64 = classWord(klass, sf_off);
    if (base == 0) return error.Unsupported;

    const addr: u64 = base +% @as(u64, @intCast(m.field_get_offset(fld)));
    try e.mapHeader(1);
    try e.str("address");
    try e.uint(addr);
}

// An IL2CPP object's first word is its Il2CppClass* (the klass handle), so the marker is just that handle.
fn il2cppInstanceMarker(ctx: *anyopaque, klass_u: u64, e: *Encoder) !void {
    _ = ctx;
    try e.mapHeader(1);
    try e.str("marker");
    try e.uint(klass_u);
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

fn il2cppClassInfo(ctx: *anyopaque, klass_u: u64, e: *Encoder) !void {
    const m = self(ctx);
    const klass: ?*anyopaque = @ptrFromInt(@as(usize, @intCast(klass_u)));
    try e.mapHeader(3);
    try e.str("namespace");
    try e.str(cspan(m.class_get_namespace(klass)));
    try e.str("name");
    try e.str(cspan(m.class_get_name(klass)));
    try e.str("parent");
    try e.uint(@intFromPtr(m.class_get_parent(klass)));
}

fn il2cppTypeKlass(ctx: *anyopaque, field_u: u64, e: *Encoder) !void {
    const m = self(ctx);
    const fld: ?*anyopaque = @ptrFromInt(@as(usize, @intCast(field_u)));
    var kptr: ?*anyopaque = null;
    if (m.class_from_type) |cft| {
        if (m.field_get_type(fld)) |t| kptr = cft(t);
    }
    try e.mapHeader(1);
    try e.str("klass");
    try e.uint(@intFromPtr(kptr));
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
        const tag = typeTag(m.type_get_type(ptype));
        const is_struct = eql(tag, "struct");
        const si = if (is_struct) structInfo(m, ptype) else StructInfo{ .klass = null, .size = 0 };
        try e.mapHeader(if (is_struct) 5 else 3);
        try e.str("name");
        const pname = if (m.method_get_param_name) |gpn| gpn(meth, i) else null;
        if (pname != null) {
            try e.str(cspan(pname));
        } else {
            var nb: [16]u8 = undefined;
            try e.str(std.fmt.bufPrint(&nb, "arg{d}", .{i}) catch "arg");
        }
        try e.str("tag");
        try e.str(tag);
        try e.str("type");
        try e.str(cspan(tname));
        if (is_struct) {
            try e.str("klass");
            try e.uint(@intFromPtr(si.klass));
            try e.str("size");
            try e.uint(si.size);
        }
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
        } else if (eql(a.tag, "struct")) {
            argv[i] = @constCast(a.str.ptr); // value type: raw bytes live in the request frame for the call
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
        } else if (eql(rtag, "struct")) { // value type by value: unbox and ship its raw bytes
            const ub = m.object_unbox orelse return error.Unsupported;
            const si = structInfo(m, rtype);
            const vp = ub(ret);
            if (vp == null or si.size == 0) {
                try e.nil();
            } else {
                try e.mapHeader(2);
                try e.str("tag");
                try e.str("struct");
                try e.str("bytes");
                const src: [*]const u8 = @ptrCast(vp);
                try e.bin(src[0..@intCast(si.size)]);
            }
        } else { // primitive value type: unbox and read its bytes
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
