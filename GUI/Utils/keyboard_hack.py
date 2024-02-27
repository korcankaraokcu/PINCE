from keyboard import key_to_scan_codes
import re as _re

# copied from keyboard.__init__.py
_is_str = lambda x: isinstance(x, str)
_is_number = lambda x: isinstance(x, int)
_is_list = lambda x: isinstance(x, (list, tuple))

def parse_hotkey(hotkey):
    ## function to replace keyboard.parse_hotkey() with fix for literal '+' in hotkey strings
    """
    Parses a user-provided hotkey into nested tuples representing the
    parsed structure, with the bottom values being lists of scan codes.
    Also accepts raw scan codes, which are then wrapped in the required
    number of nestings.

    Example:

        parse_hotkey("alt+shift+a, alt+b, c")
        #    Keys:    ^~^ ^~~~^ ^  ^~^ ^  ^
        #    Steps:   ^~~~~~~~~~^  ^~~~^  ^

        # ((alt_codes, shift_codes, a_codes), (alt_codes, b_codes), (c_codes,))
    """
    if _is_number(hotkey) or len(hotkey) == 1:
        scan_codes = key_to_scan_codes(hotkey)
        step = (scan_codes,)
        steps = (step,)
        return steps
    elif _is_list(hotkey):
        if not any(map(_is_list, hotkey)):
            step = tuple(key_to_scan_codes(k) for k in hotkey)
            steps = (step,)
            return steps
        return hotkey

    steps = []
    # since we dont have spaces in hotkey strings, we can ignore whitespace in the regex
    for step in _re.split(r'(?<!keypad ),(?!$|,)', hotkey):
        keys = _re.split(r'(?<=\+)\+(?=(?:(?:\+\+\w))|[\w ])|(?:(?<!keypad )(?<= |[\w,/*\-÷])\+)|\+(?=\+$)', step)
        steps.append(tuple(key_to_scan_codes(key) for key in keys))
    return tuple(steps)
