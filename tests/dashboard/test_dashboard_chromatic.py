from __future__ import annotations

import dataclasses
import tempfile
import unittest
from pathlib import Path

from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QColor, QImage

from src.system.dashboard_chromatic import (
    CHROMATIC_MODE_BACKGROUND,
    CHROMATIC_MODE_MANUAL,
    CHROMATIC_SETTINGS_PREFIX,
    DEFAULT_MANUAL_ACCENT,
    DEFAULT_STRENGTH,
    DashboardChromaticError,
    DashboardChromaticPalette,
    DashboardChromaticPreferences,
    DashboardChromaticPreferencesStore,
    apply_accent_strength,
    blend_colours,
    build_dashboard_chromatic_theme,
    contrast_ratio,
    extract_dashboard_palette,
    extract_dashboard_palette_from_path,
    normalise_hex_colour,
    resolve_dashboard_accent,
    sanitize_dashboard_accent,
    update_matched_palette,
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
    "compact": True,
}


def make_image(
    width,
    height,
    colour,
):
    result = QImage(
        width,
        height,
        QImage.Format.Format_ARGB32,
    )

    result.fill(
        QColor(
            colour
        )
    )

    return result


class DashboardChromaticFoundationTests(
    unittest.TestCase
):

    def test_defaults_are_safe_and_disabled(
        self,
    ):
        prefs = DashboardChromaticPreferences()

        self.assertFalse(
            prefs.enabled
        )

        self.assertEqual(
            prefs.mode,
            CHROMATIC_MODE_BACKGROUND,
        )

        self.assertEqual(
            prefs.manual_accent,
            DEFAULT_MANUAL_ACCENT,
        )

        self.assertEqual(
            prefs.strength,
            DEFAULT_STRENGTH,
        )

        self.assertFalse(
            prefs.locked
        )

        self.assertEqual(
            prefs.matched_palette,
            (),
        )

    def test_preferences_are_immutable(
        self,
    ):
        prefs = DashboardChromaticPreferences()

        with self.assertRaises(
            dataclasses.FrozenInstanceError
        ):
            prefs.enabled = True

    def test_palette_is_immutable(
        self,
    ):
        palette = (
            DashboardChromaticPalette
            .build(
                (
                    "#ff0000",
                    "#00ff00",
                )
            )
        )

        with self.assertRaises(
            dataclasses.FrozenInstanceError
        ):
            palette.colours = ()

    def test_builder_normalises_and_clamps(
        self,
    ):
        prefs = (
            DashboardChromaticPreferences
            .build(
                enabled="true",
                mode="MANUAL",
                manual_accent="#F0A",
                strength=999,
                locked="yes",
                matched_palette=(
                    "#ABCDEF",
                    "#abcdef",
                    "bad",
                ),
            )
        )

        self.assertTrue(
            prefs.enabled
        )

        self.assertEqual(
            prefs.mode,
            CHROMATIC_MODE_MANUAL,
        )

        self.assertEqual(
            prefs.manual_accent,
            "#ff00aa",
        )

        self.assertEqual(
            prefs.strength,
            100,
        )

        self.assertTrue(
            prefs.locked
        )

        self.assertEqual(
            prefs.matched_palette,
            (
                "#abcdef",
            ),
        )

        self.assertEqual(
            prefs.matched_accent,
            "#abcdef",
        )

    def test_direct_unknown_mode_is_rejected(
        self,
    ):
        with self.assertRaises(
            DashboardChromaticError
        ):
            DashboardChromaticPreferences(
                mode="unknown",
            )

    def test_direct_invalid_strength_is_rejected(
        self,
    ):
        with self.assertRaises(
            DashboardChromaticError
        ):
            DashboardChromaticPreferences(
                strength=101,
            )

    def test_direct_invalid_colour_is_rejected(
        self,
    ):
        with self.assertRaises(
            DashboardChromaticError
        ):
            DashboardChromaticPreferences(
                manual_accent="pink",
            )

    def test_short_hex_is_normalised(
        self,
    ):
        self.assertEqual(
            normalise_hex_colour(
                "#F8A"
            ),
            "#ff88aa",
        )

    def test_invalid_hex_returns_empty(
        self,
    ):
        self.assertEqual(
            normalise_hex_colour(
                "invalid"
            ),
            "",
        )

    def test_store_round_trip(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            settings = QSettings(
                str(
                    Path(temp)
                    / "settings.ini"
                ),
                QSettings.Format.IniFormat,
            )

            store = (
                DashboardChromaticPreferencesStore(
                    settings
                )
            )

            expected = (
                DashboardChromaticPreferences
                .build(
                    enabled=True,
                    mode=CHROMATIC_MODE_MANUAL,
                    manual_accent="#12ABEF",
                    strength=67,
                    locked=True,
                    matched_accent="#CC4466",
                    matched_palette=(
                        "#CC4466",
                        "#44CC88",
                        "#6655CC",
                    ),
                )
            )

            store.save(
                expected
            )

            self.assertEqual(
                store.load(),
                expected,
            )

            self.assertEqual(
                set(
                    settings.allKeys()
                ),
                {
                    CHROMATIC_SETTINGS_PREFIX
                    + "/enabled",

                    CHROMATIC_SETTINGS_PREFIX
                    + "/locked",

                    CHROMATIC_SETTINGS_PREFIX
                    + "/manual_accent",

                    CHROMATIC_SETTINGS_PREFIX
                    + "/matched_accent",

                    CHROMATIC_SETTINGS_PREFIX
                    + "/mode",

                    CHROMATIC_SETTINGS_PREFIX
                    + "/palette",

                    CHROMATIC_SETTINGS_PREFIX
                    + "/strength",
                },
            )

    def test_corrupt_store_values_fail_closed(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            settings = QSettings(
                str(
                    Path(temp)
                    / "settings.ini"
                ),
                QSettings.Format.IniFormat,
            )

            prefix = CHROMATIC_SETTINGS_PREFIX

            settings.setValue(
                prefix + "/enabled",
                "garbage",
            )

            settings.setValue(
                prefix + "/mode",
                "???",
            )

            settings.setValue(
                prefix + "/manual_accent",
                "mud",
            )

            settings.setValue(
                prefix + "/strength",
                "not-a-number",
            )

            settings.setValue(
                prefix + "/locked",
                "???",
            )

            settings.setValue(
                prefix + "/palette",
                "{broken",
            )

            prefs = (
                DashboardChromaticPreferencesStore(
                    settings
                )
                .load()
            )

            self.assertFalse(
                prefs.enabled
            )

            self.assertEqual(
                prefs.mode,
                CHROMATIC_MODE_BACKGROUND,
            )

            self.assertEqual(
                prefs.manual_accent,
                DEFAULT_MANUAL_ACCENT,
            )

            self.assertEqual(
                prefs.strength,
                DEFAULT_STRENGTH,
            )

            self.assertFalse(
                prefs.locked
            )

            self.assertEqual(
                prefs.matched_palette,
                (),
            )

    def test_solid_saturated_image_extracts_colour(
        self,
    ):
        palette = extract_dashboard_palette(
            make_image(
                32,
                32,
                "#e82f78",
            )
        )

        self.assertEqual(
            palette.primary,
            "#e82f78",
        )

    def test_near_black_is_rejected(
        self,
    ):
        self.assertEqual(
            extract_dashboard_palette(
                make_image(
                    32,
                    32,
                    "#080808",
                )
            ).colours,
            (),
        )

    def test_white_is_rejected(
        self,
    ):
        self.assertEqual(
            extract_dashboard_palette(
                make_image(
                    32,
                    32,
                    "#ffffff",
                )
            ).colours,
            (),
        )

    def test_muddy_low_saturation_is_rejected(
        self,
    ):
        self.assertEqual(
            extract_dashboard_palette(
                make_image(
                    32,
                    32,
                    "#746d68",
                )
            ).colours,
            (),
        )

    def test_transparent_pixels_are_ignored(
        self,
    ):
        value = QImage(
            32,
            32,
            QImage.Format.Format_ARGB32,
        )

        value.fill(
            QColor(
                255,
                0,
                0,
                0,
            )
        )

        self.assertEqual(
            extract_dashboard_palette(
                value
            ).colours,
            (),
        )

    def test_colourful_region_wins_over_gray(
        self,
    ):
        value = make_image(
            80,
            40,
            "#777777",
        )

        for y in range(40):
            for x in range(24):
                value.setPixelColor(
                    x,
                    y,
                    QColor(
                        "#e23783"
                    ),
                )

        self.assertEqual(
            extract_dashboard_palette(
                value
            ).primary,
            "#e23783",
        )

    def test_three_distinct_colours_are_preserved(
        self,
    ):
        value = make_image(
            90,
            30,
            "#ef3e75",
        )

        for y in range(30):
            for x in range(
                30,
                60,
            ):
                value.setPixelColor(
                    x,
                    y,
                    QColor(
                        "#30c98a"
                    ),
                )

            for x in range(
                60,
                90,
            ):
                value.setPixelColor(
                    x,
                    y,
                    QColor(
                        "#6d63e8"
                    ),
                )

        palette = extract_dashboard_palette(
            value
        )

        self.assertEqual(
            len(
                palette.colours
            ),
            3,
        )

        self.assertEqual(
            set(
                palette.colours
            ),
            {
                "#ef3e75",
                "#30c98a",
                "#6d63e8",
            },
        )

    def test_missing_path_fails_closed(
        self,
    ):
        self.assertEqual(
            extract_dashboard_palette_from_path(
                r"Z:\definitely\missing.png"
            ).colours,
            (),
        )

    def test_saved_qimage_can_be_analysed(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            path = (
                Path(temp)
                / "wallpaper.png"
            )

            source = make_image(
                24,
                24,
                "#26b8d5",
            )

            self.assertTrue(
                source.save(
                    str(path),
                    "PNG",
                )
            )

            self.assertEqual(
                extract_dashboard_palette_from_path(
                    path
                ).primary,
                "#26b8d5",
            )

    def test_black_white_contrast_is_twenty_one(
        self,
    ):
        self.assertAlmostEqual(
            contrast_ratio(
                "#000000",
                "#ffffff",
            ),
            21.0,
            places=3,
        )

    def test_sanitizer_preserves_usable_accent(
        self,
    ):
        accent = "#ff79b9"

        self.assertEqual(
            sanitize_dashboard_accent(
                accent,
                "#140812",
            ),
            accent,
        )

    def test_sanitizer_repairs_dark_on_dark(
        self,
    ):
        result = sanitize_dashboard_accent(
            "#311020",
            "#140812",
        )

        self.assertGreaterEqual(
            contrast_ratio(
                result,
                "#140812",
            ),
            4.5,
        )

    def test_sanitizer_repairs_light_on_light(
        self,
    ):
        result = sanitize_dashboard_accent(
            "#f9a8c8",
            "#fff9fc",
        )

        self.assertGreaterEqual(
            contrast_ratio(
                result,
                "#fff9fc",
            ),
            4.5,
        )

    def test_strength_zero_returns_base(
        self,
    ):
        self.assertEqual(
            apply_accent_strength(
                "#00ffaa",
                "#ff79b9",
                0,
            ),
            "#ff79b9",
        )

    def test_strength_one_hundred_returns_source(
        self,
    ):
        self.assertEqual(
            apply_accent_strength(
                "#00ffaa",
                "#ff79b9",
                100,
            ),
            "#00ffaa",
        )

    def test_blending_is_deterministic(
        self,
    ):
        self.assertEqual(
            blend_colours(
                "#000000",
                "#ffffff",
                0.5,
            ),
            "#808080",
        )

    def test_disabled_theme_is_exact_copy(
        self,
    ):
        result = build_dashboard_chromatic_theme(
            BASE_THEME,
            DashboardChromaticPreferences(),
        )

        self.assertEqual(
            result,
            BASE_THEME,
        )

        self.assertIsNot(
            result,
            BASE_THEME,
        )

    def test_manual_mode_uses_manual_accent(
        self,
    ):
        prefs = (
            DashboardChromaticPreferences
            .build(
                enabled=True,
                mode=CHROMATIC_MODE_MANUAL,
                manual_accent="#2ed7a2",
                strength=100,
            )
        )

        self.assertEqual(
            resolve_dashboard_accent(
                BASE_THEME,
                prefs,
            ),
            "#2ed7a2",
        )

    def test_background_mode_uses_matched_accent(
        self,
    ):
        prefs = (
            DashboardChromaticPreferences
            .build(
                enabled=True,
                mode=CHROMATIC_MODE_BACKGROUND,
                matched_accent="#38c7da",
                strength=100,
            )
        )

        self.assertEqual(
            resolve_dashboard_accent(
                BASE_THEME,
                prefs,
            ),
            "#38c7da",
        )

    def test_background_mode_without_match_falls_back(
        self,
    ):
        prefs = (
            DashboardChromaticPreferences
            .build(
                enabled=True,
                mode=CHROMATIC_MODE_BACKGROUND,
                strength=100,
            )
        )

        self.assertEqual(
            resolve_dashboard_accent(
                BASE_THEME,
                prefs,
            ),
            BASE_THEME["accent"],
        )

    def test_overlay_preserves_global_theme_fields(
        self,
    ):
        prefs = (
            DashboardChromaticPreferences
            .build(
                enabled=True,
                mode=CHROMATIC_MODE_MANUAL,
                manual_accent="#35c99b",
                strength=100,
            )
        )

        result = build_dashboard_chromatic_theme(
            BASE_THEME,
            prefs,
        )

        for key in (
            "background",
            "sidebar",
            "text",
            "muted",
            "compact",
            "preset",
        ):
            self.assertEqual(
                result[key],
                BASE_THEME[key],
            )

        self.assertEqual(
            result["accent"],
            "#35c99b",
        )

        self.assertNotEqual(
            result["border"],
            BASE_THEME["border"],
        )

        self.assertNotEqual(
            result["card_alt"],
            BASE_THEME["card_alt"],
        )

    def test_strength_does_not_mutate_source_palette(
        self,
    ):
        prefs = (
            DashboardChromaticPreferences
            .build(
                enabled=True,
                mode=CHROMATIC_MODE_BACKGROUND,
                strength=35,
                matched_accent="#35c99b",
                matched_palette=(
                    "#35c99b",
                    "#4b7bea",
                ),
            )
        )

        original = prefs.matched_palette

        build_dashboard_chromatic_theme(
            BASE_THEME,
            prefs,
        )

        self.assertEqual(
            prefs.matched_palette,
            original,
        )

        self.assertEqual(
            prefs.matched_accent,
            "#35c99b",
        )

    def test_locked_palette_ignores_automatic_replacement(
        self,
    ):
        prefs = (
            DashboardChromaticPreferences
            .build(
                enabled=True,
                locked=True,
                matched_accent="#ff5577",
                matched_palette=(
                    "#ff5577",
                ),
            )
        )

        replacement = (
            DashboardChromaticPalette
            .build(
                (
                    "#22ccaa",
                )
            )
        )

        result = update_matched_palette(
            prefs,
            replacement,
        )

        self.assertIs(
            result,
            prefs,
        )

    def test_force_can_recalculate_locked_palette(
        self,
    ):
        prefs = (
            DashboardChromaticPreferences
            .build(
                enabled=True,
                locked=True,
                matched_accent="#ff5577",
                matched_palette=(
                    "#ff5577",
                ),
            )
        )

        replacement = (
            DashboardChromaticPalette
            .build(
                (
                    "#22ccaa",
                    "#5688ff",
                )
            )
        )

        result = update_matched_palette(
            prefs,
            replacement,
            force=True,
        )

        self.assertEqual(
            result.matched_accent,
            "#22ccaa",
        )

        self.assertEqual(
            result.matched_palette,
            (
                "#22ccaa",
                "#5688ff",
            ),
        )

        self.assertTrue(
            result.locked
        )

    def test_unlocked_palette_updates_preview(
        self,
    ):
        prefs = (
            DashboardChromaticPreferences
            .build(
                enabled=True,
                locked=False,
            )
        )

        palette = (
            DashboardChromaticPalette
            .build(
                (
                    "#d84582",
                    "#3ec6a0",
                    "#725de5",
                )
            )
        )

        result = update_matched_palette(
            prefs,
            palette,
        )

        self.assertEqual(
            result.matched_accent,
            "#d84582",
        )

        self.assertEqual(
            result.matched_palette,
            palette.colours,
        )


if __name__ == "__main__":
    unittest.main()
