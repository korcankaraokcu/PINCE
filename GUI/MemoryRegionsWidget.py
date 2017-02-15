# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'MemoryRegionsWidget.ui'
#
# Created: Wed Feb 15 17:56:42 2017
#      by: PyQt5 UI code generator 5.2.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(684, 539)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.tableWidget_MemoryRegions = QtWidgets.QTableWidget(Form)
        self.tableWidget_MemoryRegions.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tableWidget_MemoryRegions.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tableWidget_MemoryRegions.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tableWidget_MemoryRegions.setObjectName("tableWidget_MemoryRegions")
        self.tableWidget_MemoryRegions.setColumnCount(13)
        self.tableWidget_MemoryRegions.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_MemoryRegions.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_MemoryRegions.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_MemoryRegions.setHorizontalHeaderItem(2, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_MemoryRegions.setHorizontalHeaderItem(3, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_MemoryRegions.setHorizontalHeaderItem(4, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_MemoryRegions.setHorizontalHeaderItem(5, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_MemoryRegions.setHorizontalHeaderItem(6, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_MemoryRegions.setHorizontalHeaderItem(7, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_MemoryRegions.setHorizontalHeaderItem(8, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_MemoryRegions.setHorizontalHeaderItem(9, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_MemoryRegions.setHorizontalHeaderItem(10, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_MemoryRegions.setHorizontalHeaderItem(11, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_MemoryRegions.setHorizontalHeaderItem(12, item)
        self.tableWidget_MemoryRegions.horizontalHeader().setStretchLastSection(True)
        self.tableWidget_MemoryRegions.verticalHeader().setVisible(False)
        self.tableWidget_MemoryRegions.verticalHeader().setDefaultSectionSize(16)
        self.tableWidget_MemoryRegions.verticalHeader().setMinimumSectionSize(16)
        self.gridLayout.addWidget(self.tableWidget_MemoryRegions, 0, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Memory Regions"))
        self.tableWidget_MemoryRegions.setSortingEnabled(True)
        item = self.tableWidget_MemoryRegions.horizontalHeaderItem(0)
        item.setText(_translate("Form", "Address"))
        item = self.tableWidget_MemoryRegions.horizontalHeaderItem(1)
        item.setText(_translate("Form", "Perms"))
        item = self.tableWidget_MemoryRegions.horizontalHeaderItem(2)
        item.setText(_translate("Form", "Size"))
        item = self.tableWidget_MemoryRegions.horizontalHeaderItem(3)
        item.setText(_translate("Form", "Path"))
        item = self.tableWidget_MemoryRegions.horizontalHeaderItem(4)
        item.setText(_translate("Form", "RSS"))
        item = self.tableWidget_MemoryRegions.horizontalHeaderItem(5)
        item.setText(_translate("Form", "PSS"))
        item = self.tableWidget_MemoryRegions.horizontalHeaderItem(6)
        item.setText(_translate("Form", "Shared_Clean"))
        item = self.tableWidget_MemoryRegions.horizontalHeaderItem(7)
        item.setText(_translate("Form", "Shared_Dirty"))
        item = self.tableWidget_MemoryRegions.horizontalHeaderItem(8)
        item.setText(_translate("Form", "Private_Clean"))
        item = self.tableWidget_MemoryRegions.horizontalHeaderItem(9)
        item.setText(_translate("Form", "Private_Dirty"))
        item = self.tableWidget_MemoryRegions.horizontalHeaderItem(10)
        item.setText(_translate("Form", "Referenced"))
        item = self.tableWidget_MemoryRegions.horizontalHeaderItem(11)
        item.setText(_translate("Form", "Anonymous"))
        item = self.tableWidget_MemoryRegions.horizontalHeaderItem(12)
        item.setText(_translate("Form", "Swap"))

