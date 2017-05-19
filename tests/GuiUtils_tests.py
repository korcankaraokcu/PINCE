import unittest
from libPINCE import GuiUtils


class GuiUtils_tests(unittest.TestCase):
    def test_change_text_length(self):
        self.assertEqual(GuiUtils.change_text_length("AoB[42]", 31), "AoB[31]")
