#!/usr/bin/python3
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication,QMainWindow,QTableWidgetItem,QMessageBox
from PyQt5.QtCore import Qt
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
        self.processbutton.setIcon(QIcon.fromTheme('computer'))
        self.pushButton_Open.setIcon(QIcon.fromTheme('document-open'))
        self.pushButton_Save.setIcon(QIcon.fromTheme('document-save'))
        self.pushButton_Settings.setIcon(QIcon.fromTheme('preferences-system'))
        self.pushButton_CopyToAddressList.setIcon(QIcon.fromTheme('emblem-downloads'))
        self.pushButton_CleanAddressList.setIcon(QIcon.fromTheme('user-trash'))

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
        processlist=SysUtils.getprocesslist(self)
        self.refreshprocesstable(self.processtable, processlist)
        self.pushButton_Close.clicked.connect(self.pushButton_Close_onclick)
        self.pushButton_Open.clicked.connect(self.pushButton_Open_onclick)
        self.lineEdit_searchprocess.textChanged.connect(self.generatenewlist)
        self.processtable.itemDoubleClicked.connect(self.pushButton_Open_onclick)

    def generatenewlist(self):
        if self.lineEdit_searchprocess.isModified():
            text=self.lineEdit_searchprocess.text()
            processlist=SysUtils.searchinprocessesByName(self,text)
            self.refreshprocesstable(self.processtable,processlist)
        else:
            return

#closes the window whenever ESC key is pressed
    def keyPressEvent(self, e):
        if e.key()==Qt.Key_Escape:
            self.close()

#lists currently working processes to table
    def refreshprocesstable(self, tablewidget, processlist):
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
        curItem = self.processtable.item(self.processtable.currentIndex().row(),0)
        if curItem==None:
            QMessageBox.information(self, "Error","Please select a process first")
        else:
            currentpid=int(curItem.text())
            p=SysUtils.getprocessinformation(currentpid)
            self.parent().label_SelectedProcess.setText(str(p.pid) + " - " + p.name())
            self.parent().QWidget_Toolbox.setEnabled(True)
            readable_only,writeable,executable,readable=SysUtils.getmemoryregionsByPerms(currentpid)
            x=SysUtils.excludeSharedMemoryRegions(readable)
            for m in x:
                print(m.perms)
            self.close()

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = mainForm()
    window.show()
    sys.exit(app.exec_())
