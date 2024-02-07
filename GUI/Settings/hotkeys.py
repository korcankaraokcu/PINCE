from keyboard import add_hotkey, remove_hotkey

from tr.tr import TranslationConstants as tr


class Hotkeys:
    class Hotkey:
        def __init__(self, name="", desc="", default="", func=None, custom="", handle=None):
            self.name = name
            self.desc = desc
            self.default = default
            self.func = func
            self.custom = custom
            if default == "" or func is None:
                self.handle = handle
            else:
                self.handle = add_hotkey(default, func)

        def change_key(self, custom):
            if self.handle is not None:
                remove_hotkey(self.handle)
                self.handle = None
            self.custom = custom
            if custom == '':
                return
            self.handle = add_hotkey(custom.lower(), self.func)

        def change_func(self, func):
            self.func = func
            if self.handle is not None:
                remove_hotkey(self.handle)
            if self.custom != "":
                self.handle = add_hotkey(self.custom, func)
            elif self.default != "":
                self.handle = add_hotkey(self.default, func)

        def get_active_key(self):
            if self.custom == "":
                return self.default
            return self.custom

    pause_hotkey = Hotkey("pause_hotkey", tr.PAUSE_HOTKEY, "F1")
    break_hotkey = Hotkey("break_hotkey", tr.BREAK_HOTKEY, "F2")
    continue_hotkey = Hotkey("continue_hotkey", tr.CONTINUE_HOTKEY, "F3")
    toggle_attach_hotkey = Hotkey("toggle_attach_hotkey", tr.TOGGLE_ATTACH_HOTKEY, "Shift+F10")
    exact_scan_hotkey = Hotkey("exact_scan_hotkey", tr.EXACT_SCAN_HOTKEY, "")
    increased_scan_hotkey = Hotkey("increased_scan_hotkey", tr.INC_SCAN_HOTKEY, "")
    decreased_scan_hotkey = Hotkey("decreased_scan_hotkey", tr.DEC_SCAN_HOTKEY, "")
    changed_scan_hotkey = Hotkey("changed_scan_hotkey", tr.CHANGED_SCAN_HOTKEY, "")
    unchanged_scan_hotkey = Hotkey("unchanged_scan_hotkey", tr.UNCHANGED_SCAN_HOTKEY, "")

    @staticmethod
    def get_hotkeys():
        return Hotkeys.pause_hotkey, Hotkeys.break_hotkey, Hotkeys.continue_hotkey, Hotkeys.toggle_attach_hotkey, \
            Hotkeys.exact_scan_hotkey, Hotkeys.increased_scan_hotkey, Hotkeys.decreased_scan_hotkey, \
            Hotkeys.changed_scan_hotkey, Hotkeys.unchanged_scan_hotkey
