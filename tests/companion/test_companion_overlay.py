import base64
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtCore import QPoint, QRect, QSize, Qt
from PyQt6.QtGui import QImage, QMovie
from PyQt6.QtWidgets import QApplication

from src.companion.overlay import (
    CompanionOverlay,
    _center_position_on_screen,
    _clamp_position_to_screen,
    _resolve_placement_screen,
)
from src.companion.preferences import CompanionPreferences


_ANIMATED_GIF_BASE64 = (
    "R0lGODlhQABAAIEAAAAAAP///wAAAAAAACH/C05FVFNDQVBFMi4wAwEAAAAh"
    "+QQJEgAAACwAAAAAQABAAAAImAABCBxIsKDBgwgTKlzIsKHDhxAjSpxIsaLF"
    "ixgzatzIsaPHjyBDihxJsqTJkyhTqlzJsqXLlzBjypxJs2SAmzhz6oSps2dP"
    "lz6D5mQptOjNlUaLIk0adCnTnyqf+nQqFSfVqgGuVtUqletTr0zBJhVrlKz"
    "SqFitmp3aEivPrzXjyp1Lt67du3jz6t3Lt6/fv4ADCx5MOG9AACH5BAkSAAA"
    "ALBAAFgAVABUAgQAAAP///wAAAAAAAAgzAAEIDECwoMGDAhMeXLhQIcOHBQF"
    "AnEixosWLGDNq3Mixo8ePIEOKHClxo0OMCQdeTBgQACH5BAkSAAAALBwAFgA"
    "VABUAgQAAAP///wAAAAAAAAgzAAEIDECwoMGDAhMeXLhQIcOHBQFAnEixosW"
    "LGDNq3Mixo8ePIEOKHClxo0OMCQdeTBgQACH5BAkSAAAALCgAFgAVABUAgQA"
    "AAP///wAAAAAAAAgzAAEIDECwoMGDAhMeXLhQIcOHBQFAnEixosWLGDNq3Mi"
    "xo8ePIEOKHClxo0OMCQdeTBgQADs="
)


class _FakeScreen:
    def __init__(
        self,
        name: str,
        geometry: QRect,
        available_geometry: QRect | None = None,
    ) -> None:
        self._name = name
        self._geometry = QRect(
            geometry
        )

        self._available_geometry = QRect(
            available_geometry
            if available_geometry is not None
            else geometry
        )

    def name(self) -> str:
        return self._name

    def geometry(self) -> QRect:
        return QRect(
            self._geometry
        )

    def availableGeometry(self) -> QRect:
        return QRect(
            self._available_geometry
        )


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

    def _create_gif(
        self,
        directory: str,
    ) -> Path:
        path = (
            Path(directory)
            / "companion.gif"
        )

        path.write_bytes(
            base64.b64decode(
                _ANIMATED_GIF_BASE64
            )
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

    def test_static_loader_rejects_gif_for_animated_loader(self):
        with tempfile.TemporaryDirectory() as root:
            path = self._create_gif(root)

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

    def test_animated_gif_loads_and_starts(self):
        with tempfile.TemporaryDirectory() as root:
            path = self._create_gif(root)

            self.overlay.set_animated_asset(
                path
            )

            self.app.processEvents()

            self.assertTrue(
                self.overlay.is_animated
            )

            self.assertEqual(
                self.overlay.asset_path,
                str(path),
            )

            self.assertEqual(
                self.overlay.source_size,
                (64, 64),
            )

            self.assertIsNotNone(
                self.overlay._movie
            )

            self.assertEqual(
                self.overlay._movie.state(),
                QMovie.MovieState.Running,
            )

    def test_generic_asset_routes_gif_to_animation(self):
        with tempfile.TemporaryDirectory() as root:
            path = self._create_gif(root)

            self.overlay.set_asset(
                path
            )

            self.assertTrue(
                self.overlay.is_animated
            )

            self.assertEqual(
                self.overlay.asset_path,
                str(path),
            )

    def test_animation_speed_updates_active_movie(self):
        with tempfile.TemporaryDirectory() as root:
            path = self._create_gif(root)

            self.overlay.set_animated_asset(
                path
            )

            self.overlay.set_animation_speed_percent(
                175
            )

            self.assertEqual(
                self.overlay.animation_speed_percent,
                175,
            )

            self.assertEqual(
                self.overlay._movie.speed(),
                175,
            )

    def test_gif_scale_updates_window_size(self):
        with tempfile.TemporaryDirectory() as root:
            path = self._create_gif(root)

            self.overlay.set_animated_asset(
                path
            )

            self.overlay.set_scale_percent(
                200
            )

            self.assertEqual(
                self.overlay.width(),
                128,
            )

            self.assertEqual(
                self.overlay.height(),
                128,
            )

            self.assertEqual(
                self.overlay.source_size,
                (64, 64),
            )

    def test_clear_asset_stops_animation(self):
        with tempfile.TemporaryDirectory() as root:
            path = self._create_gif(root)

            self.overlay.set_animated_asset(
                path
            )

            movie = self.overlay._movie

            self.overlay.clear_asset()

            self.assertEqual(
                movie.state(),
                QMovie.MovieState.NotRunning,
            )

            self.assertFalse(
                self.overlay.is_animated
            )

            self.assertEqual(
                self.overlay.asset_path,
                "",
            )

            self.assertEqual(
                self.overlay.source_size,
                (0, 0),
            )

    def test_switching_gif_to_static_stops_old_movie(self):
        with tempfile.TemporaryDirectory() as root:
            gif_path = self._create_gif(root)

            png_path = self._create_png(
                root,
                width=30,
                height=10,
            )

            self.overlay.set_animated_asset(
                gif_path
            )

            movie = self.overlay._movie

            self.overlay.set_static_asset(
                png_path
            )

            self.assertEqual(
                movie.state(),
                QMovie.MovieState.NotRunning,
            )

            self.assertFalse(
                self.overlay.is_animated
            )

            self.assertEqual(
                self.overlay.asset_path,
                str(png_path),
            )

            self.assertEqual(
                self.overlay.source_size,
                (30, 10),
            )

    def test_switching_static_to_gif_uses_animation(self):
        with tempfile.TemporaryDirectory() as root:
            png_path = self._create_png(root)
            gif_path = self._create_gif(root)

            self.overlay.set_static_asset(
                png_path
            )

            self.overlay.set_animated_asset(
                gif_path
            )

            self.assertTrue(
                self.overlay.is_animated
            )

            self.assertEqual(
                self.overlay.source_size,
                (64, 64),
            )

    def test_apply_preferences_routes_gif_speed_and_scale(self):
        with tempfile.TemporaryDirectory() as root:
            path = self._create_gif(root)

            self.overlay.apply_preferences(
                CompanionPreferences(
                    enabled=True,
                    asset_path=str(path),
                    scale_percent=150,
                    animation_speed_percent=160,
                )
            )

            self.app.processEvents()

            self.assertTrue(
                self.overlay.isVisible()
            )

            self.assertTrue(
                self.overlay.is_animated
            )

            self.assertEqual(
                self.overlay.animation_speed_percent,
                160,
            )

            self.assertEqual(
                self.overlay._movie.speed(),
                160,
            )

            self.assertEqual(
                self.overlay.width(),
                96,
            )

            self.assertEqual(
                self.overlay.height(),
                96,
            )


    def test_drag_is_blocked_while_click_through_enabled(self):
        self.assertTrue(
            self.overlay.click_through
        )

        started = self.overlay._begin_drag(
            QPoint(
                500,
                400,
            )
        )

        self.assertFalse(
            started
        )

        self.assertFalse(
            self.overlay.is_dragging
        )

    def test_drag_moves_window_when_click_through_disabled(self):
        self.overlay.set_click_through(
            False
        )

        self.overlay.move(
            100,
            200,
        )

        self.assertTrue(
            self.overlay._begin_drag(
                QPoint(
                    500,
                    400,
                )
            )
        )

        self.assertTrue(
            self.overlay._update_drag(
                QPoint(
                    540,
                    430,
                )
            )
        )

        self.assertEqual(
            self.overlay.pos(),
            QPoint(
                140,
                230,
            ),
        )

    def test_drag_release_emits_final_position_once(self):
        self.overlay.set_click_through(
            False
        )

        self.overlay.move(
            20,
            30,
        )

        positions = []

        self.overlay.position_changed.connect(
            lambda x, y: positions.append(
                (
                    x,
                    y,
                )
            )
        )

        self.overlay._begin_drag(
            QPoint(
                100,
                100,
            )
        )

        self.overlay._update_drag(
            QPoint(
                150,
                170,
            )
        )

        self.assertTrue(
            self.overlay._end_drag()
        )

        self.assertFalse(
            self.overlay.is_dragging
        )

        self.assertEqual(
            positions,
            [
                (
                    70,
                    100,
                )
            ],
        )

        self.assertFalse(
            self.overlay._end_drag()
        )

        self.assertEqual(
            len(positions),
            1,
        )

    def test_enabling_click_through_cancels_active_drag(self):
        self.overlay.set_click_through(
            False
        )

        positions = []

        self.overlay.position_changed.connect(
            lambda x, y: positions.append(
                (
                    x,
                    y,
                )
            )
        )

        self.overlay._begin_drag(
            QPoint(
                10,
                10,
            )
        )

        self.assertTrue(
            self.overlay.is_dragging
        )

        self.overlay.set_click_through(
            True
        )

        self.assertFalse(
            self.overlay.is_dragging
        )

        self.assertFalse(
            self.overlay._end_drag()
        )

        self.assertEqual(
            positions,
            [],
        )

    def test_drag_update_after_release_is_ignored(self):
        self.overlay.set_click_through(
            False
        )

        self.overlay.move(
            40,
            50,
        )

        self.overlay._begin_drag(
            QPoint(
                100,
                100,
            )
        )

        self.overlay._update_drag(
            QPoint(
                120,
                125,
            )
        )

        self.overlay._end_drag()

        final_position = QPoint(
            self.overlay.pos()
        )

        self.assertFalse(
            self.overlay._update_drag(
                QPoint(
                    300,
                    300,
                )
            )
        )

        self.assertEqual(
            self.overlay.pos(),
            final_position,
        )

    def test_click_through_property_tracks_toggle(self):
        self.overlay.set_click_through(
            False
        )

        self.assertFalse(
            self.overlay.click_through
        )

        self.overlay.set_click_through(
            True
        )

        self.assertTrue(
            self.overlay.click_through
        )


    def test_monitor_policy_prefers_saved_screen_name(self):
        primary = _FakeScreen(
            "PRIMARY",
            QRect(
                0,
                0,
                1920,
                1080,
            ),
        )

        secondary = _FakeScreen(
            "SECONDARY",
            QRect(
                1920,
                0,
                1920,
                1080,
            ),
        )

        resolved = _resolve_placement_screen(
            [
                primary,
                secondary,
            ],
            primary,
            preferred_name="SECONDARY",
            saved_position=QPoint(
                100,
                100,
            ),
        )

        self.assertIs(
            resolved,
            secondary,
        )

    def test_monitor_policy_falls_back_to_coordinate_screen(self):
        primary = _FakeScreen(
            "PRIMARY",
            QRect(
                0,
                0,
                1920,
                1080,
            ),
        )

        secondary = _FakeScreen(
            "SECONDARY",
            QRect(
                1920,
                0,
                1920,
                1080,
            ),
        )

        resolved = _resolve_placement_screen(
            [
                primary,
                secondary,
            ],
            primary,
            preferred_name="MISSING",
            saved_position=QPoint(
                2100,
                300,
            ),
        )

        self.assertIs(
            resolved,
            secondary,
        )

    def test_monitor_policy_falls_back_to_primary_screen(self):
        primary = _FakeScreen(
            "PRIMARY",
            QRect(
                0,
                0,
                1920,
                1080,
            ),
        )

        secondary = _FakeScreen(
            "SECONDARY",
            QRect(
                1920,
                0,
                1920,
                1080,
            ),
        )

        resolved = _resolve_placement_screen(
            [
                primary,
                secondary,
            ],
            primary,
            preferred_name="MISSING",
            saved_position=QPoint(
                9000,
                9000,
            ),
        )

        self.assertIs(
            resolved,
            primary,
        )

    def test_clamp_preserves_intentional_partial_bottom_position(
        self,
    ):
        from PyQt6.QtCore import (
            QPoint,
            QRect,
            QSize,
        )

        from src.companion.overlay import (
            _clamp_position_to_screen,
        )

        class Screen:
            def geometry(
                self,
            ):
                return QRect(
                    0,
                    0,
                    1920,
                    1080,
                )

            def availableGeometry(
                self,
            ):
                return QRect(
                    0,
                    0,
                    1920,
                    1032,
                )

        desired = QPoint(
            100,
            960,
        )

        result = _clamp_position_to_screen(
            Screen(),
            QSize(
                320,
                320,
            ),
            desired,
        )

        self.assertEqual(
            result,
            desired,
        )

    def test_clamp_preserves_intentional_partial_top_left_position(
        self,
    ):
        from PyQt6.QtCore import (
            QPoint,
            QRect,
            QSize,
        )

        from src.companion.overlay import (
            _clamp_position_to_screen,
        )

        class Screen:
            def geometry(
                self,
            ):
                return QRect(
                    0,
                    0,
                    1920,
                    1080,
                )

        desired = QPoint(
            -350,
            -250,
        )

        result = _clamp_position_to_screen(
            Screen(),
            QSize(
                400,
                300,
            ),
            desired,
        )

        self.assertEqual(
            result,
            desired,
        )

    def test_clamp_rescues_unreachable_position_with_visible_strip(
        self,
    ):
        from PyQt6.QtCore import (
            QPoint,
            QRect,
            QSize,
        )

        from src.companion.overlay import (
            _clamp_position_to_screen,
        )

        class Screen:
            def geometry(
                self,
            ):
                return QRect(
                    0,
                    0,
                    1920,
                    1080,
                )

        bottom_right = _clamp_position_to_screen(
            Screen(),
            QSize(
                400,
                300,
            ),
            QPoint(
                5000,
                5000,
            ),
        )

        self.assertEqual(
            bottom_right,
            QPoint(
                1896,
                1056,
            ),
        )

        top_left = _clamp_position_to_screen(
            Screen(),
            QSize(
                400,
                300,
            ),
            QPoint(
                -5000,
                -5000,
            ),
        )

        self.assertEqual(
            top_left,
            QPoint(
                -376,
                -276,
            ),
        )

    def test_center_position_uses_available_geometry(self):
        screen = _FakeScreen(
            "SECONDARY",
            QRect(
                1920,
                0,
                1920,
                1080,
            ),
            QRect(
                1920,
                0,
                1920,
                1032,
            ),
        )

        position = _center_position_on_screen(
            screen,
            QSize(
                200,
                100,
            ),
        )

        self.assertEqual(
            position,
            QPoint(
                2780,
                466,
            ),
        )

    def test_apply_preferences_preserves_partial_offscreen_position(
        self,
    ):
        from unittest.mock import patch

        from PyQt6.QtCore import QRect

        class Screen:
            def name(
                self,
            ):
                return "DISPLAY-PARTIAL"

            def geometry(
                self,
            ):
                return QRect(
                    0,
                    0,
                    1920,
                    1080,
                )

            def availableGeometry(
                self,
            ):
                return QRect(
                    0,
                    0,
                    1920,
                    1032,
                )

        screen = Screen()

        with tempfile.TemporaryDirectory() as root:
            path = self._create_png(
                root,
                width=320,
                height=320,
            )

            preferences = CompanionPreferences(
                enabled=True,
                asset_path=str(
                    path
                ),
                click_through=False,
                remember_position=True,
                position_x=100,
                position_y=960,
                screen_name="DISPLAY-PARTIAL",
            )

            with patch(
                "src.companion.overlay."
                "QGuiApplication.screens",
                return_value=[
                    screen,
                ],
            ), patch(
                "src.companion.overlay."
                "QGuiApplication.primaryScreen",
                return_value=screen,
            ):
                self.overlay.apply_preferences(
                    preferences
                )

                self.app.processEvents()

                self.assertEqual(
                    self.overlay.pos().x(),
                    100,
                )

                self.assertEqual(
                    self.overlay.pos().y(),
                    960,
                )

                reapplied = CompanionPreferences(
                    enabled=True,
                    asset_path=str(
                        path
                    ),
                    click_through=True,
                    remember_position=True,
                    position_x=100,
                    position_y=960,
                    screen_name="DISPLAY-PARTIAL",
                )

                self.overlay.apply_preferences(
                    reapplied
                )

                self.app.processEvents()

                self.assertEqual(
                    self.overlay.pos().x(),
                    100,
                )

                self.assertEqual(
                    self.overlay.pos().y(),
                    960,
                )

    def test_apply_preferences_centers_without_remembered_position(self):
        primary = self.app.primaryScreen()

        self.assertIsNotNone(
            primary
        )

        preferences = CompanionPreferences(
            enabled=False,
            remember_position=False,
            screen_name=primary.name(),
        )

        self.overlay.apply_preferences(
            preferences
        )

        expected = _center_position_on_screen(
            primary,
            self.overlay.size(),
        )

        self.assertEqual(
            self.overlay.pos(),
            expected,
        )


if __name__ == "__main__":
    unittest.main()
