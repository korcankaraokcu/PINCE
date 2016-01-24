# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'selectprocess.ui'
#
# Created: Sun Jan 24 16:54:05 2016
#      by: PyQt5 UI code generator 5.2.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.setWindowModality(QtCore.Qt.WindowModal)
        MainWindow.resize(597, 340)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.formLayout = QtWidgets.QFormLayout(self.centralwidget)
        self.formLayout.setObjectName("formLayout")
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setObjectName("label")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label)
        self.lineEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.lineEdit.setObjectName("lineEdit")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.lineEdit)
        self.processtable = QtWidgets.QTableWidget(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.processtable.sizePolicy().hasHeightForWidth())
        self.processtable.setSizePolicy(sizePolicy)
        self.processtable.setMinimumSize(QtCore.QSize(579, 292))
        self.processtable.setMaximumSize(QtCore.QSize(579, 292))
        self.processtable.setAutoFillBackground(False)
        self.processtable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustIgnored)
        self.processtable.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.processtable.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.processtable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.processtable.setObjectName("processtable")
        self.processtable.setColumnCount(3)
        self.processtable.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.processtable.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.processtable.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignVCenter)
        self.processtable.setHorizontalHeaderItem(2, item)
        self.processtable.horizontalHeader().setDefaultSectionSize(70)
        self.processtable.horizontalHeader().setStretchLastSection(True)
        self.processtable.verticalHeader().setVisible(False)
        self.processtable.verticalHeader().setStretchLastSection(False)
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.SpanningRole, self.processtable)
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.label.setText(_translate("MainWindow", "Name of the Process:"))
        self.processtable.setSortingEnabled(True)
        item = self.processtable.horizontalHeaderItem(0)
        item.setText(_translate("MainWindow", "PID"))
        item = self.processtable.horizontalHeaderItem(1)
        item.setText(_translate("MainWindow", "Username"))
        item = self.processtable.horizontalHeaderItem(2)
        item.setText(_translate("MainWindow", "Process Name"))

