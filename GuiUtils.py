#!/usr/bin/python3
from PyQt5.QtWidgets import QDesktopWidget
from re import search, sub

# A dictionary used to convert value_combobox index to text
# dictionaries in GuiUtils, GDB_Engine and ScriptUtils are connected to each other
# any modification in one dictionary may require a rework in others
valuetype_to_text_dict = {
    0: "Byte",
    1: "2 Bytes",
    2: "4 Bytes",
    3: "8 Bytes",
    4: "Float",
    5: "Double",
    6: "String",
    7: "AoB"
}


# dictionaries in GuiUtils, GDB_Engine and ScriptUtils are connected to each other
# any modification in one dictionary may require a rework in others
text_to_valuetype_dict = {
    "Byte": 0,
    "2 Bytes": 1,
    "4 Bytes": 2,
    "8 Bytes": 3,
    "Float": 4,
    "Double": 5
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
    if index is 6:
        returned_string = returned_string + "[" + str(length) + "]"
        if unicode:
            returned_string = returned_string + ",U"
        if not zero_terminate:
            returned_string = returned_string + ",NZT"
    elif index is 7:
        returned_string = returned_string + "[" + str(length) + "]"
    return returned_string


def text_to_valuetype(string):
    length=unicode=zero_terminate=None
    index = text_to_valuetype_dict.get(string, -1)
    if index is -1:
        if search(r"String\[\d*\]", string):  # String[10],U,NZT
            index=6
            length = sub("[^0-9]", "", string)
            length = int(length)
            if search(r",U", string):  # check if Unicode, literal string
                unicode=True
            else:
                unicode=False
            if search(r",NZT", string):  # check if not zero terminate, literal string
                zero_terminate=False
            else:
                zero_terminate=True
        elif search(r"AoB\[\d*\]", string):  # AoB[10]
            index=7
            length = sub("[^0-9]", "", string)
            length = int(length)
    return index, length, unicode, zero_terminate
