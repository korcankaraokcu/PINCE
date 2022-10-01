from PyQt6.QtGui import QValidator


class QHexValidator(QValidator):
    def __init__(self, max_limit, parent=None):
        super().__init__(parent)
        self.max_limit = max_limit

    def validate(self, p_str, p_int):
        try:
            int_repr = int(p_str, 0)
        except ValueError:
            return QValidator.Intermediate, p_str, p_int
        if int_repr > self.max_limit:
            return QValidator.Invalid, p_str, p_int
        return QValidator.Acceptable, p_str, p_int
