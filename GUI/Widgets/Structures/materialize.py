from libpince import debugcore, typedefs
from GUI.Session.session import StructureManager

_MAX_DEPTH = 16
_STRUCT_VT = typedefs.StructValueType().serialize()


def _rel_off(offset: int) -> str:
    return f"+{hex(offset)}" if offset >= 0 else f"-{hex(-offset)}"


def _read_string_length(base_addr: int, structure: typedefs.Structure) -> int | None:
    if structure.name != "System.String":
        return None
    for m in structure.members:
        if m.name == "length" and m.value_type is not None:
            raw_len = debugcore.read_memory(base_addr + m.offset, m.value_type)
            if raw_len is not None and 0 <= raw_len <= 4096:
                return raw_len
            break
    return None


def structure_to_records(
    structure: typedefs.Structure, base_addr: int = 0, _depth: int = 0, _parents: tuple[str, ...] = ()
) -> list[tuple[str, str | tuple[str | int, list[int]], tuple[int, ...], list]]:
    if _depth > _MAX_DEPTH or structure.name in _parents:
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
            if member.name in length_overrides and isinstance(member.value_type, typedefs.StringValueType):
                vt = (vt[0], length_overrides[member.name], vt[2], vt[3], vt[4])
            records.append((member.name, _rel_off(member.offset), vt, []))
        else:
            child = StructureManager.get(member.struct_ref)
            off = _rel_off(member.offset)
            if child is None:
                group_expr = typedefs.PointerChainRequest(off, [0]).serialize() if member.is_pointer else off
                records.append((member.name, group_expr, _STRUCT_VT, []))
                continue
            child_base = base_addr + member.offset
            if member.is_pointer and base_addr > 0:
                pointer_bits = 32 if debugcore.effective_arch == typedefs.INFERIOR_ARCH.ARCH_32 else 64
                ptr_val = debugcore.read_memory(base_addr + member.offset, typedefs.IntegerValueType(pointer_bits))
                if ptr_val is not None:
                    child_base = ptr_val
            children = structure_to_records(child, child_base, _depth + 1, _parents + (structure.name,))
            group_expr = typedefs.PointerChainRequest(off, [0]).serialize() if member.is_pointer else off
            records.append((member.name, group_expr, _STRUCT_VT, children))
    return records


def structure_to_group_record(structure: typedefs.Structure, base_expr: str) -> tuple[str, str, tuple[int, ...], list]:
    address = debugcore.examine_expression(base_expr).address if base_expr else None
    base_addr = int(address, 0) if address else 0
    members = structure_to_records(structure, base_addr)
    return structure.name, base_expr, _STRUCT_VT, members
