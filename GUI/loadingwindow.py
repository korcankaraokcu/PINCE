# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'loadingwindow.ui'
#
# Created: Mon May  9 01:23:45 2016
#      by: PyQt5 UI code generator 5.2.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.setWindowModality(QtCore.Qt.WindowModal)
        Dialog.resize(94, 34)
        Dialog.setModal(True)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(Dialog)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label_Animated = QtWidgets.QLabel(Dialog)
        self.label_Animated.setText("")
        self.label_Animated.setObjectName("label_Animated")
        self.horizontalLayout.addWidget(self.label_Animated)
        self.label_StatusText = QtWidgets.QLabel(Dialog)
        self.label_StatusText.setText("")
        self.label_StatusText.setObjectName("label_StatusText")
        self.horizontalLayout.addWidget(self.label_StatusText)
        self.horizontalLayout_2.addLayout(self.horizontalLayout)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))

