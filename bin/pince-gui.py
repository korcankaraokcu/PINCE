#!/usr/bin/env python3

import sys
from PyQt5.QtWidgets import QApplication

import pince.PINCE as p

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = p.MainForm()
    window.show()
    sys.exit(app.exec_())
