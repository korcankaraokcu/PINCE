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
from libpince import utils, typedefs, regexes
from tr.tr import TranslationConstants as tr

#:tag:GUI
def get_icons_directory():
    """Gets the directory of the icons

    Returns:
        str: Path to the icons directory
    """
    return utils.get_script_directory() + "/media/icons"


#:tag:GUI
def center(window):
    """Center the given window to desktop

    Args:
        window (QMainWindow, QWidget etc.): The window that'll be centered to desktop
    """
    window.frameGeometry().moveCenter(window.screen().availableGeometry().center())


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
    QScrollBar.setValue((maximum + minimum) // 2)


#:tag:GUI
def resize_to_contents(QTableWidget):
    """Resizes the columns of the given QTableWidget to its contents
    This also fixes the stretch problem of the last column

    Args:
        QTableWidget (QTableWidget): Self-explanatory
    """
    QTableWidget.resizeColumnsToContents()
    default_size = QTableWidget.horizontalHeader().defaultSectionSize()
    QTableWidget.horizontalHeader().resizeSection(QTableWidget.columnCount() - 1, default_size)


#:tag:GUI
def fill_value_combobox(QCombobox, current_index=typedefs.VALUE_INDEX.INT32):
    """Fills the given QCombobox with value_index strings

    Args:
        QCombobox (QCombobox): The combobox that'll be filled
        current_index (int): Can be a member of typedefs.VALUE_INDEX
    """
    for key in typedefs.index_to_text_dict:
        QCombobox.addItem(typedefs.index_to_text_dict[key])
    QCombobox.setCurrentIndex(current_index)

#:tag:GUI
def fill_endianness_combobox(QCombobox, current_index=typedefs.ENDIANNESS.HOST):
    """Fills the given QCombobox with endianness strings

    Args:
        QCombobox (QCombobox): The combobox that'll be filled
        current_index (int): Can be a member of typedefs.ENDIANNESS
    """
    endianness_text = [
        (typedefs.ENDIANNESS.HOST, tr.HOST),
        (typedefs.ENDIANNESS.LITTLE, tr.LITTLE),
        (typedefs.ENDIANNESS.BIG, tr.BIG)
    ]
    for endian, text in endianness_text:
        QCombobox.addItem(text, endian)
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

    Note:
        This function doesn't work properly when used within signals such as currentItemChanged, currentIndexChanged,
        currentChanged and currentRowChanged. Use the row, item, QModelIndex or whatever the signal provides instead.
        This bug occurs because those signals only update the changed row, not the selectionModel. This causes
        selectionModel().selectedRows() to return None and this function to behave improperly

        For developers: You can use the regex \.current.*\.connect to search signals if a cleanup is needed
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

    Note:
        This function doesn't work properly when used within signals such as currentItemChanged, currentIndexChanged,
        currentChanged and currentRowChanged. Use the row, item, QModelIndex or whatever the signal provides instead.
        This bug occurs because those signals only update the changed row, not the selectionModel. This causes
        selectionModel().selectedRows() to return None and this function to behave improperly

        For developers: You can use the regex \.current.*\.connect to search signals if a cleanup is needed
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
                pass
            else:
                menu.removeAction(action)

    def clean_entries(menu):
        for action in menu.actions():
            if action.isSeparator():
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


#:tag:GUI
def contains_reference_mark(string):
    """Checks if given string contains the reference mark

    Args:
        string (str): String that'll be checked for the reference mark

    Returns:
        bool: True if given string contains the reference mark, False otherwise
    """
    return True if regexes.reference_mark.search(string) else False


#:tag:GUI
def append_shortcut_to_tooltip(QObject, QShortcut):
    """Appends key string of the given QShortcut to the toolTip of the given QObject

    Args:
        QObject (QObject): Self-explanatory
        QShortcut (QShortcut): Self-explanatory
    """
    QObject.setToolTip(QObject.toolTip() + "[" + QShortcut.key().toString() + "]")