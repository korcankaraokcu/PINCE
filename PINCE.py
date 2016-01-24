#!/usr/bin/python3
from PyQt5.QtWidgets import QApplication,QMainWindow,QTableWidgetItem
from GuiUtils import *
from SysUtils import *
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
        processlist=SysUtils.getprocesslist(self)
        tablewidget.setRowCount(len(processlist))
        for i, row in enumerate(processlist):
            tablewidget.setItem(i, 0, QTableWidgetItem(str(row.get('pid'))))
            tablewidget.setItem(i, 1, QTableWidgetItem(row.get('username')))
            tablewidget.setItem(i, 2, QTableWidgetItem(row.get('name')))
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = mainForm()
    window.show()
    sys.exit(app.exec_())