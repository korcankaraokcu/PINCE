
def migrate_version(content: any) -> dict[str, any]:
    if not hasattr(content, "version") and type(content) == list:
        return legacy_to_v1(content)

    return content

def is_valid_session_data(content: dict[str, any]) -> bool:
    keys = ["version", "notes", "bookmarks", "address_tree"]
    for key in keys:
        if key not in content:
            return False
    
    return content

def legacy_to_v1(content:list) -> dict[str, any]:
    print("Migrating legacy session data to version 1")
    return {
        "version": 1,
        "notes": "",
        "bookmarks": {},
        "address_tree": content
    } 