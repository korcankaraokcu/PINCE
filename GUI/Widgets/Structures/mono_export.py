from libpince import debugcore, typedefs, monocore
from GUI.Session.session import StructureManager

_TAG_TO_VALUE_TYPE = {
    "bool": lambda: typedefs.IntegerValueType(8),
    "i1": lambda: typedefs.IntegerValueType(8, value_repr=typedefs.VALUE_REPR.SIGNED),
    "u1": lambda: typedefs.IntegerValueType(8),
    "i2": lambda: typedefs.IntegerValueType(16, value_repr=typedefs.VALUE_REPR.SIGNED),
    "u2": lambda: typedefs.IntegerValueType(16),
    "char": lambda: typedefs.IntegerValueType(16),
    "i4": lambda: typedefs.IntegerValueType(32, value_repr=typedefs.VALUE_REPR.SIGNED),
    "u4": lambda: typedefs.IntegerValueType(32),
    "i8": lambda: typedefs.IntegerValueType(64, value_repr=typedefs.VALUE_REPR.SIGNED),
    "u8": lambda: typedefs.IntegerValueType(64),
    "r4": lambda: typedefs.FloatValueType(32),
    "r8": lambda: typedefs.FloatValueType(64),
}
_MAX_INHERIT_DEPTH = 32


def _is_instance_field(fld: dict) -> bool:
    return not fld["is_static"] and not (fld["flags"] & 0x40)


def _ensure_managed_string_structure() -> str:
    if StructureManager.get("System.String") is None:
        pointer_bits = 32 if debugcore.effective_arch == typedefs.INFERIOR_ARCH.ARCH_32 else 64
        pointer_size = pointer_bits // 8
        members = [
            typedefs.StructureMember(
                "vtable_ptr",
                0,
                typedefs.IntegerValueType(pointer_bits, value_repr=typedefs.VALUE_REPR.HEX),
            ),
            typedefs.StructureMember("sync", pointer_size, typedefs.IntegerValueType(pointer_bits)),
            typedefs.StructureMember("length", pointer_size * 2, typedefs.IntegerValueType()),
            # Small preview; address-table export calculates the real length.
            typedefs.StructureMember(
                "chars",
                pointer_size * 2 + 4,
                typedefs.StringValueType("utf-16", length=32, zero_terminate=False),
            ),
        ]
        StructureManager.add(typedefs.Structure("System.String", members))
    return "System.String"


def member_from_field(fld: dict, pointer_bits: int = 64) -> "typedefs.StructureMember | None":
    if not _is_instance_field(fld):
        return None
    tag = fld.get("tag")
    if tag in _TAG_TO_VALUE_TYPE:
        return typedefs.StructureMember(fld["name"], fld["offset"], _TAG_TO_VALUE_TYPE[tag]())
    if tag == "str":
        return typedefs.StructureMember(fld["name"], fld["offset"], struct_ref=_ensure_managed_string_structure(), is_pointer=True)
    if tag == "object":
        return typedefs.StructureMember(
            fld["name"],
            fld["offset"],
            typedefs.IntegerValueType(pointer_bits, value_repr=typedefs.VALUE_REPR.HEX),
        )
    return typedefs.StructureMember(fld["name"], fld["offset"], typedefs.ByteArrayValueType(0))


def _inherited_instance_fields(client: monocore.MonoClient, class_data: dict) -> list[dict]:
    fields = []
    ptr = class_data.get("parent", 0)
    depth = 0
    while ptr != 0 and depth < _MAX_INHERIT_DEPTH:
        try:
            info = client.class_info(ptr)
        except monocore.MonoError:
            break
        fields.extend(client.fields(ptr))
        ptr = info.get("parent", 0)
        depth += 1
    return fields


def _class_name(class_data: dict) -> str:
    name = class_data.get("name", "?")
    ns = class_data.get("namespace")
    return f"{ns}.{name}" if ns else name


def _unique_name(name: str) -> str:
    counter = 1
    while StructureManager.get(f"{name}_{counter}") is not None:
        counter += 1
    return f"{name}_{counter}"


def _leaf_member(fld: dict, instance: list[dict], i: int, pointer_bits: int) -> typedefs.StructureMember:
    m = member_from_field(fld, pointer_bits)
    if isinstance(m.value_type, typedefs.ByteArrayValueType) and m.value_type.length <= 0:
        nxt = instance[i + 1]["offset"] if i + 1 < len(instance) else fld["offset"] + 8
        m.value_type.length = max(1, nxt - fld["offset"])
    return m


def _safe_type_klass(client: monocore.MonoClient, fld: dict) -> int:
    try:
        return client.type_klass(fld["field"])
    except monocore.MonoError:
        return 0


def _object_ref_name(
    client: monocore.MonoClient,
    fld: dict,
    seen: set[str],
    pointer_bits: int,
    include_inherited: bool,
) -> "str | None":
    ref_klass = _safe_type_klass(client, fld)
    if not ref_klass:
        return None
    try:
        ref_info = client.class_info(ref_klass)
        return _build_structure(client, {**ref_info, "klass": ref_klass}, seen, pointer_bits, include_inherited)
    except monocore.MonoError:
        return None


def _inline_value_type(client: monocore.MonoClient, fld: dict) -> "str | None":
    vt_klass = _safe_type_klass(client, fld)
    if vt_klass == 0:
        return None
    try:
        sub_fields = client.struct_fields(vt_klass)
        if sub_fields is None or any(sf["tag"] not in _TAG_TO_VALUE_TYPE for sf in sub_fields):
            return None
        vt_name = _class_name(client.class_info(vt_klass))
        if StructureManager.get(vt_name) is None:
            members = [
                typedefs.StructureMember(
                    sf["name"],
                    sf["offset"],
                    _TAG_TO_VALUE_TYPE[sf["tag"]](),
                )
                for sf in sub_fields
            ]
            StructureManager.add(typedefs.Structure(vt_name, members))
        return vt_name
    except monocore.MonoError:
        return None


def _build_structure(
    client: monocore.MonoClient,
    class_data: dict,
    seen: set[str],
    pointer_bits: int,
    include_inherited: bool = True,
    force_new: bool = False,
) -> str:
    name = _class_name(class_data)
    if name in seen:
        return name
    if StructureManager.get(name) is not None:
        if not force_new:
            return name
        name = _unique_name(name)
    fields = list(client.fields(class_data["klass"]))  # call can fail so do it before registering anything
    seen.add(name)
    StructureManager.add(typedefs.Structure(name, []))
    if include_inherited:
        fields += _inherited_instance_fields(client, class_data)
    instance = sorted((f for f in fields if _is_instance_field(f)), key=lambda f: f["offset"])
    members = []
    for i, fld in enumerate(instance):
        tag = fld.get("tag")
        member = None
        if tag == "object":
            ref_name = _object_ref_name(client, fld, seen, pointer_bits, include_inherited)
            if ref_name is not None:
                member = typedefs.StructureMember(fld["name"], fld["offset"], struct_ref=ref_name, is_pointer=True)
        elif tag == "struct":
            vt_name = _inline_value_type(client, fld)
            if vt_name is not None:
                member = typedefs.StructureMember(fld["name"], fld["offset"], struct_ref=vt_name, is_pointer=False)
        members.append(member if member is not None else _leaf_member(fld, instance, i, pointer_bits))
    StructureManager.update(typedefs.Structure(name, members))
    return name


def structure_from_class(client: monocore.MonoClient, class_data: dict, include_inherited: bool = True, force_new: bool = True) -> typedefs.Structure:
    pointer_bits = 32 if debugcore.effective_arch == typedefs.INFERIOR_ARCH.ARCH_32 else 64
    name = _build_structure(client, class_data, set(), pointer_bits, include_inherited, force_new)
    return StructureManager.get(name)
