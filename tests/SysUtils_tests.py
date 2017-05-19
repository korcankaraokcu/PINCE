import unittest
from libPINCE import SysUtils


class SysUtils_tests(unittest.TestCase):
    def test_split_symbol(self):
        self.assertListEqual(SysUtils.split_symbol("func(param)@plt"), ["func", "func(param)", "func(param)@plt"])
