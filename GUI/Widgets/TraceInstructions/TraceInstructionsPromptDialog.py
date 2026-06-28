from PyQt6.QtWidgets import QDialog, QWidget, QMessageBox
from GUI.Utils import guiutils
from GUI.Widgets.TraceInstructions.Form.TraceInstructionsPromptDialog import Ui_Dialog
from libpince import typedefs
from tr.tr import TranslationConstants as tr


class TraceInstructionsPromptDialog(QDialog, Ui_Dialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)
        guiutils.center_to_parent(self)

    def get_values(self) -> tuple[int, str, str, int, bool, bool]:
        try:
            max_trace_count = int(self.lineEdit_MaxTraceCount.text())
        except ValueError:
            max_trace_count = 0
        trigger_condition = self.lineEdit_TriggerCondition.text()
        stop_condition = self.lineEdit_StopCondition.text()
        if self.checkBox_StepOver.isChecked():
            step_mode = typedefs.STEP_MODE.STEP_OVER
        else:
            step_mode = typedefs.STEP_MODE.SINGLE_STEP
        stop_after_trace = self.checkBox_StopAfterTrace.isChecked()
        collect_registers = self.checkBox_CollectRegisters.isChecked()
        return max_trace_count, trigger_condition, stop_condition, step_mode, stop_after_trace, collect_registers

    def accept(self) -> None:
        try:
            max_trace_count = int(self.lineEdit_MaxTraceCount.text())
        except ValueError:
            max_trace_count = 0
        if max_trace_count >= 1:
            super().accept()
        else:
            QMessageBox.information(self, tr.ERROR, tr.MAX_TRACE_COUNT_ASSERT_GT.format(1))
