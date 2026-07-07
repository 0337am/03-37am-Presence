import sys

from PyQt6.QtWidgets import QApplication

from src.ui.main_window import MainWindow
from src.ui.tray import TrayController


app = QApplication(sys.argv)

window = MainWindow()
tray_controller = TrayController(app, window)

window.show()

sys.exit(app.exec())