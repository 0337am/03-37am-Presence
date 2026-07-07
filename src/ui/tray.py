from pathlib import Path

from PyQt6.QtCore import QEvent, QObject
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QMenu,
    QStyle,
    QSystemTrayIcon,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
YUNO_IMAGE_PATH = PROJECT_ROOT / "assets" / "yuno.png"


class TrayController(QObject):
    def __init__(self, app: QApplication, main_window):
        super().__init__()

        self.app = app
        self.main_window = main_window
        self.tray_icon = None

        self._quitting = False
        self._message_shown = False

        self.app.setQuitOnLastWindowClosed(False)
        self.main_window.installEventFilter(self)

        self.create_tray_icon()

    def create_tray_icon(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("Windows system tray is not available.")
            return

        icon = QIcon(str(YUNO_IMAGE_PATH))

        if icon.isNull():
            icon = self.main_window.style().standardIcon(
                QStyle.StandardPixmap.SP_ComputerIcon
            )

        self.main_window.setWindowIcon(icon)

        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("03:37am Presence")

        menu = QMenu()

        open_action = QAction("Open 03:37am Presence", self)
        hide_action = QAction("Hide window", self)
        quit_action = QAction("Quit", self)

        open_action.triggered.connect(self.show_window)
        hide_action.triggered.connect(self.hide_window)
        quit_action.triggered.connect(self.quit_application)

        menu.addAction(open_action)
        menu.addAction(hide_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def eventFilter(self, watched, event):
        if (
            watched is self.main_window
            and event.type() == QEvent.Type.Close
            and not self._quitting
            and self.tray_icon is not None
        ):
            event.ignore()
            self.hide_window()
            return True

        return super().eventFilter(watched, event)

    def on_tray_activated(self, reason):
        valid_reasons = (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        )

        if reason not in valid_reasons:
            return

        if self.main_window.isVisible():
            self.hide_window(show_message=False)
        else:
            self.show_window()

    def show_window(self, checked=False):
        self.main_window.showNormal()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def hide_window(self, checked=False, show_message=True):
        self.main_window.hide()

        if (
            show_message
            and not self._message_shown
            and self.tray_icon is not None
        ):
            self.tray_icon.showMessage(
                "03:37am Presence",
                "The app is still running in the system tray.",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )

            self._message_shown = True

    def quit_application(self, checked=False):
        self._quitting = True

        if self.tray_icon is not None:
            self.tray_icon.hide()

        self.main_window.close()
        self.app.quit()