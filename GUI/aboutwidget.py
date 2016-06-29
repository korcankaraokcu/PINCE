# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'aboutwidget.ui'
#
# Created: Wed Jun 29 16:34:26 2016
#      by: PyQt5 UI code generator 5.2.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_TabWidget(object):
    def setupUi(self, TabWidget):
        TabWidget.setObjectName("TabWidget")
        TabWidget.resize(721, 659)
        self.tab_Contributors = QtWidgets.QWidget()
        self.tab_Contributors.setObjectName("tab_Contributors")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.tab_Contributors)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.textBrowser_Contributors = QtWidgets.QTextBrowser(self.tab_Contributors)
        self.textBrowser_Contributors.setObjectName("textBrowser_Contributors")
        self.gridLayout_2.addWidget(self.textBrowser_Contributors, 0, 0, 1, 1)
        TabWidget.addTab(self.tab_Contributors, "")
        self.tab_License = QtWidgets.QWidget()
        self.tab_License.setObjectName("tab_License")
        self.gridLayout = QtWidgets.QGridLayout(self.tab_License)
        self.gridLayout.setObjectName("gridLayout")
        self.textBrowser_License = QtWidgets.QTextBrowser(self.tab_License)
        self.textBrowser_License.setObjectName("textBrowser_License")
        self.gridLayout.addWidget(self.textBrowser_License, 0, 0, 1, 1)
        TabWidget.addTab(self.tab_License, "")

        self.retranslateUi(TabWidget)
        TabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(TabWidget)

    def retranslateUi(self, TabWidget):
        _translate = QtCore.QCoreApplication.translate
        TabWidget.setWindowTitle(_translate("TabWidget", "About PINCE"))
        TabWidget.setTabText(TabWidget.indexOf(self.tab_Contributors), _translate("TabWidget", "Contributors"))
        TabWidget.setTabText(TabWidget.indexOf(self.tab_License), _translate("TabWidget", "License"))

