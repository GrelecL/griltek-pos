"""PIN login screen."""
import time

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import cashier.api_client as api


class LoginScreen(QWidget):
    login_success = pyqtSignal(dict)   # emits user dict

    def __init__(self, location_id: str):
        super().__init__()
        self.location_id = location_id
        self._pin = ""
        self._attempts = 0
        self._locked_until = 0.0
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Griltek POS")
        title.setFont(QFont("Sans", 28, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.status_label = QLabel("Vnesite PIN")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.pin_display = QLineEdit()
        self.pin_display.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin_display.setReadOnly(True)
        self.pin_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pin_display.setFont(QFont("Mono", 20))
        self.pin_display.setMaximumWidth(200)
        layout.addWidget(self.pin_display, alignment=Qt.AlignmentFlag.AlignCenter)

        grid = QGridLayout()
        grid.setSpacing(8)
        digits = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "C", "0", "✓"]
        for i, d in enumerate(digits):
            btn = QPushButton(d)
            btn.setFixedSize(80, 80)
            btn.setFont(QFont("Sans", 18))
            btn.clicked.connect(lambda checked, ch=d: self._on_key(ch))
            grid.addWidget(btn, i // 3, i % 3)
        layout.addLayout(grid)

    def _on_key(self, ch: str):
        if ch == "C":
            self._pin = ""
            self.pin_display.clear()
        elif ch == "✓":
            self._submit()
        else:
            if len(self._pin) < 8:
                self._pin += ch
                self.pin_display.setText("●" * len(self._pin))

    def _submit(self):
        if time.time() < self._locked_until:
            remaining = int(self._locked_until - time.time())
            self.status_label.setText(f"Zaklenjeno — počakajte {remaining}s")
            return

        result = api.pin_login(self.location_id, self._pin)
        self._pin = ""
        self.pin_display.clear()

        if result:
            self._attempts = 0
            self.status_label.setText("Vnesite PIN")
            api.set_token(result["access_token"])
            self.login_success.emit(result)
        else:
            self._attempts += 1
            from cashier.config import MAX_PIN_ATTEMPTS, PIN_LOCKOUT_SECONDS
            if self._attempts >= MAX_PIN_ATTEMPTS:
                self._locked_until = time.time() + PIN_LOCKOUT_SECONDS
                self.status_label.setText(f"Preveč napak — zaklenjeno {PIN_LOCKOUT_SECONDS}s")
                self._attempts = 0
            else:
                remaining = MAX_PIN_ATTEMPTS - self._attempts
                self.status_label.setText(f"Napačen PIN ({remaining} poskusov)")
