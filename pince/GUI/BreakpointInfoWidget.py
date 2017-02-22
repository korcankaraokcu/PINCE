# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'BreakpointInfoWidget.ui'
#
# Created by: PyQt5 UI code generator 5.8
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_TabWidget(object):
    def setupUi(self, TabWidget):
        TabWidget.setObjectName("TabWidget")
        TabWidget.resize(659, 496)
        self.tab_BreakpointInfo = QtWidgets.QWidget()
        self.tab_BreakpointInfo.setObjectName("tab_BreakpointInfo")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.tab_BreakpointInfo)
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.tableWidget_BreakpointInfo = QtWidgets.QTableWidget(self.tab_BreakpointInfo)
        self.tableWidget_BreakpointInfo.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tableWidget_BreakpointInfo.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tableWidget_BreakpointInfo.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tableWidget_BreakpointInfo.setObjectName("tableWidget_BreakpointInfo")
        self.tableWidget_BreakpointInfo.setColumnCount(6)
        self.tableWidget_BreakpointInfo.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_BreakpointInfo.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_BreakpointInfo.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_BreakpointInfo.setHorizontalHeaderItem(2, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_BreakpointInfo.setHorizontalHeaderItem(3, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_BreakpointInfo.setHorizontalHeaderItem(4, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_BreakpointInfo.setHorizontalHeaderItem(5, item)
        self.tableWidget_BreakpointInfo.horizontalHeader().setStretchLastSection(True)
        self.tableWidget_BreakpointInfo.verticalHeader().setVisible(False)
        self.tableWidget_BreakpointInfo.verticalHeader().setDefaultSectionSize(16)
        self.tableWidget_BreakpointInfo.verticalHeader().setMinimumSectionSize(16)
        self.gridLayout_2.addWidget(self.tableWidget_BreakpointInfo, 0, 0, 1, 1)
        TabWidget.addTab(self.tab_BreakpointInfo, "")
        self.tab_RawBreakpointInfo = QtWidgets.QWidget()
        self.tab_RawBreakpointInfo.setObjectName("tab_RawBreakpointInfo")
        self.gridLayout = QtWidgets.QGridLayout(self.tab_RawBreakpointInfo)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.textBrowser_BreakpointInfo = QtWidgets.QTextBrowser(self.tab_RawBreakpointInfo)
        self.textBrowser_BreakpointInfo.setObjectName("textBrowser_BreakpointInfo")
        self.gridLayout.addWidget(self.textBrowser_BreakpointInfo, 0, 0, 1, 1)
        TabWidget.addTab(self.tab_RawBreakpointInfo, "")

        self.retranslateUi(TabWidget)
        TabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(TabWidget)

    def retranslateUi(self, TabWidget):
        _translate = QtCore.QCoreApplication.translate
        TabWidget.setWindowTitle(_translate("TabWidget", "Breakpoints"))
        item = self.tableWidget_BreakpointInfo.horizontalHeaderItem(0)
        item.setText(_translate("TabWidget", "No"))
        item = self.tableWidget_BreakpointInfo.horizontalHeaderItem(1)
        item.setText(_translate("TabWidget", "Address"))
        item = self.tableWidget_BreakpointInfo.horizontalHeaderItem(2)
        item.setText(_translate("TabWidget", "Type"))
        item = self.tableWidget_BreakpointInfo.horizontalHeaderItem(3)
        item.setText(_translate("TabWidget", "Size"))
        item = self.tableWidget_BreakpointInfo.horizontalHeaderItem(4)
        item.setText(_translate("TabWidget", "On Hit"))
        item = self.tableWidget_BreakpointInfo.horizontalHeaderItem(5)
        item.setText(_translate("TabWidget", "Condition"))
        TabWidget.setTabText(TabWidget.indexOf(self.tab_BreakpointInfo), _translate("TabWidget", "Interactive"))
        TabWidget.setTabText(TabWidget.indexOf(self.tab_RawBreakpointInfo), _translate("TabWidget", "Raw"))

