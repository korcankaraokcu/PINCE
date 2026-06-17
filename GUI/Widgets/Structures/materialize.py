from libpince import typedefs
from GUI.Session.session import StructureManager

_MAX_DEPTH = 16


def _struct_vt() -> tuple:
    """Serialized ValueType for a group/header row: shows no value and stays out of the type pickers."""
    return typedefs.ValueType(typedefs.VALUE_INDEX.STRUCT).serialize()


def _leaf_expr(base_addr: int, path: list) -> "str | tuple":
    """path = [(offset, is_pointer), ...] from the structure root down to the value leaf.
    Returns a plain hex string when no pointer hop is on the path, else a serialized PointerChainRequest.
    Mirrors read_pointer_chain: the base is always dereferenced, every offset except the last is dereferenced."""
    segments = [0]
    for offset, is_pointer in path:
        segments[-1] += offset
        if is_pointer:
            segments.append(0)
    if len(segments) == 1:
        return hex(base_addr + segments[0])
    return typedefs.PointerChainRequest(hex(base_addr + segments[0]), segments[1:]).serialize()


def structure_to_records(
    structure: typedefs.Structure, base_addr: int, _path: list | None = None, _depth: int = 0
) -> list:
    """Flatten 'structure' applied at 'base_addr' into address-table records. Nested members become group rows."""
    if _path is None:
        _path = []
    if _depth > _MAX_DEPTH:
        return []
    records = []
    for member in structure.members:
        if member.value_type is not None:
            expr = _leaf_expr(base_addr, _path + [(member.offset, False)])
            records.append((member.name, expr, member.value_type.serialize(), []))
        else:
            child = StructureManager.get(member.struct_ref)
            if child is None:
                continue
            child_path = _path + [(member.offset, member.is_pointer)]
            children = structure_to_records(child, base_addr, child_path, _depth + 1)
            records.append((member.name, _leaf_expr(base_addr, child_path), _struct_vt(), children))
    return records


def structure_to_group_record(structure: typedefs.Structure, base_addr: int) -> tuple:
    """Wrap the whole structure as a single collapsible group row whose children are its members,
    so adding to the address table inserts one entry instead of scattering members at the root."""
    members = structure_to_records(structure, base_addr)
    return structure.name, _leaf_expr(base_addr, []), _struct_vt(), members
