from pathlib import Path

from PyQt6.QtCore import (
    Qt,
    QSettings,
    pyqtSignal,
)
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.system.startup import StartupManager
from src.ui.theme import (
    DEFAULT_THEME,
    THEME_PRESETS,
    ThemeManager,
)


class SettingsPage(QWidget):
    show_portrait_changed = pyqtSignal(bool)
    always_on_top_changed = pyqtSignal(bool)

    def __init__(
        self,
        theme_manager=None,
    ):
        super().__init__()

        self.store = QSettings(
            "0337am",
            "Presence",
        )

        self.theme_manager = (
            theme_manager
            or ThemeManager(self)
        )

        self.color_buttons = {}

        self.build_ui()

        self.theme_manager.theme_changed.connect(
            self.on_theme_changed
        )
        self.theme_manager.branding_changed.connect(
            self.refresh_branding_fields
        )

        self.on_theme_changed(
            self.theme_manager.theme()
        )

    @property
    def show_yuno_portrait(self) -> bool:
        return self.store.value(
            "show_yuno_portrait",
            True,
            type=bool,
        )

    @property
    def always_on_top(self) -> bool:
        return self.store.value(
            "always_on_top",
            False,
            type=bool,
        )

    @property
    def start_minimized(self) -> bool:
        return self.store.value(
            "start_minimized",
            True,
            type=bool,
        )

    def build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        content = QWidget()
        content.setObjectName(
            "settingsContent"
        )

        root = QVBoxLayout(content)
        root.setContentsMargins(
            26,
            24,
            26,
            24,
        )
        root.setSpacing(16)

        title = QLabel("Settings")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Personalise the app and control how it starts"
        )
        subtitle.setObjectName(
            "pageSubtitle"
        )

        root.addWidget(title)
        root.addWidget(subtitle)

        branding = self.create_card(
            "Branding",
            "Edit the sidebar text and portrait.",
        )

        branding_layout = branding.layout()

        current_branding = (
            self.theme_manager.branding()
        )

        self.title_input = self.create_text_field(
            "Main title",
            current_branding["title"],
        )

        self.subtitle_input = (
            self.create_text_field(
                "Subtitle",
                current_branding["subtitle"],
            )
        )

        self.footer_input = self.create_text_field(
            "Footer text",
            current_branding["footer"],
        )

        self.title_input.editingFinished.connect(
            self.save_branding_text
        )
        self.subtitle_input.editingFinished.connect(
            self.save_branding_text
        )
        self.footer_input.editingFinished.connect(
            self.save_branding_text
        )

        branding_layout.addWidget(
            self.title_input
        )
        branding_layout.addWidget(
            self.subtitle_input
        )
        branding_layout.addWidget(
            self.footer_input
        )

        visibility_row = QHBoxLayout()
        visibility_row.setSpacing(10)

        self.show_title_box = self.create_checkbox(
            "Show title",
            current_branding["show_title"],
        )
        self.show_subtitle_box = (
            self.create_checkbox(
                "Show subtitle",
                current_branding[
                    "show_subtitle"
                ],
            )
        )
        self.show_footer_box = self.create_checkbox(
            "Show footer",
            current_branding["show_footer"],
        )

        self.show_title_box.toggled.connect(
            lambda checked:
            self.change_branding_visibility(
                "show_title",
                checked,
            )
        )

        self.show_subtitle_box.toggled.connect(
            lambda checked:
            self.change_branding_visibility(
                "show_subtitle",
                checked,
            )
        )

        self.show_footer_box.toggled.connect(
            lambda checked:
            self.change_branding_visibility(
                "show_footer",
                checked,
            )
        )

        visibility_row.addWidget(
            self.show_title_box
        )
        visibility_row.addWidget(
            self.show_subtitle_box
        )
        visibility_row.addWidget(
            self.show_footer_box
        )

        branding_layout.addLayout(
            visibility_row
        )

        image_row = QHBoxLayout()
        image_row.setSpacing(10)

        choose_image = QPushButton(
            "Choose sidebar image"
        )
        choose_image.setObjectName(
            "secondaryButton"
        )
        choose_image.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        choose_image.clicked.connect(
            self.choose_branding_image
        )

        reset_image = QPushButton(
            "Use default image"
        )
        reset_image.setObjectName(
            "secondaryButton"
        )
        reset_image.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        reset_image.clicked.connect(
            self.reset_branding_image
        )

        image_row.addWidget(choose_image)
        image_row.addWidget(reset_image)
        image_row.addStretch()

        self.image_path_label = QLabel()

        selected_image = current_branding.get(
            "image_path",
            "",
        )

        if selected_image:
            self.image_path_label.setText(
                Path(selected_image).name
            )
        else:
            self.image_path_label.setText(
                "Using the default Yuno image"
            )

        self.image_path_label.setObjectName(
            "helpText"
        )

        branding_layout.addLayout(image_row)
        branding_layout.addWidget(
            self.image_path_label
        )

        theme_card = self.create_card(
            "Theme",
            "Choose a preset or create your own colour style.",
        )

        theme_layout = theme_card.layout()
        current_theme = self.theme_manager.theme()

        preset_row = QHBoxLayout()
        preset_row.setSpacing(12)

        preset_label = QLabel("Theme preset")
        preset_label.setObjectName("fieldLabel")

        self.preset_combo = QComboBox()
        self.preset_combo.setObjectName(
            "presetCombo"
        )

        self.preset_combo.addItems(
            list(THEME_PRESETS.keys())
            + ["Custom"]
        )

        current_preset = current_theme.get(
            "preset",
            "Yuno",
        )

        preset_index = (
            self.preset_combo.findText(
                current_preset
            )
        )

        if preset_index >= 0:
            self.preset_combo.setCurrentIndex(
                preset_index
            )

        self.preset_combo.currentTextChanged.connect(
            self.change_theme_preset
        )

        preset_row.addWidget(preset_label)
        preset_row.addStretch()
        preset_row.addWidget(self.preset_combo)

        theme_layout.addLayout(preset_row)

        self.compact_box = self.create_checkbox(
            "Use compact layout",
            current_theme.get(
                "compact",
                True,
            ),
        )

        self.compact_box.toggled.connect(
            self.change_compact_mode
        )

        theme_layout.addWidget(
            self.compact_box
        )

        colour_title = QLabel(
            "Custom colours"
        )
        colour_title.setObjectName(
            "fieldLabel"
        )

        theme_layout.addWidget(colour_title)

        colour_grid = QGridLayout()
        colour_grid.setHorizontalSpacing(12)
        colour_grid.setVerticalSpacing(10)

        colour_options = [
            ("background", "Background"),
            ("sidebar", "Sidebar"),
            ("card", "Main cards"),
            ("card_alt", "Status cards"),
            ("accent", "Accent"),
            ("text", "Main text"),
            ("muted", "Muted text"),
            ("border", "Borders"),
        ]

        for index, (
            colour_key,
            colour_name,
        ) in enumerate(colour_options):
            label = QLabel(colour_name)
            label.setObjectName("colourLabel")

            button = QPushButton()
            button.setObjectName(
                "colourButton"
            )
            button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )
            button.setMinimumWidth(110)

            button.clicked.connect(
                lambda checked=False, key=colour_key:
                self.choose_colour(key)
            )

            self.color_buttons[
                colour_key
            ] = button

            row = index // 2
            column = (index % 2) * 2

            colour_grid.addWidget(
                label,
                row,
                column,
            )
            colour_grid.addWidget(
                button,
                row,
                column + 1,
            )

        theme_layout.addLayout(colour_grid)

        appearance = self.create_card(
            "Window",
            "Choose how the desktop window behaves.",
        )

        appearance_layout = appearance.layout()

        self.portrait_box = self.create_checkbox(
            "Show sidebar portrait",
            self.show_yuno_portrait,
        )

        self.top_box = self.create_checkbox(
            "Keep window on top",
            self.always_on_top,
        )

        self.portrait_box.toggled.connect(
            self.change_portrait
        )

        self.top_box.toggled.connect(
            self.change_always_on_top
        )

        appearance_layout.addWidget(
            self.portrait_box
        )

        appearance_layout.addWidget(
            self.top_box
        )

        startup = self.create_card(
            "Windows startup",
            "Control how the app starts with Windows.",
        )

        startup_layout = startup.layout()

        self.windows_box = self.create_checkbox(
            "Start with Windows",
            StartupManager.is_enabled(),
        )

        self.hidden_box = self.create_checkbox(
            "Start hidden in the tray",
            self.start_minimized,
        )

        self.windows_box.toggled.connect(
            self.change_windows_startup
        )

        self.hidden_box.toggled.connect(
            self.change_start_minimized
        )

        startup_layout.addWidget(
            self.windows_box
        )

        startup_layout.addWidget(
            self.hidden_box
        )

        self.status = QLabel("")
        self.status.setObjectName("status")

        button_row = QHBoxLayout()
        button_row.setSpacing(10)

        reset_theme = QPushButton(
            "Reset theme"
        )
        reset_theme.setObjectName(
            "secondaryButton"
        )
        reset_theme.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        reset_theme.clicked.connect(
            self.reset_theme
        )

        reset_all = QPushButton(
            "Reset all settings"
        )
        reset_all.setObjectName(
            "dangerButton"
        )
        reset_all.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        reset_all.clicked.connect(
            self.reset_settings
        )

        button_row.addWidget(reset_theme)
        button_row.addWidget(reset_all)
        button_row.addStretch()

        root.addWidget(branding)
        root.addWidget(theme_card)
        root.addWidget(appearance)
        root.addWidget(startup)
        root.addWidget(self.status)
        root.addLayout(button_row)
        root.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

    def create_card(
        self,
        title: str,
        description: str,
    ) -> QFrame:
        card = QFrame()
        card.setObjectName("settingsCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(
            18,
            16,
            18,
            18,
        )
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")

        description_label = QLabel(description)
        description_label.setObjectName(
            "cardDescription"
        )
        description_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(description_label)

        return card

    @staticmethod
    def create_text_field(
        placeholder: str,
        value: str,
    ) -> QLineEdit:
        field = QLineEdit()
        field.setObjectName("textField")
        field.setPlaceholderText(placeholder)
        field.setText(value)
        field.setClearButtonEnabled(True)
        field.setMaxLength(80)

        return field

    @staticmethod
    def create_checkbox(
        text: str,
        checked: bool,
    ) -> QCheckBox:
        checkbox = QCheckBox(text)
        checkbox.setChecked(checked)
        checkbox.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        return checkbox

    def save_branding_text(self):
        values = {
            "title": self.title_input.text().strip(),
            "subtitle": self.subtitle_input.text().strip(),
            "footer": self.footer_input.text().strip(),
        }

        for key, value in values.items():
            self.theme_manager.store.setValue(
                f"branding/{key}",
                value,
            )

        self.theme_manager.store.sync()

        self.theme_manager.branding_changed.emit(
            self.theme_manager.branding()
        )

        self.status.setText(
            "Branding text saved."
        )
    def change_branding_visibility(
        self,
        key: str,
        checked: bool,
    ):
        self.theme_manager.set_branding_value(
            key,
            checked,
        )

    def choose_branding_image(self):
        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose sidebar image",
            "",
            (
                "Images (*.png *.jpg *.jpeg *.webp);;"
                "All files (*)"
            ),
        )

        if not selected_path:
            return

        saved_path = (
            self.theme_manager.save_branding_image(
                selected_path
            )
        )

        if not saved_path:
            self.status.setText(
                "The selected image could not be saved."
            )
            return

        self.image_path_label.setText(
            Path(saved_path).name
        )

        self.status.setText(
            "Sidebar image updated."
        )

    def reset_branding_image(self):
        self.theme_manager.reset_branding_image()

        self.image_path_label.setText(
            "Using the default Yuno image"
        )

        self.status.setText(
            "Default sidebar image restored."
        )

    def refresh_branding_fields(
        self,
        branding: dict,
    ):
        fields = [
            (
                self.title_input,
                branding.get("title", ""),
            ),
            (
                self.subtitle_input,
                branding.get("subtitle", ""),
            ),
            (
                self.footer_input,
                branding.get("footer", ""),
            ),
        ]

        for field, value in fields:
            field.blockSignals(True)
            field.setText(value)
            field.blockSignals(False)

        checkboxes = [
            (
                self.show_title_box,
                branding.get(
                    "show_title",
                    True,
                ),
            ),
            (
                self.show_subtitle_box,
                branding.get(
                    "show_subtitle",
                    True,
                ),
            ),
            (
                self.show_footer_box,
                branding.get(
                    "show_footer",
                    True,
                ),
            ),
        ]

        for checkbox, checked in checkboxes:
            checkbox.blockSignals(True)
            checkbox.setChecked(checked)
            checkbox.blockSignals(False)

        image_path = branding.get(
            "image_path",
            "",
        )

        if image_path:
            self.image_path_label.setText(
                Path(image_path).name
            )
        else:
            self.image_path_label.setText(
                "Using the default Yuno image"
            )

    def change_theme_preset(
        self,
        preset_name: str,
    ):
        if preset_name == "Custom":
            return

        self.theme_manager.apply_preset(
            preset_name
        )

        self.status.setText(
            f"{preset_name} theme applied."
        )

    def choose_colour(
        self,
        colour_key: str,
    ):
        current_theme = (
            self.theme_manager.theme()
        )

        current_colour = QColor(
            current_theme.get(
                colour_key,
                DEFAULT_THEME[colour_key],
            )
        )

        selected_colour = QColorDialog.getColor(
            current_colour,
            self,
            "Choose colour",
        )

        if not selected_colour.isValid():
            return

        self.theme_manager.set_theme_value(
            colour_key,
            selected_colour.name(),
        )

        self.status.setText(
            "Custom colour saved."
        )

    def change_compact_mode(
        self,
        checked: bool,
    ):
        self.theme_manager.set_theme_value(
            "compact",
            checked,
        )

        self.status.setText(
            "Layout preference saved."
        )

    def on_theme_changed(
        self,
        theme: dict,
    ):
        preset = theme.get(
            "preset",
            "Custom",
        )

        self.preset_combo.blockSignals(True)

        preset_index = (
            self.preset_combo.findText(preset)
        )

        if preset_index < 0:
            preset_index = (
                self.preset_combo.findText(
                    "Custom"
                )
            )

        self.preset_combo.setCurrentIndex(
            preset_index
        )

        self.preset_combo.blockSignals(False)

        self.compact_box.blockSignals(True)
        self.compact_box.setChecked(
            theme.get("compact", True)
        )
        self.compact_box.blockSignals(False)

        for key, button in (
            self.color_buttons.items()
        ):
            colour = theme.get(
                key,
                DEFAULT_THEME[key],
            )

            button.setText(colour.upper())

            button.setStyleSheet(
                f"""
                QPushButton {{
                    background: {colour};
                    color: {self.contrast_text(colour)};
                    border: 1px solid {theme["border"]};
                    border-radius: 8px;
                    padding: 7px 10px;
                    font-weight: bold;
                }}
                """
            )

        self.apply_page_style(theme)

    @staticmethod
    def contrast_text(
        colour: str,
    ) -> str:
        selected = QColor(colour)

        brightness = (
            selected.red() * 299
            + selected.green() * 587
            + selected.blue() * 114
        ) / 1000

        if brightness > 145:
            return "#111111"

        return "#ffffff"

    def apply_page_style(
        self,
        theme: dict,
    ):
        compact = theme.get(
            "compact",
            True,
        )

        field_padding = (
            8 if compact else 11
        )

        checkbox_padding = (
            9 if compact else 12
        )

        self.setStyleSheet(
            f"""
            QScrollArea#settingsScroll,
            QWidget#settingsContent {{
                background: {theme["background"]};
                border: none;
            }}

            QLabel#pageTitle {{
                color: {theme["text"]};
                font-size: 25px;
                font-weight: bold;
            }}

            QLabel#pageSubtitle,
            QLabel#cardDescription,
            QLabel#helpText {{
                color: {theme["muted"]};
                font-size: 12px;
            }}

            QFrame#settingsCard {{
                background: {theme["card"]};
                border: 1px solid {theme["border"]};
                border-radius: 14px;
            }}

            QLabel#cardTitle {{
                color: {theme["text"]};
                font-size: 16px;
                font-weight: bold;
            }}

            QLabel#fieldLabel,
            QLabel#colourLabel {{
                color: {theme["text"]};
                font-size: 13px;
                font-weight: 600;
            }}

            QLabel#status {{
                color: {theme["accent"]};
                font-size: 12px;
            }}

            QLineEdit#textField,
            QComboBox#presetCombo {{
                color: {theme["text"]};
                background: {theme["card_alt"]};
                border: 1px solid {theme["border"]};
                border-radius: 9px;
                padding: {field_padding}px;
                selection-background-color: {theme["accent"]};
            }}

            QLineEdit#textField:focus,
            QComboBox#presetCombo:focus {{
                border: 1px solid {theme["accent"]};
            }}

            QComboBox#presetCombo QAbstractItemView {{
                color: {theme["text"]};
                background: {theme["card_alt"]};
                border: 1px solid {theme["border"]};
                selection-background-color: {theme["accent"]};
            }}

            QCheckBox {{
                color: {theme["text"]};
                background: {theme["card_alt"]};
                border: 1px solid {theme["border"]};
                border-radius: 9px;
                padding: {checkbox_padding}px;
                spacing: 9px;
            }}

            QCheckBox:hover {{
                border: 1px solid {theme["accent"]};
            }}

            QCheckBox::indicator {{
                width: 17px;
                height: 17px;
                background: {theme["background"]};
                border: 2px solid {theme["border"]};
                border-radius: 5px;
            }}

            QCheckBox::indicator:checked {{
                background: {theme["accent"]};
                border: 2px solid {theme["accent"]};
            }}

            QPushButton#secondaryButton {{
                color: {theme["text"]};
                background: {theme["card_alt"]};
                border: 1px solid {theme["border"]};
                border-radius: 9px;
                padding: 8px 13px;
                font-weight: 600;
            }}

            QPushButton#secondaryButton:hover {{
                border: 1px solid {theme["accent"]};
            }}

            QPushButton#dangerButton {{
                color: {theme["text"]};
                background: {theme["sidebar"]};
                border: 1px solid {theme["accent"]};
                border-radius: 9px;
                padding: 8px 13px;
                font-weight: bold;
            }}

            QPushButton#dangerButton:hover {{
                background: {theme["card_alt"]};
            }}
            """
        )

    def change_portrait(
        self,
        checked: bool,
    ):
        self.store.setValue(
            "show_yuno_portrait",
            checked,
        )

        self.show_portrait_changed.emit(
            checked
        )

    def change_always_on_top(
        self,
        checked: bool,
    ):
        self.store.setValue(
            "always_on_top",
            checked,
        )

        self.always_on_top_changed.emit(
            checked
        )

    def change_windows_startup(
        self,
        checked: bool,
    ):
        success = StartupManager.set_enabled(
            checked,
            self.hidden_box.isChecked(),
        )

        if success:
            message = (
                "Windows startup enabled."
                if checked
                else "Windows startup disabled."
            )

            self.status.setText(message)
            return

        self.status.setText(
            "Windows startup could not be changed."
        )

        self.windows_box.blockSignals(True)
        self.windows_box.setChecked(
            not checked
        )
        self.windows_box.blockSignals(False)

    def change_start_minimized(
        self,
        checked: bool,
    ):
        self.store.setValue(
            "start_minimized",
            checked,
        )

        if self.windows_box.isChecked():
            StartupManager.set_enabled(
                True,
                checked,
            )

        self.status.setText(
            "Startup preference saved."
        )

    def reset_theme(self):
        self.theme_manager.reset_theme()

        self.status.setText(
            "Theme reset to Yuno."
        )

    def reset_settings(self):
        self.theme_manager.reset_theme()
        self.theme_manager.reset_branding()

        self.portrait_box.setChecked(True)
        self.top_box.setChecked(False)
        self.hidden_box.setChecked(True)
        self.windows_box.setChecked(False)

        self.status.setText(
            "All settings reset."
        )

