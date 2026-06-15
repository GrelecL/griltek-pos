"""Payment dialog — supports cash (with change) and card (mock SumUp)."""
from decimal import ROUND_HALF_UP, Decimal

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


class PaymentDialog(QDialog):
    def __init__(self, total: Decimal, parent=None):
        super().__init__(parent)
        self.total = total
        self.payments: list[dict] = []
        self.setWindowTitle("Plačilo")
        self.setMinimumWidth(400)
        self._build_ui()
        self._update_remaining()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.total_label = QLabel(f"Skupaj: {self.total:.2f} EUR")
        self.total_label.setFont(QFont("Sans", 16, QFont.Weight.Bold))
        layout.addWidget(self.total_label)

        self.remaining_label = QLabel()
        self.remaining_label.setFont(QFont("Sans", 14))
        layout.addWidget(self.remaining_label)

        # payment method
        method_row = QHBoxLayout()
        method_row.addWidget(QLabel("Način:"))
        self.method_combo = QComboBox()
        self.method_combo.addItems(["cash", "card", "sumup"])
        method_row.addWidget(self.method_combo)
        layout.addLayout(method_row)

        # amount
        amount_row = QHBoxLayout()
        amount_row.addWidget(QLabel("Znesek (EUR):"))
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0.01, 99999.99)
        self.amount_spin.setDecimals(2)
        amount_row.addWidget(self.amount_spin)
        layout.addLayout(amount_row)

        add_btn = QPushButton("Dodaj plačilo")
        add_btn.clicked.connect(self._add_payment)
        layout.addWidget(add_btn)

        self.payment_list = QListWidget()
        layout.addWidget(self.payment_list)

        self.change_label = QLabel("")
        self.change_label.setFont(QFont("Sans", 14))
        layout.addWidget(self.change_label)

        btn_row = QHBoxLayout()
        confirm_btn = QPushButton("Potrdi plačilo")
        confirm_btn.clicked.connect(self._confirm)
        cancel_btn = QPushButton("Prekliči")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(confirm_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _remaining(self) -> Decimal:
        paid = sum(Decimal(str(p["amount"])) for p in self.payments)
        return max(Decimal("0"), self.total - paid)

    def _update_remaining(self):
        rem = self._remaining()
        self.remaining_label.setText(f"Preostalo: {rem:.2f} EUR")
        self.amount_spin.setValue(float(rem))

    def _add_payment(self):
        method = self.method_combo.currentText()
        amount = Decimal(str(self.amount_spin.value())).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if amount <= 0:
            return
        change_given = Decimal("0")
        if method == "cash":
            remaining = self._remaining()
            if amount > remaining:
                change_given = amount - remaining
                amount = remaining  # collect only what's due
        self.payments.append({"method": method, "amount": str(amount), "change_given": str(change_given)})
        self.payment_list.addItem(f"{method.upper()}: {amount:.2f} EUR")
        if change_given > 0:
            self.change_label.setText(f"Vračilo: {change_given:.2f} EUR")
        self._update_remaining()

    def _confirm(self):
        if self._remaining() > Decimal("0.005"):
            QMessageBox.warning(self, "Napaka", "Plačilo ni v celoti pokrito.")
            return
        self.accept()
