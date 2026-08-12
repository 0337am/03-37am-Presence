import ctypes
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import (
    QLockFile,
    QTimer,
)
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox

from src.system.startup import StartupManager
from src.system.first_run import (
    FirstRunDecision,
    FirstRunManager,
)
from src.system.startup_native_stage import install_startup_native_stage
from src.ui.main_window import MainWindow
from src.ui.tray import TrayController
from src.ui.welcome import WelcomeDialog
from src.ui.welcome_flow import (
    WelcomeFlow,
    command_line_starts_minimized,
    should_show_main_window,
)

from src.system.media_hotkey_runtime import (
    MediaHotkeyRuntime,
)


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


def crash_log_directory() -> Path:
    local_app_data = os.environ.get(
        "LOCALAPPDATA"
    )

    if local_app_data:
        return (
            Path(local_app_data)
            / "0337am Presence"
            / "logs"
        )

    return (
        Path.home()
        / ".0337am-presence"
        / "logs"
    )


def write_crash_log(
    exception_type,
    exception_value,
    exception_traceback,
) -> Path | None:
    try:
        log_directory = (
            crash_log_directory()
        )

        log_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        timestamp = (
            datetime.now().astimezone()
        )

        log_path = (
            log_directory
            / (
                "crash_"
                + timestamp.strftime(
                    "%Y%m%d_%H%M%S_%f"
                )
                + ".log"
            )
        )

        traceback_text = "".join(
            traceback.format_exception(
                exception_type,
                exception_value,
                exception_traceback,
            )
        )

        python_version = (
            sys.version.replace(
                "\n",
                " ",
            )
        )

        report = (
            "03:37am Presence crash report\n"
            "================================\n"
            f"Timestamp: {timestamp.isoformat()}\n"
            f"Python: {python_version}\n"
            f"Executable: {sys.executable}\n"
            "Packaged: "
            f"{bool(getattr(sys, 'frozen', False))}\n"
            f"Platform: {sys.platform}\n"
            "\n"
            "Traceback\n"
            "---------\n"
            f"{traceback_text}"
        )

        log_path.write_text(
            report,
            encoding="utf-8",
        )

        return log_path

    except Exception:
        return None


def handle_unhandled_exception(
    exception_type,
    exception_value,
    exception_traceback,
):
    if issubclass(
        exception_type,
        KeyboardInterrupt,
    ):
        sys.__excepthook__(
            exception_type,
            exception_value,
            exception_traceback,
        )
        return

    log_path = write_crash_log(
        exception_type,
        exception_value,
        exception_traceback,
    )

    if log_path is not None:
        log_message = (
            "\n\nA crash report was saved to:\n"
            f"{log_path}"
        )
    else:
        log_message = (
            "\n\nThe crash report could not be saved."
        )

    app = QApplication.instance()

    if app is not None:
        try:
            QMessageBox.critical(
                None,
                "03:37am Presence - Unexpected Error",
                (
                    "03:37am Presence encountered an "
                    "unexpected error and must close."
                    f"{log_message}"
                ),
            )

            app.exit(
                1
            )

        except Exception:
            pass

    sys.__excepthook__(
        exception_type,
        exception_value,
        exception_traceback,
    )


def acquire_single_instance_lock() -> QLockFile:
    local_app_data = os.environ.get(
        "LOCALAPPDATA"
    )

    if local_app_data:
        lock_directory = (
            Path(local_app_data)
            / "0337am Presence"
        )
    else:
        lock_directory = (
            Path.home()
            / ".0337am-presence"
        )

    lock_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    lock = QLockFile(
        str(
            lock_directory
            / "03-37am Presence.lock"
        )
    )

    lock.setStaleLockTime(
        0
    )

    if lock.tryLock(
        100
    ):
        return lock

    QMessageBox.information(
        None,
        "03:37am Presence",
        (
            "03:37am Presence is already running.\n\n"
            "Check the system tray for the existing app."
        ),
    )

    raise SystemExit(
        0
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



def start_media_hotkey_runtime(
    app,
):
    runtime = None

    try:
        runtime = MediaHotkeyRuntime(
            app=app
        )

        app.aboutToQuit.connect(
            runtime.close
        )

        if not runtime.start():
            print(
                "Media hotkey runtime "
                "could not start."
            )

        return runtime

    except Exception as error:
        print(
            "Media hotkey runtime "
            "setup error:",
            error,
        )

        if runtime is not None:
            try:
                runtime.close()
            except Exception:
                pass

        return None


STARTUP_WINDOW_WARMUP_MS = 200
STARTUP_SPOTIFY_SETTLE_GRACE_MS = 100
STARTUP_REVEAL_FALLBACK_MS = 2500


def _show_window_when_startup_ready(
    window,
) -> None:
    from PyQt6.QtCore import Qt as _Qt

    hidden_native_attribute = (
        _Qt.WidgetAttribute.WA_DontShowOnScreen
    )

    state = {
        "warmup_complete": False,
        "spotify_ready": True,
        "spotify_grace_pending": False,
        "revealed": False,
    }

    def reveal_if_ready() -> None:
        if (
            state["revealed"]
            or not state["warmup_complete"]
            or not state["spotify_ready"]
        ):
            return

        state["revealed"] = True

        try:
            window.hide()
            window.setAttribute(
                hidden_native_attribute,
                False,
            )
            window.show()
        except RuntimeError:
            return

    def mark_warmup_complete() -> None:
        state["warmup_complete"] = True
        reveal_if_ready()

    def mark_spotify_settled() -> None:
        if (
            state["revealed"]
            or state["spotify_ready"]
            or state["spotify_grace_pending"]
        ):
            return

        state["spotify_grace_pending"] = True

        def finish_spotify_grace() -> None:
            state["spotify_grace_pending"] = False

            if state["revealed"]:
                return

            state["spotify_ready"] = True
            reveal_if_ready()

        QTimer.singleShot(
            STARTUP_SPOTIFY_SETTLE_GRACE_MS,
            finish_spotify_grace,
        )

    def force_reveal() -> None:
        if state["revealed"]:
            return

        state["warmup_complete"] = True
        state["spotify_ready"] = True
        reveal_if_ready()

    spotify_home = None

    try:
        pages = getattr(
            window,
            "pages",
            None,
        )

        spotify_page = getattr(
            window,
            "spotify_page",
            None,
        )

        if (
            pages is not None
            and spotify_page is not None
            and pages.currentWidget()
            is spotify_page
        ):
            content_stack = getattr(
                spotify_page,
                "content_stack",
                None,
            )

            candidate_home = getattr(
                spotify_page,
                "playlist_home",
                None,
            )

            if (
                content_stack is not None
                and candidate_home is not None
                and content_stack.currentWidget()
                is candidate_home
            ):
                spotify_home = candidate_home

    except Exception:
        spotify_home = None

    if spotify_home is not None:
        settled_check = getattr(
            spotify_home,
            "initial_content_is_settled",
            None,
        )

        settled_signal = getattr(
            spotify_home,
            "initial_content_settled",
            None,
        )

        connect = getattr(
            settled_signal,
            "connect",
            None,
        )

        if (
            callable(settled_check)
            and callable(connect)
        ):
            state["spotify_ready"] = False

            try:
                connect(
                    mark_spotify_settled
                )

                if bool(settled_check()):
                    mark_spotify_settled()

            except Exception:
                state["spotify_ready"] = True

    window.setAttribute(
        hidden_native_attribute,
        True,
    )

    window.show()

    QTimer.singleShot(
        STARTUP_WINDOW_WARMUP_MS,
        mark_warmup_complete,
    )

    QTimer.singleShot(
        STARTUP_REVEAL_FALLBACK_MS,
        force_reveal,
    )

def main() -> int:
    sys.excepthook = (
        handle_unhandled_exception
    )

    set_windows_app_id()

    StartupManager.repair_packaged_entry()

    app = QApplication(
        sys.argv
    )

    app.setApplicationName(
        "03:37am Presence"
    )
    app.setOrganizationName(
        "03:37am"
    )

    first_run_manager = (
        FirstRunManager()
    )

    try:
        first_run_decision = (
            first_run_manager.evaluate()
        )
    except Exception as error:
        print(
            "First-run setup error:",
            error,
        )

        first_run_decision = (
            FirstRunDecision(
                show_welcome=False,
                migrated_existing_install=False,
                reason="error",
            )
        )

    instance_lock = (
        acquire_single_instance_lock()
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

    install_startup_native_stage(
        MainWindow
    )

    window = MainWindow()

    QTimer.singleShot(
        0,
        window.restore_spotify_connection,
    )

    if not app_icon.isNull():
        window.setWindowIcon(
            app_icon
        )

    tray_controller = TrayController(
        app,
        window,
    )

    media_hotkey_runtime = (
        start_media_hotkey_runtime(
            app
        )
    )

    window.set_media_hotkey_reload_callback(
        (
            media_hotkey_runtime.reload
            if media_hotkey_runtime is not None
            else None
        )
    )

    window.set_update_quit_callback(
        tray_controller.quit_application
    )

    start_minimized = (
        command_line_starts_minimized(
            sys.argv
        )
    )

    show_main_window = (
        should_show_main_window(
            show_welcome=(
                first_run_decision
                .show_welcome
            ),
            start_minimized=(
                start_minimized
            ),
        )
    )

    if show_main_window:
        _show_window_when_startup_ready(
            window
        )

    welcome_dialog = None
    welcome_flow = None

    if (
        first_run_decision
        .show_welcome
    ):
        welcome_dialog = (
            WelcomeDialog(
                theme=(
                    window
                    .theme_manager
                    .theme()
                ),
                parent=window,
            )
        )

        if not app_icon.isNull():
            welcome_dialog.setWindowIcon(
                app_icon
            )

        welcome_flow = WelcomeFlow(
            manager=(
                first_run_manager
            ),
            main_window=window,
            dialog=welcome_dialog,
        )

        welcome_dialog.action_requested.connect(
            welcome_flow.handle_action
        )

        welcome_dialog.show()
        welcome_dialog.raise_()
        welcome_dialog.activateWindow()

    return app.exec()


if __name__ == "__main__":
    sys.exit(
        main()
    )
