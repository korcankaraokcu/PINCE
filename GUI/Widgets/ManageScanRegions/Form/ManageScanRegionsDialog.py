# Form implementation generated from reading ui file 'Widgets/ManageScanRegions/Form/ManageScanRegionsDialog.ui'
#
# Created by: PyQt6 UI code generator 6.6.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(724, 568)
        self.gridLayout = QtWidgets.QGridLayout(Dialog)
        self.gridLayout.setObjectName("gridLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(parent=Dialog)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.pushButton_Invert = QtWidgets.QPushButton(parent=Dialog)
        self.pushButton_Invert.setObjectName("pushButton_Invert")
        self.horizontalLayout.addWidget(self.pushButton_Invert)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)
        self.tableWidget_Regions = QScanRegionTable(parent=Dialog)
        font = QtGui.QFont()
        font.setFamily("Monospace")
        self.tableWidget_Regions.setFont(font)
        self.tableWidget_Regions.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableWidget_Regions.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableWidget_Regions.setWordWrap(False)
        self.tableWidget_Regions.setObjectName("tableWidget_Regions")
        self.tableWidget_Regions.setColumnCount(7)
        self.tableWidget_Regions.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_Regions.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_Regions.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_Regions.setHorizontalHeaderItem(2, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_Regions.setHorizontalHeaderItem(3, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_Regions.setHorizontalHeaderItem(4, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_Regions.setHorizontalHeaderItem(5, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_Regions.setHorizontalHeaderItem(6, item)
        self.tableWidget_Regions.horizontalHeader().setStretchLastSection(True)
        self.tableWidget_Regions.verticalHeader().setVisible(False)
        self.tableWidget_Regions.verticalHeader().setDefaultSectionSize(16)
        self.tableWidget_Regions.verticalHeader().setMinimumSectionSize(16)
        self.gridLayout.addWidget(self.tableWidget_Regions, 1, 0, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(parent=Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Cancel|QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 2, 0, 1, 1)

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept) # type: ignore
        self.buttonBox.rejected.connect(Dialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Manage Scan Regions"))
        self.label.setText(_translate("Dialog", "Selected regions will be deleted from the current scan"))
        self.pushButton_Invert.setText(_translate("Dialog", "Invert Selection"))
        self.tableWidget_Regions.setSortingEnabled(True)
        item = self.tableWidget_Regions.horizontalHeaderItem(0)
        item.setText(_translate("Dialog", "ID"))
        item = self.tableWidget_Regions.horizontalHeaderItem(1)
        item.setText(_translate("Dialog", "Start Address"))
        item = self.tableWidget_Regions.horizontalHeaderItem(2)
        item.setText(_translate("Dialog", "Size(bytes)"))
        item = self.tableWidget_Regions.horizontalHeaderItem(3)
        item.setText(_translate("Dialog", "Type"))
        item = self.tableWidget_Regions.horizontalHeaderItem(4)
        item.setText(_translate("Dialog", "Load Address"))
        item = self.tableWidget_Regions.horizontalHeaderItem(5)
        item.setText(_translate("Dialog", "Perms"))
        item = self.tableWidget_Regions.horizontalHeaderItem(6)
        item.setText(_translate("Dialog", "File"))
from GUI.Widgets.ManageScanRegions.ScanRegionTable import QScanRegionTable
