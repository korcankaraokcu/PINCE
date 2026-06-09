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

//! Mono embedding API backend.
//! Resolves mono_* via dlsym from the already loaded runtime, attaches the worker thread and implements the runtime.Backend vtable.
const std = @import("std");
const rt = @import("runtime.zig");
const Encoder = @import("msgpack.zig").Encoder;

const CC: std.builtin.CallingConvention = .c; // Note for later: .x86_64_win for Wine

const CStr = [*:0]const u8;

fn cspan(p: ?CStr) []const u8 {
    return if (p) |s| std.mem.span(s) else "";
}

// mono_* function pointer types
const FnDomain = *const fn () callconv(CC) ?*anyopaque;
const FnP_P = *const fn (?*anyopaque) callconv(CC) ?*anyopaque;
const ForeachCb = *const fn (?*anyopaque, ?*anyopaque) callconv(CC) void;
const FnForeach = *const fn (ForeachCb, ?*anyopaque) callconv(CC) void;
const FnP_CStr = *const fn (?*anyopaque) callconv(CC) ?CStr;
const FnImgTable = *const fn (?*anyopaque, c_int) callconv(CC) ?*anyopaque;
const FnRows = *const fn (?*anyopaque) callconv(CC) c_int;
const FnClassGet = *const fn (?*anyopaque, u32) callconv(CC) ?*anyopaque;
const FnIter = *const fn (?*anyopaque, *?*anyopaque) callconv(CC) ?*anyopaque;
const FnFieldOffset = *const fn (?*anyopaque) callconv(CC) c_int;
const FnFieldFlags = *const fn (?*anyopaque) callconv(CC) u32;
const FnTypeName = *const fn (?*anyopaque) callconv(CC) ?CStr;
const FnFullName = *const fn (?*anyopaque, c_int) callconv(CC) ?CStr;
const FnParamCount = *const fn (?*anyopaque) callconv(CC) u32;
const FnVtable = *const fn (?*anyopaque, ?*anyopaque) callconv(CC) ?*anyopaque;
const FnStaticData = *const fn (?*anyopaque) callconv(CC) ?*anyopaque;
const FnClassInit = *const fn (?*anyopaque) callconv(CC) void;
const FnFromName = *const fn (?*anyopaque, CStr, CStr) callconv(CC) ?*anyopaque;
const FnFree = *const fn (?*anyopaque) callconv(CC) void;
const FnInvoke = *const fn (?*anyopaque, ?*anyopaque, ?[*]?*anyopaque, *?*anyopaque) callconv(CC) ?*anyopaque;

const MonoApi = struct {
    allocator: std.mem.Allocator,
    root_domain: ?*anyopaque = null,
    module_buf: [256]u8 = undefined,
    module_len: usize = 0,

    get_root_domain: FnDomain,
    thread_attach: FnP_P,
    assembly_foreach: FnForeach,
    assembly_get_image: FnP_P,
    image_get_name: FnP_CStr,
    image_get_filename: FnP_CStr,
    image_get_table_info: FnImgTable,
    table_info_get_rows: FnRows,
    class_get: FnClassGet,
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
    method_full_name: FnFullName,
    method_signature: FnP_P,
    signature_get_param_count: FnParamCount,
    compile_method: FnP_P,
    class_vtable: FnVtable,
    vtable_get_static_field_data: FnStaticData,
    runtime_class_init: ?FnClassInit,
    class_from_name: FnFromName,
    free: ?FnFree,
    runtime_invoke: ?FnInvoke = null, // TODO BRK: change this when invoke is implemented
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

fn scanModule(api: *MonoApi) void {
    const io = std.Io.Threaded.global_single_threaded.io();
    const f = std.Io.Dir.openFileAbsolute(io, "/proc/self/maps", .{}) catch return;
    defer f.close(io);
    var contents: [1 << 16]u8 = undefined;
    const n = f.readPositionalAll(io, &contents, 0) catch return;
    var it = std.mem.splitScalar(u8, contents[0..n], '\n');
    while (it.next()) |line| {
        if (std.mem.indexOf(u8, line, "libmono") != null) {
            var fields = std.mem.tokenizeScalar(u8, line, ' ');
            var last: []const u8 = "";
            while (fields.next()) |fld| last = fld;
            const len = @min(last.len, api.module_buf.len);
            @memcpy(api.module_buf[0..len], last[0..len]);
            api.module_len = len;
            return;
        }
    }
}

pub fn load(allocator: std.mem.Allocator) !?rt.Backend {
    // Use dlopen(NULL) to resolve symbols across all loaded libs.
    const h = std.c.dlopen(null, std.c.RTLD{ .NOW = true });
    // If mono isn't loaded, the core symbol won't resolve so this is not a mono process.
    if (std.c.dlsym(h, "mono_get_root_domain") == null) return null;

    const api = try allocator.create(MonoApi);
    api.* = .{
        .allocator = allocator,
        .get_root_domain = try req(FnDomain, h, "mono_get_root_domain"),
        .thread_attach = try req(FnP_P, h, "mono_thread_attach"),
        .assembly_foreach = try req(FnForeach, h, "mono_assembly_foreach"),
        .assembly_get_image = try req(FnP_P, h, "mono_assembly_get_image"),
        .image_get_name = try req(FnP_CStr, h, "mono_image_get_name"),
        .image_get_filename = try req(FnP_CStr, h, "mono_image_get_filename"),
        .image_get_table_info = try req(FnImgTable, h, "mono_image_get_table_info"),
        .table_info_get_rows = try req(FnRows, h, "mono_table_info_get_rows"),
        .class_get = try req(FnClassGet, h, "mono_class_get"),
        .class_get_name = try req(FnP_CStr, h, "mono_class_get_name"),
        .class_get_namespace = try req(FnP_CStr, h, "mono_class_get_namespace"),
        .class_get_parent = try req(FnP_P, h, "mono_class_get_parent"),
        .class_get_fields = try req(FnIter, h, "mono_class_get_fields"),
        .field_get_name = try req(FnP_CStr, h, "mono_field_get_name"),
        .field_get_type = try req(FnP_P, h, "mono_field_get_type"),
        .type_get_name = try req(FnTypeName, h, "mono_type_get_name"),
        .field_get_offset = try req(FnFieldOffset, h, "mono_field_get_offset"),
        .field_get_flags = try req(FnFieldFlags, h, "mono_field_get_flags"),
        .class_get_methods = try req(FnIter, h, "mono_class_get_methods"),
        .method_get_name = try req(FnP_CStr, h, "mono_method_get_name"),
        .method_full_name = try req(FnFullName, h, "mono_method_full_name"),
        .method_signature = try req(FnP_P, h, "mono_method_signature"),
        .signature_get_param_count = try req(FnParamCount, h, "mono_signature_get_param_count"),
        .compile_method = try req(FnP_P, h, "mono_compile_method"),
        .class_vtable = try req(FnVtable, h, "mono_class_vtable"),
        .vtable_get_static_field_data = try req(FnStaticData, h, "mono_vtable_get_static_field_data"),
        .runtime_class_init = opt(FnClassInit, h, "mono_runtime_class_init"),
        .class_from_name = try req(FnFromName, h, "mono_class_from_name"),
        .free = opt(FnFree, h, "mono_free"),
        .runtime_invoke = opt(FnInvoke, h, "mono_runtime_invoke"),
    };

    api.root_domain = api.get_root_domain();
    _ = api.thread_attach(api.root_domain);
    scanModule(api);

    return rt.Backend{
        .ctx = api,
        .kind = .mono,
        .helloFn = monoHello,
        .assembliesFn = monoAssemblies,
        .classesFn = monoClasses,
        .fieldsFn = monoFields,
        .methodsFn = monoMethods,
        .compileFn = monoCompile,
        .staticAddrFn = monoStaticAddr,
        .findClassFn = monoFindClass,
        // TODO BRK: wire in .invokeFn in the invoke commit.
    };
}

fn self(ctx: *anyopaque) *MonoApi {
    return @ptrCast(@alignCast(ctx));
}

fn monoHello(ctx: *anyopaque, e: *Encoder) !void {
    const m = self(ctx);
    try e.mapHeader(6);
    try e.str("version");
    try e.uint(1);
    try e.str("arch");
    try e.str(if (@sizeOf(usize) == 8) "x64" else "x86");
    try e.str("runtime");
    try e.str("mono");
    try e.str("abi");
    try e.str("sysv");
    try e.str("module");
    try e.str(m.module_buf[0..m.module_len]);
    try e.str("root_domain");
    try e.uint(@intFromPtr(m.root_domain));
}

const CollectCtx = struct { list: *std.ArrayList(u64), allocator: std.mem.Allocator, oom: bool };
fn collectAssembly(asm_ptr: ?*anyopaque, user: ?*anyopaque) callconv(CC) void {
    const c: *CollectCtx = @ptrCast(@alignCast(user.?));
    c.list.append(c.allocator, @intFromPtr(asm_ptr)) catch {
        c.oom = true;
    };
}

fn monoAssemblies(ctx: *anyopaque, e: *Encoder) !void {
    const m = self(ctx);
    var list: std.ArrayList(u64) = .empty;
    defer list.deinit(m.allocator);

    var cc = CollectCtx{ .list = &list, .allocator = m.allocator, .oom = false };
    m.assembly_foreach(collectAssembly, &cc);
    if (cc.oom) return error.OutOfMemory;

    try e.arrayHeader(list.items.len);
    for (list.items) |au| {
        const asm_ptr: ?*anyopaque = @ptrFromInt(@as(usize, @intCast(au)));
        const img = m.assembly_get_image(asm_ptr);
        try e.mapHeader(4);
        try e.str("assembly");
        try e.uint(au);
        try e.str("image");
        try e.uint(@intFromPtr(img));
        try e.str("name");
        try e.str(cspan(m.image_get_name(img)));
        try e.str("filename");
        try e.str(cspan(m.image_get_filename(img)));
    }
}

const MONO_TABLE_TYPEDEF: c_int = 2;
const MONO_TOKEN_TYPE_DEF: u32 = 0x02000000;
fn monoClasses(ctx: *anyopaque, image_u: u64, e: *Encoder) !void {
    const m = self(ctx);
    const image: ?*anyopaque = @ptrFromInt(@as(usize, @intCast(image_u)));
    const tinfo = m.image_get_table_info(image, MONO_TABLE_TYPEDEF);
    const rows: usize = @intCast(@max(@as(c_int, 0), m.table_info_get_rows(tinfo)));

    var list: std.ArrayList(u64) = .empty;
    defer list.deinit(m.allocator);
    var i: usize = 0;
    while (i < rows) : (i += 1) {
        const token = MONO_TOKEN_TYPE_DEF | @as(u32, @intCast(i + 1));
        const klass = m.class_get(image, token);
        if (klass != null) try list.append(m.allocator, @intFromPtr(klass));
    }
    try e.arrayHeader(list.items.len);

    var idx: usize = 0;
    for (list.items) |ku| {
        idx += 1;
        const klass: ?*anyopaque = @ptrFromInt(@as(usize, @intCast(ku)));
        try e.mapHeader(5);
        try e.str("klass");
        try e.uint(ku);
        try e.str("namespace");
        try e.str(cspan(m.class_get_namespace(klass)));
        try e.str("name");
        try e.str(cspan(m.class_get_name(klass)));
        try e.str("parent");
        try e.uint(@intFromPtr(m.class_get_parent(klass)));
        try e.str("token");
        try e.uint(MONO_TOKEN_TYPE_DEF | @as(u32, @intCast(idx)));
    }
}

const FIELD_ATTRIBUTE_STATIC: u32 = 0x10;
fn monoFields(ctx: *anyopaque, klass_u: u64, e: *Encoder) !void {
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
        const flags = m.field_get_flags(fld);
        try e.mapHeader(6);
        try e.str("field");
        try e.uint(fu);
        try e.str("name");
        try e.str(cspan(m.field_get_name(fld)));
        try e.str("type");
        try e.str(cspan(tname));
        try e.str("offset");
        try e.int(m.field_get_offset(fld));
        try e.str("flags");
        try e.uint(flags);
        try e.str("is_static");
        try e.boolean((flags & FIELD_ATTRIBUTE_STATIC) != 0);
        if (m.free) |fr| if (tname) |p| fr(@ptrCast(@constCast(p)));
    }
}

fn monoMethods(ctx: *anyopaque, klass_u: u64, e: *Encoder) !void {
    const m = self(ctx);
    const klass: ?*anyopaque = @ptrFromInt(@as(usize, @intCast(klass_u)));

    var list: std.ArrayList(u64) = .empty;
    defer list.deinit(m.allocator);
    var iter: ?*anyopaque = null;
    while (m.class_get_methods(klass, &iter)) |meth| try list.append(m.allocator, @intFromPtr(meth));
    try e.arrayHeader(list.items.len);

    for (list.items) |mu| {
        // No, not the drug...
        const meth: ?*anyopaque = @ptrFromInt(@as(usize, @intCast(mu)));
        const sig = m.method_signature(meth);
        const pc: u64 = if (sig != null) m.signature_get_param_count(sig) else 0;
        const fnm = m.method_full_name(meth, 1);

        try e.mapHeader(4);
        try e.str("method");
        try e.uint(mu);
        try e.str("name");
        try e.str(cspan(m.method_get_name(meth)));
        try e.str("full_name");
        try e.str(cspan(fnm));
        try e.str("param_count");
        try e.uint(pc);
        if (m.free) |fr| if (fnm) |p| fr(@ptrCast(@constCast(p)));
    }
}

fn monoCompile(ctx: *anyopaque, method_u: u64, e: *Encoder) !void {
    const m = self(ctx);
    const meth: ?*anyopaque = @ptrFromInt(@as(usize, @intCast(method_u)));
    const addr = m.compile_method(meth);

    try e.mapHeader(1);
    try e.str("native_addr");
    try e.uint(@intFromPtr(addr));
}

fn monoStaticAddr(ctx: *anyopaque, klass_u: u64, field_u: u64, e: *Encoder) !void {
    const m = self(ctx);
    const klass: ?*anyopaque = @ptrFromInt(@as(usize, @intCast(klass_u)));
    const fld: ?*anyopaque = @ptrFromInt(@as(usize, @intCast(field_u)));
    const vt = m.class_vtable(m.root_domain, klass);

    if (vt == null) return error.NoVtable;
    if (m.runtime_class_init) |ci| ci(vt);

    const base = m.vtable_get_static_field_data(vt);
    const off = m.field_get_offset(fld);
    const addr = @intFromPtr(base) +% @as(u64, @intCast(off));

    try e.mapHeader(1);
    try e.str("address");
    try e.uint(addr);
}

fn monoFindClass(ctx: *anyopaque, image_u: u64, ns: []const u8, name: []const u8, e: *Encoder) !void {
    const m = self(ctx);
    const image: ?*anyopaque = @ptrFromInt(@as(usize, @intCast(image_u)));

    // mono_class_from_name needs NUL-terminated C strings.
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
