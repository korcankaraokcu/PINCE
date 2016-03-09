#!/usr/bin/python3
from PyQt5.QtWidgets import QDesktopWidget

# A dictionary used to convert value_combobox index to gdb/mi command
combobox_value_dict = {
    0: "db",  # byte
    1: "dh",  # 2bytes
    2: "dw",  # 4bytes
    3: "dg",  # 8bytes
    4: "fw",  # float
    5: "fg",  # double
    6: "s",  # string
    7: "xb"  # array of bytes
}


# centering a window
def center(window):
    window.move(QDesktopWidget().availableGeometry().center() - window.frameGeometry().center())


# centering a child window
def center_parent(window):
    window.move(window.parent().frameGeometry().center() - window.frameGeometry().center())


# return a string corresponding to the selected index
# returns "out of bounds" string if the index doesn't match the dictionary
def valuecombobox_to_valuetype(index=int):
    return combobox_value_dict.get(index, "out of bounds")
