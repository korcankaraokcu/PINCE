# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'FloatRegisterWidget.ui'
#
# Created by: PyQt5 UI code generator 5.8
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_TabWidget(object):
    def setupUi(self, TabWidget):
        TabWidget.setObjectName("TabWidget")
        TabWidget.resize(400, 300)
        self.FPU = QtWidgets.QWidget()
        self.FPU.setObjectName("FPU")
        self.gridLayout = QtWidgets.QGridLayout(self.FPU)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.tableWidget_FPU = QtWidgets.QTableWidget(self.FPU)
        self.tableWidget_FPU.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tableWidget_FPU.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tableWidget_FPU.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tableWidget_FPU.setObjectName("tableWidget_FPU")
        self.tableWidget_FPU.setColumnCount(2)
        self.tableWidget_FPU.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_FPU.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_FPU.setHorizontalHeaderItem(1, item)
        self.tableWidget_FPU.horizontalHeader().setStretchLastSection(True)
        self.tableWidget_FPU.verticalHeader().setVisible(False)
        self.gridLayout.addWidget(self.tableWidget_FPU, 0, 0, 1, 1)
        TabWidget.addTab(self.FPU, "")
        self.XMM = QtWidgets.QWidget()
        self.XMM.setObjectName("XMM")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.XMM)
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.tableWidget_XMM = QtWidgets.QTableWidget(self.XMM)
        self.tableWidget_XMM.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tableWidget_XMM.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tableWidget_XMM.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tableWidget_XMM.setObjectName("tableWidget_XMM")
        self.tableWidget_XMM.setColumnCount(2)
        self.tableWidget_XMM.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_XMM.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_XMM.setHorizontalHeaderItem(1, item)
        self.tableWidget_XMM.horizontalHeader().setStretchLastSection(True)
        self.tableWidget_XMM.verticalHeader().setVisible(False)
        self.gridLayout_2.addWidget(self.tableWidget_XMM, 0, 0, 1, 1)
        TabWidget.addTab(self.XMM, "")

        self.retranslateUi(TabWidget)
        TabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(TabWidget)

    def retranslateUi(self, TabWidget):
        _translate = QtCore.QCoreApplication.translate
        TabWidget.setWindowTitle(_translate("TabWidget", "Floating Point Registers"))
        item = self.tableWidget_FPU.horizontalHeaderItem(0)
        item.setText(_translate("TabWidget", "Register"))
        item = self.tableWidget_FPU.horizontalHeaderItem(1)
        item.setText(_translate("TabWidget", "Value"))
        TabWidget.setTabText(TabWidget.indexOf(self.FPU), _translate("TabWidget", "FPU"))
        item = self.tableWidget_XMM.horizontalHeaderItem(0)
        item.setText(_translate("TabWidget", "Register"))
        item = self.tableWidget_XMM.horizontalHeaderItem(1)
        item.setText(_translate("TabWidget", "Value"))
        TabWidget.setTabText(TabWidget.indexOf(self.XMM), _translate("TabWidget", "XMM"))

