from libpince import debugcore, typedefs, monocore
from GUI.Session.session import StructureManager

_TAG_TO_VALUE = {
    "bool": (typedefs.VALUE_INDEX.INT8, typedefs.VALUE_REPR.UNSIGNED),
    "i1": (typedefs.VALUE_INDEX.INT8, typedefs.VALUE_REPR.SIGNED),
    "u1": (typedefs.VALUE_INDEX.INT8, typedefs.VALUE_REPR.UNSIGNED),
    "i2": (typedefs.VALUE_INDEX.INT16, typedefs.VALUE_REPR.SIGNED),
    "u2": (typedefs.VALUE_INDEX.INT16, typedefs.VALUE_REPR.UNSIGNED),
    "char": (typedefs.VALUE_INDEX.INT16, typedefs.VALUE_REPR.UNSIGNED),
    "i4": (typedefs.VALUE_INDEX.INT32, typedefs.VALUE_REPR.SIGNED),
    "u4": (typedefs.VALUE_INDEX.INT32, typedefs.VALUE_REPR.UNSIGNED),
    "i8": (typedefs.VALUE_INDEX.INT64, typedefs.VALUE_REPR.SIGNED),
    "u8": (typedefs.VALUE_INDEX.INT64, typedefs.VALUE_REPR.UNSIGNED),
    "r4": (typedefs.VALUE_INDEX.FLOAT32, typedefs.VALUE_REPR.UNSIGNED),
    "r8": (typedefs.VALUE_INDEX.FLOAT64, typedefs.VALUE_REPR.UNSIGNED),
}
_MAX_INHERIT_DEPTH = 32


def _is_instance_field(fld: dict) -> bool:
    return not fld["is_static"] and not (fld["flags"] & 0x40)


def _ensure_managed_string_structure() -> str:
    if StructureManager.get("System.String") is None:
        is_32 = debugcore.inferior_arch == typedefs.INFERIOR_ARCH.ARCH_32
        ptr_type = typedefs.VALUE_INDEX.INT32 if is_32 else typedefs.VALUE_INDEX.INT64
        if is_32:
            members = [
                typedefs.StructureMember(
                    "vtable_ptr", 0x00, typedefs.ValueType(ptr_type, value_repr=typedefs.VALUE_REPR.HEX)
                ),
                typedefs.StructureMember("sync", 0x04, typedefs.ValueType(ptr_type)),
                typedefs.StructureMember("length", 0x08, typedefs.ValueType(typedefs.VALUE_INDEX.INT32)),
                typedefs.StructureMember(
                    "chars",
                    0x0C,
                    # We'll use a default of length 32 (about 16 UTF16 characters) for a small preview until we export
                    # this struct to address table where we calculate the proper length and modify it.
                    typedefs.ValueType(typedefs.VALUE_INDEX.STRING_UTF16, length=32, zero_terminate=False),
                ),
            ]
        else:
            members = [
                typedefs.StructureMember(
                    "vtable_ptr", 0x00, typedefs.ValueType(ptr_type, value_repr=typedefs.VALUE_REPR.HEX)
                ),
                typedefs.StructureMember("sync", 0x08, typedefs.ValueType(ptr_type)),
                typedefs.StructureMember("length", 0x10, typedefs.ValueType(typedefs.VALUE_INDEX.INT32)),
                typedefs.StructureMember(
                    "chars",
                    0x14,
                    # Same length default as 32 bits case above for the same stated reasons.
                    typedefs.ValueType(typedefs.VALUE_INDEX.STRING_UTF16, length=32, zero_terminate=False),
                ),
            ]
        StructureManager.add(typedefs.Structure("System.String", members, 0))
    return "System.String"


def member_from_field(
    fld: dict, pointer_index: typedefs.VALUE_INDEX = typedefs.VALUE_INDEX.INT64
) -> "typedefs.StructureMember | None":
    if not _is_instance_field(fld):
        return None
    tag = fld.get("tag")
    if tag in _TAG_TO_VALUE:
        index, repr_ = _TAG_TO_VALUE[tag]
        return typedefs.StructureMember(fld["name"], fld["offset"], typedefs.ValueType(index, value_repr=repr_))
    if tag == "str":
        return typedefs.StructureMember(
            fld["name"], fld["offset"], struct_ref=_ensure_managed_string_structure(), is_pointer=True
        )
    if tag == "object":
        return typedefs.StructureMember(
            fld["name"], fld["offset"], typedefs.ValueType(pointer_index, value_repr=typedefs.VALUE_REPR.HEX)
        )
    return typedefs.StructureMember(fld["name"], fld["offset"], typedefs.ValueType(typedefs.VALUE_INDEX.AOB, length=0))


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


def _leaf_member(
    fld: dict, instance: list[dict], i: int, pointer_index: typedefs.VALUE_INDEX
) -> typedefs.StructureMember:
    m = member_from_field(fld, pointer_index)
    if m.value_type is not None and m.value_type.value_index == typedefs.VALUE_INDEX.AOB and m.value_type.length <= 0:
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
    pointer_index: typedefs.VALUE_INDEX,
    include_inherited: bool,
) -> "str | None":
    ref_klass = _safe_type_klass(client, fld)
    if not ref_klass:
        return None
    try:
        ref_info = client.class_info(ref_klass)
        return _build_structure(client, {**ref_info, "klass": ref_klass}, seen, pointer_index, include_inherited)
    except monocore.MonoError:
        return None


def _inline_value_type(client: monocore.MonoClient, fld: dict) -> "str | None":
    vt_klass = _safe_type_klass(client, fld)
    if vt_klass == 0:
        return None
    try:
        sub_fields = client.struct_fields(vt_klass)
        if sub_fields is None or any(sf["tag"] not in _TAG_TO_VALUE for sf in sub_fields):
            return None
        vt_name = _class_name(client.class_info(vt_klass))
        if StructureManager.get(vt_name) is None:
            members = [
                typedefs.StructureMember(
                    sf["name"],
                    sf["offset"],
                    typedefs.ValueType(_TAG_TO_VALUE[sf["tag"]][0], value_repr=_TAG_TO_VALUE[sf["tag"]][1]),
                )
                for sf in sub_fields
            ]
            size = max((sf["offset"] + sf["width"] for sf in sub_fields), default=0)
            StructureManager.add(typedefs.Structure(vt_name, members, size))
        return vt_name
    except monocore.MonoError:
        return None


def _build_structure(
    client: monocore.MonoClient,
    class_data: dict,
    seen: set[str],
    pointer_index: typedefs.VALUE_INDEX,
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
    StructureManager.add(typedefs.Structure(name, [], 0))
    if include_inherited:
        fields += _inherited_instance_fields(client, class_data)
    instance = sorted((f for f in fields if _is_instance_field(f)), key=lambda f: f["offset"])
    members = []
    for i, fld in enumerate(instance):
        tag = fld.get("tag")
        member = None
        if tag == "object":
            ref_name = _object_ref_name(client, fld, seen, pointer_index, include_inherited)
            if ref_name is not None:
                member = typedefs.StructureMember(fld["name"], fld["offset"], struct_ref=ref_name, is_pointer=True)
        elif tag == "struct":
            vt_name = _inline_value_type(client, fld)
            if vt_name is not None:
                member = typedefs.StructureMember(fld["name"], fld["offset"], struct_ref=vt_name, is_pointer=False)
        members.append(member if member is not None else _leaf_member(fld, instance, i, pointer_index))
    size = (instance[-1]["offset"] + 8) if instance else 0
    StructureManager.update(typedefs.Structure(name, members, size))
    return name


def structure_from_class(
    client: monocore.MonoClient, class_data: dict, include_inherited: bool = True, force_new: bool = True
) -> typedefs.Structure:
    pointer_index = (
        typedefs.VALUE_INDEX.INT32
        if debugcore.inferior_arch == typedefs.INFERIOR_ARCH.ARCH_32
        else typedefs.VALUE_INDEX.INT64
    )
    name = _build_structure(client, class_data, set(), pointer_index, include_inherited, force_new)
    return StructureManager.get(name)
