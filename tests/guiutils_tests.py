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
import unittest


# from GUI.Utils import guiutils


class guiutils_tests(unittest.TestCase):
    def test_change_text_length(self):
        self.assertEqual(True, True)
        # The function below was removed during refactorization, thus making this test just a placeholder for now
        # self.assertEqual(guiutils.change_text_length("AoB[42]", 30), "AoB[30]")
