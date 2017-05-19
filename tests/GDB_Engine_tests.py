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
