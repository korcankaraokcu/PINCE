# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ReferencedStringsWidget.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(505, 434)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.splitter = QtWidgets.QSplitter(Form)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.tableWidget_References = QtWidgets.QTableWidget(self.splitter)
        self.tableWidget_References.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tableWidget_References.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tableWidget_References.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tableWidget_References.setObjectName("tableWidget_References")
        self.tableWidget_References.setColumnCount(3)
        self.tableWidget_References.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_References.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_References.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_References.setHorizontalHeaderItem(2, item)
        self.tableWidget_References.horizontalHeader().setStretchLastSection(True)
        self.tableWidget_References.verticalHeader().setVisible(False)
        self.tableWidget_References.verticalHeader().setDefaultSectionSize(16)
        self.tableWidget_References.verticalHeader().setMinimumSectionSize(16)
        self.listWidget_Referrers = QtWidgets.QListWidget(self.splitter)
        self.listWidget_Referrers.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.listWidget_Referrers.setObjectName("listWidget_Referrers")
        self.gridLayout.addWidget(self.splitter, 0, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Referenced Strings"))
        self.tableWidget_References.setSortingEnabled(True)
        item = self.tableWidget_References.horizontalHeaderItem(0)
        item.setText(_translate("Form", "Address"))
        item = self.tableWidget_References.horizontalHeaderItem(1)
        item.setText(_translate("Form", "Refcount"))
        item = self.tableWidget_References.horizontalHeaderItem(2)
        item.setText(_translate("Form", "Value"))

