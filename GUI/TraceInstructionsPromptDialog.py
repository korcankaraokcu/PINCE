# Form implementation generated from reading ui file 'TraceInstructionsPromptDialog.ui'
#
# Created by: PyQt6 UI code generator 6.5.1
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(306, 381)
        self.gridLayout = QtWidgets.QGridLayout(Dialog)
        self.gridLayout.setObjectName("gridLayout")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(parent=Dialog)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.lineEdit_MaxTraceCount = QtWidgets.QLineEdit(parent=Dialog)
        self.lineEdit_MaxTraceCount.setText("1000")
        self.lineEdit_MaxTraceCount.setObjectName("lineEdit_MaxTraceCount")
        self.verticalLayout.addWidget(self.lineEdit_MaxTraceCount)
        self.label_3 = QtWidgets.QLabel(parent=Dialog)
        self.label_3.setObjectName("label_3")
        self.verticalLayout.addWidget(self.label_3)
        self.lineEdit_TriggerCondition = QtWidgets.QLineEdit(parent=Dialog)
        self.lineEdit_TriggerCondition.setObjectName("lineEdit_TriggerCondition")
        self.verticalLayout.addWidget(self.lineEdit_TriggerCondition)
        self.label_2 = QtWidgets.QLabel(parent=Dialog)
        self.label_2.setObjectName("label_2")
        self.verticalLayout.addWidget(self.label_2)
        self.lineEdit_StopCondition = QtWidgets.QLineEdit(parent=Dialog)
        self.lineEdit_StopCondition.setObjectName("lineEdit_StopCondition")
        self.verticalLayout.addWidget(self.lineEdit_StopCondition)
        self.checkBox_StepOver = QtWidgets.QCheckBox(parent=Dialog)
        self.checkBox_StepOver.setObjectName("checkBox_StepOver")
        self.verticalLayout.addWidget(self.checkBox_StepOver)
        self.checkBox_StopAfterTrace = QtWidgets.QCheckBox(parent=Dialog)
        self.checkBox_StopAfterTrace.setObjectName("checkBox_StopAfterTrace")
        self.verticalLayout.addWidget(self.checkBox_StopAfterTrace)
        self.checkBox_GeneralRegisters = QtWidgets.QCheckBox(parent=Dialog)
        self.checkBox_GeneralRegisters.setChecked(True)
        self.checkBox_GeneralRegisters.setObjectName("checkBox_GeneralRegisters")
        self.verticalLayout.addWidget(self.checkBox_GeneralRegisters)
        self.checkBox_FlagRegisters = QtWidgets.QCheckBox(parent=Dialog)
        self.checkBox_FlagRegisters.setChecked(True)
        self.checkBox_FlagRegisters.setObjectName("checkBox_FlagRegisters")
        self.verticalLayout.addWidget(self.checkBox_FlagRegisters)
        self.checkBox_SegmentRegisters = QtWidgets.QCheckBox(parent=Dialog)
        self.checkBox_SegmentRegisters.setChecked(True)
        self.checkBox_SegmentRegisters.setObjectName("checkBox_SegmentRegisters")
        self.verticalLayout.addWidget(self.checkBox_SegmentRegisters)
        self.checkBox_FloatRegisters = QtWidgets.QCheckBox(parent=Dialog)
        self.checkBox_FloatRegisters.setChecked(True)
        self.checkBox_FloatRegisters.setObjectName("checkBox_FloatRegisters")
        self.verticalLayout.addWidget(self.checkBox_FloatRegisters)
        self.buttonBox = QtWidgets.QDialogButtonBox(parent=Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Cancel|QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept) # type: ignore
        self.buttonBox.rejected.connect(Dialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Parameters for tracing"))
        self.label.setToolTip(_translate("Dialog", "Number of the instructions that\'ll be traced"))
        self.label.setText(_translate("Dialog", "Max trace count(1 or greater):"))
        self.label_3.setToolTip(_translate("Dialog", "Tracing will start if this condition is met"))
        self.label_3.setText(_translate("Dialog", "Trigger condition(Optional, gdb expression):"))
        self.label_2.setToolTip(_translate("Dialog", "Tracing will stop whenever this condition is met"))
        self.label_2.setText(_translate("Dialog", "Stop condition(Optional, gdb expression):"))
        self.checkBox_StepOver.setText(_translate("Dialog", "Step over instead of single step"))
        self.checkBox_StopAfterTrace.setText(_translate("Dialog", "Stop when tracing ends"))
        self.checkBox_GeneralRegisters.setText(_translate("Dialog", "Collect general registers"))
        self.checkBox_FlagRegisters.setText(_translate("Dialog", "Collect flag registers"))
        self.checkBox_SegmentRegisters.setText(_translate("Dialog", "Collect segment registers"))
        self.checkBox_FloatRegisters.setText(_translate("Dialog", "Collect float registers"))
