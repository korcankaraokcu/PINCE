#!/usr/bin/python3
from PyQt5.QtWidgets import QDesktopWidget
from re import search, sub, split
import type_defs

COMBOBOX_BYTE = type_defs.COMBOBOX_BYTE
COMBOBOX_2BYTES = type_defs.COMBOBOX_2BYTES
COMBOBOX_4BYTES = type_defs.COMBOBOX_4BYTES
COMBOBOX_8BYTES = type_defs.COMBOBOX_8BYTES
COMBOBOX_FLOAT = type_defs.COMBOBOX_FLOAT
COMBOBOX_DOUBLE = type_defs.COMBOBOX_DOUBLE
COMBOBOX_STRING = type_defs.COMBOBOX_STRING
COMBOBOX_AOB = type_defs.COMBOBOX_AOB

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
    if index is COMBOBOX_STRING:
        returned_string = returned_string + "[" + str(length) + "]"
        if unicode:
            returned_string = returned_string + ",U"
        if not zero_terminate:
            returned_string = returned_string + ",NZT"
    elif index is COMBOBOX_AOB:
        returned_string = returned_string + "[" + str(length) + "]"
    return returned_string


def text_to_valuetype(string):
    length = unicode = zero_terminate = None
    index = text_to_index_dict.get(string, -1)
    if index is -1:
        if search(r"String\[\d*\]", string):  # String[10],U,NZT
            index = COMBOBOX_STRING
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
            index = COMBOBOX_AOB
            length = sub("[^0-9]", "", string)
            length = int(length)
    return index, length, unicode, zero_terminate


def text_to_index(string):
    index = text_to_index_dict.get(string, -1)
    if index is -1:
        if search(r"String", string):  # String[10],U,NZT
            index = COMBOBOX_STRING
        elif search(r"AoB", string):  # AoB[10]
            index = COMBOBOX_AOB
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


def parse_string(string, value_type):
    string = str(string)
    if not string:
        print("please enter a string first")
        return False, string
    try:
        value_type = int(value_type)
    except:
        print(str(value_type) + " can't be converted to int")
        return False, string
    if value_type is COMBOBOX_STRING:
        return True, string
    string = string.strip()
    if value_type is COMBOBOX_AOB:
        try:
            string = str(string)
            stripped_string = string.strip()
            string_list = split(r"\s+", stripped_string)
            for item in string_list:
                if len(item) > 2:
                    print(string + " can't be parsed as array of bytes")
                    return False, string
            hex_list = [int(x, 16) for x in string_list]
            return True, hex_list
        except:
            print(string + " can't be parsed as array of bytes")
            return False, string
    elif value_type is COMBOBOX_FLOAT or value_type is COMBOBOX_DOUBLE:
        try:
            string = float(string)
        except:
            try:
                string = float(int(string, 16))
            except:
                print(string + " can't be parsed as floating point variable")
                return False, string
        return True, string
    else:
        try:
            string = int(string)
        except:
            try:
                string = int(string, 16)
            except:
                try:
                    string = int(float(string))
                except:
                    print(string + " can't be parsed as integer or hexadecimal")
                    return False, string
        if value_type is COMBOBOX_BYTE:
            string = string % 256
        elif value_type is COMBOBOX_2BYTES:
            string = string % 65536
        elif value_type is COMBOBOX_4BYTES:
            string = string % 4294967296
        elif value_type is COMBOBOX_8BYTES:
            string = string % 18446744073709551616
        return True, string
