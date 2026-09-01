import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication

from src.companion.overlay import CompanionOverlay
from src.companion.preferences import CompanionPreferences


class CompanionOverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def setUp(self):
        self.overlay = CompanionOverlay()

    def tearDown(self):
        self.overlay.close()
        self.app.processEvents()

    def _create_png(
        self,
        directory: str,
        *,
        width: int = 40,
        height: int = 20,
    ) -> Path:
        path = (
            Path(directory)
            / "companion.png"
        )

        image = QImage(
            width,
            height,
            QImage.Format.Format_ARGB32,
        )

        image.fill(
            0xFFFFFFFF
        )

        self.assertTrue(
            image.save(str(path))
        )

        return path

    def test_window_uses_overlay_flags(self):
        flags = self.overlay.windowFlags()

        self.assertTrue(
            bool(
                flags
                & Qt.WindowType.Tool
            )
        )

        self.assertTrue(
            bool(
                flags
                & Qt.WindowType.FramelessWindowHint
            )
        )

        self.assertTrue(
            bool(
                flags
                & Qt.WindowType.WindowDoesNotAcceptFocus
            )
        )

        self.assertTrue(
            bool(
                flags
                & Qt.WindowType.WindowStaysOnTopHint
            )
        )

    def test_overlay_attributes_are_transparent_and_nonactivating(self):
        self.assertTrue(
            self.overlay.testAttribute(
                Qt.WidgetAttribute.WA_TranslucentBackground
            )
        )

        self.assertTrue(
            self.overlay.testAttribute(
                Qt.WidgetAttribute.WA_ShowWithoutActivating
            )
        )

    def test_static_png_loads_and_resizes_to_source(self):
        with tempfile.TemporaryDirectory() as root:
            path = self._create_png(root)

            self.overlay.set_static_asset(
                path
            )

            self.assertEqual(
                self.overlay.asset_path,
                str(path),
            )

            self.assertEqual(
                self.overlay.source_size,
                (40, 20),
            )

            self.assertEqual(
                self.overlay.width(),
                40,
            )

            self.assertEqual(
                self.overlay.height(),
                20,
            )

    def test_scale_changes_render_size(self):
        with tempfile.TemporaryDirectory() as root:
            path = self._create_png(root)

            self.overlay.set_static_asset(
                path
            )

            self.overlay.set_scale_percent(
                200
            )

            self.assertEqual(
                self.overlay.scale_percent,
                200,
            )

            self.assertEqual(
                self.overlay.width(),
                80,
            )

            self.assertEqual(
                self.overlay.height(),
                40,
            )

    def test_static_loader_rejects_gif_until_animation_milestone(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "companion.gif"
            path.write_bytes(b"GIF89a")

            with self.assertRaises(
                ValueError
            ):
                self.overlay.set_static_asset(
                    path
                )

    def test_missing_asset_is_rejected(self):
        with self.assertRaises(
            FileNotFoundError
        ):
            self.overlay.set_static_asset(
                r"C:\definitely-missing\companion.png"
            )

    def test_click_through_can_be_toggled(self):
        self.overlay.set_click_through(
            True
        )

        self.assertTrue(
            self.overlay.testAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents
            )
        )

        self.assertTrue(
            bool(
                self.overlay.windowFlags()
                & Qt.WindowType.WindowTransparentForInput
            )
        )

        self.overlay.set_click_through(
            False
        )

        self.assertFalse(
            self.overlay.testAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents
            )
        )

        self.assertFalse(
            bool(
                self.overlay.windowFlags()
                & Qt.WindowType.WindowTransparentForInput
            )
        )

    def test_always_on_top_can_be_toggled(self):
        self.overlay.set_always_on_top(
            False
        )

        self.assertFalse(
            bool(
                self.overlay.windowFlags()
                & Qt.WindowType.WindowStaysOnTopHint
            )
        )

        self.overlay.set_always_on_top(
            True
        )

        self.assertTrue(
            bool(
                self.overlay.windowFlags()
                & Qt.WindowType.WindowStaysOnTopHint
            )
        )

    def test_apply_preferences_shows_enabled_static_asset(self):
        with tempfile.TemporaryDirectory() as root:
            path = self._create_png(root)

            preferences = CompanionPreferences(
                enabled=True,
                asset_path=str(path),
                scale_percent=150,
                opacity=0.75,
                always_on_top=True,
                click_through=True,
                remember_position=True,
                position_x=120,
                position_y=240,
            )

            self.overlay.apply_preferences(
                preferences
            )

            self.app.processEvents()

            self.assertTrue(
                self.overlay.isVisible()
            )

            self.assertEqual(
                self.overlay.pos().x(),
                120,
            )

            self.assertEqual(
                self.overlay.pos().y(),
                240,
            )

            self.assertEqual(
                self.overlay.width(),
                60,
            )

            self.assertEqual(
                self.overlay.height(),
                30,
            )

    def test_apply_preferences_hides_when_disabled(self):
        with tempfile.TemporaryDirectory() as root:
            path = self._create_png(root)

            self.overlay.apply_preferences(
                CompanionPreferences(
                    enabled=False,
                    asset_path=str(path),
                )
            )

            self.app.processEvents()

            self.assertFalse(
                self.overlay.isVisible()
            )


if __name__ == "__main__":
    unittest.main()