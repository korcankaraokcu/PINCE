from libpince import typedefs
from GUI.Session.session import StructureManager

_MAX_DEPTH = 16


def _struct_vt() -> tuple[int, int, bool, int, int]:
    return typedefs.ValueType(typedefs.VALUE_INDEX.STRUCT).serialize()


def _rel_off(offset: int) -> str:
    return f"+{hex(offset)}" if offset >= 0 else f"-{hex(-offset)}"


def structure_to_records(
    structure: typedefs.Structure, _depth: int = 0
) -> list[tuple[str, str | tuple[str | int, list[int]], tuple[int, int, bool, int, int], list]]:
    if _depth > _MAX_DEPTH:
        return []
    records = []
    for member in structure.members:
        if member.value_type is not None:
            records.append((member.name, _rel_off(member.offset), member.value_type.serialize(), []))
        else:
            child = StructureManager.get(member.struct_ref)
            if child is None:
                continue
            off = _rel_off(member.offset)
            group_expr = typedefs.PointerChainRequest(off, [0]).serialize() if member.is_pointer else off
            children = structure_to_records(child, _depth + 1)
            records.append((member.name, group_expr, _struct_vt(), children))
    return records


def structure_to_group_record(
    structure: typedefs.Structure, base_addr: int
) -> tuple[str, str, tuple[int, int, bool, int, int], list]:
    members = structure_to_records(structure)
    return structure.name, hex(base_addr), _struct_vt(), members
