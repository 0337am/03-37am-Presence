from __future__ import annotations

import os
from pathlib import Path
import unittest

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QApplication,
)

from src.spotify.connection_controller import (
    SpotifyConnectionStatus,
)
from src.spotify.qt_connection_runtime import (
    SpotifyQtConnectionState,
)
from src.ui.spotify_connection_card import (
    SpotifyConnectionCard,
)


ROOT = (
    Path(
        __file__
    )
    .resolve()
    .parents[1]
)

PUBLIC_CLIENT_ID = (
    "2e081ef05a434508b7158732cb45cfaa"
)


class FakeSpotifyRuntime(
    QObject
):
    result_ready = pyqtSignal(
        str,
        object,
    )

    failed = pyqtSignal(
        str,
        str,
        str,
    )

    busy_changed = pyqtSignal(
        bool
    )

    def __init__(
        self,
    ):
        super().__init__()

        self.calls = []
        self.active_operation = None

    def _begin(
        self,
        operation,
    ):
        self.calls.append(
            operation
        )

        self.active_operation = (
            operation
        )

        self.busy_changed.emit(
            True
        )

    def restore(
        self,
    ):
        self._begin(
            "restore"
        )

    def connect_spotify(
        self,
    ):
        self._begin(
            "connect"
        )

    def disconnect(
        self,
    ):
        self._begin(
            "disconnect"
        )

    def complete(
        self,
        operation,
        status,
        message,
    ):
        self.result_ready.emit(
            operation,
            SpotifyQtConnectionState(
                status=status,
                message=message,
            ),
        )

        self.active_operation = None

        self.busy_changed.emit(
            False
        )

    def fail(
        self,
        operation,
        code,
        message,
    ):
        self.failed.emit(
            operation,
            code,
            message,
        )

        self.active_operation = None

        self.busy_changed.emit(
            False
        )


class SpotifySettingsUiTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = (
            QApplication.instance()
            or QApplication(
                []
            )
        )

    def make_card(
        self,
    ):
        runtime = (
            FakeSpotifyRuntime()
        )

        card = SpotifyConnectionCard(
            runtime
        )

        return (
            runtime,
            card,
        )

    def test_card_starts_not_connected(
        self,
    ):
        runtime, card = (
            self.make_card()
        )

        self.assertFalse(
            card.connected
        )

        self.assertEqual(
            card.connect_button.text(),
            "Connect Spotify",
        )

        self.assertTrue(
            card.connect_button.isVisibleTo(
                card
            )
        )

        card.deleteLater()

    def test_restore_is_forwarded_to_runtime(
        self,
    ):
        runtime, card = (
            self.make_card()
        )

        card.restore()

        self.assertEqual(
            runtime.calls,
            [
                "restore",
            ],
        )

        self.assertTrue(
            card.busy
        )

        runtime.complete(
            "restore",
            SpotifyConnectionStatus.CONNECTED,
            "Spotify is connected.",
        )

        self.assertTrue(
            card.connected
        )

        self.assertEqual(
            card.connection_status.text(),
            "Connected",
        )

        card.deleteLater()

    def test_connect_is_forwarded_to_runtime(
        self,
    ):
        runtime, card = (
            self.make_card()
        )

        card.connect_spotify()

        self.assertEqual(
            runtime.calls,
            [
                "connect",
            ],
        )

        runtime.complete(
            "connect",
            SpotifyConnectionStatus.CONNECTED,
            "Spotify is connected.",
        )

        self.assertTrue(
            card.connected
        )

        self.assertTrue(
            card.disconnect_button.isVisibleTo(
                card
            )
        )

        card.deleteLater()

    def test_disconnect_returns_to_safe_state(
        self,
    ):
        runtime, card = (
            self.make_card()
        )

        runtime.complete(
            "restore",
            SpotifyConnectionStatus.CONNECTED,
            "Spotify is connected.",
        )

        card.disconnect_spotify()

        self.assertEqual(
            runtime.calls,
            [
                "disconnect",
            ],
        )

        runtime.complete(
            "disconnect",
            SpotifyConnectionStatus.DISCONNECTED,
            "Spotify is disconnected.",
        )

        self.assertFalse(
            card.connected
        )

        self.assertEqual(
            card.connection_status.text(),
            "Not connected",
        )

        card.deleteLater()

    def test_reauthorization_changes_button_text(
        self,
    ):
        runtime, card = (
            self.make_card()
        )

        runtime.complete(
            "restore",
            (
                SpotifyConnectionStatus
                .REAUTHORIZATION_REQUIRED
            ),
            "Spotify must be connected again.",
        )

        self.assertFalse(
            card.connected
        )

        self.assertEqual(
            card.connection_status.text(),
            "Reconnect required",
        )

        self.assertEqual(
            card.connect_button.text(),
            "Reconnect Spotify",
        )

        card.deleteLater()

    def test_cancelled_authorization_is_not_error(
        self,
    ):
        runtime, card = (
            self.make_card()
        )

        runtime.complete(
            "connect",
            SpotifyConnectionStatus.CANCELLED,
            "Spotify authorization was cancelled.",
        )

        self.assertFalse(
            card.connected
        )

        self.assertEqual(
            card.connection_status.text(),
            "Not connected",
        )

        card.deleteLater()

    def test_runtime_failure_is_safe(
        self,
    ):
        runtime, card = (
            self.make_card()
        )

        runtime.fail(
            "connect",
            "authorization_failed",
            (
                "Spotify authorization did not "
                "complete successfully."
            ),
        )

        self.assertEqual(
            card.connection_status.text(),
            "Spotify connection error",
        )

        rendered = (
            card.connection_detail.text()
        )

        self.assertNotIn(
            "access_token",
            rendered,
        )

        self.assertNotIn(
            "refresh_token",
            rendered,
        )

        card.deleteLater()

    def test_missing_runtime_is_disabled(
        self,
    ):
        card = SpotifyConnectionCard(
            None
        )

        self.assertFalse(
            card.connect_button.isEnabled()
        )

        self.assertFalse(
            card.connected
        )

        card.deleteLater()


class SpotifySettingsSourceBoundaryTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.constants = (
            ROOT
            / "src"
            / "spotify"
            / "constants.py"
        ).read_text(
            encoding="utf-8"
        )

        cls.card = (
            ROOT
            / "src"
            / "ui"
            / "spotify_connection_card.py"
        ).read_text(
            encoding="utf-8"
        )

        cls.settings = (
            ROOT
            / "src"
            / "ui"
            / "settings.py"
        ).read_text(
            encoding="utf-8"
        )

        cls.main_window = (
            ROOT
            / "src"
            / "ui"
            / "main_window.py"
        ).read_text(
            encoding="utf-8"
        )

        cls.main = (
            ROOT
            / "main.py"
        ).read_text(
            encoding="utf-8"
        )

    def test_public_client_id_has_explicit_home(
        self,
    ):
        self.assertIn(
            "SPOTIFY_PUBLIC_CLIENT_ID",
            self.constants,
        )

        self.assertIn(
            PUBLIC_CLIENT_ID,
            self.constants,
        )

        self.assertNotIn(
            "client_secret",
            self.constants.lower(),
        )

    def test_main_window_is_composition_root(
        self,
    ):
        self.assertIn(
            "SpotifyQtConnectionRuntime",
            self.main_window,
        )

        self.assertIn(
            "SPOTIFY_PUBLIC_CLIENT_ID",
            self.main_window,
        )

        self.assertIn(
            "spotify_runtime=(",
            self.main_window,
        )

    def test_settings_has_spotify_card_and_deep_link(
        self,
    ):
        self.assertIn(
            "SpotifyConnectionCard",
            self.settings,
        )

        self.assertIn(
            '"spotify": (',
            self.settings,
        )

        self.assertIn(
            '"spotify account": "spotify"',
            self.settings,
        )

        self.assertIn(
            '"connect spotify": "spotify"',
            self.settings,
        )

    def test_production_startup_restores_session(
        self,
    ):
        self.assertIn(
            "window.restore_spotify_connection",
            self.main,
        )

        self.assertIn(
            "QTimer.singleShot(",
            self.main,
        )

    def test_card_never_handles_oauth_credentials(
        self,
    ):
        forbidden = (
            "SpotifyTokenBundle",
            "credential_store",
            "CryptProtectData",
            "CryptUnprotectData",
            "access_token",
            "refresh_token",
            "client_secret",
            "QSettings",
            "spotify_auth.dat",
        )

        for marker in forbidden:
            with self.subTest(
                marker=marker
            ):
                self.assertNotIn(
                    marker,
                    self.card,
                )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
