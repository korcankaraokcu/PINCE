from PyQt6.QtWidgets import QDialog, QTableWidgetItem
from PyQt6.QtCore import Qt
from GUI.ManageScanRegions.Form.ManageScanRegionsDialog import Ui_Dialog as ManageScanRegionsForm
from GUI.Utils import guiutils
from libpince import debugcore
import re


class ManageScanRegionsDialog(QDialog, ManageScanRegionsForm):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.deleted_regions: list[int] = []
        regions_text = debugcore.scanmem.send_command("lregions", True).decode("utf-8")
        regex = re.compile(r"\[\s*(\d+)\] (\w+),\s+(\d+) bytes,\s+(\w+),\s+(\w+),\s+([rwx-]+),\s+(.+)")
        data = regex.findall(regions_text)
        self.tableWidget_Regions.setRowCount(len(data))
        for row, (region_id, start_address, size, region_type, load_address, perms, file) in enumerate(data):
            id_item = QTableWidgetItem(region_id)
            id_item.setCheckState(Qt.CheckState.Unchecked)
            self.tableWidget_Regions.setItem(row, 0, id_item)
            self.tableWidget_Regions.setItem(row, 1, QTableWidgetItem(start_address))
            self.tableWidget_Regions.setItem(row, 2, QTableWidgetItem(size))
            self.tableWidget_Regions.setItem(row, 3, QTableWidgetItem(region_type))
            self.tableWidget_Regions.setItem(row, 4, QTableWidgetItem(load_address))
            self.tableWidget_Regions.setItem(row, 5, QTableWidgetItem(perms))
            self.tableWidget_Regions.setItem(row, 6, QTableWidgetItem(file))
        self.tableWidget_Regions.resizeColumnsToContents()
        guiutils.center_to_parent(self)
        self.pushButton_Invert.clicked.connect(self.invert_selection)

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
                debugcore.scanmem.send_command(f"dregion {region_id}")
        return super().accept()
