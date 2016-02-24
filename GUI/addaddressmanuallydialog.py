# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'addaddressmanuallydialog.ui'
#
# Created: Sat Feb 20 17:58:12 2016
#      by: PyQt5 UI code generator 5.2.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(188, 77)
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox.setGeometry(QtCore.QRect(-160, 40, 341, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setGeometry(QtCore.QRect(10, 10, 54, 15))
        self.label.setObjectName("label")
        self.lineEdit_addaddressmanually = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_addaddressmanually.setGeometry(QtCore.QRect(60, 10, 113, 23))
        self.lineEdit_addaddressmanually.setObjectName("lineEdit_addaddressmanually")

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", " "))
        self.label.setText(_translate("Dialog", "Address"))
        self.lineEdit_addaddressmanually.setText(_translate("Dialog", "0x"))

