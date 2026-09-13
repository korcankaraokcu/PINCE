#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copyright (C) 2016-2017 Korcan Karaokçu <korcankaraokcu@gmail.com>
Copyright (C) 2016-2017 Çağrı Ulaş <cagriulas@gmail.com>
Copyright (C) 2016-2017 Jakob Kreuze <jakob@memeware.net>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import importlib
import os
import signal
import sys
import traceback
from types import FrameType, TracebackType

# Must precede the imports below in case any of the PyQt and other imports want to create bytecodes.
if os.geteuid() == 0:
    sys.dont_write_bytecode = True
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"  # For GDB and other processes that will inherit environ.

from PyQt6.QtCore import (
    QLibraryInfo,
    QLocale,
    QSettings,
    QSignalBlocker,
    QTranslator,
)
from PyQt6.QtWidgets import (
    QApplication,
    QMessageBox,
)

from GUI.Session.session import SessionManager
from GUI.Settings import themes
from GUI.States import states
from GUI.Widgets.MainWindow.MainWindow import MainWindow
from libpince import typedefs, utils
from tr.tr import TranslationConstants as tr
from tr.tr import get_locale

if __name__ == "__main__":
    app = QApplication([])
    app.setApplicationName("PINCE")
    app.setOrganizationName("PINCE")
    app.setOrganizationDomain("github.io")
    app.setDesktopFileName("io.github.korcankaraokcu.PINCE")
    QSettings.setPath(QSettings.Format.NativeFormat, QSettings.Scope.UserScope, utils.get_user_path(typedefs.USER_PATHS.CONFIG))
    settings_instance = QSettings()
    translator = QTranslator()
    qt_translator = QTranslator()
    try:
        locale = settings_instance.value("General/locale", type=str)
    except SystemError:
        # We're reading the settings for the first time here
        # If there's an error due to python objects, clear settings
        settings_instance.clear()
        locale = None
    if not locale:
        locale = get_locale()
    # Load Qt's own translations for standard widget strings (file dialog buttons, message box buttons etc...).
    # Installed before PINCE's catalog so PINCE's strings take precedence on any overlap.
    translations_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if qt_translator.load(QLocale(locale), "qtbase", "_", translations_path):
        app.installTranslator(qt_translator)
    locale_file = utils.get_script_directory() + f"/i18n/qm/{locale}.qm"
    translator.load(locale_file)
    app.installTranslator(translator)
    tr.translate()
    # Reload states after QApplication instance to ensure that variables are correctly initiated
    # Reloading states after translations also ensures that hotkeys are correctly translated
    importlib.reload(states)
    importlib.reload(themes)  # Needed for correct translations


def except_hook(exception_type: type[BaseException], value: BaseException, tb: TracebackType | None) -> None:
    focused_widget = app.focusWidget()
    if focused_widget and exception_type == typedefs.GDBInitializeException:
        QMessageBox.information(focused_widget, tr.ERROR, tr.GDB_INIT)
    traceback.print_exception(exception_type, value, tb)


# From version 5.5 and onwards, PyQT calls qFatal() when an exception has been encountered
# So, we must override sys.excepthook to avoid calling of qFatal()
sys.excepthook = except_hook


# Assigned in __main__
window: "MainWindow | None" = None


def signal_handler(signal: int, frame: FrameType | None) -> None:
    with QSignalBlocker(app):
        app.quit()


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGHUP, signal_handler)


def handle_exit() -> None:
    states.exiting = True
    if window is not None and window.update_check_thread is not None:
        window.update_check_thread.wait()


if __name__ == "__main__":
    app.aboutToQuit.connect(handle_exit)
    window = MainWindow()
    window.show()

    if len(sys.argv) > 1 and sys.argv[1]:
        real_path = os.path.realpath(sys.argv[1])
        SessionManager.load_session(real_path)

    sys.exit(app.exec())
