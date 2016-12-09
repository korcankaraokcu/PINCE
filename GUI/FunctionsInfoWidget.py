# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'FunctionsInfoWidget.ui'
#
# Created: Fri Dec  9 14:18:45 2016
#      by: PyQt5 UI code generator 5.2.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(640, 555)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.tableWidget_SymbolInfo = QtWidgets.QTableWidget(Form)
        self.tableWidget_SymbolInfo.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tableWidget_SymbolInfo.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tableWidget_SymbolInfo.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tableWidget_SymbolInfo.setObjectName("tableWidget_SymbolInfo")
        self.tableWidget_SymbolInfo.setColumnCount(2)
        self.tableWidget_SymbolInfo.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_SymbolInfo.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_SymbolInfo.setHorizontalHeaderItem(1, item)
        self.tableWidget_SymbolInfo.horizontalHeader().setStretchLastSection(True)
        self.tableWidget_SymbolInfo.verticalHeader().setVisible(False)
        self.tableWidget_SymbolInfo.verticalHeader().setDefaultSectionSize(20)
        self.tableWidget_SymbolInfo.verticalHeader().setMinimumSectionSize(20)
        self.gridLayout.addWidget(self.tableWidget_SymbolInfo, 2, 0, 1, 1)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.lineEdit_SearchInput = QtWidgets.QLineEdit(Form)
        self.lineEdit_SearchInput.setObjectName("lineEdit_SearchInput")
        self.horizontalLayout.addWidget(self.lineEdit_SearchInput)
        self.pushButton_Search = QtWidgets.QPushButton(Form)
        self.pushButton_Search.setObjectName("pushButton_Search")
        self.horizontalLayout.addWidget(self.pushButton_Search)
        self.pushButton_Help = QtWidgets.QPushButton(Form)
        self.pushButton_Help.setText("")
        self.pushButton_Help.setObjectName("pushButton_Help")
        self.horizontalLayout.addWidget(self.pushButton_Help)
        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)
        self.textBrowser_AddressInfo = QtWidgets.QTextBrowser(Form)
        self.textBrowser_AddressInfo.setObjectName("textBrowser_AddressInfo")
        self.gridLayout.addWidget(self.textBrowser_AddressInfo, 1, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Functions"))
        item = self.tableWidget_SymbolInfo.horizontalHeaderItem(0)
        item.setText(_translate("Form", "Address"))
        item = self.tableWidget_SymbolInfo.horizontalHeaderItem(1)
        item.setText(_translate("Form", "Symbol"))
        self.lineEdit_SearchInput.setPlaceholderText(_translate("Form", "Enter the regex. Leave blank to see all functions"))
        self.pushButton_Search.setText(_translate("Form", "Search(Enter)"))

