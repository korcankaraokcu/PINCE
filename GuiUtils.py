#!/usr/bin/python3
from PyQt5.QtWidgets import QDesktopWidget
from re import search, sub
import type_defs

COMBOBOX_BYTE = type_defs.COMBOBOX_BYTE
COMBOBOX_2BYTES = type_defs.COMBOBOX_2BYTES
COMBOBOX_4BYTES = type_defs.COMBOBOX_4BYTES
COMBOBOX_8BYTES = type_defs.COMBOBOX_8BYTES
COMBOBOX_FLOAT = type_defs.COMBOBOX_FLOAT
COMBOBOX_DOUBLE = type_defs.COMBOBOX_DOUBLE
COMBOBOX_STRING = type_defs.COMBOBOX_STRING
COMBOBOX_AOB = type_defs.COMBOBOX_AOB  # Array of Bytes

# Represents the texts at indexes in combobox


# A dictionary used to convert value_combobox index to text
# dictionaries in GuiUtils, GDB_Engine and ScriptUtils are connected to each other
# any modification in one dictionary may require a rework in others
valuetype_to_text_dict = {
    COMBOBOX_BYTE: "Byte",
    COMBOBOX_2BYTES: "2 Bytes",
    COMBOBOX_4BYTES: "4 Bytes",
    COMBOBOX_8BYTES: "8 Bytes",
    COMBOBOX_FLOAT: "Float",
    COMBOBOX_DOUBLE: "Double",
    COMBOBOX_STRING: "String",
    COMBOBOX_AOB: "AoB"
}

# dictionaries in GuiUtils, GDB_Engine and ScriptUtils are connected to each other
# any modification in one dictionary may require a rework in others
text_to_valuetype_dict = {
    "Byte": COMBOBOX_BYTE,
    "2 Bytes": COMBOBOX_2BYTES,
    "4 Bytes": COMBOBOX_4BYTES,
    "8 Bytes": COMBOBOX_8BYTES,
    "Float": COMBOBOX_FLOAT,
    "Double": COMBOBOX_DOUBLE
}


# centering a window
def center(window):
    window.move(QDesktopWidget().availableGeometry().center() - window.frameGeometry().center())


# centering a child window
def center_to_parent(window):
    window.move(window.parent().frameGeometry().center() - window.frameGeometry().center())


# return a string corresponding to the selected index
# returns "out of bounds" string if the index doesn't match the dictionary
def valuetype_to_text(index=int, length=0, unicode=False, zero_terminate=True):
    returned_string = valuetype_to_text_dict.get(index, "out of bounds")
    if index is COMBOBOX_STRING:
        returned_string = returned_string + "[" + str(length) + "]"
        if unicode:
            returned_string = returned_string + ",U"
        if not zero_terminate:
            returned_string = returned_string + ",NZT"
    elif index is COMBOBOX_AOB:
        returned_string = returned_string + "[" + str(length) + "]"
    return returned_string


def text_to_valuetype(string):
    length = unicode = zero_terminate = None
    index = text_to_valuetype_dict.get(string, -1)
    if index is -1:
        if search(r"String\[\d*\]", string):  # String[10],U,NZT
            index = COMBOBOX_STRING
            length = sub("[^0-9]", "", string)
            length = int(length)
            if search(r",U", string):  # check if Unicode, literal string
                unicode = True
            else:
                unicode = False
            if search(r",NZT", string):  # check if not zero terminate, literal string
                zero_terminate = False
            else:
                zero_terminate = True
        elif search(r"AoB\[\d*\]", string):  # AoB[10]
            index = COMBOBOX_AOB
            length = sub("[^0-9]", "", string)
            length = int(length)
    return index, length, unicode, zero_terminate
