#!/usr/bin/python3
from PyQt5 import QtCore,QtGui,QtWidgets
from mainwindow import Ui_MainWindow as mainwindow
from selectprocess import Ui_MainWindow as processwindow

class mainForm(QtWidgets.QMainWindow, mainwindow):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)
        self.window2=None
        self.pushButton.clicked.connect(self.onclick)

    def onclick(self):
        if self.window2 is None:
            self.window2 = processForm(self)
        self.window2.show()
    def closeEvent(self, event):
        app = QtWidgets.QApplication.instance()
        app.closeAllWindows()

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