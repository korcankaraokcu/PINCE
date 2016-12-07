# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'TrackWatchpointWidget.ui'
#
# Created: Fri Dec  2 21:30:54 2016
#      by: PyQt5 UI code generator 5.2.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(530, 493)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.splitter_2 = QtWidgets.QSplitter(Form)
        self.splitter_2.setOrientation(QtCore.Qt.Vertical)
        self.splitter_2.setObjectName("splitter_2")
        self.splitter = QtWidgets.QSplitter(self.splitter_2)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.layoutWidget = QtWidgets.QWidget(self.splitter)
        self.layoutWidget.setObjectName("layoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.tableWidget_Opcodes = QtWidgets.QTableWidget(self.layoutWidget)
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
        self.verticalLayout.addWidget(self.tableWidget_Opcodes)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.pushButton_Refresh = QtWidgets.QPushButton(self.layoutWidget)
        self.pushButton_Refresh.setObjectName("pushButton_Refresh")
        self.horizontalLayout.addWidget(self.pushButton_Refresh)
        self.pushButton_Stop = QtWidgets.QPushButton(self.layoutWidget)
        self.pushButton_Stop.setObjectName("pushButton_Stop")
        self.horizontalLayout.addWidget(self.pushButton_Stop)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.textBrowser_Info = QtWidgets.QTextBrowser(self.splitter)
        self.textBrowser_Info.setObjectName("textBrowser_Info")
        self.textBrowser_Disassemble = QtWidgets.QTextBrowser(self.splitter_2)
        self.textBrowser_Disassemble.setObjectName("textBrowser_Disassemble")
        self.gridLayout.addWidget(self.splitter_2, 0, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        item = self.tableWidget_Opcodes.horizontalHeaderItem(0)
        item.setText(_translate("Form", "Count"))
        item = self.tableWidget_Opcodes.horizontalHeaderItem(1)
        item.setText(_translate("Form", "Address"))
        self.pushButton_Refresh.setText(_translate("Form", "Refresh"))
        self.pushButton_Stop.setText(_translate("Form", "Stop"))

