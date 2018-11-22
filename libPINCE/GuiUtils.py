# -*- coding: utf-8 -*-
"""
Copyright (C) 2016-2017 Korcan Karaokçu <korcankaraokcu@gmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
# PyQt5 isn't needed to run tests with travis. To reduce the testing time and complexity, we ignore the PyQt5 imports
# There'll be no tests for PyQt5 related functions in GuiUtils.py
try:
    from PyQt5.QtWidgets import QDesktopWidget
except ImportError:
    pass
from . import SysUtils, type_defs, common_regexes


#:tag:GUI
def get_icons_directory():
    """Gets the directory of the icons

    Returns:
        str: Path to the icons directory
    """
    return SysUtils.get_current_script_directory() + "/media/icons"


#:tag:GUI
def center(window):
    """Center the given window to desktop

    Args:
        window (QMainWindow, QWidget etc.): The window that'll be centered to desktop
    """
    window.move(QDesktopWidget().availableGeometry().center() - window.frameGeometry().center())


#:tag:GUI
def center_to_parent(window):
    """Center the given window to it's parent

    Args:
        window (QMainWindow, QWidget etc.): The window that'll be centered to it's parent
    """
    window.move(window.parent().frameGeometry().center() - window.frameGeometry().center())


#:tag:GUI
def center_to_window(window_secondary, window_main):
    """Center the given window_secondary to window_main

    Args:
        window_secondary (QMainWindow, QWidget etc.): The window that'll be centered to window_main
        window_main (QMainWindow, QWidget etc.): The window that window_secondary will centered to
    """
    window_secondary.move(window_main.frameGeometry().center() - window_secondary.frameGeometry().center())


#:tag:GUI
def center_scroll_bar(QScrollBar):
    """Center the given scrollbar

    Args:
        QScrollBar (QScrollbar): The scrollbar that'll be centered
    """
    maximum = QScrollBar.maximum()
    minimum = QScrollBar.minimum()
    QScrollBar.setValue((maximum + minimum) / 2)


#:tag:GUI
def fill_value_combobox(QCombobox, current_index=type_defs.VALUE_INDEX.INDEX_4BYTES):
    """Fills the given QCombobox with value_index strings

    Args:
        QCombobox (QCombobox): The combobox that'll be filled
        current_index (int): Can be a member of type_defs.VALUE_INDEX
    """
    for key in type_defs.index_to_text_dict:
        if key == type_defs.VALUE_INDEX.INDEX_AOB:
            QCombobox.addItem("Array of Bytes")
        else:
            QCombobox.addItem(type_defs.index_to_text_dict[key])
    QCombobox.setCurrentIndex(current_index)


#:tag:GUI
def get_current_row(QObject):
    """Returns the currently selected row index for the given QObject
    If you try to use only selectionModel().currentIndex().row() for this purpose, you'll get the last selected row even
    if it was unselected afterwards. This is why this function exists, it checks the selection state before returning
    the selected row

    Args:
        QObject (QObject): Self-explanatory

    Returns:
        int: Currently selected row. Returns -1 if nothing is selected
    """
    if QObject.selectionModel().selectedRows():
        return QObject.selectionModel().currentIndex().row()
    return -1


#:tag:GUI
def get_current_item(QObject):
    """Returns the currently selected item for the given QObject
    If you try to use only selectionModel().currentItem() for this purpose, you'll get the last selected item even
    if it was unselected afterwards. This is why this function exists, it checks the selection state before returning
    the selected item. Unlike get_current_row, this function can be used with QTreeWidget

    Args:
        QObject (QObject): Self-explanatory

    Returns:
        Any: Currently selected item. Returns None if nothing is selected
    """
    if QObject.selectionModel().selectedRows():
        return QObject.currentItem()


#:tag:GUI
def delete_menu_entries(QMenu, QAction_list):
    """Deletes given QActions from the QMenu recursively and cleans up the remaining redundant separators and menus
    Doesn't support menus that includes types other than actions, separators and menus

    Args:
        QMenu (QMenu): Self-explanatory
        QAction_list (list): List of QActions. Leave blank if you just want to clean the redundant separators up
    """

    def remove_entries(menu):
        for action in menu.actions():
            try:
                QAction_list.index(action)
            except ValueError:
                if action.menu():
                    remove_entries(action.menu())
            else:
                menu.removeAction(action)

    def clean_entries(menu):
        for action in menu.actions():
            if action.menu():
                clean_entries(action.menu())
                if not action.menu().actions():
                    menu.removeAction(action.menu().menuAction())
            elif action.isSeparator():
                actions = menu.actions()
                current_index = actions.index(action)
                if len(actions) == 1 or (current_index == 0 and actions[1].isSeparator()) or \
                        (current_index == -1 and actions[-2].isSeparator()) or \
                        (actions[current_index - 1].isSeparator() and actions[current_index + 1].isSeparator()):
                    menu.removeAction(action)

    remove_entries(QMenu)
    clean_entries(QMenu)


# TODO: This is a really bad design pattern, remove this function after moving classes to their own files
#:tag:GUI
def search_parents_by_function(qt_object, func_name):
    """Search for func_name in the parents of given qt_object. Once function is found, parent that possesses func_name
    is returned

    Args:
        qt_object (object): The object that'll be searched for it's parents
        func_name (str): The name of the function that'll be searched
    """
    while qt_object is not None:
        qt_object = qt_object.parent()
        if func_name in dir(qt_object):
            return qt_object


#:tag:GUI
def get_layout_widgets(layout):
    """Returns the widgets of a layout as a list

    Args:
        layout: Self-explanatory

    Returns:
        list: A list that contains the widgets of the given layout
    """
    return [layout.itemAt(x).widget() for x in range(layout.count())]


#:tag:ValueType
def valuetype_to_text(value_index=int, length=0, zero_terminate=True):
    """Returns a str according to given parameters

    Args:
        value_index (int): Determines the type of data. Can be a member of type_defs.VALUE_INDEX
        length (int): Length of the data. Only used when the value_index is INDEX_STRING or INDEX_AOB. Ignored otherwise
        zero_terminate (bool): If False, ",NZT" will be appended to str. Only used when value_index is INDEX_STRING.
        Ignored otherwise. "NZT" stands for "Not Zero Terminate"

    Returns:
        str: A str generated by given parameters
        str "out of bounds" is returned if the value_index doesn't match the dictionary

    Examples:
        value_index=type_defs.VALUE_INDEX.INDEX_STRING_UTF16, length=15, zero_terminate=False--▼
        returned str="String_UTF16[15],NZT"
        value_index=type_defs.VALUE_INDEX.INDEX_AOB, length=42-->returned str="AoB[42]"
    """
    returned_string = type_defs.index_to_text_dict.get(value_index, "out of bounds")
    if type_defs.VALUE_INDEX.is_string(value_index):
        returned_string = returned_string + "[" + str(length) + "]"
        if not zero_terminate:
            returned_string += ",NZT"
    elif value_index is type_defs.VALUE_INDEX.INDEX_AOB:
        returned_string += "[" + str(length) + "]"
    return returned_string


#:tag:ValueType
def text_to_valuetype(string):
    """Returns a tuple of parameters of the function valuetype_to_text evaluated according to given str

    Args:
        string (str): String must be generated from the function valuetype_to_text

    Returns:
        tuple: A tuple consisting of parameters of the function valuetype_to_text--▼
        value_index, length, zero_terminate, byte_length

        If value_index doesn't contain length, length will be returned as -1
        If value_index is INDEX_STRING, byte_length will be returned as -1

    Examples:
        string="String_UTF8[15],NZT"--▼
        value_index=type_defs.VALUE_INDEX.INDEX_STRING_UTF8, length=15, zero_terminate=False, byte_length=-1
        string="AoB[42]"-->value_index=type_defs.VALUE_INDEX.INDEX_AOB, length=42, None, 42
        string="Double"-->value_index=type_defs.VALUE_INDEX.INDEX_DOUBLE, length=-1, None, 8
    """
    index, length = -1, -1
    zero_terminate = None
    for key in type_defs.text_to_index_dict:
        if string.startswith(key):
            index = type_defs.text_to_index_dict[key]
            break
    byte_len = type_defs.index_to_valuetype_dict.get(index, [-1])[0]
    if type_defs.VALUE_INDEX.has_length(index):
        length = int(common_regexes.valuetype_length.search(string).group(1))
        byte_len = length
        if type_defs.VALUE_INDEX.is_string(index):
            byte_len = -1
            if common_regexes.valuetype_nzt.search(string):
                zero_terminate = False
            else:
                zero_terminate = True
    return index, length, zero_terminate, byte_len


#:tag:GUI
def change_text_length(string, length):
    """Changes the length of the given str to the given length

    Args:
        string (str): String must be generated from the function valuetype_to_text
        length (int,str): New length

    Returns:
        str: The changed str
        int: -1 is returned if the value_index of the given string isn't INDEX_STRING or INDEX_AOB
    """
    index = text_to_valuetype(string)[0]
    if type_defs.VALUE_INDEX.has_length(index):
        return common_regexes.valuetype_length.sub("[" + str(length) + "]", string)
    return -1


#:tag:GUI
def contains_reference_mark(string):
    """Checks if given string contains the reference mark

    Args:
        string (str): String that'll be checked for the reference mark

    Returns:
        bool: True if given string contains the reference mark, False otherwise
    """
    return True if common_regexes.reference_mark.search(string) else False


#:tag:GUI
def append_shortcut_to_tooltip(QObject, QShortcut):
    """Appends key string of the given QShortcut to the toolTip of the given QObject

    Args:
        QObject (QObject): Self-explanatory
        QShortcut (QShortcut): Self-explanatory
    """
    QObject.setToolTip(QObject.toolTip() + "[" + QShortcut.key().toString() + "]")
