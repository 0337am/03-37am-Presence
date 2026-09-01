from PyQt6.QtCore import (
    QEvent,
    QObject,
)
from PyQt6.QtGui import (
    QAction,
    QActionGroup,
    QIcon,
)
from PyQt6.QtWidgets import (
    QApplication,
    QMenu,
    QStyle,
    QSystemTrayIcon,
)


class TrayController(QObject):
    def __init__(
        self,
        app: QApplication,
        main_window,
    ):
        super().__init__()

        self.app = app
        self.main_window = main_window
        self.tray_icon = None

        self.mode_actions = {}
        self._companion_runtime = None

        self.companion_action = QAction(
            "Desktop Companion",
            self,
        )

        self.companion_action.setCheckable(
            True
        )

        self.companion_action.setEnabled(
            False
        )

        self.companion_action.triggered.connect(
            self.on_companion_action_triggered
        )
        self.mode_action_group = None

        self._quitting = False
        self._message_shown = False

        self.app.setQuitOnLastWindowClosed(
            False
        )

        self.main_window.installEventFilter(
            self
        )

        self.create_tray_icon()
        self.connect_presence_controller()

    def create_tray_icon(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print(
                "Windows system tray "
                "is not available."
            )
            return

        icon = self.app.windowIcon()

        if icon.isNull():
            icon = self.main_window.windowIcon()

        if icon.isNull():
            icon = (
                self.main_window
                .style()
                .standardIcon(
                    QStyle.StandardPixmap.SP_ComputerIcon
                )
            )

        self.main_window.setWindowIcon(
            icon
        )

        self.tray_icon = QSystemTrayIcon(
            icon,
            self,
        )

        self.tray_icon.setToolTip(
            "03:37am Presence"
        )

        menu = QMenu()

        open_action = QAction(
            "Open 03:37am Presence",
            self,
        )

        hide_action = QAction(
            "Hide window",
            self,
        )

        quit_action = QAction(
            "Quit",
            self,
        )

        presence_menu = QMenu(
            "Presence Mode",
            menu,
        )

        self.mode_action_group = QActionGroup(
            self
        )

        self.mode_action_group.setExclusive(
            True
        )

        modes = (
            ("music", "Music"),
            ("afk", "AFK"),
            ("sleep", "Sleep"),
            ("working", "Working"),
            ("custom", "Custom"),
            ("disabled", "Disabled"),
        )

        for mode, display_name in modes:
            mode_action = QAction(
                display_name,
                self,
            )

            mode_action.setData(
                mode
            )

            mode_action.setCheckable(
                True
            )

            self.mode_action_group.addAction(
                mode_action
            )

            presence_menu.addAction(
                mode_action
            )

            self.mode_actions[
                mode
            ] = mode_action

        self.mode_action_group.triggered.connect(
            self.on_mode_action_triggered
        )

        open_action.triggered.connect(
            self.show_window
        )

        hide_action.triggered.connect(
            self.hide_window
        )

        quit_action.triggered.connect(
            self.quit_application
        )

        menu.addAction(
            open_action
        )
        menu.addAction(
            hide_action
        )
        menu.addAction(
            self.companion_action
        )
        menu.addSeparator()

        menu.addMenu(
            presence_menu
        )

        menu.addSeparator()
        menu.addAction(
            quit_action
        )

        self.tray_icon.setContextMenu(
            menu
        )

        self.tray_icon.activated.connect(
            self.on_tray_activated
        )

        self.tray_icon.show()

    def set_companion_runtime(
        self,
        runtime,
    ):
        previous = self._companion_runtime

        if previous is runtime:
            self.sync_companion_action()
            return

        if previous is not None:
            signal = getattr(
                previous,
                "preferences_changed",
                None,
            )

            disconnect = getattr(
                signal,
                "disconnect",
                None,
            )

            if callable(disconnect):
                try:
                    disconnect(
                        self._companion_preferences_changed
                    )
                except (
                    TypeError,
                    RuntimeError,
                    ValueError,
                ):
                    pass

        self._companion_runtime = runtime

        if runtime is not None:
            signal = getattr(
                runtime,
                "preferences_changed",
                None,
            )

            connect = getattr(
                signal,
                "connect",
                None,
            )

            if callable(connect):
                try:
                    connect(
                        self._companion_preferences_changed
                    )
                except (
                    TypeError,
                    RuntimeError,
                ):
                    pass

        self.sync_companion_action()

    def _companion_preferences_changed(
        self,
        preferences,
    ):
        self.sync_companion_action(
            preferences
        )

    def sync_companion_action(
        self,
        preferences=None,
    ):
        action = getattr(
            self,
            "companion_action",
            None,
        )

        if action is None:
            return

        runtime = getattr(
            self,
            "_companion_runtime",
            None,
        )

        available = runtime is not None

        if available:
            try:
                available = not bool(
                    getattr(
                        runtime,
                        "is_shutdown",
                        False,
                    )
                )
            except Exception:
                available = False

        checked = False

        if available:
            try:
                if preferences is None:
                    preferences = getattr(
                        runtime,
                        "preferences",
                        None,
                    )

                if preferences is None:
                    available = False
                else:
                    checked = bool(
                        getattr(
                            preferences,
                            "enabled",
                            False,
                        )
                    )

            except Exception:
                available = False
                checked = False

        previous_block_state = (
            action.blockSignals(True)
        )

        try:
            action.setEnabled(
                available
            )

            action.setChecked(
                checked
                if available
                else False
            )

        finally:
            action.blockSignals(
                previous_block_state
            )

    def on_companion_action_triggered(
        self,
        checked=False,
    ):
        runtime = getattr(
            self,
            "_companion_runtime",
            None,
        )

        if runtime is None:
            self.sync_companion_action()
            return

        try:
            if bool(
                getattr(
                    runtime,
                    "is_shutdown",
                    False,
                )
            ):
                self.sync_companion_action()
                return

            updater = getattr(
                runtime,
                "update_preferences",
                None,
            )

            if not callable(updater):
                self.sync_companion_action()
                return

            preferences = updater(
                enabled=bool(checked)
            )

        except Exception:
            self.sync_companion_action()
            return

        self.sync_companion_action(
            preferences
        )
    def presence_controller(self):
        controller = getattr(
            self.main_window,
            "presence_controller",
            None,
        )

        if controller is not None:
            return controller

        presence_page = getattr(
            self.main_window,
            "presence_page",
            None,
        )

        return getattr(
            presence_page,
            "controller",
            None,
        )

    def connect_presence_controller(self):
        controller = (
            self.presence_controller()
        )

        if controller is None:
            print(
                "Tray could not find the "
                "PresenceController."
            )
            return

        controller.mode_changed.connect(
            self.sync_mode_actions
        )

        self.sync_mode_actions()

    def on_mode_action_triggered(
        self,
        action,
    ):
        mode = str(
            action.data()
            or "music"
        )

        self.set_presence_mode(
            mode
        )

    def set_presence_mode(
        self,
        mode: str,
    ):
        controller = (
            self.presence_controller()
        )

        if controller is None:
            return

        normalized = str(
            mode or "music"
        ).strip().lower()

        try:
            presence_mode = (
                controller.load_mode(
                    normalized
                )
            )

            controller.apply_mode(
                presence_mode
            )

            presence_page = getattr(
                self.main_window,
                "presence_page",
                None,
            )

            if (
                presence_page is not None
                and hasattr(
                    presence_page,
                    "load_active_mode",
                )
            ):
                presence_page.load_active_mode()

            self.sync_mode_actions(
                {
                    "mode": normalized,
                }
            )

            display_name = (
                self.mode_actions[
                    normalized
                ].text()
            )

            if normalized == "disabled":
                message = (
                    "Discord Rich Presence "
                    "has been disabled."
                )
            else:
                message = (
                    f"{display_name} presence "
                    "is now active."
                )

            if self.tray_icon is not None:
                self.tray_icon.showMessage(
                    "03:37am Presence",
                    message,
                    QSystemTrayIcon
                    .MessageIcon
                    .Information,
                    2200,
                )

        except Exception as error:
            print(
                "Tray presence change failed:",
                error,
            )

            self.sync_mode_actions()

    def sync_mode_actions(
        self,
        payload=None,
    ):
        controller = (
            self.presence_controller()
        )

        if controller is None:
            return

        mode = ""

        if isinstance(
            payload,
            dict,
        ):
            mode = str(
                payload.get(
                    "mode",
                    "",
                )
            ).strip().lower()

        if not mode:
            if getattr(
                controller,
                "auto_afk_active",
                False,
            ):
                mode = "afk"
            else:
                mode = str(
                    controller.active_mode
                ).strip().lower()

        for action_mode, action in (
            self.mode_actions.items()
        ):
            action.blockSignals(
                True
            )

            action.setChecked(
                action_mode == mode
            )

            action.blockSignals(
                False
            )

        active_action = self.mode_actions.get(
            mode
        )

        if (
            active_action is not None
            and self.tray_icon is not None
        ):
            self.tray_icon.setToolTip(
                "03:37am Presence"
                f" — {active_action.text()}"
            )

    def eventFilter(
        self,
        watched,
        event,
    ):
        closing_window = (
            watched is self.main_window
            and event.type()
            == QEvent.Type.Close
        )

        if (
            closing_window
            and not self._quitting
            and self.tray_icon is not None
        ):
            event.ignore()
            self.hide_window()
            return True

        return super().eventFilter(
            watched,
            event,
        )

    def on_tray_activated(
        self,
        reason,
    ):
        valid_reasons = (
            QSystemTrayIcon
            .ActivationReason
            .Trigger,

            QSystemTrayIcon
            .ActivationReason
            .DoubleClick,
        )

        if reason not in valid_reasons:
            return

        if self.main_window.isVisible():
            self.hide_window(
                show_message=False
            )
        else:
            self.show_window()

    def show_window(
        self,
        checked=False,
    ):
        self.main_window.showNormal()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def hide_window(
        self,
        checked=False,
        show_message=True,
    ):
        self.main_window.hide()

        if (
            show_message
            and not self._message_shown
            and self.tray_icon is not None
        ):
            self.tray_icon.showMessage(
                "03:37am Presence",
                (
                    "The app is still running "
                    "in the system tray."
                ),
                QSystemTrayIcon
                .MessageIcon
                .Information,
                3000,
            )

            self._message_shown = True

    def quit_application(
        self,
        checked=False,
    ):
        self._quitting = True

        if self.tray_icon is not None:
            self.tray_icon.hide()

        self.main_window.close()
        self.app.quit()
