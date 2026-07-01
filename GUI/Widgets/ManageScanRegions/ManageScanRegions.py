from PyQt6.QtWidgets import QDialog, QTableWidgetItem, QWidget
from PyQt6.QtCore import Qt
from GUI.Widgets.ManageScanRegions.Form.ManageScanRegionsDialog import Ui_Dialog
from GUI.Utils import guiutils
from libpince import scancore, typedefs


class ManageScanRegionsDialog(QDialog, Ui_Dialog):
    def __init__(self, parent: QWidget, scan_mode: int) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.deleted_regions: list[int] = []
        self.regions_reset = False
        self.populate_table()
        guiutils.center_to_parent(self)
        self.pushButton_Invert.clicked.connect(self.invert_selection)
        self.pushButton_Reset.clicked.connect(self.reset_regions)
        # Restoring deleted regions reloads them from the process, which only makes sense before the first
        # scan (a fresh session). Once a scan is ongoing the deleted regions' matches are already gone and
        # reloading would silently wipe the scan, so the button stays disabled until a new scan is started.
        self.pushButton_Reset.setEnabled(scan_mode == typedefs.SCAN_MODE.NEW)

    def populate_table(self) -> None:
        regions = list(scancore.memscan.regions())
        self.tableWidget_Regions.setRowCount(len(regions))
        self.tableWidget_Regions.setSortingEnabled(False)
        for row, region in enumerate(regions):
            region_id, start_address, size, region_type, load_address, perms, file = region.as_text_fields()
            id_item = QTableWidgetItem(region_id)
            id_item.setCheckState(Qt.CheckState.Unchecked)
            self.tableWidget_Regions.setItem(row, 0, id_item)
            self.tableWidget_Regions.setItem(row, 1, QTableWidgetItem(start_address))
            self.tableWidget_Regions.setItem(row, 2, QTableWidgetItem(size))
            self.tableWidget_Regions.setItem(row, 3, QTableWidgetItem(region_type))
            self.tableWidget_Regions.setItem(row, 4, QTableWidgetItem(load_address))
            self.tableWidget_Regions.setItem(row, 5, QTableWidgetItem(perms))
            self.tableWidget_Regions.setItem(row, 6, QTableWidgetItem(file))
        self.tableWidget_Regions.setSortingEnabled(True)
        self.tableWidget_Regions.resizeColumnsToContents()

    def reset_regions(self) -> None:
        scancore.memscan.reset()
        self.regions_reset = True
        self.deleted_regions.clear()
        self.populate_table()

    def invert_selection(self) -> None:
        for row in range(self.tableWidget_Regions.rowCount()):
            item = self.tableWidget_Regions.item(row, 0)
            cur_state = item.checkState()
            new_state = Qt.CheckState.Unchecked if cur_state == Qt.CheckState.Checked else Qt.CheckState.Checked
            item.setCheckState(new_state)

    def get_values(self) -> list[int]:
        return self.deleted_regions

    def accept(self) -> None:
        for row in range(self.tableWidget_Regions.rowCount()):
            item = self.tableWidget_Regions.item(row, 0)
            if item.checkState() == Qt.CheckState.Checked:
                region_id = int(item.text())
                self.deleted_regions.append(region_id)
                scancore.memscan.remove_region_by_id(int(region_id))
        return super().accept()
