# Form implementation generated from reading ui file 'DissectCodeDialog.ui'
#
# Created by: PyQt6 UI code generator 6.5.1
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(799, 412)
        self.gridLayout = QtWidgets.QGridLayout(Dialog)
        self.gridLayout.setObjectName("gridLayout")
        self.splitter = QtWidgets.QSplitter(parent=Dialog)
        self.splitter.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.splitter.setObjectName("splitter")
        self.tableWidget_ExecutableMemoryRegions = QtWidgets.QTableWidget(parent=self.splitter)
        self.tableWidget_ExecutableMemoryRegions.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableWidget_ExecutableMemoryRegions.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableWidget_ExecutableMemoryRegions.setWordWrap(False)
        self.tableWidget_ExecutableMemoryRegions.setObjectName("tableWidget_ExecutableMemoryRegions")
        self.tableWidget_ExecutableMemoryRegions.setColumnCount(2)
        self.tableWidget_ExecutableMemoryRegions.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_ExecutableMemoryRegions.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_ExecutableMemoryRegions.setHorizontalHeaderItem(1, item)
        self.tableWidget_ExecutableMemoryRegions.horizontalHeader().setStretchLastSection(True)
        self.tableWidget_ExecutableMemoryRegions.verticalHeader().setVisible(False)
        self.tableWidget_ExecutableMemoryRegions.verticalHeader().setDefaultSectionSize(16)
        self.tableWidget_ExecutableMemoryRegions.verticalHeader().setMinimumSectionSize(16)
        self.layoutWidget = QtWidgets.QWidget(parent=self.splitter)
        self.layoutWidget.setObjectName("layoutWidget")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.layoutWidget)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.label_ScanInfo = QtWidgets.QLabel(parent=self.layoutWidget)
        self.label_ScanInfo.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label_ScanInfo.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.LinksAccessibleByMouse|QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label_ScanInfo.setObjectName("label_ScanInfo")
        self.verticalLayout.addWidget(self.label_ScanInfo)
        self.label_RegionInfo = QtWidgets.QLabel(parent=self.layoutWidget)
        self.label_RegionInfo.setText("-")
        self.label_RegionInfo.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label_RegionInfo.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.LinksAccessibleByMouse|QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label_RegionInfo.setObjectName("label_RegionInfo")
        self.verticalLayout.addWidget(self.label_RegionInfo)
        self.label_RegionCountInfo = QtWidgets.QLabel(parent=self.layoutWidget)
        self.label_RegionCountInfo.setText("-")
        self.label_RegionCountInfo.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label_RegionCountInfo.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.LinksAccessibleByMouse|QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label_RegionCountInfo.setObjectName("label_RegionCountInfo")
        self.verticalLayout.addWidget(self.label_RegionCountInfo)
        self.label_4 = QtWidgets.QLabel(parent=self.layoutWidget)
        self.label_4.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label_4.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.LinksAccessibleByMouse|QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label_4.setObjectName("label_4")
        self.verticalLayout.addWidget(self.label_4)
        self.label_CurrentRange = QtWidgets.QLabel(parent=self.layoutWidget)
        self.label_CurrentRange.setText("-")
        self.label_CurrentRange.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label_CurrentRange.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.LinksAccessibleByMouse|QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label_CurrentRange.setObjectName("label_CurrentRange")
        self.verticalLayout.addWidget(self.label_CurrentRange)
        self.verticalLayout_2.addLayout(self.verticalLayout)
        self.line = QtWidgets.QFrame(parent=self.layoutWidget)
        self.line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line.setObjectName("line")
        self.verticalLayout_2.addWidget(self.line)
        self.label = QtWidgets.QLabel(parent=self.layoutWidget)
        self.label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.LinksAccessibleByMouse|QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label.setObjectName("label")
        self.verticalLayout_2.addWidget(self.label)
        self.label_StringReferenceCount = QtWidgets.QLabel(parent=self.layoutWidget)
        self.label_StringReferenceCount.setText("")
        self.label_StringReferenceCount.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.LinksAccessibleByMouse|QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label_StringReferenceCount.setObjectName("label_StringReferenceCount")
        self.verticalLayout_2.addWidget(self.label_StringReferenceCount)
        self.label_2 = QtWidgets.QLabel(parent=self.layoutWidget)
        self.label_2.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.LinksAccessibleByMouse|QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label_2.setObjectName("label_2")
        self.verticalLayout_2.addWidget(self.label_2)
        self.label_JumpReferenceCount = QtWidgets.QLabel(parent=self.layoutWidget)
        self.label_JumpReferenceCount.setText("")
        self.label_JumpReferenceCount.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.LinksAccessibleByMouse|QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label_JumpReferenceCount.setObjectName("label_JumpReferenceCount")
        self.verticalLayout_2.addWidget(self.label_JumpReferenceCount)
        self.label_3 = QtWidgets.QLabel(parent=self.layoutWidget)
        self.label_3.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.LinksAccessibleByMouse|QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label_3.setObjectName("label_3")
        self.verticalLayout_2.addWidget(self.label_3)
        self.label_CallReferenceCount = QtWidgets.QLabel(parent=self.layoutWidget)
        self.label_CallReferenceCount.setText("")
        self.label_CallReferenceCount.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.LinksAccessibleByMouse|QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label_CallReferenceCount.setObjectName("label_CallReferenceCount")
        self.verticalLayout_2.addWidget(self.label_CallReferenceCount)
        self.line_2 = QtWidgets.QFrame(parent=self.layoutWidget)
        self.line_2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line_2.setObjectName("line_2")
        self.verticalLayout_2.addWidget(self.line_2)
        self.checkBox_DiscardInvalidStrings = QtWidgets.QCheckBox(parent=self.layoutWidget)
        self.checkBox_DiscardInvalidStrings.setChecked(True)
        self.checkBox_DiscardInvalidStrings.setObjectName("checkBox_DiscardInvalidStrings")
        self.verticalLayout_2.addWidget(self.checkBox_DiscardInvalidStrings)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.pushButton_StartCancel = QtWidgets.QPushButton(parent=self.layoutWidget)
        self.pushButton_StartCancel.setText("")
        self.pushButton_StartCancel.setObjectName("pushButton_StartCancel")
        self.horizontalLayout.addWidget(self.pushButton_StartCancel)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout.addItem(spacerItem1)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        spacerItem2 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout_2.addItem(spacerItem2)
        self.gridLayout.addWidget(self.splitter, 0, 0, 1, 1)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dissect Code"))
        item = self.tableWidget_ExecutableMemoryRegions.horizontalHeaderItem(0)
        item.setText(_translate("Dialog", "Regions"))
        item = self.tableWidget_ExecutableMemoryRegions.horizontalHeaderItem(1)
        item.setText(_translate("Dialog", "Path"))
        self.label_ScanInfo.setText(_translate("Dialog", "Selected regions will be scanned"))
        self.label_4.setText(_translate("Dialog", "Currently scanning range:"))
        self.label.setText(_translate("Dialog", "String references found:"))
        self.label_2.setText(_translate("Dialog", "Jumps found:"))
        self.label_3.setText(_translate("Dialog", "Calls found:"))
        self.checkBox_DiscardInvalidStrings.setToolTip(_translate("Dialog", "Entries that can\'t be decoded as utf-8 won\'t be included in referenced strings\n"
"Unchecking it makes ReferencedStringsWidget load slower but allows you to examine non-string pointers on it"))
        self.checkBox_DiscardInvalidStrings.setText(_translate("Dialog", "Discard invalid strings"))
