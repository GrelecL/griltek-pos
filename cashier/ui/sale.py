"""Main sale screen — PLU / barcode / search → basket → payment."""
import uuid
from decimal import Decimal

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import cashier.api_client as api
from cashier.config import DEVICE_ID, LOCATION_ID, TENANT_ID
from cashier.hardware.printer import get_printer
from cashier.local.queue import enqueue
from cashier.ui.payment import PaymentDialog


class SaleScreen(QWidget):
    logout_requested = pyqtSignal()

    def __init__(self, user: dict, session: dict):
        super().__init__()
        self.user = user
        self.session = session
        self.basket: list[dict] = []   # list of line dicts
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # top bar
        top = QHBoxLayout()
        self.user_label = QLabel(f"Blagajnik: {self.user.get('display_name', '')}")
        self.session_label = QLabel(f"Seja: {self.session.get('id', '')[:8]}…")
        logout_btn = QPushButton("Odjava")
        logout_btn.clicked.connect(self.logout_requested)
        top.addWidget(self.user_label)
        top.addStretch()
        top.addWidget(self.session_label)
        top.addWidget(logout_btn)
        layout.addLayout(top)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── left: search / PLU input ──
        left = QWidget()
        left_layout = QVBoxLayout(left)

        left_layout.addWidget(QLabel("Skeniraj črtno kodo / vnesi PLU:"))
        self.scan_input = QLineEdit()
        self.scan_input.setPlaceholderText("EAN / PLU / iskanje…")
        self.scan_input.setFont(QFont("Mono", 16))
        self.scan_input.returnPressed.connect(self._on_scan)
        left_layout.addWidget(self.scan_input)

        # quick PLU numpad
        plu_grid_widget = QWidget()
        plu_grid = QGridLayout(plu_grid_widget)
        for i, label in enumerate(["1", "2", "3", "4", "5", "6", "7", "8", "9", "00", "0", "⌫"]):
            btn = QPushButton(label)
            btn.setFixedSize(70, 55)
            btn.setFont(QFont("Sans", 14))
            btn.clicked.connect(lambda _, ch=label: self._numpad_key(ch))
            plu_grid.addWidget(btn, i // 3, i % 3)
        left_layout.addWidget(plu_grid_widget)
        left_layout.addStretch()
        splitter.addWidget(left)

        # ── right: basket ──
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("Košarica:"))

        self.basket_table = QTableWidget(0, 5)
        self.basket_table.setHorizontalHeaderLabels(["PLU", "Naziv", "Kol", "Cena", "Skupaj"])
        self.basket_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.basket_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        right_layout.addWidget(self.basket_table)

        self.total_label = QLabel("Skupaj: 0.00 EUR")
        self.total_label.setFont(QFont("Sans", 18, QFont.Weight.Bold))
        right_layout.addWidget(self.total_label)

        btn_row = QHBoxLayout()
        remove_btn = QPushButton("Odstrani vrstico")
        remove_btn.clicked.connect(self._remove_line)
        pay_btn = QPushButton("PLAČILO →")
        pay_btn.setFont(QFont("Sans", 14, QFont.Weight.Bold))
        pay_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 12px;")
        pay_btn.clicked.connect(self._do_payment)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch()
        btn_row.addWidget(pay_btn)
        right_layout.addLayout(btn_row)
        splitter.addWidget(right)

        splitter.setSizes([350, 650])
        layout.addWidget(splitter)

    def _numpad_key(self, ch: str):
        if ch == "⌫":
            current = self.scan_input.text()
            self.scan_input.setText(current[:-1])
        else:
            self.scan_input.setText(self.scan_input.text() + ch)

    def _on_scan(self):
        text = self.scan_input.text().strip()
        self.scan_input.clear()
        if not text:
            return
        # try barcode first
        product = api.get_product_by_barcode(text)
        if not product:
            product = api.get_product_by_plu(TENANT_ID, text)
        if not product:
            QMessageBox.warning(self, "Ni najdeno", f"Artikel '{text}' ni najden.")
            return
        self._add_to_basket(product)

    def _add_to_basket(self, product: dict, qty: Decimal = Decimal("1")):
        # get price
        price_data = api.get_price(product["id"], LOCATION_ID)
        if not price_data:
            QMessageBox.warning(self, "Napaka", f"Artikel '{product['name']}' nima cene.")
            return
        unit_price = Decimal(str(price_data["amount"]))
        line_total = (qty * unit_price).quantize(Decimal("0.01"))

        # check if same product already in basket
        for line in self.basket:
            if line["product_id"] == product["id"]:
                line["qty"] += qty
                line["line_total"] = (line["qty"] * unit_price).quantize(Decimal("0.01"))
                self._refresh_basket()
                return

        self.basket.append({
            "product_id": product["id"],
            "plu": product["plu"],
            "product_name": product["name"],
            "qty": qty,
            "unit_price": unit_price,
            "vat_rate": Decimal(str(product["vat_rate"])),
            "discount_pct": Decimal("0"),
            "discount_amount": Decimal("0"),
            "line_total": line_total,
            "modifiers": [],
        })
        self._refresh_basket()

    def _refresh_basket(self):
        self.basket_table.setRowCount(0)
        total = Decimal("0")
        for line in self.basket:
            row = self.basket_table.rowCount()
            self.basket_table.insertRow(row)
            self.basket_table.setItem(row, 0, QTableWidgetItem(line["plu"]))
            self.basket_table.setItem(row, 1, QTableWidgetItem(line["product_name"]))
            self.basket_table.setItem(row, 2, QTableWidgetItem(str(line["qty"])))
            self.basket_table.setItem(row, 3, QTableWidgetItem(f"{line['unit_price']:.2f}"))
            self.basket_table.setItem(row, 4, QTableWidgetItem(f"{line['line_total']:.2f}"))
            total += line["line_total"]
        self.total_label.setText(f"Skupaj: {total:.2f} EUR")

    def _remove_line(self):
        row = self.basket_table.currentRow()
        if row >= 0:
            self.basket.pop(row)
            self._refresh_basket()

    def _do_payment(self):
        if not self.basket:
            QMessageBox.information(self, "Prazna košarica", "Dodajte vsaj en artikel.")
            return
        total = sum(line["line_total"] for line in self.basket)
        dlg = PaymentDialog(total, parent=self)
        if dlg.exec() != PaymentDialog.DialogCode.Accepted:
            return

        # build sale payload
        payload = {
            "transaction_uuid": str(uuid.uuid4()),
            "cash_session_id": self.session["id"],
            "location_id": LOCATION_ID,
            "device_id": DEVICE_ID,
            "user_id": self.user["user_id"],
            "sale_type": "sale",
            "lines": [
                {
                    "product_id": ln["product_id"],
                    "product_name": ln["product_name"],
                    "plu": ln["plu"],
                    "qty": str(ln["qty"]),
                    "unit_price": str(ln["unit_price"]),
                    "vat_rate": str(ln["vat_rate"]),
                    "discount_pct": str(ln["discount_pct"]),
                    "discount_amount": str(ln["discount_amount"]),
                    "modifiers": ln["modifiers"],
                }
                for ln in self.basket
            ],
            "payments": dlg.payments,
        }

        result = api.create_sale(payload)
        if not result:
            # offline: queue locally
            enqueue(payload)
            QMessageBox.warning(self, "Offline", "API nedosegljiv — račun shranjen v offline čakalno vrsto.")
            self._reset_basket()
            return

        # print receipt
        receipt = {
            "header": "Griltek POS",
            "lines": [
                {
                    "name": ln["product_name"],
                    "qty": str(ln["qty"]),
                    "unit_price": str(ln["unit_price"]),
                    "line_total": str(ln["line_total"]),
                }
                for ln in self.basket
            ],
            "total": str(total),
            "payments": dlg.payments,
            "zoi": result.get("zoi", "N/A"),
            "eor": result.get("eor", "N/A"),
        }
        get_printer().print_receipt(receipt)

        # open drawer for cash payments
        if any(p["method"] == "cash" for p in dlg.payments):
            from cashier.hardware.cash_drawer import open_drawer
            open_drawer()

        self._reset_basket()
        QMessageBox.information(self, "Uspešno", f"Račun #{result['id'][:8]} uspešno zaključen.")

    def _reset_basket(self):
        self.basket.clear()
        self._refresh_basket()
