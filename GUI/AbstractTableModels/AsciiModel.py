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

from PyQt6.QtCore import QObject
from GUI.AbstractTableModels.HexModel import HexModel
from libpince import utils


class AsciiModel(HexModel):
    def __init__(self, row_count: int, column_count: int, parent: QObject | None = None) -> None:
        super().__init__(row_count, column_count, parent)

    def display_data(self, index: int) -> str:
        return utils.aob_to_str(self.data_array[index])

    def translate_data(self, data: str) -> str:
        return utils.str_to_aob(data)
