# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'AddAddressManuallyDialog.ui'
#
# Created by: PyQt5 UI code generator 5.15.7
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(224, 390)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Dialog.sizePolicy().hasHeightForWidth())
        Dialog.setSizePolicy(sizePolicy)
        Dialog.setMinimumSize(QtCore.QSize(0, 0))
        self.gridLayout = QtWidgets.QGridLayout(Dialog)
        self.gridLayout.setObjectName("gridLayout")
        self.widget_Pointer = QtWidgets.QWidget(Dialog)
        self.widget_Pointer.setEnabled(True)
        self.widget_Pointer.setMinimumSize(QtCore.QSize(0, 0))
        self.widget_Pointer.setObjectName("widget_Pointer")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.widget_Pointer)
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_4.setSpacing(0)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.verticalLayout_Pointers = QtWidgets.QVBoxLayout()
        self.verticalLayout_Pointers.setObjectName("verticalLayout_Pointers")
        self.label_BaseAddress = QtWidgets.QLabel(self.widget_Pointer)
        self.label_BaseAddress.setObjectName("label_BaseAddress")
        self.verticalLayout_Pointers.addWidget(self.label_BaseAddress)
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.lineEdit_PtrStartAddress = QtWidgets.QLineEdit(self.widget_Pointer)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEdit_PtrStartAddress.sizePolicy().hasHeightForWidth())
        self.lineEdit_PtrStartAddress.setSizePolicy(sizePolicy)
        self.lineEdit_PtrStartAddress.setObjectName("lineEdit_PtrStartAddress")
        self.horizontalLayout_4.addWidget(self.lineEdit_PtrStartAddress)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem)
        self.verticalLayout_Pointers.addLayout(self.horizontalLayout_4)
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.addOffsetButton = QtWidgets.QPushButton(self.widget_Pointer)
        self.addOffsetButton.setObjectName("addOffsetButton")
        self.horizontalLayout_5.addWidget(self.addOffsetButton)
        self.removeOffsetButton = QtWidgets.QPushButton(self.widget_Pointer)
        self.removeOffsetButton.setObjectName("removeOffsetButton")
        self.horizontalLayout_5.addWidget(self.removeOffsetButton)
        self.verticalLayout_Pointers.addLayout(self.horizontalLayout_5)
        self.verticalLayout_4.addLayout(self.verticalLayout_Pointers)
        self.gridLayout.addWidget(self.widget_Pointer, 7, 0, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.buttonBox.sizePolicy().hasHeightForWidth())
        self.buttonBox.setSizePolicy(sizePolicy)
        self.buttonBox.setMaximumSize(QtCore.QSize(16777215, 35))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 9, 0, 1, 1)
        self.checkBox_IsPointer = QtWidgets.QCheckBox(Dialog)
        self.checkBox_IsPointer.setObjectName("checkBox_IsPointer")
        self.gridLayout.addWidget(self.checkBox_IsPointer, 3, 0, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(20, 120, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem1, 8, 0, 1, 1)
        self.verticalLayout_3 = QtWidgets.QVBoxLayout()
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label_5 = QtWidgets.QLabel(Dialog)
        self.label_5.setObjectName("label_5")
        self.horizontalLayout_3.addWidget(self.label_5)
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem2)
        self.checkBox_zeroterminate = QtWidgets.QCheckBox(Dialog)
        self.checkBox_zeroterminate.setChecked(True)
        self.checkBox_zeroterminate.setObjectName("checkBox_zeroterminate")
        self.horizontalLayout_3.addWidget(self.checkBox_zeroterminate)
        self.verticalLayout_3.addLayout(self.horizontalLayout_3)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.comboBox_ValueType = QtWidgets.QComboBox(Dialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_ValueType.sizePolicy().hasHeightForWidth())
        self.comboBox_ValueType.setSizePolicy(sizePolicy)
        self.comboBox_ValueType.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.comboBox_ValueType.setObjectName("comboBox_ValueType")
        self.horizontalLayout_2.addWidget(self.comboBox_ValueType)
        spacerItem3 = QtWidgets.QSpacerItem(13, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem3)
        self.label_length = QtWidgets.QLabel(Dialog)
        self.label_length.setObjectName("label_length")
        self.horizontalLayout_2.addWidget(self.label_length)
        self.lineEdit_length = QtWidgets.QLineEdit(Dialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEdit_length.sizePolicy().hasHeightForWidth())
        self.lineEdit_length.setSizePolicy(sizePolicy)
        self.lineEdit_length.setMaximumSize(QtCore.QSize(60, 16777215))
        self.lineEdit_length.setInputMask("")
        self.lineEdit_length.setObjectName("lineEdit_length")
        self.horizontalLayout_2.addWidget(self.lineEdit_length)
        self.verticalLayout_3.addLayout(self.horizontalLayout_2)
        self.gridLayout.addLayout(self.verticalLayout_3, 2, 0, 1, 1)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setObjectName("label")
        self.verticalLayout_2.addWidget(self.label)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.lineEdit_address = QtWidgets.QLineEdit(Dialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEdit_address.sizePolicy().hasHeightForWidth())
        self.lineEdit_address.setSizePolicy(sizePolicy)
        self.lineEdit_address.setMinimumSize(QtCore.QSize(100, 0))
        self.lineEdit_address.setText("")
        self.lineEdit_address.setObjectName("lineEdit_address")
        self.horizontalLayout.addWidget(self.lineEdit_address)
        self.label_2 = QtWidgets.QLabel(Dialog)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout.addWidget(self.label_2)
        self.label_valueofaddress = QtWidgets.QLabel(Dialog)
        self.label_valueofaddress.setText("")
        self.label_valueofaddress.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextSelectableByMouse)
        self.label_valueofaddress.setObjectName("label_valueofaddress")
        self.horizontalLayout.addWidget(self.label_valueofaddress)
        spacerItem4 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem4)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.gridLayout.addLayout(self.verticalLayout_2, 0, 0, 1, 1)
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.label_4 = QtWidgets.QLabel(Dialog)
        self.label_4.setObjectName("label_4")
        self.verticalLayout.addWidget(self.label_4)
        self.lineEdit_description = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_description.setText("")
        self.lineEdit_description.setObjectName("lineEdit_description")
        self.verticalLayout.addWidget(self.lineEdit_description)
        self.gridLayout.addLayout(self.verticalLayout, 1, 0, 1, 1)

        self.retranslateUi(Dialog)
        self.comboBox_ValueType.setCurrentIndex(-1)
        self.buttonBox.accepted.connect(Dialog.accept) # type: ignore
        self.buttonBox.rejected.connect(Dialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Add Address Manually"))
        self.label_BaseAddress.setText(_translate("Dialog", "Base Address:"))
        self.addOffsetButton.setText(_translate("Dialog", "Add Offset"))
        self.removeOffsetButton.setText(_translate("Dialog", "Remove Offset"))
        self.checkBox_IsPointer.setText(_translate("Dialog", "Pointer"))
        self.label_5.setText(_translate("Dialog", "Type:"))
        self.checkBox_zeroterminate.setText(_translate("Dialog", "Zero-Terminated"))
        self.label_length.setText(_translate("Dialog", "Length"))
        self.lineEdit_length.setText(_translate("Dialog", "10"))
        self.label.setText(_translate("Dialog", "Address:"))
        self.label_2.setText(_translate("Dialog", "="))
        self.label_4.setText(_translate("Dialog", "Description:"))
