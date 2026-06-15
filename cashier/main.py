"""Griltek POS — Cashier application entry point."""
import sys

from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox, QStackedWidget

from cashier.config import LOCATION_ID
from cashier.ui.login import LoginScreen
from cashier.ui.sale import SaleScreen
from cashier.ui.session import OpenSessionDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Griltek POS — Blagajna")
        self.setMinimumSize(1024, 700)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._user: dict | None = None
        self._session: dict | None = None

        self._show_login()

    def _show_login(self):
        self._user = None
        self._session = None
        login = LoginScreen(LOCATION_ID)
        login.login_success.connect(self._on_login)
        self._stack.addWidget(login)
        self._stack.setCurrentWidget(login)

    def _on_login(self, user: dict):
        self._user = user
        dlg = OpenSessionDialog(LOCATION_ID, user["user_id"], parent=self)
        if dlg.exec() == OpenSessionDialog.DialogCode.Accepted:
            self._session = dlg.session_data
            self._show_sale()
        else:
            QMessageBox.information(self, "Info", "Seja ni bila odprta.")

    def _show_sale(self):
        sale_screen = SaleScreen(self._user, self._session)
        sale_screen.logout_requested.connect(self._show_login)
        self._stack.addWidget(sale_screen)
        self._stack.setCurrentWidget(sale_screen)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
