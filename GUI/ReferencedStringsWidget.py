# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ReferencedStringsWidget.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(1025, 530)
        Form.setToolTip("")
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.splitter = QtWidgets.QSplitter(Form)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.layoutWidget = QtWidgets.QWidget(self.splitter)
        self.layoutWidget.setObjectName("layoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.lineEdit_Regex = QtWidgets.QLineEdit(self.layoutWidget)
        self.lineEdit_Regex.setObjectName("lineEdit_Regex")
        self.horizontalLayout_2.addWidget(self.lineEdit_Regex)
        self.checkBox_IgnoreCase = QtWidgets.QCheckBox(self.layoutWidget)
        self.checkBox_IgnoreCase.setChecked(True)
        self.checkBox_IgnoreCase.setObjectName("checkBox_IgnoreCase")
        self.horizontalLayout_2.addWidget(self.checkBox_IgnoreCase)
        self.checkBox_Regex = QtWidgets.QCheckBox(self.layoutWidget)
        self.checkBox_Regex.setObjectName("checkBox_Regex")
        self.horizontalLayout_2.addWidget(self.checkBox_Regex)
        self.pushButton_Search = QtWidgets.QPushButton(self.layoutWidget)
        self.pushButton_Search.setObjectName("pushButton_Search")
        self.horizontalLayout_2.addWidget(self.pushButton_Search)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.tableWidget_References = QtWidgets.QTableWidget(self.layoutWidget)
        self.tableWidget_References.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tableWidget_References.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tableWidget_References.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tableWidget_References.setObjectName("tableWidget_References")
        self.tableWidget_References.setColumnCount(3)
        self.tableWidget_References.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_References.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_References.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_References.setHorizontalHeaderItem(2, item)
        self.tableWidget_References.horizontalHeader().setStretchLastSection(True)
        self.tableWidget_References.verticalHeader().setVisible(False)
        self.tableWidget_References.verticalHeader().setDefaultSectionSize(16)
        self.tableWidget_References.verticalHeader().setMinimumSectionSize(16)
        self.verticalLayout.addWidget(self.tableWidget_References)
        self.listWidget_Referrers = QtWidgets.QListWidget(self.splitter)
        self.listWidget_Referrers.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.listWidget_Referrers.setObjectName("listWidget_Referrers")
        self.gridLayout.addWidget(self.splitter, 0, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Referenced Strings"))
        self.lineEdit_Regex.setPlaceholderText(_translate("Form", "Enter a string or a python-style regex"))
        self.checkBox_IgnoreCase.setToolTip(_translate("Form", "Ignore case if checked"))
        self.checkBox_IgnoreCase.setText(_translate("Form", "Ignore case"))
        self.checkBox_Regex.setToolTip(_translate("Form", "Your string will be treated as a regex if checked"))
        self.checkBox_Regex.setText(_translate("Form", "Regex"))
        self.pushButton_Search.setText(_translate("Form", "Search(Enter)"))
        self.tableWidget_References.setSortingEnabled(True)
        item = self.tableWidget_References.horizontalHeaderItem(0)
        item.setText(_translate("Form", "Address"))
        item = self.tableWidget_References.horizontalHeaderItem(1)
        item.setText(_translate("Form", "Refcount"))
        item = self.tableWidget_References.horizontalHeaderItem(2)
        item.setText(_translate("Form", "Value"))

