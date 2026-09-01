import tempfile
import unittest
from pathlib import Path

from PyQt6.QtCore import QRect
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication

from src.companion.fullscreen import (
    CompanionFullscreenController,
    ForegroundFullscreenState,
    _classify_fullscreen_geometry,
    _rects_match,
)
from src.companion.overlay import CompanionOverlay
from src.companion.preferences import CompanionPreferences


class _FakeScreen:
    def __init__(
        self,
        geometry: QRect,
    ) -> None:
        self._geometry = QRect(
            geometry
        )

    def geometry(self) -> QRect:
        return QRect(
            self._geometry
        )


class _FakeOverlay:
    def __init__(
        self,
        geometry: QRect,
    ) -> None:
        self._screen = _FakeScreen(
            geometry
        )
        self.policy_hidden = False

    def screen(self):
        return self._screen

    def set_policy_hidden(
        self,
        hidden: bool,
    ) -> None:
        self.policy_hidden = hidden


class CompanionFullscreenTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def test_rect_match_accepts_small_dwm_variance(self):
        self.assertTrue(
            _rects_match(
                (
                    0,
                    0,
                    1920,
                    1080,
                ),
                (
                    1,
                    -1,
                    1919,
                    1082,
                ),
            )
        )

    def test_classifier_accepts_full_monitor_frame(self):
        self.assertTrue(
            _classify_fullscreen_geometry(
                frame_rect=(
                    0,
                    0,
                    1920,
                    1080,
                ),
                monitor_rect=(
                    0,
                    0,
                    1920,
                    1080,
                ),
                visible=True,
                iconic=False,
                excluded_shell=False,
            )
        )

    def test_classifier_rejects_work_area_maximized_frame(self):
        self.assertFalse(
            _classify_fullscreen_geometry(
                frame_rect=(
                    0,
                    0,
                    1920,
                    1032,
                ),
                monitor_rect=(
                    0,
                    0,
                    1920,
                    1080,
                ),
                visible=True,
                iconic=False,
                excluded_shell=False,
            )
        )

    def test_classifier_rejects_invisible_window(self):
        self.assertFalse(
            _classify_fullscreen_geometry(
                frame_rect=(
                    0,
                    0,
                    1920,
                    1080,
                ),
                monitor_rect=(
                    0,
                    0,
                    1920,
                    1080,
                ),
                visible=False,
                iconic=False,
                excluded_shell=False,
            )
        )

    def test_classifier_rejects_iconic_window(self):
        self.assertFalse(
            _classify_fullscreen_geometry(
                frame_rect=(
                    0,
                    0,
                    1920,
                    1080,
                ),
                monitor_rect=(
                    0,
                    0,
                    1920,
                    1080,
                ),
                visible=True,
                iconic=True,
                excluded_shell=False,
            )
        )

    def test_classifier_rejects_shell_or_desktop(self):
        self.assertFalse(
            _classify_fullscreen_geometry(
                frame_rect=(
                    0,
                    0,
                    1920,
                    1080,
                ),
                monitor_rect=(
                    0,
                    0,
                    1920,
                    1080,
                ),
                visible=True,
                iconic=False,
                excluded_shell=True,
            )
        )

    def test_controller_hides_for_same_monitor_fullscreen(self):
        overlay = _FakeOverlay(
            QRect(
                0,
                0,
                1920,
                1080,
            )
        )

        controller = CompanionFullscreenController(
            overlay,
            detector=lambda: ForegroundFullscreenState(
                True,
                (
                    0,
                    0,
                    1920,
                    1080,
                ),
            ),
        )

        controller.set_enabled(
            True
        )

        self.assertTrue(
            overlay.policy_hidden
        )

        controller.stop()

    def test_controller_keeps_visible_for_other_monitor(self):
        overlay = _FakeOverlay(
            QRect(
                0,
                0,
                1920,
                1080,
            )
        )

        controller = CompanionFullscreenController(
            overlay,
            detector=lambda: ForegroundFullscreenState(
                True,
                (
                    1920,
                    0,
                    3840,
                    1080,
                ),
            ),
        )

        controller.set_enabled(
            True
        )

        self.assertFalse(
            overlay.policy_hidden
        )

        controller.stop()

    def test_controller_unhides_when_fullscreen_ends(self):
        overlay = _FakeOverlay(
            QRect(
                0,
                0,
                1920,
                1080,
            )
        )

        states = iter(
            (
                ForegroundFullscreenState(
                    True,
                    (
                        0,
                        0,
                        1920,
                        1080,
                    ),
                ),
                ForegroundFullscreenState(),
            )
        )

        controller = CompanionFullscreenController(
            overlay,
            detector=lambda: next(
                states
            ),
            poll_interval_ms=60_000,
        )

        controller.set_enabled(
            True
        )

        self.assertTrue(
            overlay.policy_hidden
        )

        controller.poll_now()

        self.assertFalse(
            overlay.policy_hidden
        )

        controller.stop()

    def test_disabling_policy_unhides_and_stops_polling(self):
        overlay = _FakeOverlay(
            QRect(
                0,
                0,
                1920,
                1080,
            )
        )

        controller = CompanionFullscreenController(
            overlay,
            detector=lambda: ForegroundFullscreenState(
                True,
                (
                    0,
                    0,
                    1920,
                    1080,
                ),
            ),
            poll_interval_ms=60_000,
        )

        controller.set_enabled(
            True
        )

        self.assertTrue(
            controller.is_polling
        )

        self.assertTrue(
            overlay.policy_hidden
        )

        controller.set_enabled(
            False
        )

        self.assertFalse(
            controller.is_polling
        )

        self.assertFalse(
            overlay.policy_hidden
        )

    def test_detector_exception_fails_open(self):
        overlay = _FakeOverlay(
            QRect(
                0,
                0,
                1920,
                1080,
            )
        )

        def fail():
            raise RuntimeError(
                "synthetic detector failure"
            )

        controller = CompanionFullscreenController(
            overlay,
            detector=fail,
            poll_interval_ms=60_000,
        )

        controller.set_enabled(
            True
        )

        self.assertFalse(
            overlay.policy_hidden
        )

        controller.stop()

    def test_overlay_policy_hidden_round_trip(self):
        overlay = CompanionOverlay()

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                asset_path = (
                    Path(temp_dir)
                    / "companion.png"
                )

                image = QImage(
                    32,
                    32,
                    QImage.Format.Format_ARGB32,
                )

                image.fill(
                    0xFFFFFFFF
                )

                self.assertTrue(
                    image.save(
                        str(
                            asset_path
                        )
                    )
                )

                overlay.apply_preferences(
                    CompanionPreferences(
                        enabled=True,
                        asset_path=str(
                            asset_path
                        ),
                        remember_position=False,
                    )
                )

                self.app.processEvents()

                self.assertTrue(
                    overlay.requested_visible
                )

                self.assertFalse(
                    overlay.policy_hidden
                )

                self.assertTrue(
                    overlay.isVisible()
                )

                overlay.set_policy_hidden(
                    True
                )

                self.app.processEvents()

                self.assertTrue(
                    overlay.policy_hidden
                )

                self.assertFalse(
                    overlay.isVisible()
                )

                overlay.set_policy_hidden(
                    False
                )

                self.app.processEvents()

                self.assertFalse(
                    overlay.policy_hidden
                )

                self.assertTrue(
                    overlay.isVisible()
                )
        finally:
            overlay.close()


if __name__ == "__main__":
    unittest.main()
