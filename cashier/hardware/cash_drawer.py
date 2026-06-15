"""Cash drawer control via ESC/POS printer kick command."""
from cashier.hardware.printer import get_printer


def open_drawer() -> None:
    get_printer().open_drawer()
