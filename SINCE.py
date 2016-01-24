#!/usr/bin/python3
from PyQt5.QtWidgets import QApplication,QMainWindow,QTableWidgetItem
from PyQt5.QtCore import QTimer
from GuiUtils import *
from mainwindow import Ui_MainWindow as mainwindow
from selectprocess import Ui_MainWindow as processwindow


#the mainwindow
class mainForm(QMainWindow, mainwindow):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)
        GuiUtils.center(self)
        self.processbutton.clicked.connect(self.onclick)

#shows the process select window
    def onclick(self):
        self.window = processForm(self)
        self.window.show()

#closes all windows on exit
    def closeEvent(self, event):
        app = QApplication.instance()
        app.closeAllWindows()

#process select window
class processForm(QMainWindow, processwindow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        GuiUtils.parentcenter(self)
        tablewidget = self.processtable
        currentRowCount = tablewidget.rowCount()
        tablewidget.insertRow(currentRowCount)
        tablewidget.setItem(currentRowCount, 0, QTableWidgetItem("Some text"))
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = mainForm()
    window.show()
    sys.exit(app.exec_())