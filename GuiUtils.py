#!/usr/bin/python3
from PyQt5.QtWidgets import QDesktopWidget

# A dictionary used to convert value_combobox index to text
valuetype_to_text_dict = {
    0: "Byte",
    1: "2 Bytes",
    2: "4 Bytes",
    3: "8 Bytes",
    4: "Float",
    5: "Double",
    6: "String",
    7: "Array of Bytes"
}


# centering a window
def center(window):
    window.move(QDesktopWidget().availableGeometry().center() - window.frameGeometry().center())


# centering a child window
def center_parent(window):
    window.move(window.parent().frameGeometry().center() - window.frameGeometry().center())


# return a string corresponding to the selected index
# returns "out of bounds" string if the index doesn't match the dictionary
def valuetype_to_text(index=int, length=0, unicode=False, zero_terminate=True):
    returned_string = valuetype_to_text_dict.get(index, "out of bounds")
    if index is 6:
        if unicode:
            returned_string = returned_string + ",U"
        if not zero_terminate:
            returned_string = returned_string + ",NZT"
    elif index is 7:
        returned_string = returned_string + "[" + str(length) + "]"
    return returned_string
