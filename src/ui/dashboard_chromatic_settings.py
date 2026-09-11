from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PyQt6.QtCore import (
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
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
    MAX_PALETTE_COLOURS,
    PALETTE_SOURCE_BACKGROUND,
    PALETTE_SOURCE_MANUAL,
    PALETTE_SOURCE_THEME,
    DashboardPalettePreferences,
    DashboardPalettePreferencesStore,
    effect_colours_for_style,
    extract_dashboard_palette_from_path,
    resolve_dashboard_palette,
    update_matched_palette,
)
from src.ui.dashboard_chromatic_effect import (
    ChromaticEffectPreview,
)


class DashboardChromaticSettingsWidget(
    QFrame
):

    message_changed = pyqtSignal(
        str
    )

    def __init__(
        self,
        theme_manager,
        parent=None,
        *,
        preference_store=None,
        palette_store=None,
        effect_store=None,
    ):
        super().__init__(
            parent
        )

        self.theme_manager = (
            theme_manager
        )

        if effect_store is None:
            effect_store = (
                preference_store
            )

        self.effect_store = (
            effect_store
            if effect_store
            is not None
            else DashboardChromaticPreferencesStore()
        )

        self.preference_store = (
            self.effect_store
        )

        self.palette_store = (
            palette_store
            if palette_store
            is not None
            else DashboardPalettePreferencesStore()
        )

        try:
            self._effect_preferences = (
                self.effect_store.load()
            )

        except Exception:
            self._effect_preferences = (
                DashboardChromaticPreferences()
            )

        try:
            self._palette_preferences = (
                self.palette_store.load()
            )

        except Exception:
            self._palette_preferences = (
                DashboardPalettePreferences()
            )

        self._theme = {}
        self._border_colour = (
            "#5c4777"
        )

        self._last_saved_colour_strength = (
            self._palette_preferences.strength
        )

        self._last_saved_effect_strength = (
            self._effect_preferences.strength
        )

        self._colour_commit_timer = (
            QTimer(
                self
            )
        )

        self._colour_commit_timer.setSingleShot(
            True
        )

        self._colour_commit_timer.setInterval(
            160
        )

        self._colour_commit_timer.timeout.connect(
            self._commit_colour_strength
        )

        self._effect_commit_timer = (
            QTimer(
                self
            )
        )

        self._effect_commit_timer.setSingleShot(
            True
        )

        self._effect_commit_timer.setInterval(
            160
        )

        self._effect_commit_timer.timeout.connect(
            self._commit_effect_strength
        )

        self.setObjectName(
            "dashboardChromaticPanel"
        )

        self._build_ui()
        self._connect_signals()

        theme = (
            self._current_theme()
        )

        if theme:
            self.apply_theme(
                theme
            )

        self._sync_controls()

        if (
            self._palette_preferences.source
            == PALETTE_SOURCE_BACKGROUND
            and not self._palette_preferences.locked
        ):
            atmosphere = (
                self._current_atmosphere()
            )

            if (
                self._has_background_image(
                    atmosphere
                )
            ):
                self._match_atmosphere(
                    atmosphere,
                    force=False,
                    notify=False,
                )

    @property
    def preferences(
        self,
    ):
        return (
            self._effect_preferences
        )

    @property
    def palette_preferences(
        self,
    ):
        return (
            self._palette_preferences
        )

    @property
    def effect_preferences(
        self,
    ):
        return (
            self._effect_preferences
        )

    def _build_ui(
        self,
    ):
        root = QVBoxLayout(
            self
        )

        root.setContentsMargins(
            14,
            14,
            14,
            14,
        )

        root.setSpacing(
            10
        )

        title = QLabel(
            "Dashboard Colours"
        )

        title.setObjectName(
            "dashboardChromaticTitle"
        )

        description = QLabel(
            (
                "Choose how Dashboard colours are created. "
                "Theme keeps normal styling, Match Background "
                "uses colours from your Atmosphere image, and "
                "Manual Palette lets you choose up to five."
            )
        )

        description.setObjectName(
            "dashboardChromaticHelp"
        )

        description.setWordWrap(
            True
        )

        root.addWidget(
            title
        )

        root.addWidget(
            description
        )

        source_row = QHBoxLayout()

        source_row.setSpacing(
            10
        )

        source_label = QLabel(
            "Colour source"
        )

        source_label.setObjectName(
            "fieldLabel"
        )

        source_label.setMinimumWidth(
            110
        )

        self.source_combo = QComboBox()

        self.source_combo.setObjectName(
            "dashboardPaletteSource"
        )

        self.source_combo.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.source_combo.addItem(
            "Theme",
            PALETTE_SOURCE_THEME,
        )

        self.source_combo.addItem(
            "Match Background",
            PALETTE_SOURCE_BACKGROUND,
        )

        self.source_combo.addItem(
            "Manual Palette",
            PALETTE_SOURCE_MANUAL,
        )

        source_row.addWidget(
            source_label
        )

        source_row.addWidget(
            self.source_combo,
            1,
        )

        root.addLayout(
            source_row
        )

        colour_strength_row = (
            QHBoxLayout()
        )

        colour_strength_row.setSpacing(
            10
        )

        colour_strength_label = QLabel(
            "Colour strength"
        )

        colour_strength_label.setObjectName(
            "fieldLabel"
        )

        colour_strength_label.setMinimumWidth(
            110
        )

        self.colour_strength_slider = (
            QSlider(
                Qt.Orientation.Horizontal
            )
        )

        self.colour_strength_slider.setObjectName(
            "dashboardPaletteStrength"
        )

        self.colour_strength_slider.setRange(
            0,
            100,
        )

        self.colour_strength_slider.setTracking(
            True
        )

        self.colour_strength_value = (
            QLabel()
        )

        self.colour_strength_value.setObjectName(
            "dashboardPaletteStrengthValue"
        )

        self.colour_strength_value.setMinimumWidth(
            38
        )

        self.colour_strength_value.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )

        colour_strength_row.addWidget(
            colour_strength_label
        )

        colour_strength_row.addWidget(
            self.colour_strength_slider,
            1,
        )

        colour_strength_row.addWidget(
            self.colour_strength_value
        )

        root.addLayout(
            colour_strength_row
        )

        count_row = QHBoxLayout()

        count_row.setSpacing(
            10
        )

        self.manual_count_label = QLabel(
            "Colours in palette"
        )

        self.manual_count_label.setObjectName(
            "fieldLabel"
        )

        self.manual_count_label.setMinimumWidth(
            110
        )

        self.manual_count_combo = (
            QComboBox()
        )

        self.manual_count_combo.setObjectName(
            "dashboardPaletteCount"
        )

        self.manual_count_combo.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        for count in range(
            1,
            MAX_PALETTE_COLOURS
            + 1,
        ):
            self.manual_count_combo.addItem(
                str(
                    count
                ),
                count,
            )

        count_row.addWidget(
            self.manual_count_label
        )

        count_row.addWidget(
            self.manual_count_combo,
            1,
        )

        root.addLayout(
            count_row
        )

        palette_label = QLabel(
            "Palette"
        )

        palette_label.setObjectName(
            "fieldLabel"
        )

        root.addWidget(
            palette_label
        )

        self.colour_swatches = []
        self.colour_buttons = []

        for index in range(
            MAX_PALETTE_COLOURS
        ):
            row = QHBoxLayout()

            row.setSpacing(
                10
            )

            label = QLabel(
                "Colour "
                + str(
                    index
                    + 1
                )
            )

            label.setObjectName(
                "fieldLabel"
            )

            label.setMinimumWidth(
                70
            )

            swatch = QFrame()

            swatch.setObjectName(
                "dashboardPaletteSwatch"
            )

            swatch.setFixedSize(
                42,
                24,
            )

            button = QPushButton(
                "Choose"
            )

            button.setObjectName(
                "dashboardPaletteChoose"
            )

            button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

            button.clicked.connect(
                (
                    lambda checked=False,
                    slot=index:
                    self._choose_manual_colour(
                        slot
                    )
                )
            )

            row.addWidget(
                label
            )

            row.addWidget(
                swatch
            )

            row.addWidget(
                button
            )

            row.addStretch()

            root.addLayout(
                row
            )

            self.colour_swatches.append(
                swatch
            )

            self.colour_buttons.append(
                button
            )

        match_row = QHBoxLayout()

        match_row.setSpacing(
            10
        )

        self.recalculate_button = (
            QPushButton(
                "Recalculate"
            )
        )

        self.recalculate_button.setObjectName(
            "dashboardPaletteRecalculate"
        )

        self.recalculate_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.lock_box = QCheckBox(
            "Lock matched palette"
        )

        self.lock_box.setObjectName(
            "dashboardPaletteLock"
        )

        match_row.addWidget(
            self.recalculate_button
        )

        match_row.addWidget(
            self.lock_box
        )

        match_row.addStretch()

        root.addLayout(
            match_row
        )

        separator = QFrame()

        separator.setObjectName(
            "dashboardPaletteSeparator"
        )

        separator.setFrameShape(
            QFrame.Shape.HLine
        )

        root.addWidget(
            separator
        )

        effects_title = QLabel(
            "Chromatic Effects"
        )

        effects_title.setObjectName(
            "dashboardChromaticTitle"
        )

        effects_description = QLabel(
            (
                "Optional animated effects use the same Dashboard "
                "palette. Solid and Neon use Colour 1. Gradient and "
                "Prism use every active colour, up to five."
            )
        )

        effects_description.setObjectName(
            "dashboardChromaticHelp"
        )

        effects_description.setWordWrap(
            True
        )

        root.addWidget(
            effects_title
        )

        root.addWidget(
            effects_description
        )

        preview_label = QLabel(
            "Effect preview"
        )

        preview_label.setObjectName(
            "fieldLabel"
        )

        root.addWidget(
            preview_label
        )

        self.effect_preview = (
            ChromaticEffectPreview(
                self
            )
        )

        root.addWidget(
            self.effect_preview
        )

        self.enabled_box = QCheckBox(
            "Enable Chromatic Effects"
        )

        self.enabled_box.setObjectName(
            "dashboardChromaticEnabled"
        )

        root.addWidget(
            self.enabled_box
        )

        effect_row = QHBoxLayout()

        effect_row.setSpacing(
            10
        )

        effect_label = QLabel(
            "Effect style"
        )

        effect_label.setObjectName(
            "fieldLabel"
        )

        effect_label.setMinimumWidth(
            110
        )

        self.effect_style_combo = (
            QComboBox()
        )

        self.effect_style_combo.setObjectName(
            "dashboardChromaticEffectStyle"
        )

        self.effect_style_combo.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.effect_style_combo.addItem(
            "Solid",
            CHROMATIC_EFFECT_SOLID,
        )

        self.effect_style_combo.addItem(
            "Gradient",
            CHROMATIC_EFFECT_GRADIENT,
        )

        self.effect_style_combo.addItem(
            "Neon",
            CHROMATIC_EFFECT_NEON,
        )

        self.effect_style_combo.addItem(
            "Prism",
            CHROMATIC_EFFECT_PRISM,
        )

        effect_row.addWidget(
            effect_label
        )

        effect_row.addWidget(
            self.effect_style_combo,
            1,
        )

        root.addLayout(
            effect_row
        )

        effect_strength_row = (
            QHBoxLayout()
        )

        effect_strength_row.setSpacing(
            10
        )

        effect_strength_label = QLabel(
            "Effect intensity"
        )

        effect_strength_label.setObjectName(
            "fieldLabel"
        )

        effect_strength_label.setMinimumWidth(
            110
        )

        self.strength_slider = (
            QSlider(
                Qt.Orientation.Horizontal
            )
        )

        self.strength_slider.setObjectName(
            "dashboardChromaticStrength"
        )

        self.strength_slider.setRange(
            0,
            100,
        )

        self.strength_slider.setTracking(
            True
        )

        self.strength_value = QLabel()

        self.strength_value.setObjectName(
            "dashboardChromaticStrengthValue"
        )

        self.strength_value.setMinimumWidth(
            38
        )

        self.strength_value.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )

        effect_strength_row.addWidget(
            effect_strength_label
        )

        effect_strength_row.addWidget(
            self.strength_slider,
            1,
        )

        effect_strength_row.addWidget(
            self.strength_value
        )

        root.addLayout(
            effect_strength_row
        )

        self.status_label = QLabel()

        self.status_label.setObjectName(
            "dashboardChromaticStatus"
        )

        self.status_label.setWordWrap(
            True
        )

        root.addWidget(
            self.status_label
        )

    def _connect_signals(
        self,
    ):
        self.source_combo.currentIndexChanged.connect(
            self._change_source
        )

        self.manual_count_combo.currentIndexChanged.connect(
            self._change_manual_count
        )

        self.colour_strength_slider.valueChanged.connect(
            self._change_colour_strength
        )

        self.colour_strength_slider.sliderReleased.connect(
            self._commit_colour_strength
        )

        self.recalculate_button.clicked.connect(
            self.recalculate_background
        )

        self.lock_box.toggled.connect(
            self._change_lock
        )

        self.enabled_box.toggled.connect(
            self._change_enabled
        )

        self.effect_style_combo.currentIndexChanged.connect(
            self._change_effect_style
        )

        self.strength_slider.valueChanged.connect(
            self._change_strength
        )

        self.strength_slider.sliderReleased.connect(
            self._commit_strength
        )

        atmosphere_signal = getattr(
            self.theme_manager,
            "atmosphere_changed",
            None,
        )

        connect = getattr(
            atmosphere_signal,
            "connect",
            None,
        )

        if callable(
            connect
        ):
            connect(
                self._handle_atmosphere_changed
            )

        theme_signal = getattr(
            self.theme_manager,
            "theme_changed",
            None,
        )

        connect = getattr(
            theme_signal,
            "connect",
            None,
        )

        if callable(
            connect
        ):
            connect(
                self.apply_theme
            )

    def _current_theme(
        self,
    ):
        getter = getattr(
            self.theme_manager,
            "theme",
            None,
        )

        if not callable(
            getter
        ):
            return {}

        try:
            theme = getter()

        except Exception:
            return {}

        if not isinstance(
            theme,
            dict,
        ):
            return {}

        return dict(
            theme
        )

    def _current_atmosphere(
        self,
    ):
        getter = getattr(
            self.theme_manager,
            "atmosphere",
            None,
        )

        if not callable(
            getter
        ):
            return {}

        try:
            atmosphere = getter()

        except Exception:
            return {}

        if not isinstance(
            atmosphere,
            dict,
        ):
            return {}

        return dict(
            atmosphere
        )

    @staticmethod
    def _background_image_path(
        atmosphere,
    ):
        if not isinstance(
            atmosphere,
            dict,
        ):
            return ""

        return str(
            atmosphere.get(
                "image_path",
                "",
            )
            or ""
        ).strip()

    @classmethod
    def _has_background_image(
        cls,
        atmosphere,
    ):
        value = (
            cls._background_image_path(
                atmosphere
            )
        )

        return bool(
            value
            and Path(
                value
            ).is_file()
        )

    def _notify_theme_refresh(
        self,
    ):
        theme = (
            self._current_theme()
        )

        if not theme:
            return False

        signal = getattr(
            self.theme_manager,
            "theme_changed",
            None,
        )

        emit = getattr(
            signal,
            "emit",
            None,
        )

        if not callable(
            emit
        ):
            return False

        emit(
            theme
        )

        return True

    def refresh_from_store(
        self,
    ):
        try:
            self._effect_preferences = (
                self.effect_store.load()
            )

        except Exception:
            pass

        try:
            self._palette_preferences = (
                self.palette_store.load()
            )

        except Exception:
            pass

        self._last_saved_effect_strength = (
            self._effect_preferences.strength
        )

        self._last_saved_colour_strength = (
            self._palette_preferences.strength
        )

        self._sync_controls()

    def _save_preferences(
        self,
        preferences,
        *,
        notify=True,
        message="",
    ):
        return self._save_effect(
            preferences,
            notify=notify,
            message=message,
        )

    def _save_effect(
        self,
        preferences,
        *,
        notify=True,
        message="",
    ):
        if not isinstance(
            preferences,
            DashboardChromaticPreferences,
        ):
            return False

        try:
            self.effect_store.save(
                preferences
            )

        except Exception:
            self.status_label.setText(
                "Chromatic effects could not be saved."
            )

            return False

        self._effect_preferences = (
            preferences
        )

        self._last_saved_effect_strength = (
            preferences.strength
        )

        self._sync_controls()

        if notify:
            self._notify_theme_refresh()

        if message:
            self.status_label.setText(
                message
            )

            self.message_changed.emit(
                message
            )

        return True

    def _save_palette(
        self,
        preferences,
        *,
        notify=True,
        message="",
    ):
        if not isinstance(
            preferences,
            DashboardPalettePreferences,
        ):
            return False

        try:
            self.palette_store.save(
                preferences
            )

        except Exception:
            self.status_label.setText(
                "Dashboard colours could not be saved."
            )

            return False

        self._palette_preferences = (
            preferences
        )

        self._last_saved_colour_strength = (
            preferences.strength
        )

        self._sync_controls()

        if notify:
            self._notify_theme_refresh()

        if message:
            self.status_label.setText(
                message
            )

            self.message_changed.emit(
                message
            )

        return True

    def _display_palette(
        self,
    ):
        theme = (
            self._theme
            if self._theme
            else self._current_theme()
        )

        try:
            return (
                resolve_dashboard_palette(
                    theme,
                    self._palette_preferences,
                )
            )

        except Exception:
            return ()

    def _effect_colours(
        self,
    ):
        return (
            effect_colours_for_style(
                self._display_palette(),
                self._effect_preferences.effect_style,
            )
        )

    def _sync_controls(
        self,
    ):
        palette = (
            self._palette_preferences
        )

        effect = (
            self._effect_preferences
        )

        widgets = (
            self.source_combo,
            self.manual_count_combo,
            self.colour_strength_slider,
            self.lock_box,
            self.enabled_box,
            self.effect_style_combo,
            self.strength_slider,
        )

        for widget in widgets:
            widget.blockSignals(
                True
            )

        try:
            source_index = (
                self.source_combo.findData(
                    palette.source
                )
            )

            if source_index < 0:
                source_index = 0

            self.source_combo.setCurrentIndex(
                source_index
            )

            count_index = (
                self.manual_count_combo.findData(
                    palette.manual_count
                )
            )

            if count_index < 0:
                count_index = 0

            self.manual_count_combo.setCurrentIndex(
                count_index
            )

            self.colour_strength_slider.setValue(
                palette.strength
            )

            self.lock_box.setChecked(
                palette.locked
            )

            self.enabled_box.setChecked(
                effect.enabled
            )

            effect_index = (
                self.effect_style_combo.findData(
                    effect.effect_style
                )
            )

            if effect_index < 0:
                effect_index = 0

            self.effect_style_combo.setCurrentIndex(
                effect_index
            )

            self.strength_slider.setValue(
                effect.strength
            )

        finally:
            for widget in widgets:
                widget.blockSignals(
                    False
                )

        self.colour_strength_value.setText(
            str(
                palette.strength
            )
            + "%"
        )

        self.strength_value.setText(
            str(
                effect.strength
            )
            + "%"
        )

        manual = (
            palette.source
            == PALETTE_SOURCE_MANUAL
        )

        matched = (
            palette.source
            == PALETTE_SOURCE_BACKGROUND
        )

        self.manual_count_label.setEnabled(
            manual
        )

        self.manual_count_combo.setEnabled(
            manual
        )

        self.recalculate_button.setEnabled(
            matched
        )

        self.lock_box.setEnabled(
            matched
        )

        self.effect_style_combo.setEnabled(
            effect.enabled
        )

        self.strength_slider.setEnabled(
            effect.enabled
        )

        self._update_swatches()
        self._sync_preview()
        self._update_status()

    def _update_swatches(
        self,
    ):
        palette = (
            self._palette_preferences
        )

        manual = (
            palette.source
            == PALETTE_SOURCE_MANUAL
        )

        if manual:
            values = list(
                palette.manual_palette[
                    :palette.manual_count
                ]
            )

        else:
            values = list(
                self._display_palette()
            )

        for index in range(
            MAX_PALETTE_COLOURS
        ):
            colour = (
                values[index]
                if index
                < len(
                    values
                )
                else ""
            )

            swatch = (
                self.colour_swatches[
                    index
                ]
            )

            button = (
                self.colour_buttons[
                    index
                ]
            )

            if colour:
                swatch.setStyleSheet(
                    (
                        "background: "
                        + colour
                        + "; border: 1px solid "
                        + self._border_colour
                        + "; border-radius: 6px;"
                    )
                )

                swatch.setToolTip(
                    colour.upper()
                )

                swatch.setAccessibleDescription(
                    colour.upper()
                )

            else:
                swatch.setStyleSheet(
                    (
                        "background: transparent; "
                        "border: 1px dashed "
                        + self._border_colour
                        + "; border-radius: 6px;"
                    )
                )

                swatch.setToolTip(
                    "No active colour"
                )

                swatch.setAccessibleDescription(
                    "No active colour"
                )

            editable = (
                manual
                and index
                < palette.manual_count
            )

            button.setVisible(
                manual
            )

            button.setEnabled(
                editable
            )

    def _sync_preview(
        self,
    ):
        theme = (
            self._theme
            if self._theme
            else self._current_theme()
        )

        self.effect_preview.configure(
            style=(
                self._effect_preferences.effect_style
            ),
            intensity=(
                self._effect_preferences.strength
            ),
            colours=(
                self._effect_colours()
            ),
            surface=str(
                theme.get(
                    "card_alt",
                    "#202028",
                )
            ),
            text=str(
                theme.get(
                    "text",
                    "#f4f4f6",
                )
            ),
        )

    def _update_status(
        self,
    ):
        palette = (
            self._palette_preferences
        )

        effect = (
            self._effect_preferences
        )

        if (
            palette.source
            == PALETTE_SOURCE_THEME
        ):
            source_text = (
                "Dashboard colours use the normal app theme."
            )

        elif (
            palette.source
            == PALETTE_SOURCE_BACKGROUND
        ):
            count = len(
                palette.matched_palette
            )

            if count:
                source_text = (
                    "Matched "
                    + str(
                        count
                    )
                    + " background colour"
                    + (
                        ""
                        if count == 1
                        else "s"
                    )
                    + "."
                )

                if palette.locked:
                    source_text += (
                        " Palette locked."
                    )

            else:
                source_text = (
                    "No useful background colours are matched yet; "
                    "the normal theme accent is used as fallback."
                )

        else:
            count = (
                palette.manual_count
            )

            source_text = (
                "Manual Dashboard palette uses "
                + str(
                    count
                )
                + " colour"
                + (
                    ""
                    if count == 1
                    else "s"
                )
                + "."
            )

        if effect.enabled:
            effect_text = (
                " Chromatic "
                + effect.effect_style.title()
                + " is enabled."
            )

        else:
            effect_text = (
                " Chromatic effects are off."
            )

        self.status_label.setText(
            source_text
            + effect_text
        )

    def _change_source(
        self,
        index,
    ):
        source = (
            self.source_combo.itemData(
                index
            )
        )

        if source not in {
            PALETTE_SOURCE_THEME,
            PALETTE_SOURCE_BACKGROUND,
            PALETTE_SOURCE_MANUAL,
        }:
            return

        preferences = replace(
            self._palette_preferences,
            source=source,
        )

        if not self._save_palette(
            preferences,
            notify=False,
        ):
            return

        if (
            source
            == PALETTE_SOURCE_BACKGROUND
            and not preferences.locked
        ):
            atmosphere = (
                self._current_atmosphere()
            )

            if (
                self._has_background_image(
                    atmosphere
                )
            ):
                self._match_atmosphere(
                    atmosphere,
                    force=False,
                    notify=False,
                )

        self._notify_theme_refresh()
        self._sync_controls()

        self.message_changed.emit(
            (
                "Dashboard colour source changed to "
                + self.source_combo.currentText()
                + "."
            )
        )

    def _change_manual_count(
        self,
        index,
    ):
        count = (
            self.manual_count_combo.itemData(
                index
            )
        )

        try:
            count = int(
                count
            )

        except (
            TypeError,
            ValueError,
        ):
            return

        if not (
            1
            <= count
            <= MAX_PALETTE_COLOURS
        ):
            return

        self._save_palette(
            replace(
                self._palette_preferences,
                manual_count=count,
            ),
            message=(
                "Manual Dashboard palette now uses "
                + str(
                    count
                )
                + " colour"
                + (
                    ""
                    if count == 1
                    else "s"
                )
                + "."
            ),
        )

    def _choose_manual_colour(
        self,
        index=0,
    ):
        try:
            index = int(
                index
            )

        except (
            TypeError,
            ValueError,
        ):
            return False

        if not (
            0
            <= index
            < MAX_PALETTE_COLOURS
        ):
            return False

        if (
            self._palette_preferences.source
            != PALETTE_SOURCE_MANUAL
        ):
            return False

        values = list(
            self._palette_preferences.manual_palette
        )

        colour = QColorDialog.getColor(
            QColor(
                values[
                    index
                ]
            ),
            self,
            (
                "Choose Dashboard Colour "
                + str(
                    index
                    + 1
                )
            ),
        )

        if not colour.isValid():
            return False

        values[index] = colour.name(
            QColor.NameFormat.HexRgb
        ).lower()

        return self._save_palette(
            replace(
                self._palette_preferences,
                manual_palette=tuple(
                    values
                ),
            ),
            message=(
                "Dashboard Colour "
                + str(
                    index
                    + 1
                )
                + " changed to "
                + values[
                    index
                ].upper()
                + "."
            ),
        )

    def _change_colour_strength(
        self,
        value,
    ):
        value = max(
            0,
            min(
                100,
                int(
                    value
                ),
            ),
        )

        self.colour_strength_value.setText(
            str(
                value
            )
            + "%"
        )

        if (
            value
            == self._palette_preferences.strength
        ):
            return

        self._palette_preferences = replace(
            self._palette_preferences,
            strength=value,
        )

        self._colour_commit_timer.start()

    def _commit_colour_strength(
        self,
    ):
        if (
            self._colour_commit_timer.isActive()
        ):
            self._colour_commit_timer.stop()

        if (
            self._palette_preferences.strength
            == self._last_saved_colour_strength
        ):
            return False

        return self._save_palette(
            self._palette_preferences,
            notify=True,
        )

    def _change_lock(
        self,
        checked,
    ):
        self._save_palette(
            replace(
                self._palette_preferences,
                locked=bool(
                    checked
                ),
            ),
            message=(
                "Matched Dashboard palette locked."
                if checked
                else "Matched Dashboard palette unlocked."
            ),
        )

    def _match_atmosphere(
        self,
        atmosphere,
        *,
        force=False,
        notify=True,
    ):
        if (
            self._palette_preferences.locked
            and not force
        ):
            return False

        path = (
            self._background_image_path(
                atmosphere
            )
        )

        if (
            not path
            and not force
        ):
            return False

        colours = (
            extract_dashboard_palette_from_path(
                path
            )
        )

        updated = (
            update_matched_palette(
                self._palette_preferences,
                colours,
                force=force,
            )
        )

        if (
            updated
            == self._palette_preferences
        ):
            self._sync_controls()

            return False

        return self._save_palette(
            updated,
            notify=notify,
        )

    def _handle_atmosphere_changed(
        self,
        atmosphere,
    ):
        if (
            self._palette_preferences.source
            != PALETTE_SOURCE_BACKGROUND
        ):
            return

        if (
            self._palette_preferences.locked
        ):
            return

        if not self._has_background_image(
            atmosphere
        ):
            return

        if self._match_atmosphere(
            atmosphere,
            force=False,
            notify=True,
        ):
            self.message_changed.emit(
                "Dashboard palette matched the new Atmosphere background."
            )

    def recalculate_background(
        self,
    ):
        atmosphere = (
            self._current_atmosphere()
        )

        self._match_atmosphere(
            atmosphere,
            force=True,
            notify=True,
        )

        self._sync_controls()

        count = len(
            self._palette_preferences.matched_palette
        )

        if count:
            message = (
                "Background palette recalculated with "
                + str(
                    count
                )
                + " colour"
                + (
                    ""
                    if count == 1
                    else "s"
                )
                + "."
            )

        else:
            message = (
                "No useful Dashboard colours were found "
                "in the current background."
            )

        self.status_label.setText(
            message
        )

        self.message_changed.emit(
            message
        )

        return bool(
            count
        )

    def _change_enabled(
        self,
        checked,
    ):
        self._save_effect(
            replace(
                self._effect_preferences,
                enabled=bool(
                    checked
                ),
            ),
            message=(
                "Chromatic effects enabled."
                if checked
                else "Chromatic effects disabled."
            ),
        )

    def _change_effect_style(
        self,
        index,
    ):
        style = (
            self.effect_style_combo.itemData(
                index
            )
        )

        if style not in {
            CHROMATIC_EFFECT_SOLID,
            CHROMATIC_EFFECT_GRADIENT,
            CHROMATIC_EFFECT_NEON,
            CHROMATIC_EFFECT_PRISM,
        }:
            return

        self._save_effect(
            replace(
                self._effect_preferences,
                effect_style=style,
            ),
            message=(
                "Chromatic effect changed to "
                + str(
                    style
                ).title()
                + "."
            ),
        )

    def _change_strength(
        self,
        value,
    ):
        value = max(
            0,
            min(
                100,
                int(
                    value
                ),
            ),
        )

        self.strength_value.setText(
            str(
                value
            )
            + "%"
        )

        if (
            value
            == self._effect_preferences.strength
        ):
            return

        self._effect_preferences = replace(
            self._effect_preferences,
            strength=value,
        )

        self._sync_preview()

        self._effect_commit_timer.start()

    def _commit_strength(
        self,
    ):
        return (
            self._commit_effect_strength()
        )

    def _commit_effect_strength(
        self,
    ):
        if (
            self._effect_commit_timer.isActive()
        ):
            self._effect_commit_timer.stop()

        if (
            self._effect_preferences.strength
            == self._last_saved_effect_strength
        ):
            return False

        return self._save_effect(
            self._effect_preferences,
            notify=True,
        )

    def apply_theme(
        self,
        theme,
    ):
        if not isinstance(
            theme,
            dict,
        ):
            return

        self._theme = dict(
            theme
        )

        card_alt = str(
            theme.get(
                "card_alt",
                "#3e2e54",
            )
        )

        border = str(
            theme.get(
                "border",
                "#5c4777",
            )
        )

        text = str(
            theme.get(
                "text",
                "#fff5fb",
            )
        )

        muted = str(
            theme.get(
                "muted",
                "#bca9ce",
            )
        )

        accent = str(
            theme.get(
                "accent",
                "#ff79b9",
            )
        )

        self._border_colour = (
            border
        )

        self.setStyleSheet(
            f"""
            QFrame#dashboardChromaticPanel {{
                background: {card_alt};
                border: 1px solid {border};
                border-radius: 12px;
            }}

            QLabel#dashboardChromaticTitle {{
                color: {text};
                font-size: 11px;
                font-weight: 800;
            }}

            QLabel#dashboardChromaticHelp,
            QLabel#dashboardChromaticStatus,
            QLabel#dashboardPaletteStrengthValue,
            QLabel#dashboardChromaticStrengthValue {{
                color: {muted};
            }}

            QLabel#fieldLabel {{
                color: {text};
            }}

            QComboBox#dashboardPaletteSource,
            QComboBox#dashboardPaletteCount,
            QComboBox#dashboardChromaticEffectStyle {{
                color: {text};
                background: transparent;
                border: 1px solid {border};
                border-radius: 7px;
                padding: 6px 9px;
            }}

            QComboBox#dashboardPaletteSource:hover,
            QComboBox#dashboardPaletteCount:hover,
            QComboBox#dashboardChromaticEffectStyle:hover {{
                border-color: {accent};
            }}

            QPushButton#dashboardPaletteChoose,
            QPushButton#dashboardPaletteRecalculate {{
                color: {text};
                background: transparent;
                border: 1px solid {border};
                border-radius: 7px;
                padding: 6px 10px;
            }}

            QPushButton#dashboardPaletteChoose:hover,
            QPushButton#dashboardPaletteRecalculate:hover {{
                border-color: {accent};
            }}

            QFrame#dashboardPaletteSeparator {{
                color: {border};
                background: {border};
                max-height: 1px;
                border: none;
            }}

            QSlider#dashboardPaletteStrength::groove:horizontal,
            QSlider#dashboardChromaticStrength::groove:horizontal {{
                height: 5px;
                background: {border};
                border-radius: 2px;
            }}

            QSlider#dashboardPaletteStrength::handle:horizontal,
            QSlider#dashboardChromaticStrength::handle:horizontal {{
                width: 16px;
                margin: -6px 0;
                background: {accent};
                border: 1px solid {accent};
                border-radius: 8px;
            }}

            QSlider#dashboardPaletteStrength::sub-page:horizontal,
            QSlider#dashboardChromaticStrength::sub-page:horizontal {{
                background: {accent};
                border-radius: 2px;
            }}
            """
        )

        self._update_swatches()
        self._sync_preview()
