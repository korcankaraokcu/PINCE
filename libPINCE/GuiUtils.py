# -*- coding: utf-8 -*-
"""
Copyright (C) 2016 Korcan Karaokçu <korcankaraokcu@gmail.com>

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
from PyQt5.QtWidgets import QDesktopWidget
from re import search, sub
from . import type_defs


def center(window):
    """Center the given window to desktop

    Args:
        window (QMainWindow, QWidget etc.): The window that'll be centered to desktop
    """
    window.move(QDesktopWidget().availableGeometry().center() - window.frameGeometry().center())


def center_to_parent(window):
    """Center the given window to it's parent

    Args:
        window (QMainWindow, QWidget etc.): The window that'll be centered to it's parent
    """
    window.move(window.parent().frameGeometry().center() - window.frameGeometry().center())


def center_to_window(window_secondary, window_main):
    """Center the given window_secondary to window_main

    Args:
        window_secondary (QMainWindow, QWidget etc.): The window that'll be centered to window_main
        window_main (QMainWindow, QWidget etc.): The window that window_secondary will centered to
    """
    window_secondary.move(window_main.frameGeometry().center() - window_secondary.frameGeometry().center())


def center_scroll_bar(QScrollBar):
    """Center the given scrollbar

    Args:
        QScrollBar (QScrollbar): The scrollbar that'll be centered
    """
    maximum = QScrollBar.maximum()
    minimum = QScrollBar.minimum()
    QScrollBar.setValue((maximum + minimum) / 2)


def valuetype_to_text(value_index=int, length=0, is_unicode=False, zero_terminate=True):
    """Returns a str according to given parameters

    Args:
        value_index (int): Determines the type of data. Can be a member of type_defs.VALUE_INDEX
        length (int): Length of the data. Only used when the value_index is INDEX_STRING or INDEX_AOB. Ignored otherwise
        is_unicode (bool): If True, ",U" will be appended to str. Only used when value_index is INDEX_STRING.
        Ignored otherwise. "U" stands for "Unicode"
        zero_terminate (bool): If False, ",NZT" will be appended to str. Only used when value_index is INDEX_STRING.
        Ignored otherwise. "NZT" stands for "Not Zero Terminate"

    Returns:
        str: A str generated by given parameters
        str "out of bounds" is returned if the value_index doesn't match the dictionary

    Examples:
        value_index=type_defs.VALUE_INDEX.INDEX_STRING, length=15, is_unicode=True, zero_terminate=False--▼
        returned str="String[15],U,NZT"
        value_index=type_defs.VALUE_INDEX.INDEX_AOB, length=42-->returned str="AoB[42]"
    """
    returned_string = type_defs.index_to_text_dict.get(value_index, "out of bounds")
    if value_index is type_defs.VALUE_INDEX.INDEX_STRING:
        returned_string = returned_string + "[" + str(length) + "]"
        if is_unicode:
            returned_string = returned_string + ",U"
        if not zero_terminate:
            returned_string = returned_string + ",NZT"
    elif value_index is type_defs.VALUE_INDEX.INDEX_AOB:
        returned_string = returned_string + "[" + str(length) + "]"
    return returned_string


def text_to_valuetype(string):
    """Returns a tuple of parameters of the function valuetype_to_text evaluated according to given str

    Args:
        string (str): String must be generated from the function valuetype_to_text

    Returns:
        tuple: A tuple consisting of parameters of the function valuetype_to_text--▼
        value_index, length, unicode, zero_terminate

    Examples:
        string="String[15],U,NZT"--▼
        value_index=type_defs.VALUE_INDEX.INDEX_STRING, length=15, is_unicode=True, zero_terminate=False
        string="AoB[42]"-->value_index=type_defs.VALUE_INDEX.INDEX_AOB, length=42, None, None
    """
    length = unicode = zero_terminate = None
    index = type_defs.text_to_index_dict.get(string, -1)
    if index is -1:
        if search(r"String\[\d*\]", string):  # String[10],U,NZT
            index = type_defs.VALUE_INDEX.INDEX_STRING
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
            index = type_defs.VALUE_INDEX.INDEX_AOB
            length = sub("[^0-9]", "", string)
            length = int(length)
    return index, length, unicode, zero_terminate


def text_to_index(string):
    """Converts given str to type_defs.VALUE_INDEX

    Simplified version of the function text_to_valuetype for only extracting value_index

    Args:
        string (str): String must be generated from the function valuetype_to_text

    Returns:
        int: A member of type_defs.VALUE_INDEX
    """
    index = type_defs.text_to_index_dict.get(string, -1)
    if index is -1:
        if search(r"String", string):  # String[10],U,NZT
            index = type_defs.VALUE_INDEX.INDEX_STRING
        elif search(r"AoB", string):  # AoB[10]
            index = type_defs.VALUE_INDEX.INDEX_AOB
    return index


def text_to_length(string):
    """Converts given str to length

    Simplified version of the function text_to_valuetype for only extracting length

    Args:
        string (str): String must be generated from the function valuetype_to_text

    Returns:
        int: Length
        -1 is returned if the value_index of the given string isn't INDEX_STRING or INDEX_AOB
    """
    index = type_defs.text_to_index_dict.get(string, -1)
    if index is -1:
        search(r"\[\d*\]", string)
        length = sub("[^0-9]", "", string)
        return int(length)
    return -1


def change_text_length(string, length):
    """Changes the length of the given str to the given length

    Args:
        string (str): String must be generated from the function valuetype_to_text
        length (int,str): New length

    Returns:
        str: The changed str
        int: -1 is returned if the value_index of the given string isn't INDEX_STRING or INDEX_AOB
    """
    index = type_defs.text_to_index_dict.get(string, -1)
    if index is -1:
        return sub(r"\[\d*\]", "[" + str(length) + "]", string)
    return -1


def remove_bookmark_mark(string):
    """Removes the bookmark mark from the given string

    Args:
        string (str): String that'll be cleansed from the bookmark mark

    Returns:
        str: Remaining str after the cleansing
    """
    return sub(r"\(M\)", "", string, count=1)
