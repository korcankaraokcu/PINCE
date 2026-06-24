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

from PyQt6.QtWidgets import (
    QWidget,
    QScrollBar,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QListWidget,
    QListWidgetItem,
    QComboBox,
    QMenu,
    QLayout,
    QMessageBox,
    QFileDialog,
)
from PyQt6.QtCore import QObject, QRegularExpression
from PyQt6.QtGui import QShortcut, QRegularExpressionValidator
from libpince import debugcore, utils, typedefs, regexes
from libpince.libmemscan.memscan import ScanLevel
from tr.tr import TranslationConstants as tr
from typing import overload
from contextlib import contextmanager
import os

validator_map: dict[str, QRegularExpressionValidator | None] = {
    "int": QRegularExpressionValidator(QRegularExpression(regexes.decimal_number.pattern)),  # integers
    "int_hex": QRegularExpressionValidator(QRegularExpression(regexes.hex_number_gui.pattern)),  # hexadecimals
    "float": QRegularExpressionValidator(QRegularExpression(regexes.float_number.pattern)),  # floats
    "bytearray": QRegularExpressionValidator(QRegularExpression(regexes.bytearray_input.pattern)),  # array of bytes
    "string": None,
}


def own_path_as_user(path: str, recursive: bool = False) -> None:
    """chowns a path PINCE created as root back to the user who launched it.

    Args:
        path (str): Path to chown
        recursive (bool): Also chown everything under path if it's a directory
    """
    if os.geteuid() != 0:
        return
    uid, gid = utils.get_user_ids()
    if not uid.isdigit() or not gid.isdigit() or int(uid) == 0:
        return
    uid, gid = int(uid), int(gid)
    paths = [path]
    if recursive:
        for root, dirs, files in os.walk(path):
            paths += [os.path.join(root, name) for name in dirs + files]
    for target in paths:
        try:
            os.chown(target, uid, gid)
        except OSError as e:
            utils.logger.error(f"Failed to chown {target}: {e}")


@contextmanager
def save_dialog_as_user(parent: QWidget | None, caption: str, directory: str, file_filter: str, extension: str = ""):
    """Opens a save dialog and chowns the chosen path back to the user once the block exits."""
    file_path, _ = QFileDialog.getSaveFileName(parent, caption, directory, file_filter)
    if file_path and extension:
        file_path = utils.append_file_extension(file_path, extension)
    try:
        yield file_path or None
    finally:
        if file_path and os.path.exists(file_path):
            own_path_as_user(file_path)


def get_icons_directory() -> str:
    """Gets the directory of the icons

    Returns:
        str: Path to the icons directory
    """
    return utils.get_script_directory() + "/media/icons"


def center(window: QWidget) -> None:
    """Center the given window to desktop

    Args:
        window (QWidget): The window that'll be centered to desktop
    """
    frame = window.frameGeometry()
    frame.moveCenter(window.screen().availableGeometry().center())
    window.move(frame.topLeft())


def center_to_parent(window: QWidget) -> None:
    """Center the given window to its parent

    Args:
        window (QWidget): The window that'll be centered to its parent
    """
    parent: QWidget = window.parent()
    window.move(parent.frameGeometry().center() - window.rect().center())


def center_scroll_bar(scrollbar: QScrollBar) -> None:
    """Center the given scrollbar

    Args:
        scrollbar (QScrollbar): Self-explanatory
    """
    maximum = scrollbar.maximum()
    minimum = scrollbar.minimum()
    scrollbar.setValue((maximum + minimum) // 2)


def resize_to_contents(tablewidget: QTableWidget) -> None:
    """Resizes the columns of the given QTableWidget to its contents
    This also fixes the stretch problem of the last column

    Args:
        tablewidget (QTableWidget): Self-explanatory
    """
    tablewidget.resizeColumnsToContents()
    default_size = tablewidget.horizontalHeader().defaultSectionSize()
    tablewidget.horizontalHeader().resizeSection(tablewidget.columnCount() - 1, default_size)


def fill_value_combobox(combobox: QComboBox, current_index: int = typedefs.VALUE_INDEX.INT32) -> None:
    """Fills the given QComboBox with value_index strings

    Args:
        combobox (QComboBox): The combobox that'll be filled
        current_index (int): Can be a member of typedefs.VALUE_INDEX
    """
    for key in typedefs.index_to_text_dict:
        combobox.addItem(typedefs.index_to_text_dict[key], key)
    idx = combobox.findData(current_index)
    if idx >= 0:
        combobox.setCurrentIndex(idx)


def fill_endianness_combobox(combobox: QComboBox, current_index: int = typedefs.ENDIANNESS.HOST) -> None:
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
    idx = combobox.findData(current_index)
    if idx >= 0:
        combobox.setCurrentIndex(idx)
    else:
        combobox.setCurrentIndex(0)


def fill_scope_combobox(combobox: QComboBox, current_index: ScanLevel = ScanLevel.HEAP_STACK_EXE_BSS) -> None:
    scan_scope_text = [
        (ScanLevel.HEAP_STACK_EXE, tr.BASIC),
        (ScanLevel.HEAP_STACK_EXE_BSS, tr.NORMAL),
        (ScanLevel.ALL_RW, tr.RW),
        (ScanLevel.ALL, tr.FULL),
    ]
    for scope, text in scan_scope_text:
        combobox.addItem(text, scope)
    idx = combobox.findData(current_index)
    if idx >= 0:
        combobox.setCurrentIndex(idx)
    else:
        combobox.setCurrentIndex(0)


def fill_alignment_combobox(combobox: QComboBox) -> None:
    """Fills the given QComboBox with alignment strings

    Args:
        combobox (QComboBox): The combobox that'll be filled
    """
    alignment_text_val = [
        (tr.AUTO, 0),
        ("1", 1),
        ("2", 2),
        ("4", 4),
        ("8", 8),
        ("16", 16),
    ]
    for text, value in alignment_text_val:
        combobox.addItem(text, value)
    combobox.setCurrentIndex(combobox.findData(0))


def get_current_row(tablewidget: QTableWidget) -> int:
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


@overload
def get_current_item(listwidget: QListWidget) -> QListWidgetItem | None: ...


@overload
def get_current_item(tablewidget: QTableWidget) -> QTableWidgetItem | None: ...


@overload
def get_current_item(treewidget: QTreeWidget) -> QTreeWidgetItem | None: ...


def get_current_item(
    widget: QListWidget | QTableWidget | QTreeWidget,
) -> QListWidgetItem | QTableWidgetItem | QTreeWidgetItem | None:
    r"""Returns the currently selected item for the given widget
    If you try to use only selectionModel().currentItem() for this purpose, you'll get the last selected item even
    if it was unselected afterwards. This is why this function exists, it checks the selection state before returning
    the selected item. Unlike get_current_row, this function can be used with QTreeWidget

    Args:
        widget (QListWidget | QTableWidget | QTreeWidget): Self-explanatory

    Returns:
        Any: Currently selected item. Returns None if nothing is selected

    Note:
        This function doesn't work properly when used within signals such as currentItemChanged, currentIndexChanged,
        currentChanged and currentRowChanged. Use the row, item, QModelIndex or whatever the signal provides instead.
        This bug occurs because those signals only update the changed row, not the selectionModel. This causes
        selectionModel().selectedRows() to return None and this function to behave improperly

        For developers: You can use the regex \.current.*\.connect to search signals if a cleanup is needed
    """
    if widget.selectionModel().selectedRows():
        return widget.currentItem()


def delete_menu_entries(menu: QMenu, QAction_list: list) -> None:
    """Deletes given QActions from the QMenu recursively and cleans up the remaining redundant separators and menus
    Doesn't support menus that includes types other than actions, separators and menus

    Args:
        menu (QMenu): Self-explanatory
        QAction_list (list): List of QActions. Leave blank if you just want to clean the redundant separators up
    """

    def remove_entries(menu: QMenu) -> None:
        for action in menu.actions():
            if action in QAction_list:
                menu.removeAction(action)
            elif action.menu() is not None:  # descend into submenus to delete nested entries
                remove_entries(action.menu())

    def clean_entries(menu: QMenu) -> None:
        for action in menu.actions():
            if action.menu() is not None:
                clean_entries(action.menu())
            elif action.isSeparator():
                actions = menu.actions()
                current_index = actions.index(action)
                if (
                    len(actions) == 1
                    or (current_index == 0 and actions[1].isSeparator())
                    or (current_index == len(actions) - 1 and actions[-2].isSeparator())
                    or (
                        0 < current_index < len(actions) - 1
                        and actions[current_index - 1].isSeparator()
                        and actions[current_index + 1].isSeparator()
                    )
                ):
                    menu.removeAction(action)

    remove_entries(menu)
    clean_entries(menu)


# TODO: This is a really bad design pattern, remove this function after moving classes to their own files
def search_parents_by_function(qt_object: QObject, func_name: str) -> QObject | None:
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


def get_layout_widgets(layout: QLayout) -> list[QWidget]:
    """Returns the widgets of a QLayout as a list

    Args:
        layout: Self-explanatory

    Returns:
        list: A list that contains the widgets of the given layout
    """
    return [layout.itemAt(x).widget() for x in range(layout.count())]


def contains_reference_mark(string: str) -> bool:
    """Checks if given string contains the reference mark

    Args:
        string (str): String that'll be checked for the reference mark

    Returns:
        bool: True if given string contains the reference mark, False otherwise
    """
    return True if regexes.reference_mark.search(string) else False


def append_shortcut_to_tooltip(qt_object: QObject, shortcut: QShortcut) -> None:
    """Appends key string of the given QShortcut to the toolTip of the given QObject

    Args:
        qt_object (QObject): Self-explanatory
        shortcut (QShortcut): Self-explanatory
    """
    qt_object.setToolTip(qt_object.toolTip() + "[" + shortcut.key().toString() + "]")


def check_inferior_running(widget: QWidget | None = None, show_message: bool = True) -> str | None:
    """Checks if a process is selected and is running

    Args:
        widget (QWidget | None): Parent widget for the message box. If None, message box will have no parent
        show_message (bool): If True, a message box will be shown if the inferior is running

    Returns:
        str: The error message, if the inferior is running or no process is selected
        None: If the inferior is stopped and a process is selected
    """
    if debugcore.currentpid == -1:
        if show_message:
            QMessageBox.information(widget, tr.ERROR, tr.NO_PROCESS_SELECTED)
        return tr.NO_PROCESS_SELECTED
    if debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING:
        if show_message:
            QMessageBox.information(widget, tr.ERROR, tr.REQUIRE_PROCESS_STOP)
        return tr.REQUIRE_PROCESS_STOP
    return None
