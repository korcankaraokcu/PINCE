#!/usr/bin/python3
from PyQt5.QtWidgets import QDesktopWidget
class GuiUtils(object):

#centering a window
    def center(self):
        self.move(QDesktopWidget().availableGeometry().center() - self.frameGeometry().center())

#centering a child window, doesn't work as intended yet
    def parentcenter(self):
        self.move(self.parent().frameGeometry().center().x() - self.frameGeometry().width()/2, self.parent().frameGeometry().center().y() - self.frameGeometry().height()/2)
