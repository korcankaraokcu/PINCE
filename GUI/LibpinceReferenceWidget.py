# Form implementation generated from reading ui file 'LibpinceReferenceWidget.ui'
#
# Created by: PyQt6 UI code generator 6.5.1
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(887, 569)
        self.gridLayout_2 = QtWidgets.QGridLayout(Form)
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_2.setSpacing(0)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.splitter = QtWidgets.QSplitter(parent=Form)
        self.splitter.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(10)
        self.splitter.setObjectName("splitter")
        self.widget_TypeDefs = QtWidgets.QWidget(parent=self.splitter)
        self.widget_TypeDefs.setObjectName("widget_TypeDefs")
        self.gridLayout = QtWidgets.QGridLayout(self.widget_TypeDefs)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.label_5 = QtWidgets.QLabel(parent=self.widget_TypeDefs)
        self.label_5.setObjectName("label_5")
        self.horizontalLayout_4.addWidget(self.label_5)
        self.line = QtWidgets.QFrame(parent=self.widget_TypeDefs)
        self.line.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line.setObjectName("line")
        self.horizontalLayout_4.addWidget(self.line)
        self.label_3 = QtWidgets.QLabel(parent=self.widget_TypeDefs)
        self.label_3.setObjectName("label_3")
        self.horizontalLayout_4.addWidget(self.label_3)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem)
        self.gridLayout.addLayout(self.horizontalLayout_4, 0, 0, 1, 1)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.lineEdit_SearchText = QtWidgets.QLineEdit(parent=self.widget_TypeDefs)
        self.lineEdit_SearchText.setObjectName("lineEdit_SearchText")
        self.horizontalLayout_2.addWidget(self.lineEdit_SearchText)
        self.pushButton_TextUp = QtWidgets.QPushButton(parent=self.widget_TypeDefs)
        self.pushButton_TextUp.setText("")
        self.pushButton_TextUp.setObjectName("pushButton_TextUp")
        self.horizontalLayout_2.addWidget(self.pushButton_TextUp)
        self.pushButton_TextDown = QtWidgets.QPushButton(parent=self.widget_TypeDefs)
        self.pushButton_TextDown.setText("")
        self.pushButton_TextDown.setObjectName("pushButton_TextDown")
        self.horizontalLayout_2.addWidget(self.pushButton_TextDown)
        self.label_FoundCount = QtWidgets.QLabel(parent=self.widget_TypeDefs)
        self.label_FoundCount.setText("0/0")
        self.label_FoundCount.setObjectName("label_FoundCount")
        self.horizontalLayout_2.addWidget(self.label_FoundCount)
        self.gridLayout.addLayout(self.horizontalLayout_2, 1, 0, 1, 1)
        self.textBrowser_TypeDefs = QtWidgets.QTextBrowser(parent=self.widget_TypeDefs)
        self.textBrowser_TypeDefs.setObjectName("textBrowser_TypeDefs")
        self.gridLayout.addWidget(self.textBrowser_TypeDefs, 2, 0, 1, 1)
        self.widget_Resources = QtWidgets.QWidget(parent=self.splitter)
        self.widget_Resources.setObjectName("widget_Resources")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.widget_Resources)
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.stackedWidget_Resources = QtWidgets.QStackedWidget(parent=self.widget_Resources)
        self.stackedWidget_Resources.setObjectName("stackedWidget_Resources")
        self.page = QtWidgets.QWidget()
        self.page.setObjectName("page")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.page)
        self.gridLayout_4.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_4.setSpacing(0)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.treeWidget_ResourceTree = QtWidgets.QTreeWidget(parent=self.page)
        self.treeWidget_ResourceTree.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.treeWidget_ResourceTree.setObjectName("treeWidget_ResourceTree")
        self.treeWidget_ResourceTree.headerItem().setText(0, "Item Name")
        self.gridLayout_4.addWidget(self.treeWidget_ResourceTree, 0, 0, 1, 1)
        self.stackedWidget_Resources.addWidget(self.page)
        self.page_2 = QtWidgets.QWidget()
        self.page_2.setObjectName("page_2")
        self.gridLayout_5 = QtWidgets.QGridLayout(self.page_2)
        self.gridLayout_5.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_5.setSpacing(0)
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.tableWidget_ResourceTable = QtWidgets.QTableWidget(parent=self.page_2)
        self.tableWidget_ResourceTable.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableWidget_ResourceTable.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tableWidget_ResourceTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableWidget_ResourceTable.setObjectName("tableWidget_ResourceTable")
        self.tableWidget_ResourceTable.setColumnCount(2)
        self.tableWidget_ResourceTable.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_ResourceTable.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_ResourceTable.setHorizontalHeaderItem(1, item)
        self.tableWidget_ResourceTable.horizontalHeader().setStretchLastSection(True)
        self.tableWidget_ResourceTable.verticalHeader().setVisible(False)
        self.tableWidget_ResourceTable.verticalHeader().setDefaultSectionSize(16)
        self.tableWidget_ResourceTable.verticalHeader().setMinimumSectionSize(16)
        self.gridLayout_5.addWidget(self.tableWidget_ResourceTable, 0, 0, 1, 1)
        self.stackedWidget_Resources.addWidget(self.page_2)
        self.gridLayout_3.addWidget(self.stackedWidget_Resources, 2, 0, 1, 1)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.label_4 = QtWidgets.QLabel(parent=self.widget_Resources)
        self.label_4.setObjectName("label_4")
        self.verticalLayout_2.addWidget(self.label_4)
        self.lineEdit_Search = QtWidgets.QLineEdit(parent=self.widget_Resources)
        self.lineEdit_Search.setObjectName("lineEdit_Search")
        self.verticalLayout_2.addWidget(self.lineEdit_Search)
        self.horizontalLayout.addLayout(self.verticalLayout_2)
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(parent=self.widget_Resources)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.comboBox_SourceFile = QtWidgets.QComboBox(parent=self.widget_Resources)
        self.comboBox_SourceFile.setObjectName("comboBox_SourceFile")
        self.verticalLayout.addWidget(self.comboBox_SourceFile)
        self.horizontalLayout.addLayout(self.verticalLayout)
        self.gridLayout_3.addLayout(self.horizontalLayout, 0, 0, 1, 1)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label_2 = QtWidgets.QLabel(parent=self.widget_Resources)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_3.addWidget(self.label_2)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem1)
        self.pushButton_ShowTypeDefs = QtWidgets.QPushButton(parent=self.widget_Resources)
        self.pushButton_ShowTypeDefs.setObjectName("pushButton_ShowTypeDefs")
        self.horizontalLayout_3.addWidget(self.pushButton_ShowTypeDefs)
        self.gridLayout_3.addLayout(self.horizontalLayout_3, 1, 0, 1, 1)
        self.gridLayout_2.addWidget(self.splitter, 0, 0, 1, 1)

        self.retranslateUi(Form)
        self.stackedWidget_Resources.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "libpince Reference"))
        self.label_5.setText(_translate("Form", "Search"))
        self.label_3.setText(_translate("Form", "typedefs(Type Definitions)"))
        self.treeWidget_ResourceTree.headerItem().setText(1, _translate("Form", "Value"))
        self.tableWidget_ResourceTable.setSortingEnabled(True)
        item = self.tableWidget_ResourceTable.horizontalHeaderItem(0)
        item.setText(_translate("Form", "Item Name"))
        item = self.tableWidget_ResourceTable.horizontalHeaderItem(1)
        item.setText(_translate("Form", "Value"))
        self.label_4.setText(_translate("Form", "Search"))
        self.label.setText(_translate("Form", "Source File"))
        self.label_2.setText(_translate("Form", "Resources(Mouse-over items to see docstrings)"))
        self.pushButton_ShowTypeDefs.setText(_translate("Form", "Hide typedefs"))
