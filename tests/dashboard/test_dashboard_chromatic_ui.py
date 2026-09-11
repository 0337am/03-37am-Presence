from __future__ import annotations

import math
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtCore import (
    QObject,
    QSettings,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QColor,
    QImage,
)
from PyQt6.QtWidgets import QApplication

from src.system.dashboard_chromatic import (
    DashboardChromaticPreferencesStore,
)
from src.system.dashboard_palette import (
    MAX_PALETTE_COLOURS,
    PALETTE_SOURCE_BACKGROUND,
    PALETTE_SOURCE_MANUAL,
    PALETTE_SOURCE_THEME,
    DashboardPalettePreferences,
    DashboardPalettePreferencesStore,
    build_dashboard_palette_theme,
    effect_colours_for_style,
    extract_dashboard_palette_from_image,
    extract_dashboard_palette_from_path,
    normalise_manual_palette,
    normalise_palette,
    resolve_dashboard_palette,
    update_matched_palette,
)
from src.ui.dashboard import DashboardPage
from src.ui.dashboard_chromatic_settings import (
    DashboardChromaticSettingsWidget,
)


BASE_THEME = {
    "preset": "Yuno",
    "background": "#140812",
    "sidebar": "#210b1a",
    "card": "#352747",
    "card_alt": "#3e2e54",
    "accent": "#ff79b9",
    "text": "#fff5fb",
    "muted": "#bca9ce",
    "border": "#5c4777",
}


class _ThemeManager(
    QObject
):

    theme_changed = pyqtSignal(
        dict
    )

    atmosphere_changed = pyqtSignal(
        dict
    )

    def __init__(
        self,
        atmosphere=None,
    ):
        super().__init__()

        self._atmosphere = (
            dict(
                atmosphere
            )
            if isinstance(
                atmosphere,
                dict,
            )
            else {
                "enabled": False,
                "image_path": "",
                "blur": 0,
                "opacity": 100,
                "dim": 0,
            }
        )

    def theme(
        self,
    ):
        return dict(
            BASE_THEME
        )

    def atmosphere(
        self,
    ):
        return dict(
            self._atmosphere
        )

    def set_atmosphere(
        self,
        atmosphere,
    ):
        self._atmosphere = dict(
            atmosphere
        )

        self.atmosphere_changed.emit(
            dict(
                atmosphere
            )
        )


def _settings(
    temp,
    filename,
):
    return QSettings(
        str(
            Path(
                temp
            )
            / filename
        ),
        QSettings.Format.IniFormat,
    )


def _palette_store(
    temp,
):
    return (
        DashboardPalettePreferencesStore(
            _settings(
                temp,
                "palette.ini",
            )
        )
    )


def _effect_store(
    temp,
):
    return (
        DashboardChromaticPreferencesStore(
            _settings(
                temp,
                "effect.ini",
            )
        )
    )


def _solid_image(
    temp,
    colour,
    filename,
):
    path = (
        Path(
            temp
        )
        / filename
    )

    image = QImage(
        40,
        40,
        QImage.Format.Format_ARGB32,
    )

    image.fill(
        QColor(
            colour
        )
    )

    if not image.save(
        str(
            path
        )
    ):
        raise RuntimeError(
            "Could not save test image."
        )

    return path


def _five_colour_image(
    temp,
):
    values = (
        "#e13d7b",
        "#28c99a",
        "#6a63e8",
        "#f2ad45",
        "#d85be8",
    )

    image = QImage(
        100,
        40,
        QImage.Format.Format_ARGB32,
    )

    stripe = (
        image.width()
        // len(
            values
        )
    )

    for (
        index,
        value,
    ) in enumerate(
        values
    ):
        start = (
            index
            * stripe
        )

        end = (
            image.width()
            if index
            == len(
                values
            ) - 1
            else start
            + stripe
        )

        colour = QColor(
            value
        )

        for x in range(
            start,
            end,
        ):
            for y in range(
                image.height()
            ):
                image.setPixelColor(
                    x,
                    y,
                    colour,
                )

    path = (
        Path(
            temp
        )
        / "five.png"
    )

    if not image.save(
        str(
            path
        )
    ):
        raise RuntimeError(
            "Could not save five-colour image."
        )

    return (
        path,
        values,
    )


def _rgb_distance(
    first,
    second,
):
    one = QColor(
        first
    )

    two = QColor(
        second
    )

    return math.sqrt(
        (
            one.red()
            - two.red()
        )
        ** 2
        + (
            one.green()
            - two.green()
        )
        ** 2
        + (
            one.blue()
            - two.blue()
        )
        ** 2
    )


def _assert_palette_near(
    testcase,
    actual,
    expected,
    tolerance=8.0,
):
    testcase.assertEqual(
        len(
            actual
        ),
        len(
            expected
        ),
    )

    remaining = list(
        actual
    )

    for expected_colour in (
        expected
    ):
        distances = [
            (
                _rgb_distance(
                    candidate,
                    expected_colour,
                ),
                index,
                candidate,
            )
            for (
                index,
                candidate,
            ) in enumerate(
                remaining
            )
        ]

        distance, index, candidate = (
            min(
                distances,
                key=lambda item:
                    item[0],
            )
        )

        testcase.assertLessEqual(
            distance,
            tolerance,
            (
                expected_colour
                + " was not recovered closely enough; nearest was "
                + candidate
                + " at RGB distance "
                + str(
                    round(
                        distance,
                        3,
                    )
                )
            ),
        )

        remaining.pop(
            index
        )


class DashboardChromaticUiTests(
    unittest.TestCase
):

    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def test_default_palette_source_is_theme(
        self,
    ):
        self.assertEqual(
            DashboardPalettePreferences()
            .source,
            PALETTE_SOURCE_THEME,
        )

    def test_manual_palette_has_five_slots(
        self,
    ):
        self.assertEqual(
            len(
                DashboardPalettePreferences()
                .manual_palette
            ),
            MAX_PALETTE_COLOURS,
        )

    def test_manual_palette_padding_reuses_source_colour(
        self,
    ):
        self.assertEqual(
            normalise_manual_palette(
                (
                    "#123456",
                )
            ),
            (
                "#123456",
                "#123456",
                "#123456",
                "#123456",
                "#123456",
            ),
        )

    def test_normalise_palette_caps_at_five(
        self,
    ):
        result = (
            normalise_palette(
                (
                    "#ff0000",
                    "#00ff00",
                    "#0000ff",
                    "#ffff00",
                    "#ff00ff",
                    "#00ffff",
                )
            )
        )

        self.assertEqual(
            len(
                result
            ),
            5,
        )

    def test_builder_clamps_manual_count(
        self,
    ):
        self.assertEqual(
            DashboardPalettePreferences
            .build(
                manual_count=-10
            )
            .manual_count,
            1,
        )

        self.assertEqual(
            DashboardPalettePreferences
            .build(
                manual_count=99
            )
            .manual_count,
            5,
        )

    def test_palette_store_round_trip(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            store = (
                _palette_store(
                    temp
                )
            )

            expected = (
                DashboardPalettePreferences
                .build(
                    source=(
                        PALETTE_SOURCE_MANUAL
                    ),
                    manual_palette=(
                        "#111111",
                        "#222222",
                        "#333333",
                        "#444444",
                        "#555555",
                    ),
                    manual_count=5,
                    matched_palette=(
                        "#ff0000",
                        "#00ff00",
                    ),
                    strength=63,
                    locked=True,
                )
            )

            store.save(
                expected
            )

            self.assertEqual(
                store.load(),
                expected,
            )

    def test_theme_source_uses_theme_accent(
        self,
    ):
        self.assertEqual(
            resolve_dashboard_palette(
                BASE_THEME,
                DashboardPalettePreferences(),
            ),
            (
                BASE_THEME[
                    "accent"
                ],
            ),
        )

    def test_manual_source_preserves_exact_five_colours(
        self,
    ):
        values = (
            "#e13d7b",
            "#28c99a",
            "#6a63e8",
            "#f2ad45",
            "#d85be8",
        )

        preferences = (
            DashboardPalettePreferences
            .build(
                source=(
                    PALETTE_SOURCE_MANUAL
                ),
                manual_palette=values,
                manual_count=5,
            )
        )

        self.assertEqual(
            resolve_dashboard_palette(
                BASE_THEME,
                preferences,
            ),
            values,
        )

    def test_manual_source_preserves_duplicates(
        self,
    ):
        values = (
            "#e13d7b",
            "#e13d7b",
            "#28c99a",
            "#28c99a",
            "#6a63e8",
        )

        preferences = (
            DashboardPalettePreferences
            .build(
                source=(
                    PALETTE_SOURCE_MANUAL
                ),
                manual_palette=values,
                manual_count=5,
            )
        )

        self.assertEqual(
            resolve_dashboard_palette(
                BASE_THEME,
                preferences,
            ),
            values,
        )

    def test_background_source_uses_matched_palette(
        self,
    ):
        values = (
            "#e13d7b",
            "#28c99a",
            "#6a63e8",
        )

        preferences = (
            DashboardPalettePreferences
            .build(
                source=(
                    PALETTE_SOURCE_BACKGROUND
                ),
                matched_palette=values,
            )
        )

        self.assertEqual(
            resolve_dashboard_palette(
                BASE_THEME,
                preferences,
            ),
            values,
        )

    def test_missing_match_falls_back_to_theme(
        self,
    ):
        preferences = (
            DashboardPalettePreferences
            .build(
                source=(
                    PALETTE_SOURCE_BACKGROUND
                ),
            )
        )

        self.assertEqual(
            resolve_dashboard_palette(
                BASE_THEME,
                preferences,
            ),
            (
                BASE_THEME[
                    "accent"
                ],
            ),
        )

    def test_theme_source_static_theme_is_exact_passthrough(
        self,
    ):
        self.assertEqual(
            build_dashboard_palette_theme(
                BASE_THEME,
                DashboardPalettePreferences(),
            ),
            BASE_THEME,
        )

    def test_zero_strength_is_exact_passthrough(
        self,
    ):
        preferences = (
            DashboardPalettePreferences
            .build(
                source=(
                    PALETTE_SOURCE_MANUAL
                ),
                manual_palette=(
                    "#28c99a",
                ),
                strength=0,
            )
        )

        self.assertEqual(
            build_dashboard_palette_theme(
                BASE_THEME,
                preferences,
            ),
            BASE_THEME,
        )

    def test_manual_palette_recolours_dashboard_without_effect_dependency(
        self,
    ):
        preferences = (
            DashboardPalettePreferences
            .build(
                source=(
                    PALETTE_SOURCE_MANUAL
                ),
                manual_palette=(
                    "#28c99a",
                ),
                strength=100,
            )
        )

        result = (
            build_dashboard_palette_theme(
                BASE_THEME,
                preferences,
            )
        )

        self.assertNotEqual(
            result[
                "accent"
            ],
            BASE_THEME[
                "accent"
            ],
        )

        self.assertEqual(
            result[
                "background"
            ],
            BASE_THEME[
                "background"
            ],
        )

        self.assertEqual(
            result[
                "text"
            ],
            BASE_THEME[
                "text"
            ],
        )

    def test_background_palette_recolours_static_dashboard(
        self,
    ):
        preferences = (
            DashboardPalettePreferences
            .build(
                source=(
                    PALETTE_SOURCE_BACKGROUND
                ),
                matched_palette=(
                    "#28c99a",
                    "#6a63e8",
                    "#f2ad45",
                ),
                strength=100,
            )
        )

        result = (
            build_dashboard_palette_theme(
                BASE_THEME,
                preferences,
            )
        )

        self.assertNotEqual(
            result[
                "accent"
            ],
            BASE_THEME[
                "accent"
            ],
        )

        self.assertNotEqual(
            result[
                "border"
            ],
            BASE_THEME[
                "border"
            ],
        )

    def test_extract_solid_colour(
        self,
    ):
        image = QImage(
            30,
            30,
            QImage.Format.Format_ARGB32,
        )

        image.fill(
            QColor(
                "#e13d7b"
            )
        )

        self.assertEqual(
            extract_dashboard_palette_from_image(
                image
            ),
            (
                "#e13d7b",
            ),
        )

    def test_extract_black_returns_empty(
        self,
    ):
        image = QImage(
            30,
            30,
            QImage.Format.Format_ARGB32,
        )

        image.fill(
            QColor(
                "#000000"
            )
        )

        self.assertEqual(
            extract_dashboard_palette_from_image(
                image
            ),
            (),
        )

    def test_missing_image_path_returns_empty(
        self,
    ):
        self.assertEqual(
            extract_dashboard_palette_from_path(
                "Z:/definitely/not/here.png"
            ),
            (),
        )

    def test_scaled_extractor_returns_five_near_source_colours(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            (
                path,
                expected,
            ) = (
                _five_colour_image(
                    temp
                )
            )

            palette = (
                extract_dashboard_palette_from_path(
                    path
                )
            )

            self.assertEqual(
                len(
                    palette
                ),
                5,
            )

            _assert_palette_near(
                self,
                palette,
                expected,
                tolerance=8.0,
            )

    def test_lock_blocks_background_replacement(
        self,
    ):
        preferences = (
            DashboardPalettePreferences
            .build(
                source=(
                    PALETTE_SOURCE_BACKGROUND
                ),
                matched_palette=(
                    "#e13d7b",
                ),
                locked=True,
            )
        )

        updated = (
            update_matched_palette(
                preferences,
                (
                    "#28c99a",
                ),
            )
        )

        self.assertEqual(
            updated,
            preferences,
        )

    def test_force_recalculate_overrides_lock(
        self,
    ):
        preferences = (
            DashboardPalettePreferences
            .build(
                source=(
                    PALETTE_SOURCE_BACKGROUND
                ),
                matched_palette=(
                    "#e13d7b",
                ),
                locked=True,
            )
        )

        updated = (
            update_matched_palette(
                preferences,
                (
                    "#28c99a",
                ),
                force=True,
            )
        )

        self.assertTrue(
            updated.locked
        )

        self.assertEqual(
            updated.matched_palette,
            (
                "#28c99a",
            ),
        )

    def test_gradient_uses_all_five_palette_colours(
        self,
    ):
        values = (
            "#e13d7b",
            "#28c99a",
            "#6a63e8",
            "#f2ad45",
            "#d85be8",
        )

        self.assertEqual(
            effect_colours_for_style(
                values,
                "gradient",
            ),
            values,
        )

    def test_prism_uses_all_five_palette_colours(
        self,
    ):
        values = (
            "#e13d7b",
            "#28c99a",
            "#6a63e8",
            "#f2ad45",
            "#d85be8",
        )

        self.assertEqual(
            effect_colours_for_style(
                values,
                "prism",
            ),
            values,
        )

    def test_solid_and_neon_use_colour_one_only(
        self,
    ):
        values = (
            "#e13d7b",
            "#28c99a",
            "#6a63e8",
        )

        self.assertEqual(
            effect_colours_for_style(
                values,
                "solid",
            ),
            (
                "#e13d7b",
            ),
        )

        self.assertEqual(
            effect_colours_for_style(
                values,
                "neon",
            ),
            (
                "#e13d7b",
            ),
        )

    def test_widget_has_three_sources_and_five_slots(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            widget = (
                DashboardChromaticSettingsWidget(
                    theme_manager=(
                        _ThemeManager()
                    ),
                    preference_store=(
                        _effect_store(
                            temp
                        )
                    ),
                    palette_store=(
                        _palette_store(
                            temp
                        )
                    ),
                )
            )

            self.assertEqual(
                widget.source_combo.count(),
                3,
            )

            self.assertEqual(
                len(
                    widget.colour_buttons
                ),
                5,
            )

            self.assertEqual(
                len(
                    widget.colour_swatches
                ),
                5,
            )

    def test_existing_preference_store_argument_remains_supported(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            effect_store = (
                _effect_store(
                    temp
                )
            )

            widget = (
                DashboardChromaticSettingsWidget(
                    theme_manager=(
                        _ThemeManager()
                    ),
                    preference_store=(
                        effect_store
                    ),
                    palette_store=(
                        _palette_store(
                            temp
                        )
                    ),
                )
            )

            self.assertIs(
                widget.effect_store,
                effect_store,
            )

    def test_manual_count_can_be_five(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            palette_store = (
                _palette_store(
                    temp
                )
            )

            palette_store.save(
                DashboardPalettePreferences
                .build(
                    source=(
                        PALETTE_SOURCE_MANUAL
                    ),
                )
            )

            widget = (
                DashboardChromaticSettingsWidget(
                    theme_manager=(
                        _ThemeManager()
                    ),
                    preference_store=(
                        _effect_store(
                            temp
                        )
                    ),
                    palette_store=(
                        palette_store
                    ),
                )
            )

            index = (
                widget.manual_count_combo
                .findData(
                    5
                )
            )

            widget.manual_count_combo.setCurrentIndex(
                index
            )

            self.assertEqual(
                palette_store.load()
                .manual_count,
                5,
            )

    def test_manual_colour_picker_persists_exact_value(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            palette_store = (
                _palette_store(
                    temp
                )
            )

            palette_store.save(
                DashboardPalettePreferences
                .build(
                    source=(
                        PALETTE_SOURCE_MANUAL
                    ),
                    manual_count=5,
                )
            )

            widget = (
                DashboardChromaticSettingsWidget(
                    theme_manager=(
                        _ThemeManager()
                    ),
                    preference_store=(
                        _effect_store(
                            temp
                        )
                    ),
                    palette_store=(
                        palette_store
                    ),
                )
            )

            with patch(
                (
                    "src.ui."
                    "dashboard_chromatic_settings."
                    "QColorDialog.getColor"
                ),
                return_value=QColor(
                    "#22bb99"
                ),
            ):
                self.assertTrue(
                    widget._choose_manual_colour(
                        3
                    )
                )

            self.assertEqual(
                palette_store.load()
                .manual_palette[3],
                "#22bb99",
            )

    def test_cancelled_colour_picker_is_fail_closed(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            palette_store = (
                _palette_store(
                    temp
                )
            )

            palette_store.save(
                DashboardPalettePreferences
                .build(
                    source=(
                        PALETTE_SOURCE_MANUAL
                    ),
                    manual_count=5,
                )
            )

            before = (
                palette_store.load()
            )

            widget = (
                DashboardChromaticSettingsWidget(
                    theme_manager=(
                        _ThemeManager()
                    ),
                    preference_store=(
                        _effect_store(
                            temp
                        )
                    ),
                    palette_store=(
                        palette_store
                    ),
                )
            )

            with patch(
                (
                    "src.ui."
                    "dashboard_chromatic_settings."
                    "QColorDialog.getColor"
                ),
                return_value=QColor(),
            ):
                self.assertFalse(
                    widget._choose_manual_colour(
                        2
                    )
                )

            self.assertEqual(
                palette_store.load(),
                before,
            )

    def test_colour_strength_is_debounced(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            palette_store = (
                _palette_store(
                    temp
                )
            )

            palette_store.save(
                DashboardPalettePreferences
                .build(
                    source=(
                        PALETTE_SOURCE_MANUAL
                    ),
                    strength=80,
                )
            )

            widget = (
                DashboardChromaticSettingsWidget(
                    theme_manager=(
                        _ThemeManager()
                    ),
                    preference_store=(
                        _effect_store(
                            temp
                        )
                    ),
                    palette_store=(
                        palette_store
                    ),
                )
            )

            widget._change_colour_strength(
                31
            )

            self.assertEqual(
                widget.palette_preferences
                .strength,
                31,
            )

            self.assertEqual(
                palette_store.load()
                .strength,
                80,
            )

            widget._commit_colour_strength()

            self.assertEqual(
                palette_store.load()
                .strength,
                31,
            )

    def test_background_change_updates_palette_with_effects_off(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            first = _solid_image(
                temp,
                "#e13d7b",
                "first.png",
            )

            second = _solid_image(
                temp,
                "#28c99a",
                "second.png",
            )

            manager = _ThemeManager(
                {
                    "enabled": True,
                    "image_path": str(
                        first
                    ),
                    "blur": 0,
                    "opacity": 100,
                    "dim": 0,
                }
            )

            palette_store = (
                _palette_store(
                    temp
                )
            )

            palette_store.save(
                DashboardPalettePreferences
                .build(
                    source=(
                        PALETTE_SOURCE_BACKGROUND
                    ),
                )
            )

            widget = (
                DashboardChromaticSettingsWidget(
                    theme_manager=manager,
                    preference_store=(
                        _effect_store(
                            temp
                        )
                    ),
                    palette_store=(
                        palette_store
                    ),
                )
            )

            manager.set_atmosphere(
                {
                    "enabled": True,
                    "image_path": str(
                        second
                    ),
                    "blur": 0,
                    "opacity": 100,
                    "dim": 0,
                }
            )

            self.assertEqual(
                palette_store.load()
                .matched_palette,
                (
                    "#28c99a",
                ),
            )

            self.assertFalse(
                widget.effect_preferences
                .enabled
            )

    def test_unlocked_background_disable_clears_matched_palette(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            image = _solid_image(
                temp,
                "#e13d7b",
                "active.png",
            )

            manager = _ThemeManager(
                {
                    "enabled": True,
                    "image_path": str(
                        image
                    ),
                    "blur": 0,
                    "opacity": 100,
                    "dim": 0,
                }
            )

            palette_store = (
                _palette_store(
                    temp
                )
            )

            palette_store.save(
                DashboardPalettePreferences
                .build(
                    source=(
                        PALETTE_SOURCE_BACKGROUND
                    ),
                    matched_palette=(
                        "#e13d7b",
                    ),
                    locked=False,
                )
            )

            widget = (
                DashboardChromaticSettingsWidget(
                    theme_manager=manager,
                    preference_store=(
                        _effect_store(
                            temp
                        )
                    ),
                    palette_store=(
                        palette_store
                    ),
                )
            )

            manager.set_atmosphere(
                {
                    "enabled": False,
                    "image_path": str(
                        image
                    ),
                    "blur": 0,
                    "opacity": 100,
                    "dim": 0,
                }
            )

            self.assertEqual(
                palette_store.load()
                .matched_palette,
                (),
            )

            self.assertEqual(
                widget.palette_preferences
                .matched_palette,
                (),
            )

    def test_locked_background_disable_preserves_matched_palette(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            image = _solid_image(
                temp,
                "#e13d7b",
                "locked.png",
            )

            manager = _ThemeManager(
                {
                    "enabled": True,
                    "image_path": str(
                        image
                    ),
                    "blur": 0,
                    "opacity": 100,
                    "dim": 0,
                }
            )

            palette_store = (
                _palette_store(
                    temp
                )
            )

            palette_store.save(
                DashboardPalettePreferences
                .build(
                    source=(
                        PALETTE_SOURCE_BACKGROUND
                    ),
                    matched_palette=(
                        "#e13d7b",
                    ),
                    locked=True,
                )
            )

            widget = (
                DashboardChromaticSettingsWidget(
                    theme_manager=manager,
                    preference_store=(
                        _effect_store(
                            temp
                        )
                    ),
                    palette_store=(
                        palette_store
                    ),
                )
            )

            manager.set_atmosphere(
                {
                    "enabled": False,
                    "image_path": str(
                        image
                    ),
                    "blur": 0,
                    "opacity": 100,
                    "dim": 0,
                }
            )

            self.assertEqual(
                palette_store.load()
                .matched_palette,
                (
                    "#e13d7b",
                ),
            )

            self.assertTrue(
                widget.palette_preferences
                .locked
            )

    def test_switch_to_background_without_active_image_clears_stale_palette(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            image = _solid_image(
                temp,
                "#e13d7b",
                "inactive.png",
            )

            manager = _ThemeManager(
                {
                    "enabled": False,
                    "image_path": str(
                        image
                    ),
                    "blur": 0,
                    "opacity": 100,
                    "dim": 0,
                }
            )

            palette_store = (
                _palette_store(
                    temp
                )
            )

            palette_store.save(
                DashboardPalettePreferences
                .build(
                    source=(
                        PALETTE_SOURCE_THEME
                    ),
                    matched_palette=(
                        "#e13d7b",
                    ),
                    locked=False,
                )
            )

            widget = (
                DashboardChromaticSettingsWidget(
                    theme_manager=manager,
                    preference_store=(
                        _effect_store(
                            temp
                        )
                    ),
                    palette_store=(
                        palette_store
                    ),
                )
            )

            index = (
                widget.source_combo.findData(
                    PALETTE_SOURCE_BACKGROUND
                )
            )

            widget.source_combo.setCurrentIndex(
                index
            )

            stored = (
                palette_store.load()
            )

            self.assertEqual(
                stored.source,
                PALETTE_SOURCE_BACKGROUND,
            )

            self.assertEqual(
                stored.matched_palette,
                (),
            )

    def test_unlock_without_active_background_clears_preserved_palette(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            image = _solid_image(
                temp,
                "#e13d7b",
                "unlock-inactive.png",
            )

            manager = _ThemeManager(
                {
                    "enabled": False,
                    "image_path": str(
                        image
                    ),
                    "blur": 0,
                    "opacity": 100,
                    "dim": 0,
                }
            )

            palette_store = (
                _palette_store(
                    temp
                )
            )

            palette_store.save(
                DashboardPalettePreferences
                .build(
                    source=(
                        PALETTE_SOURCE_BACKGROUND
                    ),
                    matched_palette=(
                        "#e13d7b",
                    ),
                    locked=True,
                )
            )

            widget = (
                DashboardChromaticSettingsWidget(
                    theme_manager=manager,
                    preference_store=(
                        _effect_store(
                            temp
                        )
                    ),
                    palette_store=(
                        palette_store
                    ),
                )
            )

            widget.lock_box.setChecked(
                False
            )

            stored = (
                palette_store.load()
            )

            self.assertFalse(
                stored.locked
            )

            self.assertEqual(
                stored.matched_palette,
                (),
            )

    def test_unlock_with_active_background_refreshes_current_image(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            old_image = _solid_image(
                temp,
                "#e13d7b",
                "old.png",
            )

            current_image = _solid_image(
                temp,
                "#28c99a",
                "current.png",
            )

            manager = _ThemeManager(
                {
                    "enabled": True,
                    "image_path": str(
                        current_image
                    ),
                    "blur": 0,
                    "opacity": 100,
                    "dim": 0,
                }
            )

            palette_store = (
                _palette_store(
                    temp
                )
            )

            palette_store.save(
                DashboardPalettePreferences
                .build(
                    source=(
                        PALETTE_SOURCE_BACKGROUND
                    ),
                    matched_palette=(
                        "#e13d7b",
                    ),
                    locked=True,
                )
            )

            widget = (
                DashboardChromaticSettingsWidget(
                    theme_manager=manager,
                    preference_store=(
                        _effect_store(
                            temp
                        )
                    ),
                    palette_store=(
                        palette_store
                    ),
                )
            )

            self.assertTrue(
                old_image.is_file()
            )

            widget.lock_box.setChecked(
                False
            )

            stored = (
                palette_store.load()
            )

            self.assertFalse(
                stored.locked
            )

            self.assertEqual(
                stored.matched_palette,
                (
                    "#28c99a",
                ),
            )

    def test_dashboard_static_resolver_uses_palette_store(
        self,
    ):
        class _Store:

            def load(
                self,
            ):
                return (
                    DashboardPalettePreferences
                    .build(
                        source=(
                            PALETTE_SOURCE_MANUAL
                        ),
                        manual_palette=(
                            "#28c99a",
                        ),
                        strength=100,
                    )
                )

        with patch(
            (
                "src.ui.dashboard."
                "DashboardPalettePreferencesStore"
            ),
            return_value=_Store(),
        ):
            result = (
                DashboardPage
                ._resolve_dashboard_chromatic_theme(
                    BASE_THEME
                )
            )

        self.assertNotEqual(
            result[
                "accent"
            ],
            BASE_THEME[
                "accent"
            ],
        )

        self.assertEqual(
            result[
                "background"
            ],
            BASE_THEME[
                "background"
            ],
        )


if __name__ == "__main__":
    unittest.main()
