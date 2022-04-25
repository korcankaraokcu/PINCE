# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'HandleSignalsDialog.ui'
#
# Created by: PyQt5 UI code generator 5.14.1
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(268, 244)
        self.gridLayout = QtWidgets.QGridLayout(Dialog)
        self.gridLayout.setObjectName("gridLayout")
        self.tableWidget_Signals = QtWidgets.QTableWidget(Dialog)
        self.tableWidget_Signals.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tableWidget_Signals.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tableWidget_Signals.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tableWidget_Signals.setObjectName("tableWidget_Signals")
        self.tableWidget_Signals.setColumnCount(2)
        self.tableWidget_Signals.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_Signals.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_Signals.setHorizontalHeaderItem(1, item)
        self.tableWidget_Signals.horizontalHeader().setStretchLastSection(True)
        self.tableWidget_Signals.verticalHeader().setVisible(False)
        self.tableWidget_Signals.verticalHeader().setDefaultSectionSize(16)
        self.tableWidget_Signals.verticalHeader().setMinimumSectionSize(16)
        self.gridLayout.addWidget(self.tableWidget_Signals, 0, 0, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 1, 0, 1, 1)

        self.retranslateUi(Dialog)
        self.buttonBox.rejected.connect(Dialog.reject)
        self.buttonBox.accepted.connect(Dialog.accept)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Handle Signals"))
        item = self.tableWidget_Signals.horizontalHeaderItem(0)
        item.setText(_translate("Dialog", "Signal"))
        item = self.tableWidget_Signals.horizontalHeaderItem(1)
        item.setText(_translate("Dialog", "Ignore"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Dialog = QtWidgets.QDialog()
    ui = Ui_Dialog()
    ui.setupUi(Dialog)
    Dialog.show()
    sys.exit(app.exec_())
