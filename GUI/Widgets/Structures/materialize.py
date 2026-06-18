from libpince import debugcore, typedefs
from GUI.Session.session import StructureManager

_MAX_DEPTH = 16


def _struct_vt() -> tuple[int, int, bool, int, int]:
    return typedefs.ValueType(typedefs.VALUE_INDEX.STRUCT).serialize()


def _rel_off(offset: int) -> str:
    return f"+{hex(offset)}" if offset >= 0 else f"-{hex(-offset)}"


def _read_string_length(base_addr: int, structure: typedefs.Structure) -> int | None:
    if structure.name != "System.String":
        return None
    for m in structure.members:
        if m.name == "length" and m.value_type is not None:
            raw_len = debugcore.read_memory(
                base_addr + m.offset,
                m.value_type.value_index,
                m.value_type.length,
                m.value_type.zero_terminate,
                m.value_type.value_repr,
                m.value_type.endian,
            )
            if raw_len is not None and 0 <= raw_len <= 4096:
                return raw_len
            break
    return None


def structure_to_records(
    structure: typedefs.Structure, _depth: int = 0, base_addr: int = 0
) -> list[tuple[str, str | tuple[str | int, list[int]], tuple[int, int, bool, int, int], list]]:
    if _depth > _MAX_DEPTH:
        return []
    length_overrides = {}
    if structure.name == "System.String" and base_addr > 0:
        str_len = _read_string_length(base_addr, structure)
        if str_len is not None:
            length_overrides["chars"] = str_len
    records = []
    for member in structure.members:
        if member.value_type is not None:
            vt = member.value_type.serialize()
            if member.name in length_overrides:
                vt = (vt[0], length_overrides[member.name], vt[2], vt[3], vt[4])
            records.append((member.name, _rel_off(member.offset), vt, []))
        else:
            child = StructureManager.get(member.struct_ref)
            if child is None:
                continue
            off = _rel_off(member.offset)
            child_base = base_addr + member.offset
            if member.is_pointer and base_addr > 0:
                ptr_index = (
                    typedefs.VALUE_INDEX.INT32
                    if debugcore.inferior_arch == typedefs.INFERIOR_ARCH.ARCH_32
                    else typedefs.VALUE_INDEX.INT64
                )
                ptr_val = debugcore.read_memory(base_addr + member.offset, ptr_index)
                if ptr_val is not None:
                    child_base = ptr_val
            children = structure_to_records(child, _depth + 1, child_base)
            group_expr = typedefs.PointerChainRequest(off, [0]).serialize() if member.is_pointer else off
            records.append((member.name, group_expr, _struct_vt(), children))
    return records


def structure_to_group_record(
    structure: typedefs.Structure, base_addr: int
) -> tuple[str, str, tuple[int, int, bool, int, int], list]:
    members = structure_to_records(structure, 0, base_addr)
    return structure.name, hex(base_addr), _struct_vt(), members
