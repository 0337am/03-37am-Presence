import ctypes
import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from src.ui.main_window import MainWindow
from src.ui.tray import TrayController


def resource_path(
    relative_path: str,
) -> Path:
    packaged_root = getattr(
        sys,
        "_MEIPASS",
        None,
    )

    if packaged_root:
        base_path = Path(
            packaged_root
        )
    else:
        base_path = (
            Path(__file__)
            .resolve()
            .parent
        )

    return (
        base_path
        / relative_path
    )


def set_windows_app_id():
    if sys.platform != "win32":
        return

    try:
        app_id = (
            "0337am.Presence."
            "Desktop"
        )

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            app_id
        )

    except Exception:
        pass


set_windows_app_id()

app = QApplication(
    sys.argv
)

app.setApplicationName(
    "03:37am Presence"
)
app.setOrganizationName(
    "03:37am"
)

icon_path = resource_path(
    "icons/app_icon.ico"
)

app_icon = QIcon(
    str(icon_path)
)

if not app_icon.isNull():
    app.setWindowIcon(
        app_icon
    )

window = MainWindow()

if not app_icon.isNull():
    window.setWindowIcon(
        app_icon
    )

tray_controller = TrayController(
    app,
    window,
)

window.show()

sys.exit(
    app.exec()
)