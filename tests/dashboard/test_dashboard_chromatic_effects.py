from __future__ import annotations

import inspect
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtCore import (
    QObject,
    QSettings,
    Qt,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
)

from src.system.dashboard_chromatic import (
    CHROMATIC_EFFECT_GRADIENT,
    CHROMATIC_EFFECT_NEON,
    CHROMATIC_EFFECT_PRISM,
    CHROMATIC_EFFECT_SOLID,
    DashboardChromaticPreferences,
    DashboardChromaticPreferencesStore,
)
from src.system.dashboard_palette import (
    PALETTE_SOURCE_MANUAL,
    DashboardPalettePreferences,
    DashboardPalettePreferencesStore,
)
from src.ui.dashboard import DashboardPage
from src.ui.dashboard_chromatic_effect import (
    ChromaticEffectPreview,
    DashboardChromaticEffectOverlay,
)
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

    def theme(
        self,
    ):
        return dict(
            BASE_THEME
        )

    def atmosphere(
        self,
    ):
        return {
            "enabled": False,
            "image_path": "",
            "blur": 0,
            "opacity": 100,
            "dim": 0,
        }


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


class DashboardChromaticEffectTests(
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

    def test_default_effect_is_solid(
        self,
    ):
        self.assertEqual(
            DashboardChromaticPreferences()
            .effect_style,
            CHROMATIC_EFFECT_SOLID,
        )

    def test_effect_store_persists_prism(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            store = (
                DashboardChromaticPreferencesStore(
                    _settings(
                        temp,
                        "effect.ini",
                    )
                )
            )

            preferences = (
                DashboardChromaticPreferences
                .build(
                    effect_style=(
                        CHROMATIC_EFFECT_PRISM
                    ),
                )
            )

            store.save(
                preferences
            )

            self.assertEqual(
                store.load()
                .effect_style,
                CHROMATIC_EFFECT_PRISM,
            )

    def test_overlay_is_mouse_transparent(
        self,
    ):
        canvas = QFrame()

        overlay = (
            DashboardChromaticEffectOverlay(
                canvas,
                target_provider=lambda: (),
            )
        )

        self.assertTrue(
            overlay.testAttribute(
                Qt.WidgetAttribute
                .WA_TransparentForMouseEvents
            )
        )

    def test_solid_timer_is_off(
        self,
    ):
        canvas = QFrame()

        canvas.resize(
            320,
            220,
        )

        canvas.show()

        overlay = (
            DashboardChromaticEffectOverlay(
                canvas,
                target_provider=lambda: (),
            )
        )

        overlay.configure(
            enabled=True,
            style=(
                CHROMATIC_EFFECT_SOLID
            ),
            intensity=80,
            colours=(
                "#e13d7b",
            ),
        )

        self.app.processEvents()

        self.assertFalse(
            overlay._animation_timer
            .isActive()
        )

        canvas.close()

    def test_gradient_timer_runs(
        self,
    ):
        canvas = QFrame()

        canvas.resize(
            320,
            220,
        )

        canvas.show()

        overlay = (
            DashboardChromaticEffectOverlay(
                canvas,
                target_provider=lambda: (),
            )
        )

        overlay.configure(
            enabled=True,
            style=(
                CHROMATIC_EFFECT_GRADIENT
            ),
            intensity=80,
            colours=(
                "#e13d7b",
                "#28c99a",
            ),
        )

        self.app.processEvents()

        self.assertTrue(
            overlay._animation_timer
            .isActive()
        )

        canvas.close()

    def test_neon_timer_runs(
        self,
    ):
        canvas = QFrame()

        canvas.resize(
            320,
            220,
        )

        canvas.show()

        overlay = (
            DashboardChromaticEffectOverlay(
                canvas,
                target_provider=lambda: (),
            )
        )

        overlay.configure(
            enabled=True,
            style=(
                CHROMATIC_EFFECT_NEON
            ),
            intensity=80,
            colours=(
                "#e13d7b",
            ),
        )

        self.app.processEvents()

        self.assertTrue(
            overlay._animation_timer
            .isActive()
        )

        canvas.close()

    def test_prism_timer_runs(
        self,
    ):
        canvas = QFrame()

        canvas.resize(
            320,
            220,
        )

        canvas.show()

        overlay = (
            DashboardChromaticEffectOverlay(
                canvas,
                target_provider=lambda: (),
            )
        )

        overlay.configure(
            enabled=True,
            style=(
                CHROMATIC_EFFECT_PRISM
            ),
            intensity=80,
            colours=(
                "#e13d7b",
                "#28c99a",
                "#6a63e8",
                "#f2ad45",
                "#d85be8",
            ),
        )

        self.app.processEvents()

        self.assertTrue(
            overlay._animation_timer
            .isActive()
        )

        canvas.close()

    def test_preview_accepts_five_colours(
        self,
    ):
        preview = (
            ChromaticEffectPreview()
        )

        preview.configure(
            style=(
                CHROMATIC_EFFECT_PRISM
            ),
            intensity=80,
            colours=(
                "#e13d7b",
                "#28c99a",
                "#6a63e8",
                "#f2ad45",
                "#d85be8",
            ),
            surface="#18181f",
            text="#f4f4f6",
        )

        self.assertEqual(
            len(
                preview.colours
            ),
            5,
        )

    def test_gradient_renderer_iterates_five_colour_stops(
        self,
    ):
        import src.ui.dashboard_chromatic_effect as module

        source = (
            inspect.getsource(
                module._gradient_brush
            )
            .replace(
                " ",
                "",
            )
            .replace(
                "\n",
                "",
            )
        )

        self.assertIn(
            "colours[:5]",
            source,
        )

        self.assertIn(
            "enumerate(values)",
            source,
        )

    def test_settings_exposes_four_effects(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            widget = (
                DashboardChromaticSettingsWidget(
                    theme_manager=(
                        _ThemeManager()
                    ),
                    preference_store=(
                        DashboardChromaticPreferencesStore(
                            _settings(
                                temp,
                                "effect.ini",
                            )
                        )
                    ),
                    palette_store=(
                        DashboardPalettePreferencesStore(
                            _settings(
                                temp,
                                "palette.ini",
                            )
                        )
                    ),
                )
            )

            self.assertEqual(
                [
                    widget.effect_style_combo
                    .itemText(
                        index
                    )
                    for index
                    in range(
                        widget.effect_style_combo
                        .count()
                    )
                ],
                [
                    "Solid",
                    "Gradient",
                    "Neon",
                    "Prism",
                ],
            )

    def test_effect_intensity_is_separate_from_colour_strength(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            palette_store = (
                DashboardPalettePreferencesStore(
                    _settings(
                        temp,
                        "palette.ini",
                    )
                )
            )

            effect_store = (
                DashboardChromaticPreferencesStore(
                    _settings(
                        temp,
                        "effect.ini",
                    )
                )
            )

            palette_store.save(
                DashboardPalettePreferences
                .build(
                    source=(
                        PALETTE_SOURCE_MANUAL
                    ),
                    strength=25,
                )
            )

            effect_store.save(
                DashboardChromaticPreferences
                .build(
                    strength=80,
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
                        palette_store
                    ),
                )
            )

            widget._change_strength(
                63
            )

            self.assertEqual(
                widget.effect_preferences
                .strength,
                63,
            )

            self.assertEqual(
                widget.palette_preferences
                .strength,
                25,
            )

    def test_effect_intensity_save_is_debounced(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            effect_store = (
                DashboardChromaticPreferencesStore(
                    _settings(
                        temp,
                        "effect.ini",
                    )
                )
            )

            effect_store.save(
                DashboardChromaticPreferences
                .build(
                    strength=80,
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
                        DashboardPalettePreferencesStore(
                            _settings(
                                temp,
                                "palette.ini",
                            )
                        )
                    ),
                )
            )

            widget._change_strength(
                41
            )

            self.assertEqual(
                effect_store.load()
                .strength,
                80,
            )

            widget._commit_strength()

            self.assertEqual(
                effect_store.load()
                .strength,
                41,
            )

    def test_animation_tick_does_not_restyle_or_persist(
        self,
    ):
        source = (
            inspect.getsource(
                DashboardChromaticEffectOverlay
                ._tick
            )
            + inspect.getsource(
                ChromaticEffectPreview
                ._tick
            )
        ).casefold()

        self.assertNotIn(
            "theme_changed",
            source,
        )

        self.assertNotIn(
            "qsettings",
            source,
        )

        self.assertNotIn(
            "setstylesheet",
            source,
        )

        self.assertIn(
            "update()",
            source,
        )

    def test_dashboard_effect_sync_uses_palette_store(
        self,
    ):
        source = (
            inspect.getsource(
                DashboardPage
                ._sync_dashboard_chromatic_effect
            )
            .casefold()
        )

        self.assertIn(
            "dashboardpalettepreferencesstore",
            source,
        )

        self.assertIn(
            "effect_colours_for_style",
            source,
        )

        self.assertNotIn(
            "resolve_dashboard_effect_colours",
            source,
        )

    def test_effect_disabled_hides_overlay(
        self,
    ):
        canvas = QFrame()

        canvas.resize(
            320,
            220,
        )

        canvas.show()

        overlay = (
            DashboardChromaticEffectOverlay(
                canvas,
                target_provider=lambda: (),
            )
        )

        overlay.configure(
            enabled=False,
            style=(
                CHROMATIC_EFFECT_PRISM
            ),
            intensity=100,
            colours=(
                "#e13d7b",
                "#28c99a",
                "#6a63e8",
            ),
        )

        self.app.processEvents()

        self.assertFalse(
            overlay.isVisible()
        )

        self.assertFalse(
            overlay._animation_timer
            .isActive()
        )

        canvas.close()


if __name__ == "__main__":
    unittest.main()
