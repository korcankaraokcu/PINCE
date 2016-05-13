# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'loadingwidget.ui'
#
# Created: Fri May 13 03:12:03 2016
#      by: PyQt5 UI code generator 5.2.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.setWindowModality(QtCore.Qt.WindowModal)
        Form.resize(447, 300)
        Form.setCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        Form.setWindowTitle("")
        Form.setAutoFillBackground(True)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(Form)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.label_Animated = QtWidgets.QLabel(Form)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_Animated.sizePolicy().hasHeightForWidth())
        self.label_Animated.setSizePolicy(sizePolicy)
        self.label_Animated.setText("")
        self.label_Animated.setScaledContents(False)
        self.label_Animated.setObjectName("label_Animated")
        self.horizontalLayout.addWidget(self.label_Animated)
        self.label_StatusText = QtWidgets.QLabel(Form)
        self.label_StatusText.setObjectName("label_StatusText")
        self.horizontalLayout.addWidget(self.label_StatusText)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem1)
        self.horizontalLayout_2.addLayout(self.horizontalLayout)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        self.label_StatusText.setText(_translate("Form", "Processing"))

