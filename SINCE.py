#!/usr/bin/python3
from PyQt5 import QtCore,QtGui,QtWidgets
from mainwindow import Ui_MainWindow as mainwindow
from selectprocess import Ui_MainWindow as processwindow

#the mainwindow
class mainForm(QtWidgets.QMainWindow, mainwindow):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)
        self.processbutton.clicked.connect(self.onclick)

#shows the process select window
    def onclick(self):
        self.window = processForm(self)
        self.window.show()

#closes all windows on exit
    def closeEvent(self, event):
        app = QtWidgets.QApplication.instance()
        app.closeAllWindows()

#process select window
class processForm(QtWidgets.QMainWindow, processwindow):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    window = mainForm()
    window.show()
    sys.exit(app.exec_())