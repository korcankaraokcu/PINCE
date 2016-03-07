#!/usr/bin/python3
from PyQt5.QtWidgets import QDesktopWidget

combobox_value_dict={             #test
    0:"byte",
    1:"short",
    2:"int",
    3:"long",
    4:"float",
    5:"double",

}

# centering a window
def center(window):
    window.move(QDesktopWidget().availableGeometry().center() - window.frameGeometry().center())


# centering a child window
def center_parent(window):
    window.move(window.parent().frameGeometry().center() - window.frameGeometry().center())

def valuecombobox_to_valuetype(combobox):            #test
    print("lasf")