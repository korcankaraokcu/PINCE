#!/usr/bin/python3
from PyQt5.QtWidgets import QDesktopWidget,QApplication,QMainWindow
from mainwindow import Ui_MainWindow as mainwindow
from selectprocess import Ui_MainWindow as processwindow

#the mainwindow
class mainForm(QMainWindow, mainwindow):
    def __init__(self, parent=None):
        super().__init__()
        self.center()
        self.setupUi(self)
        self.processbutton.clicked.connect(self.onclick)

#shows the process select window
    def onclick(self):
        self.window = processForm(self)
        self.window.show()

#closes all windows on exit
    def closeEvent(self, event):
        app = QApplication.instance()
        app.closeAllWindows()

#centering a window
    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

#process select window
class processForm(QMainWindow, processwindow):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = mainForm()
    window.show()
    sys.exit(app.exec_())