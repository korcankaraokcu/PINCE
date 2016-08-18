from GUI.CustomTableViews.HexView import QHexView

class QAsciiView(QHexView):
    # data_array is returned from GDB_Engine.hex_dump()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.horizontalHeader().setDefaultSectionSize(15)
