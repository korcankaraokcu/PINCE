# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'HexEditDialog.ui'
#
# Created by: PyQt5 UI code generator 5.8
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(515, 138)
        self.gridLayout = QtWidgets.QGridLayout(Dialog)
        self.gridLayout.setObjectName("gridLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.lineEdit_Address = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_Address.setObjectName("lineEdit_Address")
        self.horizontalLayout.addWidget(self.lineEdit_Address)
        self.label_2 = QtWidgets.QLabel(Dialog)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout.addWidget(self.label_2)
        self.lineEdit_Length = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_Length.setObjectName("lineEdit_Length")
        self.horizontalLayout.addWidget(self.lineEdit_Length)
        self.pushButton_Refresh = QtWidgets.QPushButton(Dialog)
        self.pushButton_Refresh.setObjectName("pushButton_Refresh")
        self.horizontalLayout.addWidget(self.pushButton_Refresh)
        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)
        self.lineEdit_AsciiView = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_AsciiView.setObjectName("lineEdit_AsciiView")
        self.gridLayout.addWidget(self.lineEdit_AsciiView, 1, 0, 1, 1)
        self.lineEdit_HexView = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_HexView.setObjectName("lineEdit_HexView")
        self.gridLayout.addWidget(self.lineEdit_HexView, 2, 0, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 3, 0, 1, 1)

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Hex Edit"))
        self.label.setText(_translate("Dialog", "Address:"))
        self.label_2.setText(_translate("Dialog", "Length:"))
        self.pushButton_Refresh.setText(_translate("Dialog", "Refresh"))

