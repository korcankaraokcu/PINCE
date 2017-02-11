# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'LogFileWidget.ui'
#
# Created: Sat Feb 11 01:51:44 2017
#      by: PyQt5 UI code generator 5.2.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(582, 558)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.label_FilePath = QtWidgets.QLabel(Form)
        self.label_FilePath.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextSelectableByMouse)
        self.label_FilePath.setObjectName("label_FilePath")
        self.gridLayout.addWidget(self.label_FilePath, 0, 0, 1, 1)
        self.textBrowser_LogContent = QtWidgets.QTextBrowser(Form)
        self.textBrowser_LogContent.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        self.textBrowser_LogContent.setObjectName("textBrowser_LogContent")
        self.gridLayout.addWidget(self.textBrowser_LogContent, 1, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.label_FilePath.setText(_translate("Form", "TextLabel"))

