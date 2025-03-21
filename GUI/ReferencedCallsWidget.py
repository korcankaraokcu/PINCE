# Form implementation generated from reading ui file 'ReferencedCallsWidget.ui'
#
# Created by: PyQt6 UI code generator 6.6.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(1025, 530)
        Form.setToolTip("")
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.splitter = QtWidgets.QSplitter(parent=Form)
        self.splitter.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.splitter.setObjectName("splitter")
        self.layoutWidget = QtWidgets.QWidget(parent=self.splitter)
        self.layoutWidget.setObjectName("layoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.lineEdit_Regex = QtWidgets.QLineEdit(parent=self.layoutWidget)
        self.lineEdit_Regex.setObjectName("lineEdit_Regex")
        self.horizontalLayout_2.addWidget(self.lineEdit_Regex)
        self.checkBox_CaseSensitive = QtWidgets.QCheckBox(parent=self.layoutWidget)
        self.checkBox_CaseSensitive.setObjectName("checkBox_CaseSensitive")
        self.horizontalLayout_2.addWidget(self.checkBox_CaseSensitive)
        self.checkBox_Regex = QtWidgets.QCheckBox(parent=self.layoutWidget)
        self.checkBox_Regex.setObjectName("checkBox_Regex")
        self.horizontalLayout_2.addWidget(self.checkBox_Regex)
        self.pushButton_Search = QtWidgets.QPushButton(parent=self.layoutWidget)
        self.pushButton_Search.setObjectName("pushButton_Search")
        self.horizontalLayout_2.addWidget(self.pushButton_Search)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.tableWidget_References = QtWidgets.QTableWidget(parent=self.layoutWidget)
        font = QtGui.QFont()
        font.setFamily("Monospace")
        self.tableWidget_References.setFont(font)
        self.tableWidget_References.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableWidget_References.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tableWidget_References.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableWidget_References.setWordWrap(False)
        self.tableWidget_References.setObjectName("tableWidget_References")
        self.tableWidget_References.setColumnCount(2)
        self.tableWidget_References.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_References.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_References.setHorizontalHeaderItem(1, item)
        self.tableWidget_References.horizontalHeader().setStretchLastSection(True)
        self.tableWidget_References.verticalHeader().setVisible(False)
        self.tableWidget_References.verticalHeader().setDefaultSectionSize(16)
        self.tableWidget_References.verticalHeader().setMinimumSectionSize(16)
        self.verticalLayout.addWidget(self.tableWidget_References)
        self.listWidget_Referrers = QtWidgets.QListWidget(parent=self.splitter)
        font = QtGui.QFont()
        font.setFamily("Monospace")
        self.listWidget_Referrers.setFont(font)
        self.listWidget_Referrers.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.listWidget_Referrers.setObjectName("listWidget_Referrers")
        self.gridLayout.addWidget(self.splitter, 0, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Referenced Calls"))
        self.lineEdit_Regex.setPlaceholderText(_translate("Form", "Enter a string or a python regex"))
        self.checkBox_CaseSensitive.setToolTip(_translate("Form", "Ignore case if checked"))
        self.checkBox_CaseSensitive.setText(_translate("Form", "Case sensitive"))
        self.checkBox_Regex.setToolTip(_translate("Form", "Your string will be treated as a regex if checked"))
        self.checkBox_Regex.setText(_translate("Form", "Regex"))
        self.pushButton_Search.setText(_translate("Form", "Search(Enter)"))
        self.tableWidget_References.setSortingEnabled(True)
        item = self.tableWidget_References.horizontalHeaderItem(0)
        item.setText(_translate("Form", "Address"))
        item = self.tableWidget_References.horizontalHeaderItem(1)
        item.setText(_translate("Form", "Refcount"))
