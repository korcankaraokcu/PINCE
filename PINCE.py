#!/usr/bin/python3
from PyQt5.QtWidgets import QApplication,QMainWindow,QTableWidgetItem,QMessageBox
from GuiUtils import *
from SysUtils import *
from mainwindow import Ui_MainWindow as mainwindow
from selectprocess import Ui_MainWindow as processwindow

#the PID of the process we'll attach to
currentpid=0

#the mainwindow
class mainForm(QMainWindow, mainwindow):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)
        GuiUtils.center(self)
        self.processbutton.clicked.connect(self.processbutton_onclick)

#shows the process select window
    def processbutton_onclick(self):
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
        self.tablewidget = self.processtable
        processlist=SysUtils.getprocesslist(self)
        self.refreshprocesstable(self.tablewidget, processlist)
        self.pushButton_Close.clicked.connect(self.pushButton_Close_onclick)
        self.pushButton_Open.clicked.connect(self.pushButton_Open_onclick)
        self.lineEdit_searchprocess.textChanged.connect(self.generatenewlist)

    def generatenewlist(self):
        if self.lineEdit_searchprocess.isModified():
            text=self.lineEdit_searchprocess.text()
            processlist=SysUtils.searchinprocessesByName(self,text)
            self.refreshprocesstable(self.tablewidget,processlist)
        else:
            return
#lists currently working processes to table
    def refreshprocesstable(self,tablewidget, processlist):
        tablewidget.setRowCount(0)
        tablewidget.setRowCount(len(processlist))
        for i, row in enumerate(processlist):
            tablewidget.setItem(i, 0, QTableWidgetItem(str(row.pid)))
            tablewidget.setItem(i, 1, QTableWidgetItem(row.username()))
            tablewidget.setItem(i, 2, QTableWidgetItem(row.name()))

#self-explanatory
    def pushButton_Close_onclick(self):
        self.close()

#gets the pid out of the selection to set currentpid
    def pushButton_Open_onclick(self):
        global currentpid
        curItem = self.tablewidget.item(self.tablewidget.currentIndex().row(),0)
        if curItem==None:
            QMessageBox.information(self, "Error","Please select a process first")
        else:
            currentpid=int(curItem.text())
            print(currentpid)
            self.close()


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = mainForm()
    window.show()
    sys.exit(app.exec_())