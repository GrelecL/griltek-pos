"""Barcode scanner — keyboard wedge mode (reads stdin in dev, HID in prod)."""
# In production, keyboard wedge scanners type the barcode + Enter into the focused QLineEdit.
# This module is a placeholder for serial/HID scanner support.
# TODO: real impl — pyserial or hid library for dedicated scanner


class BarcodeScanner:
    """Keyboard-wedge scanners need no special driver — they type into QLineEdit."""
    pass


_scanner = BarcodeScanner()


def get_scanner() -> BarcodeScanner:
    return _scanner
