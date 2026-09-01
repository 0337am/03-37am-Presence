import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtCore import QEvent
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
)

from src.ui.tray import TrayController


class TrayCloseBehaviorTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def setUp(self):
        self.window = QMainWindow()

        with (
            patch.object(
                TrayController,
                "create_tray_icon",
            ),
            patch.object(
                TrayController,
                "connect_presence_controller",
            ),
        ):
            self.controller = TrayController(
                self.app,
                self.window,
            )

    def tearDown(self):
        self.window.removeEventFilter(
            self.controller
        )

        self.controller._quitting = True
        self.window.close()

    def test_native_close_hides_to_tray(
        self,
    ):
        self.controller.tray_icon = object()
        self.controller.hide_window = Mock()
        self.controller.quit_application = Mock()

        event = QCloseEvent()

        handled = self.controller.eventFilter(
            self.window,
            event,
        )

        self.assertTrue(handled)
        self.assertFalse(event.isAccepted())

        self.controller.hide_window.assert_called_once_with()
        self.controller.quit_application.assert_not_called()

    def test_native_close_without_tray_falls_through(
        self,
    ):
        self.controller.tray_icon = None
        self.controller.hide_window = Mock()
        self.controller.quit_application = Mock()

        event = QCloseEvent()

        handled = self.controller.eventFilter(
            self.window,
            event,
        )

        self.assertFalse(handled)

        self.controller.hide_window.assert_not_called()
        self.controller.quit_application.assert_not_called()

    def test_close_during_existing_quit_is_not_intercepted(
        self,
    ):
        self.controller.tray_icon = object()
        self.controller._quitting = True
        self.controller.hide_window = Mock()
        self.controller.quit_application = Mock()

        event = QCloseEvent()

        handled = self.controller.eventFilter(
            self.window,
            event,
        )

        self.assertFalse(handled)

        self.controller.hide_window.assert_not_called()
        self.controller.quit_application.assert_not_called()

    def test_non_close_event_is_not_intercepted(
        self,
    ):
        self.controller.tray_icon = object()
        self.controller.hide_window = Mock()
        self.controller.quit_application = Mock()

        event = QEvent(
            QEvent.Type.WindowStateChange
        )

        handled = self.controller.eventFilter(
            self.window,
            event,
        )

        self.assertFalse(handled)

        self.controller.hide_window.assert_not_called()
        self.controller.quit_application.assert_not_called()


if __name__ == "__main__":
    unittest.main()
