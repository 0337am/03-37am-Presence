import csv
import os
import shutil
from pathlib import Path

from PyQt6.QtCore import (
    Qt,
    QSettings,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from src.library.history_store import HistoryStore
from src.system.startup import StartupManager
from src.system.settings_backup import (
    SettingsBackupError,
    SettingsBackupManager,
)
from src.ui.theme import (
    ATMOSPHERE_RANGES,
    DEFAULT_ATMOSPHERE,
    DEFAULT_THEME,
    THEME_PRESETS,
    ThemeManager,
)

from src.music.source_preferences import (
    SourcePreferencesStore,
)

from src.ui.artwork_hosting_card import (
    ArtworkHostingCard,
)

from src.system.afk_preferences import (
    AfkPreferencesStore,
)

def colour_with_alpha(
    colour: str,
    alpha: float,
) -> str:
    value = str(colour or "").strip()

    if value.startswith("#"):
        value = value[1:]

    if len(value) != 6:
        return colour

    try:
        red = int(value[0:2], 16)
        green = int(value[2:4], 16)
        blue = int(value[4:6], 16)
    except ValueError:
        return colour

    channel = max(
        0,
        min(
            255,
            int(255 * alpha),
        ),
    )

    return (
        f"rgba({red}, {green}, {blue}, {channel})"
    )


class SleekComboBox(QComboBox):
    def __init__(
        self,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self.arrow_label = QLabel(
            "\u25be",
            self,
        )
        self.arrow_label.setObjectName(
            "comboArrow"
        )
        self.arrow_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.arrow_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        self.arrow_label.setFixedWidth(
            28
        )

        self._position_arrow()

    def _position_arrow(self):
        arrow_width = (
            self.arrow_label.width()
        )

        self.arrow_label.setGeometry(
            max(
                0,
                self.width()
                - arrow_width,
            ),
            0,
            arrow_width,
            self.height(),
        )

        self.arrow_label.raise_()

    def resizeEvent(
        self,
        event,
    ):
        super().resizeEvent(
            event
        )

        self._position_arrow()

    def showEvent(
        self,
        event,
    ):
        super().showEvent(
            event
        )

        self._position_arrow()


from src.library.csv_export import (
    export_listening_activity_csv
    as write_listening_activity_csv,
    export_track_summary_csv
    as write_track_summary_csv,
)

class SettingsPage(QWidget):
    show_portrait_changed = pyqtSignal(bool)
    always_on_top_changed = pyqtSignal(bool)
    storage_changed = pyqtSignal()

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
        self.atmosphere_sliders = {}
        self.atmosphere_value_labels = {}
        self._pending_atmosphere_slider_key = ""
        self._atmosphere_preview_timer = QTimer(self)
        self._atmosphere_preview_timer.setSingleShot(True)
        self._atmosphere_preview_timer.setInterval(32)
        self._atmosphere_preview_timer.timeout.connect(
            self.commit_pending_atmosphere_slider
        )

        self.source_preferences_store = (
            SourcePreferencesStore()
        )

        self.afk_preferences_store = (
            AfkPreferencesStore()
        )

        self.history_store = (
            HistoryStore()
        )

        self.settings_backup_manager = (
            SettingsBackupManager(
                settings=self.store,
                source_store=(
                    self.source_preferences_store
                ),
                afk_store=(
                    self.afk_preferences_store
                ),
            )
        )

        self.diagnostics_provider = None
        self._last_diagnostics_text = ""

        self.build_ui()

        self.theme_manager.theme_changed.connect(
            self.on_theme_changed
        )
        self.theme_manager.branding_changed.connect(
            self.refresh_branding_fields
        )
        self.theme_manager.atmosphere_changed.connect(
            self.refresh_atmosphere_fields
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
        self.settings_scroll = scroll
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
            "Edit the sidebar title, subtitle, and portrait.",
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

        self.title_input.editingFinished.connect(
            self.save_branding_text
        )
        self.subtitle_input.editingFinished.connect(
            self.save_branding_text
        )

        branding_layout.addWidget(
            self.title_input
        )
        branding_layout.addWidget(
            self.subtitle_input
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
            "Show About footer",
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
                "About uses the app icon by default"
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

        self.preset_combo = SleekComboBox()
        self.preset_combo.setObjectName(
            "presetCombo"
        )

        self.preset_combo.addItems(
            list(THEME_PRESETS.keys())
            + ["Custom"]
        )

        current_preset = current_theme.get(
            "preset",
            "Midnight",
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

        atmosphere_card = self.create_card(
            "Atmosphere",
            (
                "Choose a local background image "
                "and tune how strongly it appears."
            ),
        )

        atmosphere_layout = atmosphere_card.layout()
        current_atmosphere = (
            self.theme_manager.atmosphere()
        )

        self.atmosphere_enabled_box = (
            self.create_checkbox(
                "Enable custom background",
                current_atmosphere.get(
                    "enabled",
                    DEFAULT_ATMOSPHERE["enabled"],
                ),
            )
        )
        self.atmosphere_enabled_box.toggled.connect(
            self.change_atmosphere_enabled
        )

        atmosphere_help = QLabel(
            (
                "Background images stay local on this "
                "device and are not exported in settings backups."
            )
        )
        atmosphere_help.setObjectName(
            "helpText"
        )
        atmosphere_help.setWordWrap(True)

        atmosphere_button_row = QHBoxLayout()
        atmosphere_button_row.setSpacing(10)

        self.choose_background_button = QPushButton(
            "Choose background"
        )
        self.choose_background_button.setObjectName(
            "secondaryButton"
        )
        self.choose_background_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.choose_background_button.clicked.connect(
            self.choose_atmosphere_background
        )

        self.reset_background_button = QPushButton(
            "Reset background"
        )
        self.reset_background_button.setObjectName(
            "secondaryButton"
        )
        self.reset_background_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.reset_background_button.clicked.connect(
            self.reset_atmosphere_background
        )

        atmosphere_button_row.addWidget(
            self.choose_background_button
        )
        atmosphere_button_row.addWidget(
            self.reset_background_button
        )
        atmosphere_button_row.addStretch()

        self.atmosphere_image_label = QLabel()
        self.atmosphere_image_label.setObjectName(
            "helpText"
        )
        self.atmosphere_image_label.setWordWrap(True)

        atmosphere_layout.addWidget(
            self.atmosphere_enabled_box
        )
        atmosphere_layout.addWidget(
            atmosphere_help
        )
        atmosphere_layout.addLayout(
            atmosphere_button_row
        )
        atmosphere_layout.addWidget(
            self.atmosphere_image_label
        )

        atmosphere_controls = (
            (
                "blur",
                "Blur",
                "px",
            ),
            (
                "opacity",
                "Image opacity",
                "%",
            ),
            (
                "dim",
                "Dim overlay",
                "%",
            ),
        )

        for key, label_text, suffix in atmosphere_controls:
            row = QHBoxLayout()
            row.setSpacing(12)

            label = QLabel(label_text)
            label.setObjectName("fieldLabel")
            label.setMinimumWidth(110)

            slider = QSlider(
                Qt.Orientation.Horizontal
            )
            slider.setObjectName(
                "atmosphereSlider"
            )
            slider.setCursor(
                Qt.CursorShape.PointingHandCursor
            )
            slider.setMinimumHeight(34)
            slider.setTracking(True)

            minimum, maximum = ATMOSPHERE_RANGES[key]
            slider.setRange(
                minimum,
                maximum,
            )
            slider.setValue(
                current_atmosphere.get(
                    key,
                    DEFAULT_ATMOSPHERE[key],
                )
            )

            value_label = QLabel()
            value_label.setObjectName(
                "helpText"
            )
            value_label.setMinimumWidth(54)
            value_label.setAlignment(
                Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignVCenter
            )

            self.atmosphere_sliders[key] = slider
            self.atmosphere_value_labels[key] = (
                value_label,
                suffix,
            )

            slider.sliderMoved.connect(
                lambda value, slider_key=key:
                self.preview_atmosphere_slider(
                    slider_key,
                    value,
                )
            )
            slider.valueChanged.connect(
                lambda value, slider_key=key:
                self.update_atmosphere_slider_label(
                    slider_key,
                    value,
                )
            )
            slider.sliderReleased.connect(
                lambda slider_key=key, slider_widget=slider:
                self.commit_atmosphere_slider(
                    slider_key,
                    slider_widget,
                )
            )

            row.addWidget(label)
            row.addWidget(
                slider,
                stretch=1,
            )
            row.addWidget(value_label)

            atmosphere_layout.addLayout(row)

        self.refresh_atmosphere_fields(
            current_atmosphere
        )

        source_preferences = (
            self.source_preferences_store.load()
        )

        sources = self.create_card(
            "Media sources",
            (
                "Choose which apps are allowed to "
                "update your Discord presence."
            ),
        )

        sources_layout = sources.layout()

        self.spotify_source_box = (
            self.create_checkbox(
                "Enable Spotify",
                source_preferences.spotify_enabled,
            )
        )

        self.browser_source_box = (
            self.create_checkbox(
                (
                    "Enable browser media "
                    "(Chrome, Edge, Firefox, "
                    "Brave, Opera, and Vivaldi)"
                ),
                source_preferences.browser_enabled,
            )
        )

        browser_help = QLabel(
            (
                "Browser media includes SoundCloud "
                "and other websites that expose "
                "Windows media controls."
            )
        )
        browser_help.setObjectName(
            "helpText"
        )
        browser_help.setWordWrap(
            True
        )

        self.spotify_source_box.toggled.connect(
            self.change_source_preferences
        )

        self.browser_source_box.toggled.connect(
            self.change_source_preferences
        )

        sources_layout.addWidget(
            self.spotify_source_box
        )

        sources_layout.addWidget(
            self.browser_source_box
        )

        sources_layout.addWidget(
            browser_help
        )

        self.artwork_hosting_card = (
            ArtworkHostingCard()
        )

        self.artwork_hosting_card.message_changed.connect(
            self.set_status_message
        )

        afk_preferences = (
            self.afk_preferences_store.load()
        )

        auto_afk = self.create_card(
            "Auto AFK",
            (
                "Automatically switch to AFK mode "
                "when no keyboard or mouse activity "
                "is detected."
            ),
        )

        auto_afk_layout = auto_afk.layout()

        self.auto_afk_box = (
            self.create_checkbox(
                "Enable Auto AFK",
                afk_preferences.enabled,
            )
        )

        timeout_row = QHBoxLayout()
        timeout_row.setSpacing(12)

        timeout_label = QLabel(
            "Switch to AFK after"
        )
        timeout_label.setObjectName(
            "fieldLabel"
        )

        self.afk_timeout_combo = SleekComboBox()
        self.afk_timeout_combo.setObjectName(
            "presetCombo"
        )

        timeout_options = [
            1,
            5,
            10,
            15,
            30,
            60,
        ]

        if (
            afk_preferences.timeout_minutes
            not in timeout_options
        ):
            timeout_options.append(
                afk_preferences.timeout_minutes
            )
            timeout_options.sort()

        for minutes in timeout_options:
            label = (
                "1 minute"
                if minutes == 1
                else f"{minutes} minutes"
            )

            self.afk_timeout_combo.addItem(
                label,
                minutes,
            )

        timeout_index = (
            self.afk_timeout_combo.findData(
                afk_preferences.timeout_minutes
            )
        )

        if timeout_index >= 0:
            self.afk_timeout_combo.setCurrentIndex(
                timeout_index
            )

        self.afk_timeout_combo.setEnabled(
            afk_preferences.enabled
        )

        afk_help = QLabel(
            (
                "When activity returns, the app "
                "restores the presence mode that "
                "was active before AFK."
            )
        )
        afk_help.setObjectName(
            "helpText"
        )
        afk_help.setWordWrap(
            True
        )

        self.auto_afk_box.toggled.connect(
            self.afk_timeout_combo.setEnabled
        )

        self.auto_afk_box.toggled.connect(
            self.change_afk_preferences
        )

        self.afk_timeout_combo.currentIndexChanged.connect(
            self.change_afk_preferences
        )

        timeout_row.addWidget(
            timeout_label
        )
        timeout_row.addStretch()
        timeout_row.addWidget(
            self.afk_timeout_combo
        )

        auto_afk_layout.addWidget(
            self.auto_afk_box
        )
        auto_afk_layout.addLayout(
            timeout_row
        )
        auto_afk_layout.addWidget(
            afk_help
        )

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

        storage = self.create_card(
            "Data & Storage",
            (
                "Review, export, or clear the "
                "persistent data saved by the app."
            ),
        )

        storage_layout = storage.layout()

        storage_grid = QGridLayout()
        storage_grid.setHorizontalSpacing(18)
        storage_grid.setVerticalSpacing(9)

        library_label = QLabel(
            "Library"
        )
        library_label.setObjectName(
            "fieldLabel"
        )

        self.storage_library_value = QLabel(
            "0 tracks • 0 plays"
        )
        self.storage_library_value.setObjectName(
            "helpText"
        )

        database_label = QLabel(
            "Library database"
        )
        database_label.setObjectName(
            "fieldLabel"
        )

        self.storage_database_value = QLabel(
            "0 B"
        )
        self.storage_database_value.setObjectName(
            "helpText"
        )

        artwork_label = QLabel(
            "Artwork cache"
        )
        artwork_label.setObjectName(
            "fieldLabel"
        )

        self.storage_artwork_value = QLabel(
            "0 B"
        )
        self.storage_artwork_value.setObjectName(
            "helpText"
        )

        location_label = QLabel(
            "Saved-data location"
        )
        location_label.setObjectName(
            "fieldLabel"
        )

        self.storage_location_value = QLabel("")
        self.storage_location_value.setObjectName(
            "helpText"
        )
        self.storage_location_value.setWordWrap(
            True
        )

        storage_grid.addWidget(
            library_label,
            0,
            0,
        )
        storage_grid.addWidget(
            self.storage_library_value,
            0,
            1,
        )

        storage_grid.addWidget(
            database_label,
            1,
            0,
        )
        storage_grid.addWidget(
            self.storage_database_value,
            1,
            1,
        )

        storage_grid.addWidget(
            artwork_label,
            2,
            0,
        )
        storage_grid.addWidget(
            self.storage_artwork_value,
            2,
            1,
        )

        storage_grid.addWidget(
            location_label,
            3,
            0,
        )
        storage_grid.addWidget(
            self.storage_location_value,
            3,
            1,
        )

        storage_grid.setColumnStretch(
            1,
            1,
        )

        storage_layout.addLayout(
            storage_grid
        )

        storage_safe_row = QHBoxLayout()
        storage_safe_row.setSpacing(8)

        open_data_button = QPushButton(
            "Open data folder"
        )
        open_data_button.setObjectName(
            "secondaryButton"
        )
        open_data_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        open_data_button.clicked.connect(
            self.open_data_folder
        )

        export_library_button = QPushButton(
            "Export Library CSV"
        )
        export_library_button.setObjectName(
            "secondaryButton"
        )
        export_library_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        export_library_button.clicked.connect(
            self.export_library_csv
        )

        export_activity_button = QPushButton(
            "Export Activity CSV"
        )
        export_activity_button.setObjectName(
            "secondaryButton"
        )
        export_activity_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        export_activity_button.setAccessibleName(
            "Export confirmed listening activity CSV"
        )
        export_activity_button.setToolTip(
            "Export confirmed Playing events "
            "recorded since timeline tracking began."
        )
        export_activity_button.clicked.connect(
            self.export_listening_activity_csv
        )

        storage_safe_row.addWidget(
            open_data_button
        )
        storage_safe_row.addWidget(
            export_library_button
        )
        storage_safe_row.addWidget(
            export_activity_button
        )
        storage_safe_row.addStretch()

        storage_danger_row = QHBoxLayout()
        storage_danger_row.setSpacing(8)

        clear_artwork_button = QPushButton(
            "Clear artwork cache"
        )
        clear_artwork_button.setObjectName(
            "dangerButton"
        )
        clear_artwork_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        clear_artwork_button.clicked.connect(
            self.clear_artwork_cache
        )

        clear_history_button = QPushButton(
            "Clear listening history"
        )
        clear_history_button.setObjectName(
            "dangerButton"
        )
        clear_history_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        clear_history_button.clicked.connect(
            self.clear_listening_history
        )

        storage_danger_row.addWidget(
            clear_artwork_button
        )
        storage_danger_row.addWidget(
            clear_history_button
        )
        storage_danger_row.addStretch()

        storage_layout.addLayout(
            storage_safe_row
        )
        storage_layout.addLayout(
            storage_danger_row
        )

        settings_backup = self.create_card(
            "Settings Backup & Restore",
            (
                "Export a portable copy of your app "
                "settings or restore one later."
            ),
        )

        settings_backup_layout = (
            settings_backup.layout()
        )

        backup_privacy_help = QLabel(
            (
                "Custom Link cards and Atmosphere slider "
                "values are included. Listening history, "
                "artwork cache, Link-card icon cache, "
                "OAuth tokens, API credentials, "
                "diagnostics, local file paths, custom "
                "sidebar images, and custom Atmosphere "
                "backgrounds are never included."
            )
        )
        backup_privacy_help.setObjectName(
            "helpText"
        )
        backup_privacy_help.setWordWrap(
            True
        )

        self.include_artwork_hosting_box = (
            self.create_checkbox(
                (
                    "Include artwork-hosting "
                    "account details"
                ),
                False,
            )
        )
        self.include_artwork_hosting_box.setToolTip(
            (
                "Adds your Cloudinary cloud name "
                "and unsigned upload preset. "
                "API keys and secrets are never "
                "supported."
            )
        )

        artwork_backup_help = QLabel(
            (
                "Leave this off for a privacy-safe "
                "backup. Turn it on only when you "
                "want to move your personal hosting "
                "configuration to another device."
            )
        )
        artwork_backup_help.setObjectName(
            "helpText"
        )
        artwork_backup_help.setWordWrap(
            True
        )

        atmosphere_backup_help = QLabel(
            (
                "Atmosphere restores blur, opacity, "
                "and dim values only. Choose the "
                "background image again on each device."
            )
        )
        atmosphere_backup_help.setObjectName(
            "helpText"
        )
        atmosphere_backup_help.setWordWrap(
            True
        )

        backup_button_row = QHBoxLayout()
        backup_button_row.setSpacing(
            8
        )

        export_settings_button = QPushButton(
            "Export settings"
        )
        export_settings_button.setObjectName(
            "secondaryButton"
        )
        export_settings_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        export_settings_button.clicked.connect(
            self.export_settings_backup
        )

        restore_settings_button = QPushButton(
            "Restore settings"
        )
        restore_settings_button.setObjectName(
            "secondaryButton"
        )
        restore_settings_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        restore_settings_button.clicked.connect(
            self.restore_settings_backup
        )

        backup_button_row.addWidget(
            export_settings_button
        )
        backup_button_row.addWidget(
            restore_settings_button
        )
        backup_button_row.addStretch()

        settings_backup_layout.addWidget(
            backup_privacy_help
        )
        settings_backup_layout.addWidget(
            self.include_artwork_hosting_box
        )
        settings_backup_layout.addWidget(
            artwork_backup_help
        )
        settings_backup_layout.addWidget(
            atmosphere_backup_help
        )
        settings_backup_layout.addLayout(
            backup_button_row
        )

        diagnostics = self.create_card(
            "Diagnostics & Support",
            (
                "View the app's live status and copy "
                "a troubleshooting report."
            ),
        )

        diagnostics_layout = diagnostics.layout()

        diagnostics_grid = QGridLayout()
        diagnostics_grid.setHorizontalSpacing(18)
        diagnostics_grid.setVerticalSpacing(8)

        self.diagnostic_values = {}

        diagnostic_rows = (
            ("app_version", "App version"),
            ("discord", "Discord"),
            ("presence_mode", "Presence mode"),
            ("media", "Current media"),
            ("media_source", "Media source"),
            ("enabled_sources", "Enabled sources"),
            ("auto_afk", "Auto AFK"),
            ("library", "Library"),
            ("media_error", "Latest media error"),
        )

        for row_index, (
            diagnostic_key,
            diagnostic_name,
        ) in enumerate(
            diagnostic_rows
        ):
            name_label = QLabel(
                diagnostic_name
            )
            name_label.setObjectName(
                "fieldLabel"
            )

            value_label = QLabel(
                "Waiting for app status..."
            )
            value_label.setObjectName(
                "helpText"
            )
            value_label.setWordWrap(
                True
            )
            value_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )

            diagnostics_grid.addWidget(
                name_label,
                row_index,
                0,
            )

            diagnostics_grid.addWidget(
                value_label,
                row_index,
                1,
            )

            self.diagnostic_values[
                diagnostic_key
            ] = value_label

        diagnostics_grid.setColumnStretch(
            1,
            1,
        )

        diagnostics_layout.addLayout(
            diagnostics_grid
        )

        diagnostics_buttons = QHBoxLayout()
        diagnostics_buttons.setSpacing(8)

        refresh_diagnostics_button = QPushButton(
            "Refresh diagnostics"
        )
        refresh_diagnostics_button.setObjectName(
            "secondaryButton"
        )
        refresh_diagnostics_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        refresh_diagnostics_button.clicked.connect(
            self.refresh_diagnostics
        )

        copy_diagnostics_button = QPushButton(
            "Copy diagnostics"
        )
        copy_diagnostics_button.setObjectName(
            "secondaryButton"
        )
        copy_diagnostics_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        copy_diagnostics_button.clicked.connect(
            self.copy_diagnostics
        )

        diagnostics_buttons.addWidget(
            refresh_diagnostics_button
        )
        diagnostics_buttons.addWidget(
            copy_diagnostics_button
        )
        diagnostics_buttons.addStretch()

        diagnostics_layout.addLayout(
            diagnostics_buttons
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
        root.addWidget(atmosphere_card)
        root.addWidget(sources)
        root.addWidget(
            self.artwork_hosting_card
        )
        root.addWidget(auto_afk)
        root.addWidget(appearance)
        root.addWidget(startup)
        root.addWidget(storage)
        root.addWidget(
            settings_backup
        )
        root.addWidget(diagnostics)
        root.addWidget(self.status)
        root.addLayout(button_row)
        root.addStretch()

        self.settings_sections = {
            "theme": theme_card,
            "atmosphere": atmosphere_card,
            "media_sources": sources,
            "artwork_hosting": (
                self.artwork_hosting_card
            ),
            "auto_afk": auto_afk,
            "data_storage": storage,
            "settings_backup": (
                settings_backup
            ),
            "diagnostics": diagnostics,
        }

        scroll.setWidget(content)
        outer.addWidget(scroll)

        self.refresh_storage_summary()
        self.refresh_diagnostics()

    def set_status_message(
        self,
        message: str,
    ):
        self.status.setText(
            str(message)
        )

    def set_diagnostics_provider(
        self,
        provider,
    ):
        self.diagnostics_provider = provider
        self.refresh_diagnostics()

    def refresh_diagnostics(self):
        values = {
            "app_version": "Waiting for app status...",
            "discord": "Waiting for app status...",
            "presence_mode": "Waiting for app status...",
            "media": "Waiting for app status...",
            "media_source": "Waiting for app status...",
            "enabled_sources": "Waiting for app status...",
            "auto_afk": "Waiting for app status...",
            "library": "Waiting for app status...",
            "media_error": "None",
        }

        provider = getattr(
            self,
            "diagnostics_provider",
            None,
        )

        if callable(provider):
            try:
                provided_values = provider()

                if isinstance(
                    provided_values,
                    dict,
                ):
                    for key, value in (
                        provided_values.items()
                    ):
                        if key in values:
                            values[key] = str(
                                value
                            )

            except Exception as error:
                values[
                    "media_error"
                ] = (
                    "Diagnostics refresh failed: "
                    f"{error}"
                )

        label_order = (
            ("app_version", "App version"),
            ("discord", "Discord"),
            ("presence_mode", "Presence mode"),
            ("media", "Current media"),
            ("media_source", "Media source"),
            ("enabled_sources", "Enabled sources"),
            ("auto_afk", "Auto AFK"),
            ("library", "Library"),
            ("media_error", "Latest media error"),
        )

        report_lines = [
            "03:37am Presence Diagnostics",
            "----------------------------",
        ]

        for key, display_name in label_order:
            value = str(
                values.get(
                    key,
                    "Unavailable",
                )
            )

            label = self.diagnostic_values.get(
                key
            )

            if label is not None:
                label.setText(
                    value
                )

            report_lines.append(
                f"{display_name}: {value}"
            )

        self._last_diagnostics_text = (
            "\n".join(
                report_lines
            )
        )

    def copy_diagnostics(self):
        self.refresh_diagnostics()

        clipboard = (
            QApplication.clipboard()
        )

        if clipboard is None:
            self.status.setText(
                "The clipboard is unavailable."
            )
            return

        clipboard.setText(
            self._last_diagnostics_text
        )

        self.status.setText(
            "Diagnostics copied to the clipboard."
        )

    def data_directory(self) -> Path:
        directory = (
            self.history_store
            .database_path
            .parent
        )

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        return directory

    def artwork_cache_directory(self) -> Path:
        return (
            self.data_directory()
            / "artwork_cache"
        )

    @staticmethod
    def directory_size(
        directory: Path,
    ) -> int:
        if not directory.exists():
            return 0

        total = 0

        for item in directory.rglob("*"):
            if not item.is_file():
                continue

            try:
                total += item.stat().st_size
            except OSError:
                continue

        return total

    @staticmethod
    def format_bytes(
        byte_count: int,
    ) -> str:
        value = float(
            max(
                0,
                int(byte_count),
            )
        )

        units = (
            "B",
            "KB",
            "MB",
            "GB",
        )

        for unit in units:
            if (
                value < 1024
                or unit == units[-1]
            ):
                if unit == "B":
                    return (
                        f"{int(value)} {unit}"
                    )

                return (
                    f"{value:.1f} {unit}"
                )

            value /= 1024

        return "0 B"

    def database_size(self) -> int:
        database_path = (
            self.history_store
            .database_path
        )

        total = 0

        for suffix in (
            "",
            "-wal",
            "-shm",
        ):
            path = Path(
                str(database_path)
                + suffix
            )

            if not path.exists():
                continue

            try:
                total += path.stat().st_size
            except OSError:
                continue

        return total

    def refresh_storage_summary(self):
        try:
            total_tracks = (
                self.history_store
                .count_tracks()
            )

            total_plays = (
                self.history_store
                .total_plays()
            )

        except Exception:
            total_tracks = 0
            total_plays = 0

        track_word = (
            "track"
            if total_tracks == 1
            else "tracks"
        )

        play_word = (
            "play"
            if total_plays == 1
            else "plays"
        )

        self.storage_library_value.setText(
            (
                f"{total_tracks} {track_word}"
                " • "
                f"{total_plays} {play_word}"
            )
        )

        self.storage_database_value.setText(
            self.format_bytes(
                self.database_size()
            )
        )

        self.storage_artwork_value.setText(
            self.format_bytes(
                self.directory_size(
                    self.artwork_cache_directory()
                )
            )
        )

        self.storage_location_value.setText(
            str(
                self.data_directory()
            )
        )

    def open_data_folder(self):
        directory = self.data_directory()

        try:
            os.startfile(
                str(directory)
            )

            self.status.setText(
                "Opened the saved-data folder."
            )

        except Exception as error:
            QMessageBox.warning(
                self,
                "Folder could not be opened",
                str(error),
            )

    def export_library_csv(self):
        suggested_path = (
            self.data_directory()
            / "03-37am-library.csv"
        )

        selected_path, _ = (
            QFileDialog.getSaveFileName(
                self,
                "Export Library Summary",
                str(suggested_path),
                "CSV files (*.csv)",
            )
        )

        if not selected_path:
            return

        try:
            tracks = (
                self.history_store.list_tracks(
                    limit=50000
                )
            )

            destination, row_count = (
                write_track_summary_csv(
                    selected_path,
                    tracks,
                )
            )

            self.status.setText(
                "Library summary exported: "
                f"{row_count} tracks to "
                f"{destination.name}."
            )

        except Exception as error:
            QMessageBox.warning(
                self,
                "Export failed",
                (
                    "The Library summary could not "
                    "be exported."
                    "\n\n"
                    f"{error}"
                ),
            )

    def export_listening_activity_csv(self):
        suggested_path = (
            self.data_directory()
            / "03-37am-listening-activity.csv"
        )

        selected_path, _ = (
            QFileDialog.getSaveFileName(
                self,
                "Export Listening Activity",
                str(suggested_path),
                "CSV files (*.csv)",
            )
        )

        if not selected_path:
            return

        try:
            events = (
                self.history_store.list_events(
                    limit=50000
                )
            )

            destination, row_count = (
                write_listening_activity_csv(
                    selected_path,
                    events,
                )
            )

            self.status.setText(
                "Listening activity exported: "
                f"{row_count} confirmed plays to "
                f"{destination.name}."
            )

        except Exception as error:
            QMessageBox.warning(
                self,
                "Export failed",
                (
                    "The listening activity could "
                    "not be exported."
                    "\n\n"
                    f"{error}"
                ),
            )

    @staticmethod
    def _backup_dialog_directory() -> Path:
        documents = (
            Path.home()
            / "Documents"
        )

        if documents.exists():
            return documents

        return Path.home()

    def export_settings_backup(self):
        include_artwork_hosting = (
            self.include_artwork_hosting_box
            .isChecked()
        )

        if include_artwork_hosting:
            response = QMessageBox.question(
                self,
                "Include personal hosting details?",
                (
                    "This backup will include your "
                    "Cloudinary cloud name and "
                    "unsigned upload preset."
                    "\n\n"
                    "The file will contain personal "
                    "account identifiers. API keys, "
                    "secrets, tokens, history, cached "
                    "artwork, and Link-card icons are "
                    "still excluded."
                    "\n\n"
                    "Continue?"
                ),
                (
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No
                ),
                QMessageBox.StandardButton.No,
            )

            if (
                response
                != QMessageBox.StandardButton.Yes
            ):
                return

        suggested_path = (
            self._backup_dialog_directory()
            / (
                self.settings_backup_manager
                .suggested_filename()
            )
        )

        selected_path, _ = (
            QFileDialog.getSaveFileName(
                self,
                "Export Settings Backup",
                str(
                    suggested_path
                ),
                "JSON files (*.json)",
            )
        )

        if not selected_path:
            return

        try:
            destination = (
                self.settings_backup_manager
                .export_backup(
                    selected_path,
                    include_artwork_hosting=(
                        include_artwork_hosting
                    ),
                )
            )

        except SettingsBackupError as error:
            QMessageBox.warning(
                self,
                "Settings backup failed",
                str(error),
            )
            return

        except OSError as error:
            QMessageBox.warning(
                self,
                "Settings backup failed",
                (
                    "The backup could not be saved."
                    "\n\n"
                    f"{error}"
                ),
            )
            return

        privacy_note = (
            " Personal artwork-hosting details "
            "were included."
            if include_artwork_hosting
            else (
                " Personal artwork-hosting details "
                "were excluded."
            )
        )

        self.status.setText(
            (
                "Settings backup saved as "
                f"{destination.name}."
                + privacy_note
            )
        )

    def restore_settings_backup(self):
        selected_path, _ = (
            QFileDialog.getOpenFileName(
                self,
                "Restore Settings Backup",
                str(
                    self._backup_dialog_directory()
                ),
                "JSON files (*.json);;All files (*)",
            )
        )

        if not selected_path:
            return

        try:
            preview = (
                self.settings_backup_manager
                .preview_backup(
                    selected_path
                )
            )

        except SettingsBackupError as error:
            QMessageBox.warning(
                self,
                "Invalid settings backup",
                str(error),
            )
            return

        personal_note = (
            (
                "\n\nThis backup contains personal "
                "artwork-hosting account details, "
                "which will replace the current "
                "hosting configuration."
            )
            if preview.includes_artwork_hosting
            else (
                "\n\nArtwork-hosting account "
                "details are not included, so your "
                "current hosting configuration will "
                "be kept."
            )
        )

        response = QMessageBox.question(
            self,
            "Restore settings?",
            (
                "This will replace your theme, "
                "branding text, media sources, "
                "Auto AFK settings, dashboard "
                "layout, custom Link cards, window "
                "preferences, and Windows startup "
                "preference."
                "\n\n"
                "Listening history, artwork cache, "
                "and Link-card icon cache will not "
                "be changed."
                + personal_note
                + (
                    "\n\nA private local safety "
                    "backup will be created first."
                    "\n\nContinue?"
                )
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if (
            response
            != QMessageBox.StandardButton.Yes
        ):
            return

        try:
            result = (
                self.settings_backup_manager
                .restore_backup(
                    selected_path
                )
            )

        except SettingsBackupError as error:
            QMessageBox.warning(
                self,
                "Settings restore failed",
                str(error),
            )
            return

        except OSError as error:
            QMessageBox.warning(
                self,
                "Settings restore failed",
                (
                    "The settings could not be "
                    "restored."
                    "\n\n"
                    f"{error}"
                ),
            )
            return

        self.refresh_after_settings_restore()

        hosting_note = (
            (
                "\n\nArtwork-hosting account "
                "details were restored."
            )
            if result.restored_artwork_hosting
            else (
                "\n\nYour existing artwork-hosting "
                "account details were preserved."
            )
        )

        QMessageBox.information(
            self,
            "Settings restored",
            (
                "Your settings were restored "
                "successfully."
                + hosting_note
                + (
                    "\n\nRestart 03:37am Presence "
                    "to apply the restored dashboard "
                    "layout and every background "
                    "service setting."
                    "\n\nA private safety backup "
                    "was saved in the app data "
                    "folder."
                )
            ),
        )

        self.status.setText(
            (
                "Settings restored. Restart the app "
                "to finish applying them."
            )
        )

    def refresh_after_settings_restore(self):
        self.theme_manager.theme_changed.emit(
            self.theme_manager.theme()
        )

        self.theme_manager.branding_changed.emit(
            self.theme_manager.branding()
        )

        source_preferences = (
            self.source_preferences_store.load()
        )

        self.spotify_source_box.blockSignals(
            True
        )
        self.browser_source_box.blockSignals(
            True
        )

        self.spotify_source_box.setChecked(
            source_preferences.spotify_enabled
        )
        self.browser_source_box.setChecked(
            source_preferences.browser_enabled
        )

        self.spotify_source_box.blockSignals(
            False
        )
        self.browser_source_box.blockSignals(
            False
        )

        afk_preferences = (
            self.afk_preferences_store.load()
        )

        self.auto_afk_box.blockSignals(
            True
        )
        self.afk_timeout_combo.blockSignals(
            True
        )

        self.auto_afk_box.setChecked(
            afk_preferences.enabled
        )

        timeout_index = (
            self.afk_timeout_combo.findData(
                afk_preferences.timeout_minutes
            )
        )

        if timeout_index < 0:
            minutes = (
                afk_preferences.timeout_minutes
            )

            timeout_label = (
                "1 minute"
                if minutes == 1
                else f"{minutes} minutes"
            )

            self.afk_timeout_combo.addItem(
                timeout_label,
                minutes,
            )

            timeout_index = (
                self.afk_timeout_combo.findData(
                    minutes
                )
            )

        self.afk_timeout_combo.setCurrentIndex(
            timeout_index
        )
        self.afk_timeout_combo.setEnabled(
            afk_preferences.enabled
        )

        self.auto_afk_box.blockSignals(
            False
        )
        self.afk_timeout_combo.blockSignals(
            False
        )

        self.portrait_box.blockSignals(
            True
        )
        self.top_box.blockSignals(
            True
        )
        self.hidden_box.blockSignals(
            True
        )
        self.windows_box.blockSignals(
            True
        )

        self.portrait_box.setChecked(
            self.show_yuno_portrait
        )
        self.top_box.setChecked(
            self.always_on_top
        )
        self.hidden_box.setChecked(
            self.start_minimized
        )
        self.windows_box.setChecked(
            StartupManager.is_enabled()
        )

        self.portrait_box.blockSignals(
            False
        )
        self.top_box.blockSignals(
            False
        )
        self.hidden_box.blockSignals(
            False
        )
        self.windows_box.blockSignals(
            False
        )

        self.show_portrait_changed.emit(
            self.show_yuno_portrait
        )
        self.always_on_top_changed.emit(
            self.always_on_top
        )

        self.refresh_storage_summary()
        self.refresh_diagnostics()

    def clear_artwork_cache(self):
        response = QMessageBox.question(
            self,
            "Clear artwork cache",
            (
                "Delete all saved album-art thumbnails?"
                "\n\n"
                "Artwork will be cached again as "
                "songs are played."
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if (
            response
            != QMessageBox.StandardButton.Yes
        ):
            return

        cache_directory = (
            self.artwork_cache_directory()
        )

        try:
            if cache_directory.exists():
                shutil.rmtree(
                    cache_directory
                )

            cache_directory.mkdir(
                parents=True,
                exist_ok=True,
            )

        except OSError as error:
            QMessageBox.warning(
                self,
                "Cache could not be cleared",
                str(error),
            )
            return

        self.refresh_storage_summary()
        self.storage_changed.emit()

        self.status.setText(
            "Artwork cache cleared."
        )

    def clear_listening_history(self):
        response = QMessageBox.question(
            self,
            "Clear listening history",
            (
                "Permanently delete every saved "
                "track and listening event?"
                "\n\n"
                "This cannot be undone."
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if (
            response
            != QMessageBox.StandardButton.Yes
        ):
            return

        try:
            self.history_store.clear_history()

        except Exception as error:
            QMessageBox.warning(
                self,
                "History could not be cleared",
                str(error),
            )
            return

        self.refresh_storage_summary()
        self.storage_changed.emit()

        self.status.setText(
            "Listening history cleared."
        )

    def show_section(
        self,
        section_name: str,
    ):
        requested = str(
            section_name or ""
        ).strip().lower()

        aliases = {
            "afk": "auto_afk",
            "auto afk": "auto_afk",
            "sources": "media_sources",
            "media": "media_sources",
            "media sources": "media_sources",
            "artwork": "artwork_hosting",
            "cloudinary": "artwork_hosting",
            "hosting": "artwork_hosting",
            "artwork hosting": "artwork_hosting",
            "colours": "theme",
            "colors": "theme",
            "data": "data_storage",
            "storage": "data_storage",
            "data storage": "data_storage",
            "data & storage": "data_storage",
            "backup": "settings_backup",
            "restore": "settings_backup",
            "settings backup": "settings_backup",
            "backup & restore": "settings_backup",
            "support": "diagnostics",
            "diagnostic": "diagnostics",
            "diagnostics & support": "diagnostics",
        }

        section_key = aliases.get(
            requested,
            requested,
        )

        sections = getattr(
            self,
            "settings_sections",
            {},
        )

        card = sections.get(
            section_key
        )

        scroll = getattr(
            self,
            "settings_scroll",
            None,
        )

        if card is None or scroll is None:
            return

        QTimer.singleShot(
            0,
            lambda target=card, area=scroll:
            area.ensureWidgetVisible(
                target,
                0,
                24,
            )
        )

        self._highlight_settings_card(
            card
        )

    def _highlight_settings_card(
        self,
        card,
    ):
        previous = getattr(
            self,
            "_focused_settings_card",
            None,
        )

        if (
            previous is not None
            and previous is not card
        ):
            self._clear_settings_highlight(
                previous
            )

        self._focused_settings_card = card

        card.setProperty(
            "deepLinkFocus",
            True,
        )

        self._refresh_widget_style(
            card
        )

        QTimer.singleShot(
            1600,
            lambda target=card:
            self._clear_settings_highlight(
                target
            )
        )

    def _clear_settings_highlight(
        self,
        card,
    ):
        if (
            getattr(
                self,
                "_focused_settings_card",
                None,
            )
            is not card
        ):
            return

        card.setProperty(
            "deepLinkFocus",
            False,
        )

        self._focused_settings_card = None

        self._refresh_widget_style(
            card
        )

    @staticmethod
    def _refresh_widget_style(
        widget,
    ):
        style = widget.style()

        style.unpolish(
            widget
        )
        style.polish(
            widget
        )

        widget.update()

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
            "About uses the app icon by default"
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
                "About uses the app icon by default"
            )

    def refresh_atmosphere_fields(
        self,
        atmosphere: dict,
    ):
        enabled = bool(
            atmosphere.get(
                "enabled",
                False,
            )
        )
        image_path = str(
            atmosphere.get(
                "image_path",
                "",
            )
            or ""
        )

        self.atmosphere_enabled_box.blockSignals(True)
        self.atmosphere_enabled_box.setChecked(
            enabled
        )
        self.atmosphere_enabled_box.blockSignals(False)

        if image_path:
            self.atmosphere_image_label.setText(
                f"Using: {Path(image_path).name}"
            )
        else:
            self.atmosphere_image_label.setText(
                "No custom background selected."
            )

        self.reset_background_button.setEnabled(
            bool(image_path)
        )

        for key, slider in self.atmosphere_sliders.items():
            value = int(
                atmosphere.get(
                    key,
                    DEFAULT_ATMOSPHERE[key],
                )
            )

            slider.blockSignals(True)
            slider.setValue(value)
            slider.setEnabled(enabled)
            slider.blockSignals(False)

            label, suffix = self.atmosphere_value_labels[
                key
            ]
            label.setText(
                f"{value}{suffix}"
            )
            label.setEnabled(enabled)

    def choose_atmosphere_background(self):
        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose background image",
            "",
            (
                "Images (*.png *.jpg *.jpeg *.webp);;"
                "All files (*)"
            ),
        )

        if not selected_path:
            return

        valid, message = (
            self.theme_manager.validate_background_image_source(
                selected_path
            )
        )

        if not valid:
            self.status.setText(message)
            return

        saved_path = (
            self.theme_manager.save_background_image(
                selected_path
            )
        )

        if not saved_path:
            self.status.setText(
                "The selected background could not be saved."
            )
            return

        self.status.setText(
            "Background saved. It will appear when Atmosphere rendering is enabled."
        )

    def reset_atmosphere_background(self):
        self.theme_manager.reset_background_image()

        self.status.setText(
            "Custom background removed."
        )

    def change_atmosphere_enabled(
        self,
        checked: bool,
    ):
        self.theme_manager.set_atmosphere_value(
            "enabled",
            checked,
        )

        if checked:
            self.status.setText(
                "Atmosphere background enabled."
            )
        else:
            self.status.setText(
                "Atmosphere background disabled."
            )

    def update_atmosphere_slider_label(
        self,
        key: str,
        value: int,
    ):
        if key not in self.atmosphere_value_labels:
            return

        label, suffix = self.atmosphere_value_labels[
            key
        ]
        label.setText(
            f"{int(value)}{suffix}"
        )

    def preview_atmosphere_slider(
        self,
        key: str,
        value: int,
    ):
        self.update_atmosphere_slider_label(
            key,
            value,
        )
        self._pending_atmosphere_slider_key = key

        if not self._atmosphere_preview_timer.isActive():
            self._atmosphere_preview_timer.start()

    def commit_pending_atmosphere_slider(self):
        key = self._pending_atmosphere_slider_key

        if not key:
            return

        slider = self.atmosphere_sliders.get(
            key
        )

        if slider is None:
            return

        self.change_atmosphere_slider(
            key,
            slider.value(),
            quiet=True,
        )

    def commit_atmosphere_slider(
        self,
        key: str,
        slider,
    ):
        value = int(
            slider.sliderPosition()
        )

        slider.blockSignals(True)
        slider.setValue(value)
        slider.blockSignals(False)

        self.update_atmosphere_slider_label(
            key,
            value,
        )

        self._pending_atmosphere_slider_key = ""
        self._atmosphere_preview_timer.stop()

        self.change_atmosphere_slider(
            key,
            value,
        )

    def change_atmosphere_slider(
        self,
        key: str,
        value: int,
        quiet: bool = False,
    ):
        self.theme_manager.set_atmosphere_value(
            key,
            value,
        )

        if not quiet:
            self.status.setText(
                "Atmosphere setting saved."
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

    def change_source_preferences(
        self,
        _checked: bool = False,
    ):
        preferences = (
            self.source_preferences_store.update(
                spotify_enabled=(
                    self.spotify_source_box.isChecked()
                ),
                browser_enabled=(
                    self.browser_source_box.isChecked()
                ),
            )
        )

        enabled_sources = []

        if preferences.spotify_enabled:
            enabled_sources.append(
                "Spotify"
            )

        if preferences.browser_enabled:
            enabled_sources.append(
                "browser media"
            )

        if enabled_sources:
            source_text = " and ".join(
                enabled_sources
            )

            self.status.setText(
                f"Media sources saved: {source_text}."
            )
        else:
            self.status.setText(
                "All media sources are disabled."
            )
 
    def change_afk_preferences(
        self,
        _value=None,
    ):
        timeout_minutes = (
            self.afk_timeout_combo.currentData()
        )

        if timeout_minutes is None:
            timeout_minutes = 10

        preferences = (
            self.afk_preferences_store.update(
                enabled=(
                    self.auto_afk_box.isChecked()
                ),
                timeout_minutes=int(
                    timeout_minutes
                ),
            )
        )

        if preferences.enabled:
            self.status.setText(
                (
                    "Auto AFK enabled after "
                    f"{preferences.timeout_minutes} "
                    "minute"
                    + (
                        ""
                        if preferences.timeout_minutes == 1
                        else "s"
                    )
                    + "."
                )
            )
        else:
            self.status.setText(
                "Auto AFK disabled."
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

        card_glass = colour_with_alpha(
            theme["card"],
            0.66,
        )
        card_alt_glass = colour_with_alpha(
            theme["card_alt"],
            0.72,
        )
        page_background = "transparent"

        self.setStyleSheet(
            f"""
            QScrollArea#settingsScroll,
            QWidget#settingsContent {{
                background: {page_background};
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
                background: {card_glass};
                border: 1px solid {theme["border"]};
                border-radius: 14px;
            }}

            QFrame#settingsCard[deepLinkFocus="true"] {{
                border: 2px solid {theme["accent"]};
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
                background: {card_alt_glass};
                border: 1px solid {theme["border"]};
                border-radius: 9px;
                padding: {field_padding}px;
                selection-background-color: {theme["accent"]};
            }}

            QLineEdit#textField:focus,
            QComboBox#presetCombo:focus {{
                border: 1px solid {theme["accent"]};
            }}

            QComboBox#presetCombo {{
                padding-right: 30px;
            }}

            QComboBox#presetCombo::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 28px;
                border: none;
                background: transparent;
            }}

            QComboBox#presetCombo::down-arrow {{
                image: none;
                width: 0px;
                height: 0px;
            }}

            QLabel#comboArrow {{
                color: {theme["text"]};
                background: transparent;
                border: none;
                font-size: 11px;
                font-weight: 700;
            }}

            QLabel#comboArrow:disabled {{
                color: {theme["muted"]};
            }}

            QComboBox#presetCombo QAbstractItemView {{
                color: {theme["text"]};
                background: {card_alt_glass};
                border: 1px solid {theme["border"]};
                selection-background-color: {theme["accent"]};
            }}

            QSlider#atmosphereSlider {{
                min-height: 34px;
            }}

            QSlider#atmosphereSlider::groove:horizontal {{
                height: 7px;
                background: {card_alt_glass};
                border: 1px solid {theme["border"]};
                border-radius: 4px;
            }}

            QSlider#atmosphereSlider::handle:horizontal {{
                width: 20px;
                height: 20px;
                margin: -7px 0;
                background: {theme["accent"]};
                border: 1px solid {theme["text"]};
                border-radius: 9px;
            }}

            QSlider#atmosphereSlider::handle:horizontal:hover {{
                border: 2px solid {theme["text"]};
            }}

            QSlider#atmosphereSlider:disabled {{
                opacity: 0.55;
            }}

            QCheckBox {{
                color: {theme["text"]};
                background: {card_alt_glass};
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
                background: {card_alt_glass};
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
                background: {card_alt_glass};
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
        self.theme_manager.reset_atmosphere()

        self.status.setText(
            "Theme and Atmosphere reset to default."
        )

    def reset_settings(self):
        self.theme_manager.reset_theme()
        self.theme_manager.reset_atmosphere()
        self.theme_manager.reset_branding()

        self.portrait_box.setChecked(True)
        self.top_box.setChecked(False)
        self.hidden_box.setChecked(True)
        self.windows_box.setChecked(False)

        self.artwork_hosting_card.reset_preferences()

        self.status.setText(
            "All settings reset."
        )

