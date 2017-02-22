# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'SearchOpcodeWidget.ui'
#
# Created by: PyQt5 UI code generator 5.8
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(631, 490)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label_3 = QtWidgets.QLabel(Form)
        self.label_3.setObjectName("label_3")
        self.horizontalLayout_2.addWidget(self.label_3)
        self.lineEdit_Regex = QtWidgets.QLineEdit(Form)
        self.lineEdit_Regex.setObjectName("lineEdit_Regex")
        self.horizontalLayout_2.addWidget(self.lineEdit_Regex)
        self.pushButton_Search = QtWidgets.QPushButton(Form)
        self.pushButton_Search.setObjectName("pushButton_Search")
        self.horizontalLayout_2.addWidget(self.pushButton_Search)
        self.pushButton_Help = QtWidgets.QPushButton(Form)
        self.pushButton_Help.setText("")
        self.pushButton_Help.setObjectName("pushButton_Help")
        self.horizontalLayout_2.addWidget(self.pushButton_Help)
        self.gridLayout.addLayout(self.horizontalLayout_2, 0, 0, 1, 1)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(Form)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.lineEdit_Start = QtWidgets.QLineEdit(Form)
        self.lineEdit_Start.setObjectName("lineEdit_Start")
        self.horizontalLayout.addWidget(self.lineEdit_Start)
        self.label_2 = QtWidgets.QLabel(Form)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout.addWidget(self.label_2)
        self.lineEdit_End = QtWidgets.QLineEdit(Form)
        self.lineEdit_End.setObjectName("lineEdit_End")
        self.horizontalLayout.addWidget(self.lineEdit_End)
        self.gridLayout.addLayout(self.horizontalLayout, 1, 0, 1, 1)
        self.tableWidget_Opcodes = QtWidgets.QTableWidget(Form)
        self.tableWidget_Opcodes.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tableWidget_Opcodes.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tableWidget_Opcodes.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tableWidget_Opcodes.setObjectName("tableWidget_Opcodes")
        self.tableWidget_Opcodes.setColumnCount(2)
        self.tableWidget_Opcodes.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_Opcodes.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_Opcodes.setHorizontalHeaderItem(1, item)
        self.tableWidget_Opcodes.horizontalHeader().setStretchLastSection(True)
        self.tableWidget_Opcodes.verticalHeader().setVisible(False)
        self.tableWidget_Opcodes.verticalHeader().setDefaultSectionSize(16)
        self.tableWidget_Opcodes.verticalHeader().setMinimumSectionSize(16)
        self.gridLayout.addWidget(self.tableWidget_Opcodes, 2, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Search for Opcodes"))
        self.label_3.setText(_translate("Form", "Regex"))
        self.lineEdit_Regex.setPlaceholderText(_translate("Form", "Enter a python-style regular expression"))
        self.pushButton_Search.setText(_translate("Form", "Search(Enter)"))
        self.label.setText(_translate("Form", "Start"))
        self.label_2.setText(_translate("Form", "End"))
        item = self.tableWidget_Opcodes.horizontalHeaderItem(0)
        item.setText(_translate("Form", "Address"))
        item = self.tableWidget_Opcodes.horizontalHeaderItem(1)
        item.setText(_translate("Form", "Opcodes"))

