# -*- coding: utf-8 -*-
"""
Copyright (C) Korcan Karaokçu <korcankaraokcu@gmail.com>

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
from PyQt6.QtWidgets import QWidget, QScrollBar, QTableWidget, QComboBox, QMenu, QLayout
from PyQt6.QtCore import QObject, QRegularExpression
from PyQt6.QtGui import QShortcut, QRegularExpressionValidator
from libpince import utils, typedefs, regexes
from tr.tr import TranslationConstants as tr

validator_map: dict[str, QRegularExpressionValidator | None] = {
    "int": QRegularExpressionValidator(QRegularExpression(regexes.decimal_number.pattern)),  # integers
    "int_hex": QRegularExpressionValidator(QRegularExpression(regexes.hex_number_gui.pattern)),  # hexadecimals
    "float": QRegularExpressionValidator(QRegularExpression(regexes.float_number.pattern)),  # floats
    "bytearray": QRegularExpressionValidator(QRegularExpression(regexes.bytearray_input.pattern)),  # array of bytes
    "string": None,
}


def get_icons_directory():
    """Gets the directory of the icons

    Returns:
        str: Path to the icons directory
    """
    return utils.get_script_directory() + "/media/icons"


def center(window: QWidget):
    """Center the given window to desktop

    Args:
        window (QWidget): The window that'll be centered to desktop
    """
    window.frameGeometry().moveCenter(window.screen().availableGeometry().center())


def center_to_parent(window: QWidget):
    """Center the given window to its parent

    Args:
        window (QWidget): The window that'll be centered to its parent
    """
    parent: QWidget = window.parent()
    window.move(parent.frameGeometry().center() - window.rect().center())


def center_scroll_bar(scrollbar: QScrollBar):
    """Center the given scrollbar

    Args:
        scrollbar (QScrollbar): Self-explanatory
    """
    maximum = scrollbar.maximum()
    minimum = scrollbar.minimum()
    scrollbar.setValue((maximum + minimum) // 2)


def resize_to_contents(tablewidget: QTableWidget):
    """Resizes the columns of the given QTableWidget to its contents
    This also fixes the stretch problem of the last column

    Args:
        tablewidget (QTableWidget): Self-explanatory
    """
    tablewidget.resizeColumnsToContents()
    default_size = tablewidget.horizontalHeader().defaultSectionSize()
    tablewidget.horizontalHeader().resizeSection(tablewidget.columnCount() - 1, default_size)


def fill_value_combobox(combobox: QComboBox, current_index: int = typedefs.VALUE_INDEX.INT32):
    """Fills the given QComboBox with value_index strings

    Args:
        combobox (QComboBox): The combobox that'll be filled
        current_index (int): Can be a member of typedefs.VALUE_INDEX
    """
    for key in typedefs.index_to_text_dict:
        combobox.addItem(typedefs.index_to_text_dict[key])
    combobox.setCurrentIndex(current_index)


def fill_endianness_combobox(combobox: QComboBox, current_index: int = typedefs.ENDIANNESS.HOST):
    """Fills the given QComboBox with endianness strings

    Args:
        combobox (QComboBox): The combobox that'll be filled
        current_index (int): Can be a member of typedefs.ENDIANNESS
    """
    endianness_text = [
        (typedefs.ENDIANNESS.HOST, tr.HOST),
        (typedefs.ENDIANNESS.LITTLE, tr.LITTLE),
        (typedefs.ENDIANNESS.BIG, tr.BIG),
    ]
    for endian, text in endianness_text:
        combobox.addItem(text, endian)
    combobox.setCurrentIndex(current_index)


def get_current_row(tablewidget: QTableWidget):
    r"""Returns the currently selected row index for the given QTableWidget
    If you try to use only selectionModel().currentIndex().row() for this purpose, you'll get the last selected row even
    if it was unselected afterwards. This is why this function exists, it checks the selection state before returning
    the selected row

    Args:
        tablewidget (QTableWidget): Self-explanatory

    Returns:
        int: Currently selected row. Returns -1 if nothing is selected

    Note:
        This function doesn't work properly when used within signals such as currentItemChanged, currentIndexChanged,
        currentChanged and currentRowChanged. Use the row, item, QModelIndex or whatever the signal provides instead.
        This bug occurs because those signals only update the changed row, not the selectionModel. This causes
        selectionModel().selectedRows() to return None and this function to behave improperly

        For developers: You can use the regex \.current.*\.connect to search signals if a cleanup is needed
    """
    if tablewidget.selectionModel().selectedRows():
        return tablewidget.selectionModel().currentIndex().row()
    return -1


def get_current_item(tablewidget: QTableWidget):
    r"""Returns the currently selected item for the given QTableWidget
    If you try to use only selectionModel().currentItem() for this purpose, you'll get the last selected item even
    if it was unselected afterwards. This is why this function exists, it checks the selection state before returning
    the selected item. Unlike get_current_row, this function can be used with QTreeWidget

    Args:
        tablewidget (QTableWidget): Self-explanatory

    Returns:
        Any: Currently selected item. Returns None if nothing is selected

    Note:
        This function doesn't work properly when used within signals such as currentItemChanged, currentIndexChanged,
        currentChanged and currentRowChanged. Use the row, item, QModelIndex or whatever the signal provides instead.
        This bug occurs because those signals only update the changed row, not the selectionModel. This causes
        selectionModel().selectedRows() to return None and this function to behave improperly

        For developers: You can use the regex \.current.*\.connect to search signals if a cleanup is needed
    """
    if tablewidget.selectionModel().selectedRows():
        return tablewidget.currentItem()


def delete_menu_entries(menu: QMenu, QAction_list: list):
    """Deletes given QActions from the QMenu recursively and cleans up the remaining redundant separators and menus
    Doesn't support menus that includes types other than actions, separators and menus

    Args:
        menu (QMenu): Self-explanatory
        QAction_list (list): List of QActions. Leave blank if you just want to clean the redundant separators up
    """

    def remove_entries(menu: QMenu):
        for action in menu.actions():
            try:
                QAction_list.index(action)
            except ValueError:
                pass
            else:
                menu.removeAction(action)

    def clean_entries(menu: QMenu):
        for action in menu.actions():
            if action.isSeparator():
                actions = menu.actions()
                current_index = actions.index(action)
                if (
                    len(actions) == 1
                    or (current_index == 0 and actions[1].isSeparator())
                    or (current_index == -1 and actions[-2].isSeparator())
                    or (actions[current_index - 1].isSeparator() and actions[current_index + 1].isSeparator())
                ):
                    menu.removeAction(action)

    remove_entries(menu)
    clean_entries(menu)


# TODO: This is a really bad design pattern, remove this function after moving classes to their own files
def search_parents_by_function(qt_object: QObject, func_name: str):
    """Search for func_name in the parents of given QObject. Once function is found, parent that possesses func_name
    is returned

    Args:
        qt_object (QObject): The object that'll be searched for it's parents
        func_name (str): The name of the function that'll be searched
    """
    while qt_object is not None:
        qt_object = qt_object.parent()
        if func_name in dir(qt_object):
            return qt_object


def get_layout_widgets(layout: QLayout):
    """Returns the widgets of a QLayout as a list

    Args:
        layout: Self-explanatory

    Returns:
        list: A list that contains the widgets of the given layout
    """
    return [layout.itemAt(x).widget() for x in range(layout.count())]


def contains_reference_mark(string: str):
    """Checks if given string contains the reference mark

    Args:
        string (str): String that'll be checked for the reference mark

    Returns:
        bool: True if given string contains the reference mark, False otherwise
    """
    return True if regexes.reference_mark.search(string) else False


def append_shortcut_to_tooltip(qt_object: QObject, shortcut: QShortcut):
    """Appends key string of the given QShortcut to the toolTip of the given QObject

    Args:
        qt_object (QObject): Self-explanatory
        shortcut (QShortcut): Self-explanatory
    """
    qt_object.setToolTip(qt_object.toolTip() + "[" + shortcut.key().toString() + "]")
