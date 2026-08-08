from __future__ import annotations

from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from src.spotify.qt_connection_runtime import (
    SpotifyQtConnectionRuntimeError,
)


class SpotifyConnectionCard(
    QFrame
):
    message_changed = pyqtSignal(
        str
    )

    def __init__(
        self,
        runtime=None,
        parent=None,
    ) -> None:
        super().__init__(
            parent
        )

        self.setObjectName(
            "settingsCard"
        )

        self._runtime = runtime
        self._connected = False
        self._requires_reauthorization = False
        self._busy = False

        self._build_ui()
        self._connect_runtime()

        if runtime is None:
            self._show_unavailable()
        else:
            self._show_not_connected(
                (
                    "Checking for a saved Spotify "
                    "connection has not started yet."
                )
            )

    @property
    def connected(
        self,
    ) -> bool:
        return self._connected

    @property
    def busy(
        self,
    ) -> bool:
        return self._busy

    def _build_ui(
        self,
    ) -> None:
        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            18,
            16,
            18,
            16,
        )

        layout.setSpacing(
            10
        )

        title = QLabel(
            "Spotify"
        )

        title.setObjectName(
            "cardTitle"
        )

        description = QLabel(
            (
                "Securely connect Spotify to unlock "
                "account-backed features such as your "
                "library, playlists, devices and playback "
                "controls. Windows media support remains "
                "available without Spotify."
            )
        )

        description.setObjectName(
            "cardDescription"
        )

        description.setWordWrap(
            True
        )

        self.connection_status = QLabel(
            "Not connected"
        )

        self.connection_status.setObjectName(
            "status"
        )

        self.connection_status.setWordWrap(
            True
        )

        self.connection_detail = QLabel(
            ""
        )

        self.connection_detail.setObjectName(
            "helpText"
        )

        self.connection_detail.setWordWrap(
            True
        )

        privacy = QLabel(
            (
                "OAuth tokens are encrypted with Windows "
                "DPAPI for the current Windows account. "
                "They are not stored in Settings backups."
            )
        )

        privacy.setObjectName(
            "helpText"
        )

        privacy.setWordWrap(
            True
        )

        button_row = QHBoxLayout()

        button_row.setSpacing(
            8
        )

        self.connect_button = QPushButton(
            "Connect Spotify"
        )

        self.connect_button.setObjectName(
            "secondaryButton"
        )

        self.connect_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.connect_button.clicked.connect(
            self.connect_spotify
        )

        self.disconnect_button = QPushButton(
            "Disconnect Spotify"
        )

        self.disconnect_button.setObjectName(
            "dangerButton"
        )

        self.disconnect_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.disconnect_button.clicked.connect(
            self.disconnect_spotify
        )

        self.disconnect_button.setVisible(
            False
        )

        button_row.addWidget(
            self.connect_button
        )

        button_row.addWidget(
            self.disconnect_button
        )

        button_row.addStretch()

        layout.addWidget(
            title
        )

        layout.addWidget(
            description
        )

        layout.addWidget(
            self.connection_status
        )

        layout.addWidget(
            self.connection_detail
        )

        layout.addWidget(
            privacy
        )

        layout.addLayout(
            button_row
        )

    def _connect_runtime(
        self,
    ) -> None:
        runtime = self._runtime

        if runtime is None:
            return

        runtime.result_ready.connect(
            self._handle_result
        )

        runtime.failed.connect(
            self._handle_failure
        )

        runtime.busy_changed.connect(
            self._handle_busy
        )

    def _status_value(
        self,
        result,
    ) -> str:
        status = getattr(
            result,
            "status",
            "",
        )

        value = getattr(
            status,
            "value",
            status,
        )

        return str(
            value or ""
        ).strip().lower()

    def _set_detail(
        self,
        message: str,
    ) -> None:
        checked = str(
            message or ""
        ).strip()

        self.connection_detail.setText(
            checked
        )

        if checked:
            self.message_changed.emit(
                checked
            )

    def _sync_buttons(
        self,
    ) -> None:
        available = (
            self._runtime is not None
        )

        self.connect_button.setEnabled(
            available
            and not self._busy
            and not self._connected
        )

        self.disconnect_button.setEnabled(
            available
            and not self._busy
            and self._connected
        )

        self.connect_button.setVisible(
            not self._connected
        )

        self.disconnect_button.setVisible(
            self._connected
        )

        self.connect_button.setText(
            (
                "Reconnect Spotify"
                if self._requires_reauthorization
                else "Connect Spotify"
            )
        )

    def _show_unavailable(
        self,
    ) -> None:
        self._connected = False
        self._requires_reauthorization = False

        self.connection_status.setText(
            "Spotify connection unavailable"
        )

        self.connection_detail.setText(
            (
                "The Spotify connection runtime "
                "is not available in this context."
            )
        )

        self._sync_buttons()

    def _show_not_connected(
        self,
        message: str,
    ) -> None:
        self._connected = False
        self._requires_reauthorization = False

        self.connection_status.setText(
            "Not connected"
        )

        self._set_detail(
            message
        )

        self._sync_buttons()

    def _show_connected(
        self,
        message: str,
        *,
        refreshed: bool = False,
    ) -> None:
        self._connected = True
        self._requires_reauthorization = False

        self.connection_status.setText(
            (
                "Connected and refreshed"
                if refreshed
                else "Connected"
            )
        )

        self._set_detail(
            message
            or "Spotify is securely connected."
        )

        self._sync_buttons()

    def _show_reauthorization(
        self,
        message: str,
    ) -> None:
        self._connected = False
        self._requires_reauthorization = True

        self.connection_status.setText(
            "Reconnect required"
        )

        self._set_detail(
            message
            or (
                "Spotify needs permission to "
                "connect again."
            )
        )

        self._sync_buttons()

    def restore(
        self,
    ) -> None:
        if self._runtime is None:
            self._show_unavailable()
            return

        self.connection_status.setText(
            "Checking saved connection..."
        )

        self._set_detail(
            (
                "Restoring your encrypted Spotify "
                "session."
            )
        )

        self._invoke_runtime(
            "restore"
        )

    @pyqtSlot()
    def connect_spotify(
        self,
    ) -> None:
        if self._runtime is None:
            self._show_unavailable()
            return

        self.connection_status.setText(
            "Waiting for Spotify..."
        )

        self._set_detail(
            (
                "Your browser will open Spotify's "
                "authorization page."
            )
        )

        self._invoke_runtime(
            "connect_spotify"
        )

    @pyqtSlot()
    def disconnect_spotify(
        self,
    ) -> None:
        if self._runtime is None:
            self._show_unavailable()
            return

        self.connection_status.setText(
            "Disconnecting..."
        )

        self._set_detail(
            (
                "Removing the locally encrypted "
                "Spotify authorization."
            )
        )

        self._invoke_runtime(
            "disconnect"
        )

    def _invoke_runtime(
        self,
        method_name: str,
    ) -> None:
        method = getattr(
            self._runtime,
            method_name,
            None,
        )

        if not callable(
            method
        ):
            self._show_failure(
                (
                    "The Spotify connection action "
                    "is unavailable."
                )
            )
            return

        try:
            method()

        except SpotifyQtConnectionRuntimeError as error:
            self._show_failure(
                error.message
            )

        except Exception:
            self._show_failure(
                (
                    "The Spotify connection action "
                    "could not be started."
                )
            )

    def _show_failure(
        self,
        message: str,
    ) -> None:
        self.connection_status.setText(
            "Spotify connection error"
        )

        self._set_detail(
            message
            or (
                "The Spotify connection action "
                "could not be completed."
            )
        )

        self._sync_buttons()

    @pyqtSlot(
        str,
        object,
    )
    def _handle_result(
        self,
        operation: str,
        result,
    ) -> None:
        status = self._status_value(
            result
        )

        message = str(
            getattr(
                result,
                "message",
                "",
            )
            or ""
        ).strip()

        if status == "connected":
            self._show_connected(
                message
            )
            return

        if status == "refreshed":
            self._show_connected(
                message,
                refreshed=True,
            )
            return

        if status == "disconnected":
            self._show_not_connected(
                (
                    message
                    or "Spotify is not connected."
                )
            )
            return

        if (
            status
            == "reauthorization_required"
        ):
            self._show_reauthorization(
                message
            )
            return

        if status == "cancelled":
            self._show_not_connected(
                (
                    message
                    or (
                        "Spotify authorization "
                        "was cancelled."
                    )
                )
            )
            return

        self._show_failure(
            (
                "Spotify returned an unexpected "
                "connection state."
            )
        )

    @pyqtSlot(
        str,
        str,
        str,
    )
    def _handle_failure(
        self,
        operation: str,
        error_code: str,
        message: str,
    ) -> None:
        self._show_failure(
            message
            or (
                "The Spotify connection operation "
                "failed."
            )
        )

    @pyqtSlot(
        bool,
    )
    def _handle_busy(
        self,
        busy: bool,
    ) -> None:
        self._busy = bool(
            busy
        )

        self._sync_buttons()
