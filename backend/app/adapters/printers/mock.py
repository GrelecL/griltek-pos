"""Mock ESC/POS printer — prints to stdout. Replace with python-escpos in Step 4."""


class MockPrinter:
    def print_receipt(self, sale_data: dict) -> None:
        # TODO: real impl — connect python-escpos printer
        lines = [
            "=" * 40,
            f"  {sale_data.get('tenant_name', 'Griltek POS')}",
            f"  {sale_data.get('location_name', '')}",
            "=" * 40,
        ]
        for line in sale_data.get("lines", []):
            lines.append(
                f"{line['name'][:20]:<20} {line['qty']:>4} x {line['unit_price']:>7.2f}"
            )
            lines.append(f"{'':>30} {line['line_total']:>9.2f}")
        lines += [
            "-" * 40,
            f"{'SKUPAJ':>30} {sale_data.get('total', 0):>9.2f} EUR",
            "=" * 40,
            f"ZOI: {sale_data.get('zoi', 'N/A')}",
            f"EOR: {sale_data.get('eor', 'N/A')}",
            "=" * 40,
        ]
        print("\n".join(lines))


_printer = MockPrinter()


def get_printer() -> MockPrinter:
    return _printer
