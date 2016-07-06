#!/usr/bin/python3
from PyQt5.QtWidgets import QDesktopWidget
from re import search, match, sub
import type_defs

INDEX_BYTE = type_defs.INDEX_BYTE
INDEX_2BYTES = type_defs.INDEX_2BYTES
INDEX_4BYTES = type_defs.INDEX_4BYTES
INDEX_8BYTES = type_defs.INDEX_8BYTES
INDEX_FLOAT = type_defs.INDEX_FLOAT
INDEX_DOUBLE = type_defs.INDEX_DOUBLE
INDEX_STRING = type_defs.INDEX_STRING
INDEX_AOB = type_defs.INDEX_AOB

index_to_text_dict = type_defs.index_to_text_dict
text_to_index_dict = type_defs.text_to_index_dict


# centering a window
def center(window):
    window.move(QDesktopWidget().availableGeometry().center() - window.frameGeometry().center())


# centering a child window
def center_to_parent(window):
    window.move(window.parent().frameGeometry().center() - window.frameGeometry().center())


# return a string corresponding to the selected index
# returns "out of bounds" string if the index doesn't match the dictionary
def valuetype_to_text(index=int, length=0, unicode=False, zero_terminate=True):
    returned_string = index_to_text_dict.get(index, "out of bounds")
    if index is INDEX_STRING:
        returned_string = returned_string + "[" + str(length) + "]"
        if unicode:
            returned_string = returned_string + ",U"
        if not zero_terminate:
            returned_string = returned_string + ",NZT"
    elif index is INDEX_AOB:
        returned_string = returned_string + "[" + str(length) + "]"
    return returned_string


def text_to_valuetype(string):
    length = unicode = zero_terminate = None
    index = text_to_index_dict.get(string, -1)
    if index is -1:
        if search(r"String\[\d*\]", string):  # String[10],U,NZT
            index = INDEX_STRING
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
            index = INDEX_AOB
            length = sub("[^0-9]", "", string)
            length = int(length)
    return index, length, unicode, zero_terminate


def text_to_index(string):
    index = text_to_index_dict.get(string, -1)
    if index is -1:
        if search(r"String", string):  # String[10],U,NZT
            index = INDEX_STRING
        elif search(r"AoB", string):  # AoB[10]
            index = INDEX_AOB
    return index


def text_to_length(string):
    index = text_to_index_dict.get(string, -1)
    if index is -1:
        search(r"\[\d*\]", string)
        length = sub("[^0-9]", "", string)
        return int(length)
    return -1


def change_text_length(string, length):
    index = text_to_index_dict.get(string, -1)
    if index is -1:
        return sub(r"\[\d*\]", "[" + str(length) + "]", string)
    return -1


def check_for_bookmark_mark(string):
    return match(r"\(M\)", string)


def remove_bookmark_mark(string):
    return sub(r"\(M\)", "", string, count=1)
