"""Cash session open/close dialogs."""
from PyQt6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

import cashier.api_client as api


class OpenSessionDialog(QDialog):
    def __init__(self, location_id: str, user_id: str, parent=None):
        super().__init__(parent)
        self.location_id = location_id
        self.user_id = user_id
        self.session_data: dict | None = None
        self.setWindowTitle("Odpri blagajniško sejo")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Začetni znesek gotovine (EUR):"))
        self.float_spin = QDoubleSpinBox()
        self.float_spin.setRange(0, 9999.99)
        self.float_spin.setDecimals(2)
        self.float_spin.setValue(0.0)
        layout.addWidget(self.float_spin)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Odpri sejo")
        ok_btn.clicked.connect(self._open)
        cancel_btn = QPushButton("Prekliči")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _open(self):
        result = api.open_cash_session(
            self.location_id, self.user_id, self.float_spin.value()
        )
        if result:
            self.session_data = result
            self.accept()
        else:
            QMessageBox.warning(self, "Napaka", "Ni mogoče odpreti seje (API nedosegljiv?)")


class CloseSessionDialog(QDialog):
    def __init__(self, session_id: str, parent=None):
        super().__init__(parent)
        self.session_id = session_id
        self.setWindowTitle("Zapri blagajniško sejo")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Zaključni znesek gotovine (EUR):"))
        self.float_spin = QDoubleSpinBox()
        self.float_spin.setRange(0, 9999.99)
        self.float_spin.setDecimals(2)
        layout.addWidget(self.float_spin)

        x_btn = QPushButton("X-poročilo (vmesno)")
        x_btn.clicked.connect(self._x_report)
        layout.addWidget(x_btn)

        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        layout.addWidget(self.report_text)

        btn_layout = QHBoxLayout()
        close_btn = QPushButton("Zapri sejo (Z-poročilo)")
        close_btn.clicked.connect(self._close)
        cancel_btn = QPushButton("Prekliči")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(close_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _x_report(self):
        data = api.get_x_report(self.session_id)
        if data:
            self.report_text.setPlainText(
                f"X-Poročilo\n"
                f"Skupaj prodaja: {data['total_sales']} EUR\n"
                f"Skupaj vračila: {data['total_returns']} EUR\n"
                f"Neto prodaja:   {data['net_sales']} EUR\n"
                f"Gotovina:       {data['cash_sales']} EUR\n"
                f"Kartica:        {data['card_sales']} EUR\n"
                f"Pričakovana got:{data['expected_cash']} EUR\n"
                f"Št. računov:    {data['sale_count']}\n"
            )

    def _close(self):
        result = api.close_cash_session(self.session_id, self.float_spin.value())
        if result:
            self.accept()
        else:
            QMessageBox.warning(self, "Napaka", "Ni mogoče zapreti seje")
