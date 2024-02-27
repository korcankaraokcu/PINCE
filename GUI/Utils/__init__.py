import keyboard
from . import keyboard_hack

# replace keyboard.parse_hotkey() with fix for literal '+' in hotkey strings
keyboard.parse_hotkey = keyboard_hack.parse_hotkey
