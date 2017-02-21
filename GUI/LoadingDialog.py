# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'LoadingDialog.ui'
#
# Created: Tue Feb 21 22:38:30 2017
#      by: PyQt5 UI code generator 5.2.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(208, 89)
        self.gridLayout_2 = QtWidgets.QGridLayout(Dialog)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.label_Animated = QtWidgets.QLabel(Dialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_Animated.sizePolicy().hasHeightForWidth())
        self.label_Animated.setSizePolicy(sizePolicy)
        self.label_Animated.setText("")
        self.label_Animated.setScaledContents(False)
        self.label_Animated.setObjectName("label_Animated")
        self.horizontalLayout.addWidget(self.label_Animated)
        self.label_StatusText = QtWidgets.QLabel(Dialog)
        self.label_StatusText.setObjectName("label_StatusText")
        self.horizontalLayout.addWidget(self.label_StatusText)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem1)
        self.gridLayout_2.addLayout(self.horizontalLayout, 0, 0, 1, 1)
        self.widget_Cancel = QtWidgets.QWidget(Dialog)
        self.widget_Cancel.setObjectName("widget_Cancel")
        self.gridLayout = QtWidgets.QGridLayout(self.widget_Cancel)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem2, 0, 0, 1, 1)
        self.pushButton_Cancel = QtWidgets.QPushButton(self.widget_Cancel)
        self.pushButton_Cancel.setObjectName("pushButton_Cancel")
        self.gridLayout.addWidget(self.pushButton_Cancel, 0, 1, 1, 1)
        spacerItem3 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem3, 0, 2, 1, 1)
        self.gridLayout_2.addWidget(self.widget_Cancel, 1, 0, 1, 1)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.label_StatusText.setText(_translate("Dialog", "Processing"))
        self.pushButton_Cancel.setText(_translate("Dialog", "Cancel"))

