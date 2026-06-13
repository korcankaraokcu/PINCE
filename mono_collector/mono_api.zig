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
const resolver = @import("resolver.zig");
const common = @import("common.zig");

const CC = common.CC;
const CStr = common.CStr;
const cspan = common.cspan;
const eql = common.eql;
const typeTag = common.typeTag;
const typeWidth = common.typeWidth;
const emitBits = common.emitBits;
const req = common.req;
const opt = common.opt;

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
const FnTypeType = *const fn (?*anyopaque) callconv(CC) c_int;
const FnStringNew = *const fn (?*anyopaque, CStr) callconv(CC) ?*anyopaque;
const FnParamNames = *const fn (?*anyopaque, [*]?CStr) callconv(CC) void;

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
    signature_get_params: FnIter,
    signature_get_return_type: FnP_P,
    signature_is_instance: ?FnTypeType,
    type_get_type: FnTypeType,
    method_get_param_names: ?FnParamNames,
    string_new: ?FnStringNew,
    string_to_utf8: ?FnP_CStr,
    object_unbox: ?FnP_P,
    compile_method: FnP_P,
    class_vtable: FnVtable,
    vtable_get_static_field_data: FnStaticData,
    runtime_class_init: ?FnClassInit,
    class_from_name: FnFromName,
    class_from_mono_type: ?FnP_P,
    free: ?FnFree,
    runtime_invoke: ?FnInvoke = null,
};

pub fn load(allocator: std.mem.Allocator) !?rt.Backend {
    // Bind the runtime module using the resolver.
    // ELF -> dlopen/dlsym, PE -> export parsing.
    const substr = if (resolver.is_wine) "mono-2.0-bdwgc.dll" else "libmono";
    var path_buf: [256]u8 = undefined;
    var path_len: usize = 0;
    const mod = resolver.open(allocator, "mono_get_root_domain", substr, &path_buf, &path_len) orelse return null;

    const api = try allocator.create(MonoApi);
    api.* = .{
        .allocator = allocator,
        .get_root_domain = try req(FnDomain, mod, "mono_get_root_domain"),
        .thread_attach = try req(FnP_P, mod, "mono_thread_attach"),
        .assembly_foreach = try req(FnForeach, mod, "mono_assembly_foreach"),
        .assembly_get_image = try req(FnP_P, mod, "mono_assembly_get_image"),
        .image_get_name = try req(FnP_CStr, mod, "mono_image_get_name"),
        .image_get_filename = try req(FnP_CStr, mod, "mono_image_get_filename"),
        .image_get_table_info = try req(FnImgTable, mod, "mono_image_get_table_info"),
        .table_info_get_rows = try req(FnRows, mod, "mono_table_info_get_rows"),
        .class_get = try req(FnClassGet, mod, "mono_class_get"),
        .class_get_name = try req(FnP_CStr, mod, "mono_class_get_name"),
        .class_get_namespace = try req(FnP_CStr, mod, "mono_class_get_namespace"),
        .class_get_parent = try req(FnP_P, mod, "mono_class_get_parent"),
        .class_get_fields = try req(FnIter, mod, "mono_class_get_fields"),
        .field_get_name = try req(FnP_CStr, mod, "mono_field_get_name"),
        .field_get_type = try req(FnP_P, mod, "mono_field_get_type"),
        .type_get_name = try req(FnTypeName, mod, "mono_type_get_name"),
        .field_get_offset = try req(FnFieldOffset, mod, "mono_field_get_offset"),
        .field_get_flags = try req(FnFieldFlags, mod, "mono_field_get_flags"),
        .class_get_methods = try req(FnIter, mod, "mono_class_get_methods"),
        .method_get_name = try req(FnP_CStr, mod, "mono_method_get_name"),
        .method_full_name = try req(FnFullName, mod, "mono_method_full_name"),
        .method_signature = try req(FnP_P, mod, "mono_method_signature"),
        .signature_get_param_count = try req(FnParamCount, mod, "mono_signature_get_param_count"),
        .signature_get_params = try req(FnIter, mod, "mono_signature_get_params"),
        .signature_get_return_type = try req(FnP_P, mod, "mono_signature_get_return_type"),
        .signature_is_instance = opt(FnTypeType, mod, "mono_signature_is_instance"),
        .type_get_type = try req(FnTypeType, mod, "mono_type_get_type"),
        .method_get_param_names = opt(FnParamNames, mod, "mono_method_get_param_names"),
        .string_new = opt(FnStringNew, mod, "mono_string_new"),
        .string_to_utf8 = opt(FnP_CStr, mod, "mono_string_to_utf8"),
        .object_unbox = opt(FnP_P, mod, "mono_object_unbox"),
        .compile_method = try req(FnP_P, mod, "mono_compile_method"),
        .class_vtable = try req(FnVtable, mod, "mono_class_vtable"),
        .vtable_get_static_field_data = try req(FnStaticData, mod, "mono_vtable_get_static_field_data"),
        .runtime_class_init = opt(FnClassInit, mod, "mono_runtime_class_init"),
        .class_from_name = try req(FnFromName, mod, "mono_class_from_name"),
        .class_from_mono_type = opt(FnP_P, mod, "mono_class_from_mono_type"),
        .free = opt(FnFree, mod, "mono_free"),
        .runtime_invoke = opt(FnInvoke, mod, "mono_runtime_invoke"),
    };

    api.root_domain = api.get_root_domain();
    _ = api.thread_attach(api.root_domain);

    @memcpy(api.module_buf[0..path_len], path_buf[0..path_len]);
    api.module_len = path_len;

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
        .invokeFn = monoInvoke,
        .signatureFn = monoSignature,
        .classInfoFn = monoClassInfo,
        .typeKlassFn = monoTypeKlass,
        .instanceMarkerFn = monoInstanceMarker,
    };
}

inline fn self(ctx: *anyopaque) *MonoApi {
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

// A Mono object's first word is its MonoVTable*, so that's the marker we scan for.
// No class init needed as the vtable is the same whether the .ctor ran or not.
fn monoInstanceMarker(ctx: *anyopaque, klass_u: u64, e: *Encoder) !void {
    const m = self(ctx);
    const klass: ?*anyopaque = @ptrFromInt(@as(usize, @intCast(klass_u)));
    const vt = m.class_vtable(m.root_domain, klass);
    if (vt == null) return error.NoVtable;

    try e.mapHeader(1);
    try e.str("marker");
    try e.uint(@intFromPtr(vt));
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

fn monoClassInfo(ctx: *anyopaque, klass_u: u64, e: *Encoder) !void {
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

fn monoTypeKlass(ctx: *anyopaque, field_u: u64, e: *Encoder) !void {
    const m = self(ctx);
    const fld: ?*anyopaque = @ptrFromInt(@as(usize, @intCast(field_u)));
    var kptr: ?*anyopaque = null;
    if (m.class_from_mono_type) |cft| {
        if (m.field_get_type(fld)) |t| kptr = cft(t);
    }
    try e.mapHeader(1);
    try e.str("klass");
    try e.uint(@intFromPtr(kptr));
}

inline fn encodeTypeRef(m: *MonoApi, e: *Encoder, t: ?*anyopaque) !void {
    const tname = m.type_get_name(t);
    try e.mapHeader(2);
    try e.str("tag");
    try e.str(typeTag(m.type_get_type(t)));
    try e.str("name");
    try e.str(cspan(tname));
    if (m.free) |fr| if (tname) |p| fr(@ptrCast(@constCast(p)));
}

fn monoSignature(ctx: *anyopaque, method_u: u64, e: *Encoder) !void {
    const m = self(ctx);
    const meth: ?*anyopaque = @ptrFromInt(@as(usize, @intCast(method_u)));
    const sig = m.method_signature(meth);
    if (sig == null) return error.NoSignature;
    const pc = m.signature_get_param_count(sig);

    var name_buf: [64]?CStr = undefined;
    var have_names = false;
    if (m.method_get_param_names) |gpn| {
        if (pc <= name_buf.len) {
            @memset(name_buf[0..pc], null);
            gpn(meth, &name_buf);
            have_names = true;
        }
    }

    const is_instance = if (m.signature_is_instance) |f| f(sig) != 0 else true;
    try e.mapHeader(3);
    try e.str("static");
    try e.boolean(!is_instance);
    try e.str("ret");
    try encodeTypeRef(m, e, m.signature_get_return_type(sig));
    try e.str("params");
    try e.arrayHeader(pc);
    var iter: ?*anyopaque = null;
    var idx: usize = 0;
    while (m.signature_get_params(sig, &iter)) |ptype| : (idx += 1) {
        const tname = m.type_get_name(ptype);
        try e.mapHeader(3);
        try e.str("name");
        if (have_names and idx < pc and name_buf[idx] != null) {
            try e.str(cspan(name_buf[idx]));
        } else {
            var nb: [16]u8 = undefined;
            try e.str(std.fmt.bufPrint(&nb, "arg{d}", .{idx}) catch "arg");
        }
        try e.str("tag");
        try e.str(typeTag(m.type_get_type(ptype)));
        try e.str("type");
        try e.str(cspan(tname));
        if (m.free) |fr| if (tname) |p| fr(@ptrCast(@constCast(p)));
    }
}

fn monoInvoke(ctx: *anyopaque, method_u: u64, obj_u: u64, args: []const rt.Arg, e: *Encoder) !void {
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
            argv[i] = sn(m.root_domain, @ptrCast(&sbuf)); // reference type: object pointer
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
        const sig = m.method_signature(meth);
        const rtype = if (sig != null) m.signature_get_return_type(sig) else null;
        const renum: c_int = if (rtype != null) m.type_get_type(rtype) else 0x01;
        const rtag = typeTag(renum);
        if (renum == 0x01 or ret == null) { // void / null
            try e.nil();
        } else if (eql(rtag, "str") and m.string_to_utf8 != null) {
            const c = m.string_to_utf8.?(ret);
            try e.mapHeader(2);
            try e.str("tag");
            try e.str("str");
            try e.str("val");
            try e.str(cspan(c));
            if (m.free) |fr| if (c) |p| fr(@ptrCast(@constCast(p)));
        } else if (eql(rtag, "object") or eql(rtag, "str")) {
            try emitBits(e, "object", @intFromPtr(ret)); // object handle / unconvertible string
        } else { // value type: unbox and read its raw bytes
            const ub = m.object_unbox orelse return error.Unsupported;
            const vp = ub(ret);
            var bits: u64 = 0;
            if (vp) |p| {
                const w = typeWidth(rtag);
                const src: [*]const u8 = @ptrCast(p);
                @memcpy(std.mem.asBytes(&bits)[0..w], src[0..w]);
            }
            try emitBits(e, rtag, bits);
        }
    }
    try e.str("exception");
    try e.uint(@intFromPtr(exc));
}
