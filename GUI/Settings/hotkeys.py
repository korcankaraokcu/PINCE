from keyboard import add_hotkey, remove_hotkey
from typing import Callable
from tr.tr import TranslationConstants as tr


class Hotkey:
    def __init__(self, name="", desc="", default="", func=None, custom="", handle=None) -> None:
        self.name = name
        self.desc = desc
        self.default = default
        self.func = func
        self.custom = custom
        if default == "" or func is None:
            self.handle = handle
        else:
            self.handle = add_hotkey(default, func)

    def change_key(self, custom: str) -> None:
        if self.handle is not None:
            remove_hotkey(self.handle)
            self.handle = None
        self.custom = custom
        if custom == "":
            return
        self.handle = add_hotkey(custom.lower(), self.func)

    def change_func(self, func: Callable) -> None:
        self.func = func
        if self.handle is not None:
            remove_hotkey(self.handle)
        if self.custom != "":
            self.handle = add_hotkey(self.custom, func)
        elif self.default != "":
            self.handle = add_hotkey(self.default, func)

    def get_active_key(self) -> str:
        if self.custom == "":
            return self.default
        return self.custom


class Hotkeys:
    def __init__(self) -> None:
        self.pause_hotkey = Hotkey("pause_hotkey", tr.PAUSE_HOTKEY, "F1")
        self.break_hotkey = Hotkey("break_hotkey", tr.BREAK_HOTKEY, "F2")
        self.continue_hotkey = Hotkey("continue_hotkey", tr.CONTINUE_HOTKEY, "F3")
        self.toggle_attach_hotkey = Hotkey("toggle_attach_hotkey", tr.TOGGLE_ATTACH_HOTKEY, "Shift+F10")
        self.exact_scan_hotkey = Hotkey("exact_scan_hotkey", tr.EXACT_SCAN_HOTKEY, "")
        self.increased_scan_hotkey = Hotkey("increased_scan_hotkey", tr.INC_SCAN_HOTKEY, "")
        self.decreased_scan_hotkey = Hotkey("decreased_scan_hotkey", tr.DEC_SCAN_HOTKEY, "")
        self.changed_scan_hotkey = Hotkey("changed_scan_hotkey", tr.CHANGED_SCAN_HOTKEY, "")
        self.unchanged_scan_hotkey = Hotkey("unchanged_scan_hotkey", tr.UNCHANGED_SCAN_HOTKEY, "")

    def get_hotkeys(self) -> list[Hotkey]:
        hotkey_list = []
        for _, value in vars(self).items():
            if isinstance(value, Hotkey):
                hotkey_list.append(value)
        return hotkey_list
