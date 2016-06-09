# represents the index of columns in address table
FROZEN_COL = 0  # Frozen
DESC_COL = 1  # Description
ADDR_COL = 2  # Address
TYPE_COL = 3  # Type
VALUE_COL = 4  # Value

# represents the index of valuetype combobox
# any change at indexes may require rework on the dictionaries located at GuiUtils, GDB_Engine and ScriptUtils
COMBOBOX_BYTE = 0
COMBOBOX_2BYTES = 1
COMBOBOX_4BYTES = 2
COMBOBOX_8BYTES = 3
COMBOBOX_FLOAT = 4
COMBOBOX_DOUBLE = 5
COMBOBOX_STRING = 6
COMBOBOX_AOB = 7  # Array of Bytes