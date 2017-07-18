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
from libPINCE import GDB_Engine, type_defs
from tests import common_defs


class GDB_Engine_tests(unittest.TestCase):
    def test_read_registers(self):
        register_dict = GDB_Engine.read_registers()
        if GDB_Engine.inferior_arch == type_defs.INFERIOR_ARCH.ARCH_64:
            test_register = "rax"
        else:
            test_register = "eax"
        self.assertRegex(register_dict[test_register], common_defs.regex_hex)
