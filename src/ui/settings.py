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
    QProgressBar,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from src.library.history_store import HistoryStore
from src.system.startup import StartupManager
from src.ui.update_controller import (
    UpdateCheckController,
    describe_update_result,
)
from src.ui.update_download_controller import (
    UpdateDownloadController,
    describe_download_progress,
    describe_download_result,
)
from src.ui.update_install_controller import (
    UpdateInstallController,
)
from src.version import APP_VERSION, RELEASE_NAME
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

from src.ui.companion_settings import (
    CompanionSettingsCard,
)

from src.ui.artwork_hosting_card import (
    ArtworkHostingCard,
)

from src.ui.discord_application_library_card import (
    DiscordApplicationLibrarySettingsCard,
)

from src.ui.discord_identity_card import (
    DiscordIdentitySettingsCard,
)

from src.ui.spotify_connection_card import (
    SpotifyConnectionCard,
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

from src.ui.media_hotkey_settings import (
    MediaHotkeySettingsCard,
)

from src.system.media_hotkey_preferences import (
    MediaHotkeyPreferencesStore,
)

from src.system.local_music_preferences import (
    LocalMusicPreferencesStore,
)
from src.media.qt_local_music_runtime import (
    LocalMusicQtScanRuntime,
)
from src.ui.local_music_settings import (
    LocalMusicSettingsCard,
)

class SettingsPage(QWidget):
    show_portrait_changed = pyqtSignal(bool)
    always_on_top_changed = pyqtSignal(bool)
    storage_changed = pyqtSignal()

    def __init__(
        self,
        theme_manager=None,
        *,
        spotify_runtime=None,
        discord_application_store=None,
        discord_identity_store=None,
        discord_identity_runtime=None,
    ):
        super().__init__()

        self.discord_application_store = (
            discord_application_store
        )

        self.discord_identity_store = (
            discord_identity_store
        )
        self.discord_identity_runtime = (
            discord_identity_runtime
        )

        self.store = QSettings(
            "0337am",
            "Presence",
        )

        self.theme_manager = (
            theme_manager
            or ThemeManager(self)
        )

        self.spotify_runtime = (
            spotify_runtime
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

        self.media_hotkey_preferences_store = (
            MediaHotkeyPreferencesStore()
        )
        self.local_music_preferences_store = (
            LocalMusicPreferencesStore()
        )

        self.local_music_runtime = (
            LocalMusicQtScanRuntime(
                parent=self
            )
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
                media_hotkey_store=(
                    self.media_hotkey_preferences_store
                ),
                discord_application_store=(
                    self.discord_application_store
                ),
            )
        )

        self.diagnostics_provider = None
        self._last_diagnostics_text = ""

        self.update_controller = (
            UpdateCheckController(self)
        )

        self.update_download_controller = (
            UpdateDownloadController(self)
        )

        self.update_install_controller = (
            UpdateInstallController()
        )

        self._latest_update_result = None
        self._verified_update_download = None

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

        shell = QHBoxLayout()
        shell.setContentsMargins(
            18,
            18,
            18,
            18,
        )
        shell.setSpacing(14)

        navigation = QFrame()
        navigation.setObjectName(
            "settingsCategoryRail"
        )
        navigation.setMinimumWidth(176)
        navigation.setMaximumWidth(196)

        navigation_layout = QVBoxLayout(
            navigation
        )
        navigation_layout.setContentsMargins(
            10,
            12,
            10,
            12,
        )
        navigation_layout.setSpacing(6)

        navigation_title = QLabel(
            "SETTINGS"
        )
        navigation_title.setObjectName(
            "settingsCategoryRailTitle"
        )

        navigation_help = QLabel(
            "Choose a category"
        )
        navigation_help.setObjectName(
            "settingsCategoryRailHelp"
        )

        navigation_layout.addWidget(
            navigation_title
        )
        navigation_layout.addWidget(
            navigation_help
        )
        navigation_layout.addSpacing(6)

        category_definitions = (
            (
                "general",
                "General",
                "appearance",
            ),
            (
                "discord",
                "Discord",
                "discord_identity",
            ),
            (
                "customization",
                "Customization",
                "branding",
            ),
            (
                "spotify",
                "Spotify",
                "spotify",
            ),
            (
                "local_music",
                "Local Music",
                "local_music",
            ),
            (
                "playback",
                "Playback",
                "media_hotkeys",
            ),
            (
                "library_data",
                "Library && Data",
                "data_storage",
            ),
            (
                "updates",
                "Updates",
                "updates",
            ),
            (
                "advanced",
                "Advanced",
                "diagnostics",
            ),
        )

        self.settings_category_buttons = {}

        for (
            category_key,
            label_text,
            section_target,
        ) in category_definitions:
            button = QPushButton(
                label_text
            )
            button.setObjectName(
                "settingsCategoryButton"
            )
            button.setCheckable(True)
            button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )
            button.setMinimumHeight(36)

            button.clicked.connect(
                lambda checked=False,
                target=section_target:
                self.show_section(
                    target
                )
            )

            navigation_layout.addWidget(
                button
            )

            self.settings_category_buttons[
                category_key
            ] = button

        navigation_layout.addStretch()

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

        self.settings_page_title = title
        self.settings_page_subtitle = subtitle

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

        self.discord_application_library_card = (
            DiscordApplicationLibrarySettingsCard(
                application_store=(
                    self.discord_application_store
                ),
            )
        )

        self.discord_application_library_card.message_changed.connect(
            lambda message:
            self.set_status_message(
                message,
                category="discord",
            )
        )

        self.discord_identity_card = (
            DiscordIdentitySettingsCard(
                preference_store=(
                    self.discord_identity_store
                ),
                runtime=(
                    self.discord_identity_runtime
                ),
            )
        )

        self.discord_identity_card.message_changed.connect(
            lambda message:
            self.set_status_message(
                message,
                category="discord",
            )
        )

        self.spotify_connection_card = (
            SpotifyConnectionCard(
                self.spotify_runtime
            )
        )

        self.spotify_connection_card.message_changed.connect(
            lambda message:
            self.set_status_message(
                message,
                category="spotify",
            )
        )

        self.artwork_hosting_card = (
            ArtworkHostingCard()
        )

        self.artwork_hosting_card.message_changed.connect(
            lambda message:
            self.set_status_message(
                message,
                category="discord",
            )
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
                "Custom Link cards, Atmosphere slider values, "
                "global media hotkeys, and Discord Application "
                "Library entries are included. "
                "Listening history, "
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

        self.media_hotkeys_card = (
            MediaHotkeySettingsCard(
                preference_store=(
                    self.media_hotkey_preferences_store
                ),
                status_callback=(
                    lambda message:
                    self.set_status_message(
                        message,
                        category="playback",
                    )
                ),
            )
        )
        self.local_music_card = (
            LocalMusicSettingsCard(
                self.local_music_preferences_store,
                self.local_music_runtime,
                theme_manager=(
                    self.theme_manager
                ),
            )
        )


        updates = self.create_card(
            "Updates",
            (
                "Check the official public release "
                "feed without interrupting playback."
            ),
        )

        updates_layout = updates.layout()

        update_version_row = QHBoxLayout()
        update_version_row.setSpacing(10)

        update_version_title = QLabel(
            "Installed version"
        )
        update_version_title.setObjectName(
            "fieldLabel"
        )

        self.update_current_version = QLabel(
            f"v{APP_VERSION} — {RELEASE_NAME}"
        )
        self.update_current_version.setObjectName(
            "valueLabel"
        )

        update_version_row.addWidget(
            update_version_title
        )
        update_version_row.addWidget(
            self.update_current_version
        )
        update_version_row.addStretch()

        updates_layout.addLayout(
            update_version_row
        )

        self.update_status_label = QLabel(
            "Updates have not been checked yet."
        )
        self.update_status_label.setObjectName(
            "helpText"
        )
        self.update_status_label.setWordWrap(
            True
        )

        self.update_details_label = QLabel(
            (
                "Checks run only when requested "
                "and contact the official public "
                "release repository."
            )
        )
        self.update_details_label.setObjectName(
            "helpText"
        )
        self.update_details_label.setWordWrap(
            True
        )

        updates_layout.addWidget(
            self.update_status_label
        )
        updates_layout.addWidget(
            self.update_details_label
        )

        update_button_row = QHBoxLayout()
        update_button_row.setSpacing(8)

        self.check_updates_button = QPushButton(
            "Check for updates"
        )
        self.check_updates_button.setObjectName(
            "secondaryButton"
        )
        self.check_updates_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.check_updates_button.clicked.connect(
            self.check_for_updates
        )

        self.download_update_button = QPushButton(
            "Download update"
        )
        self.download_update_button.setObjectName(
            "secondaryButton"
        )
        self.download_update_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.download_update_button.setVisible(
            False
        )
        self.download_update_button.clicked.connect(
            self.download_available_update
        )

        self.install_update_button = QPushButton(
            "Install update"
        )
        self.install_update_button.setObjectName(
            "secondaryButton"
        )
        self.install_update_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.install_update_button.setVisible(
            False
        )
        self.install_update_button.clicked.connect(
            self.install_verified_update
        )

        update_button_row.addWidget(
            self.check_updates_button
        )
        update_button_row.addWidget(
            self.download_update_button
        )
        update_button_row.addWidget(
            self.install_update_button
        )
        update_button_row.addStretch()

        updates_layout.addLayout(
            update_button_row
        )

        self.update_progress = QProgressBar()
        self.update_progress.setObjectName(
            "updateProgress"
        )
        self.update_progress.setRange(
            0,
            100,
        )
        self.update_progress.setValue(
            0
        )
        self.update_progress.setTextVisible(
            True
        )
        self.update_progress.setVisible(
            False
        )

        updates_layout.addWidget(
            self.update_progress
        )

        self.update_controller.busy_changed.connect(
            self._set_update_busy
        )
        self.update_controller.status_changed.connect(
            self._set_update_status
        )
        self.update_controller.result_ready.connect(
            self._handle_update_result
        )

        self.update_download_controller.busy_changed.connect(
            self._set_download_busy
        )
        self.update_download_controller.status_changed.connect(
            self._set_update_status
        )
        self.update_download_controller.progress_changed.connect(
            self._handle_download_progress
        )
        self.update_download_controller.result_ready.connect(
            self._handle_download_result
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

        self.companion_settings_card = (
            CompanionSettingsCard(
                self
            )
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

        self.reset_theme_button = (
            reset_theme
        )
        self.reset_all_settings_button = (
            reset_all
        )

        button_row.addWidget(reset_theme)
        button_row.addWidget(reset_all)
        button_row.addStretch()

        root.addWidget(branding)
        root.addWidget(theme_card)
        root.addWidget(atmosphere_card)
        root.addWidget(
            self.discord_application_library_card
        )
        root.addWidget(
            self.discord_identity_card
        )
        root.addWidget(sources)
        root.addWidget(
            self.spotify_connection_card
        )
        root.addWidget(
            self.artwork_hosting_card
        )
        root.addWidget(auto_afk)
        root.addWidget(appearance)
        root.addWidget(startup)
        root.addWidget(
            self.media_hotkeys_card
        )
        root.addWidget(
            self.local_music_card
        )
        root.addWidget(storage)
        root.addWidget(
            settings_backup
        )
        root.addWidget(updates)
        root.addWidget(diagnostics)
        root.addWidget(
            self.companion_settings_card
        )
        root.addWidget(self.status)
        root.addLayout(button_row)
        root.addStretch()

        self.settings_sections = {
            "branding": branding,
            "theme": theme_card,
            "atmosphere": atmosphere_card,
            "media_sources": sources,
            "discord_applications": (
                self.discord_application_library_card
            ),
            "discord_identity": (
                self.discord_identity_card
            ),
            "spotify": (
                self.spotify_connection_card
            ),
            "artwork_hosting": (
                self.artwork_hosting_card
            ),
            "auto_afk": auto_afk,
            "appearance": appearance,
            "windows_startup": startup,
            "media_hotkeys": (
                self.media_hotkeys_card
            ),
            "local_music": (
                self.local_music_card
            ),
            "data_storage": storage,
            "settings_backup": (
                settings_backup
            ),
            "updates": updates,
            "diagnostics": diagnostics,
        }

        self.settings_section_categories = {
            "appearance": "general",
            "windows_startup": "general",
            "media_sources": "discord",
            "discord_applications": "discord",
            "discord_identity": "discord",
            "artwork_hosting": "discord",
            "auto_afk": "discord",
            "branding": "customization",
            "theme": "customization",
            "atmosphere": "customization",
            "spotify": "spotify",
            "local_music": "local_music",
            "media_hotkeys": "playback",
            "data_storage": "library_data",
            "settings_backup": "library_data",
            "updates": "updates",
            "diagnostics": "advanced",
        }

        self.settings_category_cards = {
            "general": (
                appearance,
                startup,
            ),
            "discord": (
                self.discord_application_library_card,
                self.discord_identity_card,
                sources,
                self.artwork_hosting_card,
                auto_afk,
            ),
            "customization": (
                branding,
                theme_card,
                atmosphere_card,
            ),
            "spotify": (
                self.spotify_connection_card,
            ),
            "local_music": (
                self.local_music_card,
            ),
            "playback": (
                self.media_hotkeys_card,
            ),
            "library_data": (
                storage,
                settings_backup,
            ),
            "updates": (
                updates,
            ),
            "advanced": (
                diagnostics,
            ),
        }

        self._register_companion_settings_card()

        self.settings_category_extras = {
            "customization": (
                self.reset_theme_button,
            ),
            "advanced": (
                self.reset_all_settings_button,
            ),
        }

        self.settings_category_descriptions = {
            "general": (
                "Everyday application and window behaviour."
            ),
            "discord": (
                "Control Discord identity, presence sources, "
                "artwork, and automatic AFK behaviour."
            ),
            "customization": (
                "Personalise branding, colours, themes, "
                "and atmosphere."
            ),
            "spotify": (
                "Connect and manage your Spotify account."
            ),
            "local_music": (
                "Manage local music folders and scanning."
            ),
            "playback": (
                "Configure global media controls and hotkeys."
            ),
            "library_data": (
                "Review, export, back up, and manage app data."
            ),
            "updates": (
                "Check, download, and install app updates."
            ),
            "advanced": (
                "Diagnostics, support tools, and reset options."
            ),
        }

        scroll.setWidget(content)

        shell.addWidget(
            navigation
        )
        shell.addWidget(
            scroll,
            1,
        )

        outer.addLayout(
            shell
        )

        self._set_active_settings_category(
            "general"
        )

        self.refresh_storage_summary()
        self.refresh_diagnostics()

    def set_status_message(
        self,
        message: str,
        *,
        category: str | None = None,
    ):
        active_category = str(
            getattr(
                self,
                "_active_settings_category",
                "general",
            )
            or "general"
        ).strip().lower()

        target_category = str(
            category
            or active_category
        ).strip().lower()

        if not target_category:
            target_category = (
                active_category
            )

        status_messages = getattr(
            self,
            "_settings_status_messages",
            None,
        )

        if status_messages is None:
            status_messages = {}
            self._settings_status_messages = (
                status_messages
            )

        text = str(
            message or ""
        )

        status_messages[
            target_category
        ] = text

        if (
            target_category
            == active_category
        ):
            self.status.setText(
                text
            )

    def restore_spotify_connection(
        self,
    ) -> None:
        self.spotify_connection_card.restore()

    def shutdown_local_music(
        self,
    ) -> bool:
        runtime = getattr(
            self,
            "local_music_runtime",
            None,
        )

        if runtime is None:
            return True

        shutdown = getattr(
            runtime,
            "shutdown",
            None,
        )

        if not callable(
            shutdown
        ):
            return True

        try:
            return bool(
                shutdown()
            )

        except Exception:
            return False


    def set_media_hotkey_reload_callback(
        self,
        callback,
    ):
        self.media_hotkeys_card.set_reload_callback(
            callback
        )

    def set_update_quit_callback(
        self,
        callback,
    ):
        self.update_install_controller.set_quit_callback(
            callback
        )

    def install_verified_update(self):
        download_result = (
            self._verified_update_download
        )

        if download_result is None:
            self._set_update_status(
                "No verified update is ready "
                "to install."
            )
            return

        if (
            not self.update_install_controller
            .quit_callback_available
        ):
            QMessageBox.warning(
                self,
                "Update cannot start",
                (
                    "The app shutdown callback is "
                    "unavailable. Restart 03:37am "
                    "Presence and try again."
                ),
            )
            return

        version = str(
            getattr(
                download_result,
                "version",
                "",
            )
            or ""
        ).strip()

        version_label = (
            f"v{version}"
            if version
            else "the downloaded version"
        )

        response = QMessageBox.question(
            self,
            "Install update?",
            (
                f"{version_label} has been downloaded "
                "and verified."
                "\n\n"
                "03:37am Presence will launch the "
                "installer and close."
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
            self._set_update_status(
                "Update installation cancelled."
            )
            return

        self.install_update_button.setEnabled(
            False
        )

        install_result = (
            self.update_install_controller.launch(
                download_result,
                user_approved=True,
            )
        )

        message = str(
            getattr(
                install_result,
                "message",
                "",
            )
            or ""
        ).strip()

        error_code = str(
            getattr(
                install_result,
                "error_code",
                "",
            )
            or ""
        ).strip()

        launched = bool(
            getattr(
                install_result,
                "launched",
                False,
            )
        )

        if launched:
            self._set_update_status(
                message
                or (
                    "The verified installer "
                    "was launched."
                )
            )

            if error_code == "quit_failed":
                QMessageBox.warning(
                    self,
                    "Installer started",
                    (
                        message
                        or (
                            "The installer started, "
                            "but the app could not "
                            "close automatically."
                        )
                    ),
                )

            return

        self.install_update_button.setEnabled(
            True
        )

        failure_message = (
            message
            or (
                "The verified installer could "
                "not be launched."
            )
        )

        QMessageBox.warning(
            self,
            "Update could not start",
            failure_message,
        )

        self._set_update_status(
            failure_message
        )

    def check_for_updates(self):
        if (
            self.update_download_controller
            .is_busy
        ):
            self._set_update_status(
                "Wait for the current update "
                "download to finish."
            )
            return

        self._verified_update_download = None
        self.download_update_button.setVisible(
            False
        )
        self.install_update_button.setVisible(
            False
        )
        self.update_progress.setVisible(
            False
        )

        started = (
            self.update_controller
            .start_check()
        )

        if not started:
            self._set_update_status(
                "An update check is already running."
            )

    def download_available_update(self):
        if self.update_controller.is_busy:
            self._set_update_status(
                "Wait for the update check "
                "to finish."
            )
            return

        result = self._latest_update_result

        release = getattr(
            result,
            "release",
            None,
        )

        if release is None:
            self._set_update_status(
                "No verified release is "
                "available to download."
            )
            return

        self._verified_update_download = None
        self.install_update_button.setVisible(
            False
        )

        self.update_progress.setRange(
            0,
            0,
        )
        self.update_progress.setVisible(
            True
        )

        started = (
            self.update_download_controller
            .start_download(
                release
            )
        )

        if not started:
            self._set_update_status(
                "An update download is "
                "already running."
            )

    def _set_update_busy(
        self,
        busy: bool,
    ):
        busy = bool(busy)

        download_busy = (
            self.update_download_controller
            .is_busy
        )

        self.check_updates_button.setEnabled(
            not busy
            and not download_busy
        )

        self.check_updates_button.setText(
            (
                "Checking..."
                if busy
                else "Check for updates"
            )
        )

        if (
            self.download_update_button
            .isVisible()
        ):
            self.download_update_button.setEnabled(
                not busy
                and not download_busy
                and (
                    self._verified_update_download
                    is None
                )
            )

    def _set_download_busy(
        self,
        busy: bool,
    ):
        busy = bool(busy)

        check_busy = (
            self.update_controller
            .is_busy
        )

        self.check_updates_button.setEnabled(
            not busy
            and not check_busy
        )

        if (
            self._verified_update_download
            is not None
        ):
            self.download_update_button.setText(
                "Downloaded & verified"
            )
            self.download_update_button.setEnabled(
                False
            )
            return

        self.download_update_button.setText(
            (
                "Downloading..."
                if busy
                else "Download update"
            )
        )

        self.download_update_button.setEnabled(
            not busy
            and not check_busy
        )

    def _set_update_status(
        self,
        message: str,
    ):
        message = str(
            message or ""
        ).strip()

        if not message:
            return

        self.update_status_label.setText(
            message
        )

    @staticmethod
    def _result_boolean(
        result,
        name: str,
    ) -> bool:
        value = getattr(
            result,
            name,
            False,
        )

        if callable(value):
            try:
                value = value()
            except TypeError:
                return False

        return bool(value)

    def _handle_update_result(
        self,
        result,
    ):
        self._latest_update_result = result
        self._verified_update_download = None
        self.install_update_button.setVisible(
            False
        )

        presentation = (
            describe_update_result(
                result,
                current_version=APP_VERSION,
            )
        )

        self.update_status_label.setText(
            presentation.headline
        )

        self.update_details_label.setText(
            presentation.detail
        )

        can_download = (
            self._result_boolean(
                result,
                "can_download_update",
            )
        )

        release = getattr(
            result,
            "release",
            None,
        )

        show_download = bool(
            presentation.update_available
            and can_download
            and release is not None
        )

        self.download_update_button.setVisible(
            show_download
        )
        self.download_update_button.setEnabled(
            show_download
        )
        self.download_update_button.setText(
            "Download update"
        )

        self.update_progress.setVisible(
            False
        )

        self.set_status_message(
            presentation.headline
        )

    def _handle_download_progress(
        self,
        progress,
    ):
        presentation = (
            describe_download_progress(
                progress
            )
        )

        if presentation.indeterminate:
            self.update_progress.setRange(
                0,
                0,
            )
        else:
            self.update_progress.setRange(
                0,
                presentation.maximum,
            )
            self.update_progress.setValue(
                presentation.value
            )

        self.update_progress.setVisible(
            True
        )

        self.update_status_label.setText(
            presentation.text
        )

    def _handle_download_result(
        self,
        result,
    ):
        presentation = (
            describe_download_result(
                result
            )
        )

        self.update_status_label.setText(
            presentation.headline
        )

        self.update_details_label.setText(
            presentation.detail
        )

        if presentation.ready:
            self._verified_update_download = (
                result
            )

            self.update_progress.setRange(
                0,
                100,
            )
            self.update_progress.setValue(
                100
            )
            self.update_progress.setVisible(
                True
            )

            self.download_update_button.setText(
                "Downloaded & verified"
            )
            self.download_update_button.setEnabled(
                False
            )

            self.install_update_button.setText(
                "Install update"
            )
            self.install_update_button.setEnabled(
                True
            )
            self.install_update_button.setVisible(
                True
            )

        else:
            self._verified_update_download = None
            self.update_progress.setVisible(
                False
            )
            self.download_update_button.setText(
                "Download update"
            )
            self.download_update_button.setEnabled(
                True
            )

            self.install_update_button.setVisible(
                False
            )

        self.set_status_message(
            presentation.headline
        )

    def _register_companion_settings_card(
        self,
    ) -> None:
        card = self.companion_settings_card

        self.settings_sections[
            "desktop_companion"
        ] = card

        customization_key = None

        for key in self.settings_category_cards:
            normalized = str(
                key
            ).strip().casefold()

            if normalized in {
                "customization",
                "customisation",
            }:
                customization_key = key
                break

        if customization_key is None:
            raise RuntimeError(
                "Customization Settings category is missing."
            )

        existing = self.settings_category_cards[
            customization_key
        ]

        if isinstance(
            existing,
            tuple,
        ):
            if card not in existing:
                self.settings_category_cards[
                    customization_key
                ] = existing + (
                    card,
                )

        elif isinstance(
            existing,
            list,
        ):
            if card not in existing:
                existing.append(
                    card
                )

        else:
            cards = list(
                existing
            )

            if card not in cards:
                cards.append(
                    card
                )

            self.settings_category_cards[
                customization_key
            ] = cards

        section_categories = getattr(
            self,
            "settings_section_categories",
            None,
        )

        if isinstance(
            section_categories,
            dict,
        ):
            section_categories[
                "desktop_companion"
            ] = customization_key

    def set_companion_runtime(
        self,
        runtime,
    ) -> None:
        self.companion_runtime = runtime

        self.companion_settings_card.set_runtime(
            runtime
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

        hotkey_preview_note = (
            (
                "\n\nGlobal media hotkeys are included "
                "and will replace your current hotkey "
                "configuration."
            )
            if preview.includes_media_hotkeys
            else (
                "\n\nThis older backup does not contain "
                "global media hotkeys, so your current "
                "hotkeys will be kept."
            )
        )

        response = QMessageBox.question(
            self,
            "Restore settings?",
            (
                "This will replace your theme, "
                "branding text, media sources, "
                "Auto AFK settings, global media "
                "hotkeys, dashboard layout, custom "
                "Link cards, window preferences, Windows "
                "startup preference, and Discord Application "
                "Library entries when included by the backup."
                "\n\n"
                "Listening history, artwork cache, "
                "and Link-card icon cache will not "
                "be changed."
                + personal_note
                + hotkey_preview_note
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

        hotkeys_live = (
            self.refresh_after_settings_restore()
        )

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

        hotkey_restore_note = (
            (
                "\n\nGlobal media hotkeys were restored "
                "and applied immediately."
            )
            if (
                result.restored_media_hotkeys
                and hotkeys_live
            )
            else (
                (
                    "\n\nGlobal media hotkeys were restored, "
                    "but Windows could not activate them "
                    "immediately. Review the Global Media "
                    "Hotkeys card or restart the app."
                )
                if result.restored_media_hotkeys
                else (
                    "\n\nThis backup did not contain global "
                    "media hotkeys, so your existing hotkey "
                    "configuration was preserved."
                )
            )
        )

        QMessageBox.information(
            self,
            "Settings restored",
            (
                "Your settings were restored "
                "successfully."
                + hosting_note
                + hotkey_restore_note
                + (
                    "\n\nRestart 03:37am Presence "
                    "to apply the restored dashboard "
                    "layout and any remaining background "
                    "service settings."
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

        hotkeys_live = True

        try:
            self.media_hotkeys_card.refresh_from_store()

            hotkeys_live = (
                self.media_hotkeys_card.reload_runtime()
            )

        except Exception as error:
            print(
                "Media hotkey restore refresh error:",
                error,
            )

            hotkeys_live = False

        application_library_card = getattr(
            self,
            "discord_application_library_card",
            None,
        )

        refresh_applications = getattr(
            application_library_card,
            "refresh_from_store",
            None,
        )

        if callable(
            refresh_applications
        ):
            try:
                refresh_applications()

                entries_changed = getattr(
                    application_library_card,
                    "entries_changed",
                    None,
                )

                emit_entries_changed = getattr(
                    entries_changed,
                    "emit",
                    None,
                )

                if callable(
                    emit_entries_changed
                ):
                    emit_entries_changed()

            except Exception as error:
                print(
                    "Discord Application Library "
                    "restore refresh error:",
                    error,
                )

        self.refresh_storage_summary()
        self.refresh_diagnostics()

        return hotkeys_live

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

    def _set_active_settings_category(
        self,
        category_key: str,
    ):
        buttons = getattr(
            self,
            "settings_category_buttons",
            {},
        )

        requested = str(
            category_key or ""
        ).strip().lower()

        if (
            requested not in buttons
            and buttons
        ):
            requested = "general"

        self._active_settings_category = (
            requested
        )

        for key, button in buttons.items():
            button.blockSignals(
                True
            )
            button.setChecked(
                key == requested
            )
            button.blockSignals(
                False
            )

        category_cards = getattr(
            self,
            "settings_category_cards",
            {},
        )

        for key, cards in (
            category_cards.items()
        ):
            visible = (
                key == requested
            )

            for card in cards:
                card.setVisible(
                    visible
                )

        category_extras = getattr(
            self,
            "settings_category_extras",
            {},
        )

        all_extras = set()

        for extras in (
            category_extras.values()
        ):
            all_extras.update(
                extras
            )

        selected_extras = set(
            category_extras.get(
                requested,
                (),
            )
        )

        for widget in all_extras:
            widget.setVisible(
                widget in selected_extras
            )

        subtitle = getattr(
            self,
            "settings_page_subtitle",
            None,
        )

        descriptions = getattr(
            self,
            "settings_category_descriptions",
            {},
        )

        if subtitle is not None:
            subtitle.setText(
                descriptions.get(
                    requested,
                    "Configure 03:37am Presence.",
                )
            )

        status = getattr(
            self,
            "status",
            None,
        )

        status_messages = getattr(
            self,
            "_settings_status_messages",
            {},
        )

        if status is not None:
            status.setText(
                status_messages.get(
                    requested,
                    "",
                )
            )

        scroll = getattr(
            self,
            "settings_scroll",
            None,
        )

        if scroll is not None:
            scroll.verticalScrollBar().setValue(
                0
            )

    def show_section(
        self,
        section_name: str,
    ):
        requested = str(
            section_name or ""
        ).strip().lower()

        aliases = {
            "general": "appearance",
            "window": "appearance",
            "window settings": "appearance",
            "windows startup": "windows_startup",
            "startup": "windows_startup",
            "discord": "discord_identity",
            "discord identity": "discord_identity",
            "presence identity": "discord_identity",
            "application id": "discord_identity",
            "discord applications": "discord_applications",
            "discord application": "discord_applications",
            "discord application library": "discord_applications",
            "application library": "discord_applications",
            "customization": "branding",
            "customisation": "branding",
            "branding": "branding",
            "playback": "media_hotkeys",
            "library": "data_storage",
            "library data": "data_storage",
            "library & data": "data_storage",
            "advanced": "diagnostics",
            "local music": "local_music",
            "local files": "local_music",
            "music folders": "local_music",
            "afk": "auto_afk",
            "auto afk": "auto_afk",
            "sources": "media_sources",
            "media": "media_sources",
            "media sources": "media_sources",
            "spotify": "spotify",
            "spotify account": "spotify",
            "spotify connection": "spotify",
            "connect spotify": "spotify",
            "artwork": "artwork_hosting",
            "cloudinary": "artwork_hosting",
            "hosting": "artwork_hosting",
            "artwork hosting": "artwork_hosting",
            "colours": "theme",
            "colors": "theme",
            "hotkey": "media_hotkeys",
            "hotkeys": "media_hotkeys",
            "shortcut": "media_hotkeys",
            "shortcuts": "media_hotkeys",
            "media hotkeys": "media_hotkeys",
            "global hotkeys": "media_hotkeys",
            "media controls": "media_hotkeys",
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

        category_key = getattr(
            self,
            "settings_section_categories",
            {},
        ).get(
            section_key
        )

        if category_key:
            self._set_active_settings_category(
                category_key
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

        # Clear our Python-side reference first. A delayed
        # QTimer callback can outlive the underlying Qt widget,
        # leaving a valid Python wrapper around a deleted C++
        # object.
        self._focused_settings_card = None

        try:
            card.setProperty(
                "deepLinkFocus",
                False,
            )
        except RuntimeError:
            return

        self._refresh_widget_style(
            card
        )

    @staticmethod
    def _refresh_widget_style(
        widget,
    ):
        try:
            style = widget.style()

            style.unpolish(
                widget
            )
            style.polish(
                widget
            )

            widget.update()

        except RuntimeError:
            # Qt may delete a card after a delayed deep-link
            # cleanup has already been scheduled. Treat that
            # normal lifetime race as completed cleanup.
            return

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

            QFrame#settingsCategoryRail {{
                background: {theme["card"]};
                border: 1px solid {theme["border"]};
                border-radius: 12px;
            }}

            QLabel#settingsCategoryRailTitle {{
                color: {theme["text"]};
                background: transparent;
                border: none;
                font-size: 10px;
                font-weight: 800;
                letter-spacing: 1px;
                padding: 2px 8px 0px 8px;
            }}

            QLabel#settingsCategoryRailHelp {{
                color: {theme["muted"]};
                background: transparent;
                border: none;
                font-size: 9px;
                padding: 0px 8px 4px 8px;
            }}

            QPushButton#settingsCategoryButton {{
                color: {theme["text"]};
                background: transparent;
                border: 1px solid transparent;
                border-radius: 8px;
                text-align: left;
                padding: 7px 10px;
                font-size: 10px;
                font-weight: 650;
            }}

            QPushButton#settingsCategoryButton:hover {{
                background: {theme["card_alt"]};
                border: 1px solid {theme["border"]};
            }}

            QPushButton#settingsCategoryButton:checked {{
                color: {theme["text"]};
                background: {theme["card_alt"]};
                border: 1px solid {theme["accent"]};
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

            QProgressBar#updateProgress {{
                color: {theme["text"]};
                background: {card_alt_glass};
                border: 1px solid {theme["border"]};
                border-radius: 7px;
                min-height: 18px;
                text-align: center;
            }}

            QProgressBar#updateProgress::chunk {{
                background: {theme["accent"]};
                border-radius: 6px;
            }}

            QPushButton#secondaryButton:disabled {{
                color: {theme["muted"]};
                border-color: {theme["border"]};
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

        self.discord_identity_card.reset_preferences()

        self.media_hotkeys_card.reset_preferences()

        self.status.setText(
            "All settings reset."
        )

