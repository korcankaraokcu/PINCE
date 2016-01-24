#!/usr/bin/python3
from PyQt5.QtWidgets import QDesktopWidget

class GuiUtils(object):

#centering a window
    def center(self):
        self.move(QDesktopWidget().availableGeometry().center() - self.frameGeometry().center())

#centering a child window
    def parentcenter(self):
        self.move(self.parent().frameGeometry().center() - self.frameGeometry().center())
