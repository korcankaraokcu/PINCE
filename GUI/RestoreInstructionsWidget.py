# Form implementation generated from reading ui file 'RestoreInstructionsWidget.ui'
#
# Created by: PyQt6 UI code generator 6.5.1
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(400, 400)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.tableWidget_Instructions = QtWidgets.QTableWidget(parent=Form)
        self.tableWidget_Instructions.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableWidget_Instructions.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tableWidget_Instructions.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableWidget_Instructions.setWordWrap(False)
        self.tableWidget_Instructions.setObjectName("tableWidget_Instructions")
        self.tableWidget_Instructions.setColumnCount(3)
        self.tableWidget_Instructions.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_Instructions.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_Instructions.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_Instructions.setHorizontalHeaderItem(2, item)
        self.tableWidget_Instructions.horizontalHeader().setStretchLastSection(True)
        self.tableWidget_Instructions.verticalHeader().setVisible(False)
        self.tableWidget_Instructions.verticalHeader().setDefaultSectionSize(16)
        self.tableWidget_Instructions.verticalHeader().setMinimumSectionSize(16)
        self.gridLayout.addWidget(self.tableWidget_Instructions, 0, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Restore Instructions"))
        self.tableWidget_Instructions.setSortingEnabled(True)
        item = self.tableWidget_Instructions.horizontalHeaderItem(0)
        item.setText(_translate("Form", "Address"))
        item = self.tableWidget_Instructions.horizontalHeaderItem(1)
        item.setText(_translate("Form", "Original OpCode"))
        item = self.tableWidget_Instructions.horizontalHeaderItem(2)
        item.setText(_translate("Form", "Original Instruction"))
