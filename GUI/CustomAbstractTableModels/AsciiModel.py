from GUI.CustomAbstractTableModels.HexModel import QHexModel

import SysUtils


class QAsciiModel(QHexModel):
    # data_array is returned from GDB_Engine.hex_dump()
    def __init__(self, row_count, column_count, data_array=None, parent=None):
        if data_array is not None:
            SysUtils.aob_to_ascii(data_array)
        super().__init__(row_count, column_count, data_array, parent)

    def refresh(self, new_data_array):
        self.data_array = SysUtils.aob_to_ascii(new_data_array)
