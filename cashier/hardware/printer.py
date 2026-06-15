"""ESC/POS receipt printer — mock implementation. Real impl in Step 6."""


class ReceiptPrinter:
    def __init__(self):
        self.connected = False
        # TODO: real impl — connect python-escpos USB/network printer

    def print_receipt(self, receipt_data: dict) -> bool:
        """Print receipt. Returns True on success."""
        try:
            self._mock_print(receipt_data)
            return True
        except Exception:
            return False

    def open_drawer(self) -> None:
        # TODO: real impl — ESC/POS drawer kick command
        print("[MOCK] Cash drawer opened")

    def _mock_print(self, d: dict) -> None:
        W = 42
        sep = "=" * W
        lines = [sep, d.get("header", "GRILTEK POS").center(W), sep]
        for ln in d.get("lines", []):
            name = ln["name"][:22]
            qty_price = f"{ln['qty']} x {float(ln['unit_price']):.2f}"
            total = f"{float(ln['line_total']):.2f}"
            lines.append(f"{name:<22}{qty_price:>10}{total:>8}")
        lines += [
            "-" * W,
            f"{'SKUPAJ / TOTAL':<28}{float(d.get('total', 0)):.2f} EUR",
        ]
        for pay in d.get("payments", []):
            lines.append(f"  {pay['method'].upper():<26}{float(pay['amount']):.2f} EUR")
        lines += [
            "=" * W,
            f"ZOI: {d.get('zoi', 'N/A (Step 5)')}",
            f"EOR: {d.get('eor', 'N/A (Step 5)')}",
            "=" * W,
        ]
        print("\n".join(lines))


_printer = ReceiptPrinter()


def get_printer() -> ReceiptPrinter:
    return _printer
