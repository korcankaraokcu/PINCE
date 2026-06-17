from libpince import debugcore, typedefs, monocore

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


def member_from_field(
    fld: dict, pointer_index: typedefs.VALUE_INDEX = typedefs.VALUE_INDEX.INT64
) -> "typedefs.StructureMember | None":
    if fld["is_static"] or (fld["flags"] & 0x40):
        return None
    tag = fld.get("tag")
    if tag in _TAG_TO_VALUE:
        index, repr_ = _TAG_TO_VALUE[tag]
        return typedefs.StructureMember(fld["name"], fld["offset"], typedefs.ValueType(index, value_repr=repr_))
    if tag in ("object", "str"):
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
        for fld in client.fields(ptr):
            fields.append(fld)
        ptr = info.get("parent", 0)
        depth += 1
    return fields


def structure_from_class(
    client: monocore.MonoClient, class_data: dict, include_inherited: bool = True
) -> typedefs.Structure:
    pointer_index = (
        typedefs.VALUE_INDEX.INT32
        if debugcore.inferior_arch == typedefs.INFERIOR_ARCH.ARCH_32
        else typedefs.VALUE_INDEX.INT64
    )
    name = class_data.get("name", "?")
    if class_data.get("namespace"):
        name = f"{class_data['namespace']}.{name}"
    fields = list(client.fields(class_data["klass"]))
    if include_inherited:
        fields += _inherited_instance_fields(client, class_data)
    instance = [f for f in fields if not f["is_static"] and not (f["flags"] & 0x40)]
    instance.sort(key=lambda f: f["offset"])
    members = []
    for i, fld in enumerate(instance):
        m = member_from_field(fld, pointer_index)
        if m.value_type.value_index == typedefs.VALUE_INDEX.AOB and m.value_type.length <= 0:
            nxt = instance[i + 1]["offset"] if i + 1 < len(instance) else fld["offset"] + 8
            m.value_type.length = max(1, nxt - fld["offset"])
        members.append(m)
    size = (instance[-1]["offset"] + 8) if instance else 0
    return typedefs.Structure(name, members, size)
