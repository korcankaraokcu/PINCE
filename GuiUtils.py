#!/usr/bin/python3
from PyQt5.QtWidgets import QDesktopWidget


# centering a window
def center(window):
    window.move(QDesktopWidget().availableGeometry().center() - window.frameGeometry().center())


# centering a child window
def center_parent(window):
    window.move(window.parent().frameGeometry().center() - window.frameGeometry().center())
