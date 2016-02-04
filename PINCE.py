#!/usr/bin/python3
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication,QMainWindow,QTableWidgetItem,QMessageBox,QProgressBar
from PyQt5.QtCore import Qt
from GuiUtils import *
from SysUtils import *
from GDB_Engine import GDB_Engine,Command
from mainwindow import Ui_MainWindow as mainwindow
from selectprocess import Ui_MainWindow as processwindow

#the PID of the process we'll attach to
currentpid=0

#the mainwindow
class mainForm(QMainWindow, mainwindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        GuiUtils.center(self)
        self.processbutton.clicked.connect(self.processbutton_onclick)
        self.pushButton_NewFirstScan.clicked.connect(self.NewFirstScan_onclick)
        self.pushButton_NextScan.clicked.connect(self.NextScan_onclick)
        self.processbutton.setIcon(QIcon.fromTheme('computer'))
        self.pushButton_Open.setIcon(QIcon.fromTheme('document-open'))
        self.pushButton_Save.setIcon(QIcon.fromTheme('document-save'))
        self.pushButton_Settings.setIcon(QIcon.fromTheme('preferences-system'))
        self.pushButton_CopyToAddressList.setIcon(QIcon.fromTheme('emblem-downloads'))
        self.pushButton_CleanAddressList.setIcon(QIcon.fromTheme('user-trash'))

    def NewFirstScan_onclick(self):
        if self.pushButton_NewFirstScan.text()=="First Scan":
            self.pushButton_NextScan.setEnabled(True)
            self.pushButton_UndoScan.setEnabled(True)
            self.pushButton_NewFirstScan.setText("New Scan")
            return
        if self.pushButton_NewFirstScan.text()=="New Scan":
            self.pushButton_NextScan.setEnabled(False)
            self.pushButton_UndoScan.setEnabled(False)
            self.pushButton_NewFirstScan.setText("First Scan")

    def NextScan_onclick(self):
        if self.tableWidget_valuesearchtable.rowCount()<=0:
            return

#shows the process select window
    def processbutton_onclick(self):
        self.window = processForm(self)
        self.window.show()

#closes all windows on exit
    def closeEvent(self, event):
        if not currentpid==0:
            gdbprocess.jobqueue.put(["deattach"])
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
        if curItem is None:
            QMessageBox.information(self, "Error","Please select a process first")
        else:
            pid=int(curItem.text())
            if not SysUtils.isprocessvalid(pid):
                QMessageBox.information(self, "Error","Selected process is not valid")
                return
            if pid==currentpid:
                QMessageBox.information(self, "Error","You're debugging this process already")
                return
            tracedby=SysUtils.isTraced(pid)
            if tracedby:
                QMessageBox.information(self, "Error","That process is already being traced by " + tracedby + ", could not attach to the process")
                return
            print("processing")                                                      #progressbar koy buraya
            gdbprocess.jobqueue.put(["canattach",str(pid)])
            result=gdbprocess.resultqueue.get()
            if not result:
                print("done")                                                        #progressbar finish
                QMessageBox.information(self, "Error","Permission denied, could not attach to the process")
                return
            if not currentpid==0:
                gdbprocess.jobqueue.put(["deattach"])
            currentpid=pid
            gdbprocess.jobqueue.put(["attach",str(currentpid)])
            p=SysUtils.getprocessinformation(currentpid)
            self.parent().label_SelectedProcess.setText(str(p.pid) + " - " + p.name())
            self.parent().QWidget_Toolbox.setEnabled(True)
            self.parent().pushButton_NextScan.setEnabled(False)
            self.parent().pushButton_UndoScan.setEnabled(False)
            readable_only,writeable,executable,readable=SysUtils.getmemoryregionsByPerms(currentpid)              #test
            print("done")                                                                 #progressbar finish
            self.close()

if __name__ == "__main__":
    import sys
    command=Command("kek")
    gdbprocess=GDB_Engine()
    gdbprocess.start()
    app = QApplication(sys.argv)
    window = mainForm()
    window.show()
    sys.exit(app.exec_())
