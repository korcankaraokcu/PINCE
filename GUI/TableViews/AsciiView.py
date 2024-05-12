"""
Copyright (C) 2016-2017 Korcan Karaokçu <korcankaraokcu@gmail.com>

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

from GUI.TableViews.HexView import QHexView
from GUI.ItemDelegates.HexDelegate import QHexDelegate
from libpince import typedefs


class QAsciiView(QHexView):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 12 is minimum size with current font, otherwise it will be cut off
        self.horizontalHeader().setMinimumSectionSize(12)
        self.horizontalHeader().setDefaultSectionSize(12)
        self.horizontalHeader().setMaximumSectionSize(12)
        self.write_type = typedefs.VALUE_INDEX.STRING_UTF8
        self.delegate = QHexDelegate(1, ".+")
        self.delegate.closeEditor.connect(self.on_editor_close)
        self.setItemDelegate(self.delegate)
