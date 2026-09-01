from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from src.companion.preferences import (
    CompanionPreferences,
    default_companion_preferences,
)


SUPPORTED_ASSET_FILTER = (
    "Companion images "
    "(*.png *.jpg *.jpeg *.webp *.gif)"
)


class CompanionSettingsCard(QFrame):
    """
    User-facing Desktop Companion controls.

    The card never owns persistence or overlay lifecycle.
    All changes route through CompanionRuntime.
    """

    def __init__(
        self,
        parent=None,
    ) -> None:
        super().__init__(
            parent
        )

        self.setObjectName(
            "settingsCard"
        )

        self._runtime = None
        self._syncing = False

        self._build_ui()
        self._set_runtime_controls_enabled(
            False
        )

    @property
    def runtime(self):
        return self._runtime

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
            18,
        )
        layout.setSpacing(
            10
        )

        title = QLabel(
            "Desktop Companion"
        )
        title.setObjectName(
            "cardTitle"
        )

        description = QLabel(
            "Display a local image or animated GIF "
            "as a lightweight transparent desktop companion."
        )
        description.setObjectName(
            "cardDescription"
        )
        description.setWordWrap(
            True
        )

        layout.addWidget(
            title
        )
        layout.addWidget(
            description
        )

        self.enabled_box = QCheckBox(
            "Enable Desktop Companion"
        )
        self.enabled_box.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        layout.addWidget(
            self.enabled_box
        )

        asset_label = QLabel(
            "Companion asset"
        )
        asset_label.setObjectName(
            "fieldLabel"
        )

        self.asset_path_label = QLabel(
            "No asset selected"
        )
        self.asset_path_label.setObjectName(
            "helpText"
        )
        self.asset_path_label.setWordWrap(
            True
        )
        self.asset_path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        asset_buttons = QHBoxLayout()
        asset_buttons.setSpacing(
            8
        )

        self.choose_asset_button = QPushButton(
            "Choose image or GIF"
        )
        self.choose_asset_button.setObjectName(
            "secondaryButton"
        )
        self.choose_asset_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.clear_asset_button = QPushButton(
            "Remove asset"
        )
        self.clear_asset_button.setObjectName(
            "secondaryButton"
        )
        self.clear_asset_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        asset_buttons.addWidget(
            self.choose_asset_button
        )
        asset_buttons.addWidget(
            self.clear_asset_button
        )
        asset_buttons.addStretch()

        layout.addWidget(
            asset_label
        )
        layout.addWidget(
            self.asset_path_label
        )
        layout.addLayout(
            asset_buttons
        )

        grid = QGridLayout()
        grid.setHorizontalSpacing(
            14
        )
        grid.setVerticalSpacing(
            9
        )

        scale_label = QLabel(
            "Scale"
        )
        scale_label.setObjectName(
            "fieldLabel"
        )

        self.scale_spin = QSpinBox()
        self.scale_spin.setRange(
            25,
            400,
        )
        self.scale_spin.setSuffix(
            " %"
        )
        self.scale_spin.setMinimumWidth(
            105
        )

        opacity_label = QLabel(
            "Opacity"
        )
        opacity_label.setObjectName(
            "fieldLabel"
        )

        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(
            10,
            100,
        )
        self.opacity_spin.setSuffix(
            " %"
        )
        self.opacity_spin.setMinimumWidth(
            105
        )

        speed_label = QLabel(
            "GIF speed"
        )
        speed_label.setObjectName(
            "fieldLabel"
        )

        self.animation_speed_spin = QSpinBox()
        self.animation_speed_spin.setRange(
            25,
            400,
        )
        self.animation_speed_spin.setSuffix(
            " %"
        )
        self.animation_speed_spin.setMinimumWidth(
            105
        )

        grid.addWidget(
            scale_label,
            0,
            0,
        )
        grid.addWidget(
            self.scale_spin,
            0,
            1,
        )

        grid.addWidget(
            opacity_label,
            1,
            0,
        )
        grid.addWidget(
            self.opacity_spin,
            1,
            1,
        )

        grid.addWidget(
            speed_label,
            2,
            0,
        )
        grid.addWidget(
            self.animation_speed_spin,
            2,
            1,
        )

        grid.setColumnStretch(
            2,
            1,
        )

        layout.addLayout(
            grid
        )

        self.always_on_top_box = QCheckBox(
            "Always on top"
        )
        self.click_through_box = QCheckBox(
            "Click-through"
        )
        self.remember_position_box = QCheckBox(
            "Remember position and monitor"
        )
        self.hide_in_fullscreen_box = QCheckBox(
            "Hide during fullscreen apps"
        )

        for checkbox in (
            self.always_on_top_box,
            self.click_through_box,
            self.remember_position_box,
            self.hide_in_fullscreen_box,
        ):
            checkbox.setCursor(
                Qt.CursorShape.PointingHandCursor
            )
            layout.addWidget(
                checkbox
            )

        interaction_help = QLabel(
            "Turn click-through off when you want to "
            "drag the Companion to a new position."
        )
        interaction_help.setObjectName(
            "helpText"
        )
        interaction_help.setWordWrap(
            True
        )

        layout.addWidget(
            interaction_help
        )

        position_row = QHBoxLayout()
        position_row.setSpacing(
            8
        )

        self.position_label = QLabel(
            "No saved position"
        )
        self.position_label.setObjectName(
            "helpText"
        )

        self.reset_position_button = QPushButton(
            "Reset saved position"
        )
        self.reset_position_button.setObjectName(
            "secondaryButton"
        )
        self.reset_position_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        position_row.addWidget(
            self.position_label,
            stretch=1,
        )
        position_row.addWidget(
            self.reset_position_button
        )

        layout.addLayout(
            position_row
        )

        footer_row = QHBoxLayout()
        footer_row.setSpacing(
            8
        )

        self.reset_defaults_button = QPushButton(
            "Reset Companion defaults"
        )
        self.reset_defaults_button.setObjectName(
            "secondaryButton"
        )
        self.reset_defaults_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        footer_row.addWidget(
            self.reset_defaults_button
        )
        footer_row.addStretch()

        layout.addLayout(
            footer_row
        )

        self.status_label = QLabel(
            "Desktop Companion runtime is not connected yet."
        )
        self.status_label.setObjectName(
            "helpText"
        )
        self.status_label.setWordWrap(
            True
        )

        layout.addWidget(
            self.status_label
        )

        self.enabled_box.toggled.connect(
            self._enabled_changed
        )

        self.scale_spin.valueChanged.connect(
            self._scale_changed
        )

        self.opacity_spin.valueChanged.connect(
            self._opacity_changed
        )

        self.animation_speed_spin.valueChanged.connect(
            self._animation_speed_changed
        )

        self.always_on_top_box.toggled.connect(
            self._always_on_top_changed
        )

        self.click_through_box.toggled.connect(
            self._click_through_changed
        )

        self.remember_position_box.toggled.connect(
            self._remember_position_changed
        )

        self.hide_in_fullscreen_box.toggled.connect(
            self._hide_in_fullscreen_changed
        )

        self.choose_asset_button.clicked.connect(
            self.choose_asset
        )

        self.clear_asset_button.clicked.connect(
            self.clear_asset
        )

        self.reset_position_button.clicked.connect(
            self.reset_saved_position
        )

        self.reset_defaults_button.clicked.connect(
            self.reset_defaults
        )

    def set_runtime(
        self,
        runtime,
    ) -> None:
        previous = self._runtime

        if previous is runtime:
            self.refresh_from_runtime()
            return

        if previous is not None:
            signal = getattr(
                previous,
                "preferences_changed",
                None,
            )

            if (
                signal is not None
                and hasattr(
                    signal,
                    "disconnect",
                )
            ):
                try:
                    signal.disconnect(
                        self._runtime_preferences_changed
                    )
                except (
                    TypeError,
                    RuntimeError,
                    ValueError,
                ):
                    pass

        self._runtime = runtime

        if runtime is None:
            self._set_runtime_controls_enabled(
                False
            )

            self.status_label.setText(
                "Desktop Companion runtime is unavailable."
            )

            return

        if not hasattr(
            runtime,
            "update_preferences",
        ):
            raise TypeError(
                "runtime must provide update_preferences()."
            )

        signal = getattr(
            runtime,
            "preferences_changed",
            None,
        )

        if (
            signal is not None
            and hasattr(
                signal,
                "connect",
            )
        ):
            signal.connect(
                self._runtime_preferences_changed
            )

        self._set_runtime_controls_enabled(
            True
        )

        self.refresh_from_runtime()

    def _set_runtime_controls_enabled(
        self,
        enabled: bool,
    ) -> None:
        for widget in (
            self.enabled_box,
            self.choose_asset_button,
            self.clear_asset_button,
            self.scale_spin,
            self.opacity_spin,
            self.animation_speed_spin,
            self.always_on_top_box,
            self.click_through_box,
            self.remember_position_box,
            self.hide_in_fullscreen_box,
            self.reset_position_button,
            self.reset_defaults_button,
        ):
            widget.setEnabled(
                enabled
            )

    def refresh_from_runtime(
        self,
    ) -> None:
        runtime = self._runtime

        if runtime is None:
            return

        preferences = getattr(
            runtime,
            "preferences",
            None,
        )

        if not isinstance(
            preferences,
            CompanionPreferences,
        ):
            return

        self._syncing = True

        try:
            self.enabled_box.setChecked(
                preferences.enabled
            )

            self.scale_spin.setValue(
                preferences.scale_percent
            )

            self.opacity_spin.setValue(
                int(
                    round(
                        preferences.opacity
                        * 100
                    )
                )
            )

            self.animation_speed_spin.setValue(
                preferences.animation_speed_percent
            )

            self.always_on_top_box.setChecked(
                preferences.always_on_top
            )

            self.click_through_box.setChecked(
                preferences.click_through
            )

            self.remember_position_box.setChecked(
                preferences.remember_position
            )

            self.hide_in_fullscreen_box.setChecked(
                preferences.hide_in_fullscreen
            )

            if preferences.asset_path:
                self.asset_path_label.setText(
                    preferences.asset_path
                )
            else:
                self.asset_path_label.setText(
                    "No asset selected"
                )

            if (
                preferences.position_x is not None
                and preferences.position_y is not None
            ):
                monitor = (
                    f" on {preferences.screen_name}"
                    if preferences.screen_name
                    else ""
                )

                self.position_label.setText(
                    "Saved at "
                    f"{preferences.position_x}, "
                    f"{preferences.position_y}"
                    f"{monitor}"
                )
            else:
                self.position_label.setText(
                    "No saved position"
                )

        finally:
            self._syncing = False

        error_text = str(
            getattr(
                runtime,
                "last_error",
                "",
            )
            or ""
        ).strip()

        if error_text:
            self.status_label.setText(
                "Companion could not use the selected asset: "
                + error_text
            )
        else:
            self.status_label.setText(
                "Changes apply immediately."
            )

    def _runtime_preferences_changed(
        self,
        _preferences,
    ) -> None:
        self.refresh_from_runtime()

    def _update(
        self,
        **changes,
    ):
        if self._syncing:
            return None

        runtime = self._runtime

        if runtime is None:
            return None

        try:
            updated = runtime.update_preferences(
                **changes
            )
        except Exception as error:
            self.status_label.setText(
                "Companion setting could not be saved: "
                + str(
                    error
                )
            )
            return None

        self.refresh_from_runtime()

        return updated

    def _enabled_changed(
        self,
        checked: bool,
    ) -> None:
        self._update(
            enabled=bool(
                checked
            )
        )

    def _scale_changed(
        self,
        value: int,
    ) -> None:
        self._update(
            scale_percent=int(
                value
            )
        )

    def _opacity_changed(
        self,
        value: int,
    ) -> None:
        self._update(
            opacity=(
                int(
                    value
                )
                / 100.0
            )
        )

    def _animation_speed_changed(
        self,
        value: int,
    ) -> None:
        self._update(
            animation_speed_percent=int(
                value
            )
        )

    def _always_on_top_changed(
        self,
        checked: bool,
    ) -> None:
        self._update(
            always_on_top=bool(
                checked
            )
        )

    def _click_through_changed(
        self,
        checked: bool,
    ) -> None:
        self._update(
            click_through=bool(
                checked
            )
        )

    def _remember_position_changed(
        self,
        checked: bool,
    ) -> None:
        self._update(
            remember_position=bool(
                checked
            )
        )

    def _hide_in_fullscreen_changed(
        self,
        checked: bool,
    ) -> None:
        self._update(
            hide_in_fullscreen=bool(
                checked
            )
        )

    def choose_asset(
        self,
    ) -> None:
        runtime = self._runtime

        if runtime is None:
            return

        current_path = str(
            getattr(
                runtime.preferences,
                "asset_path",
                "",
            )
            or ""
        )

        start_directory = ""

        if current_path:
            current = Path(
                current_path
            )

            if current.parent.exists():
                start_directory = str(
                    current.parent
                )

        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Desktop Companion image or GIF",
            start_directory,
            SUPPORTED_ASSET_FILTER,
        )

        if not selected_path:
            return

        self._update(
            asset_path=selected_path
        )

    def clear_asset(
        self,
    ) -> None:
        self._update(
            enabled=False,
            asset_path="",
        )

    def reset_saved_position(
        self,
    ) -> None:
        self._update(
            position_x=None,
            position_y=None,
            screen_name="",
        )

    def reset_defaults(
        self,
    ) -> None:
        defaults = (
            default_companion_preferences()
        )

        self._update(
            **asdict(
                defaults
            )
        )
