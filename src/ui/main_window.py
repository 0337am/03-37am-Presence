from pathlib import Path

from PyQt6.QtCore import (
    Qt,
    QTimer,
    pyqtSlot,
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.discord.extended_presence import (
    ExtendedDiscordPresence,
)
from src.discord.presence_controller import (
    PresenceController,
)
from src.system.afk_preferences import (
    AfkPreferencesStore,
)
from src.system.idle_monitor import (
    WindowsIdleMonitor,
)
from src.ui.about import AboutPage
from src.ui.dashboard import DashboardPage
from src.ui.library import LibraryPage
from src.ui.presence_page import PresencePage
from src.ui.settings import SettingsPage
from src.ui.theme import ThemeManager
from src.version import (
    APP_VERSION,
    RELEASE_NAME,
)


PROJECT_ROOT = (
    Path(__file__).resolve().parents[2]
)

YUNO_IMAGE_PATH = (
    PROJECT_ROOT
    / "assets"
    / "yuno.png"
)


class NavigationButton(QPushButton):
    def __init__(
        self,
        icon_text: str,
        text: str,
    ):
        super().__init__()

        self.setObjectName(
            "navigationButton"
        )
        self.setCheckable(True)

        self.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.setMinimumHeight(44)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            12,
            0,
            10,
            0,
        )
        layout.setSpacing(8)

        icon_label = QLabel(
            icon_text
        )
        icon_label.setObjectName(
            "navigationEmoji"
        )
        icon_label.setFixedWidth(22)

        icon_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        text_label = QLabel(text)
        text_label.setObjectName(
            "navigationText"
        )

        text_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
        )

        icon_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )

        text_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )

        layout.addWidget(
            icon_label
        )
        layout.addWidget(
            text_label,
            stretch=1,
        )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self._shutting_down = False

        self.setWindowTitle(
            "03:37am Presence"
        )
        self.resize(1450, 840)
        self.setMinimumSize(
            1050,
            680,
        )

        self.discord = (
            ExtendedDiscordPresence()
        )

        self.presence_controller = (
            PresenceController(
                self.discord
            )
        )

        self.afk_preferences_store = (
            AfkPreferencesStore()
        )

        self.theme_manager = (
            ThemeManager(self)
        )

        root = QWidget()
        root.setObjectName("root")

        self.setCentralWidget(root)

        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        main_layout.setSpacing(0)

        self.build_sidebar(
            main_layout
        )
        self.build_pages(
            main_layout
        )

        self.apply_theme(
            self.theme_manager.theme()
        )
        self.apply_branding(
            self.theme_manager.branding()
        )

        self.connect_services()
        self.apply_saved_settings()
        self.switch_page(0)

    def build_sidebar(
        self,
        main_layout,
    ):
        # COMPACT_GUIDE_SIDEBAR
        self.sidebar = QFrame()
        self.sidebar.setObjectName(
            "sidebar"
        )
        self.sidebar.setFixedWidth(210)

        sidebar_layout = QVBoxLayout(
            self.sidebar
        )
        sidebar_layout.setContentsMargins(
            14,
            16,
            14,
            12,
        )
        sidebar_layout.setSpacing(7)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(9)

        self.yuno_picture = QLabel()
        self.yuno_picture.setObjectName(
            "yunoPicture"
        )
        self.yuno_picture.setFixedSize(
            44,
            44,
        )
        self.yuno_picture.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)

        self.logo = QLabel(
            "03:37am"
        )
        self.logo.setObjectName(
            "logo"
        )
        self.logo.setWordWrap(True)

        self.subtitle = QLabel(
            "Presence"
        )
        self.subtitle.setObjectName(
            "subtitle"
        )

        brand_text.addWidget(
            self.logo
        )
        brand_text.addWidget(
            self.subtitle
        )

        brand_row.addWidget(
            self.yuno_picture
        )
        brand_row.addLayout(
            brand_text,
            stretch=1,
        )

        sidebar_layout.addLayout(
            brand_row
        )
        sidebar_layout.addSpacing(16)

        self.dashboard_button = NavigationButton(
            "🏠",
            "Dashboard",
        )

        self.presence_button = NavigationButton(
            "👥",
            "Presence",
        )

        self.library_button = NavigationButton(
            "📁",
            "Library",
        )

        self.settings_button = NavigationButton(
            "⚙️",
            "Settings",
        )

        self.about_button = NavigationButton(
            "ℹ️",
            "About",
        )

        self.navigation_buttons = [
            self.dashboard_button,
            self.presence_button,
            self.library_button,
            self.settings_button,
            self.about_button,
        ]

        for button in self.navigation_buttons:
            sidebar_layout.addWidget(
                button
            )

        sidebar_layout.addStretch()

        self.tagline = QLabel("", self.sidebar)
        self.tagline.setObjectName(
            "tagline"
        )
        self.tagline.setVisible(
            False
        )

        compact_panel = QFrame()
        compact_panel.setObjectName(
            "compactPanel"
        )

        compact_layout = QVBoxLayout(
            compact_panel
        )
        compact_layout.setContentsMargins(
            10,
            9,
            10,
            9,
        )
        compact_layout.setSpacing(7)

        compact_top = QHBoxLayout()
        compact_top.setSpacing(8)

        compact_label = QLabel(
            "Compact Mode"
        )
        compact_label.setObjectName(
            "sidebarCompactLabel"
        )

        self.compact_mode_button = QCheckBox()
        self.compact_mode_button.setObjectName(
            "sidebarToggle"
        )
        self.compact_mode_button.setFixedSize(
            38,
            20,
        )
        self.compact_mode_button.setChecked(
            bool(
                self.theme_manager.theme().get(
                    "compact",
                    True,
                )
            )
        )
        self.compact_mode_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.compact_mode_button.toggled.connect(
            self.change_sidebar_compact_mode
        )

        compact_top.addWidget(
            compact_label
        )
        compact_top.addStretch()
        compact_top.addWidget(
            self.compact_mode_button
        )

        compact_bottom = QHBoxLayout()
        compact_bottom.setSpacing(8)

        theme_label = QLabel(
            "Theme settings"
        )
        theme_label.setObjectName(
            "sidebarThemeLabel"
        )

        theme_shortcut = QPushButton("Theme")
        theme_shortcut.setObjectName(
            "sidebarThemeButton"
        )
        theme_shortcut.setFixedSize(
            54,
            32,
        )
        theme_shortcut.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        theme_shortcut.clicked.connect(
            lambda:
            self.open_settings_section(
                "theme"
            )
        )

        compact_bottom.addWidget(
            theme_label
        )
        compact_bottom.addStretch()
        compact_bottom.addWidget(
            theme_shortcut
        )

        compact_layout.addLayout(
            compact_top
        )
        compact_layout.addLayout(
            compact_bottom
        )

        sidebar_layout.addWidget(
            compact_panel
        )

        self.version_label = QLabel(
            f"v{APP_VERSION}"
        )
        self.version_label.setObjectName(
            "versionLabel"
        )
        self.version_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        sidebar_layout.addWidget(
            self.version_label
        )

        main_layout.addWidget(
            self.sidebar
        )

    def build_pages(
        self,
        main_layout,
    ):
        self.pages = QStackedWidget()
        self.pages.setObjectName(
            "pages"
        )

        self.dashboard_page = DashboardPage(
            self.theme_manager
        )

        self.presence_page = PresencePage(
            self.presence_controller,
            self.theme_manager,
        )

        self.library_page = LibraryPage(
            self.theme_manager
        )

        self.settings_page = SettingsPage(
            self.theme_manager
        )

        self.settings_page.set_diagnostics_provider(
            self.collect_diagnostics
        )

        self.about_page = AboutPage(
            self.theme_manager
        )

        self.pages.addWidget(
            self.dashboard_page
        )

        self.pages.addWidget(
            self.presence_page
        )

        self.pages.addWidget(
            self.library_page
        )

        self.pages.addWidget(
            self.settings_page
        )

        self.pages.addWidget(
            self.about_page
        )

        main_layout.addWidget(
            self.pages,
            stretch=1,
        )

        self.dashboard_button.clicked.connect(
            lambda: self.switch_page(0)
        )

        self.presence_button.clicked.connect(
            lambda: self.switch_page(1)
        )

        self.library_button.clicked.connect(
            lambda: self.switch_page(2)
        )

        self.settings_button.clicked.connect(
            lambda: self.switch_page(3)
        )

        self.about_button.clicked.connect(
            lambda: self.switch_page(4)
        )

    def open_settings_section(
        self,
        section_name: str,
    ):
        self.switch_page(3)

        QTimer.singleShot(
            0,
            lambda target=section_name:
            self.settings_page.show_section(
                target
            )
        )

    def switch_page(
        self,
        page_index: int,
    ):
        self.pages.setCurrentIndex(
            page_index
        )

        for index, button in enumerate(
            self.navigation_buttons
        ):
            button.setChecked(
                index == page_index
            )

        if page_index == 3:
            refresh_storage = getattr(
                self.settings_page,
                "refresh_storage_summary",
                None,
            )

            refresh_diagnostics = getattr(
                self.settings_page,
                "refresh_diagnostics",
                None,
            )

            if callable(
                refresh_storage
            ):
                refresh_storage()

            if callable(
                refresh_diagnostics
            ):
                refresh_diagnostics()

    def refresh_storage_views(self):
        library_refresh = getattr(
            self.library_page,
            "load_history",
            None,
        )

        dashboard_refresh = getattr(
            self.dashboard_page,
            "refresh_dashboard_data",
            None,
        )

        settings_refresh = getattr(
            self.settings_page,
            "refresh_storage_summary",
            None,
        )

        diagnostics_refresh = getattr(
            self.settings_page,
            "refresh_diagnostics",
            None,
        )

        if callable(
            library_refresh
        ):
            library_refresh()

        if callable(
            dashboard_refresh
        ):
            dashboard_refresh()

        if callable(
            settings_refresh
        ):
            settings_refresh()

        if callable(
            diagnostics_refresh
        ):
            diagnostics_refresh()

    def collect_diagnostics(
        self,
    ) -> dict[str, str]:
        discord_status = (
            "Connected"
            if self.discord.is_connected
            else "Disconnected"
        )

        active_mode = str(
            self.presence_controller.active_mode
            or "music"
        ).strip().replace(
            "_",
            " ",
        ).title()

        if (
            self.presence_controller
            .auto_afk_active
        ):
            active_mode = "AFK (automatic)"

        song = getattr(
            self.dashboard_page,
            "song",
            None,
        )

        media_title = str(
            getattr(
                song,
                "title",
                "",
            )
            or ""
        ).strip()

        music_state_label = getattr(
            self.dashboard_page,
            "music_status",
            None,
        )

        music_state = (
            music_state_label.text()
            if music_state_label is not None
            else "Unknown"
        )

        waiting_titles = {
            "",
            "Waiting for media...",
            "Nothing playing",
        }

        if media_title in waiting_titles:
            media_description = (
                f"No active media ({music_state})"
            )
        else:
            media_description = (
                f"{media_title} ({music_state})"
            )

        source_app = str(
            getattr(
                song,
                "source_app",
                "",
            )
            or ""
        ).strip()

        display_source = getattr(
            self.dashboard_page,
            "_display_source",
            None,
        )

        if callable(
            display_source
        ):
            media_source = display_source(
                source_app
            )
        else:
            media_source = (
                source_app
                or "None detected"
            )

        if (
            media_source == "Unknown"
            and not source_app
        ):
            media_source = "None detected"

        source_preferences = (
            self.settings_page
            .source_preferences_store
            .load()
        )

        enabled_sources = (
            "Spotify: "
            + (
                "On"
                if source_preferences.spotify_enabled
                else "Off"
            )
            + " | Browser media: "
            + (
                "On"
                if source_preferences.browser_enabled
                else "Off"
            )
        )

        afk_preferences = (
            self.afk_preferences_store.load()
        )

        try:
            idle_seconds = max(
                0,
                int(
                    WindowsIdleMonitor.idle_seconds()
                ),
            )

            idle_minutes = (
                idle_seconds // 60
            )

            idle_remainder = (
                idle_seconds % 60
            )

            idle_text = (
                f"{idle_minutes}m "
                f"{idle_remainder}s idle"
            )

        except Exception:
            idle_text = "Idle time unavailable"

        if afk_preferences.enabled:
            auto_afk = (
                "Enabled after "
                f"{afk_preferences.timeout_minutes} "
                "minute"
                + (
                    ""
                    if afk_preferences.timeout_minutes == 1
                    else "s"
                )
                + f" | {idle_text}"
            )

            if (
                self.presence_controller
                .auto_afk_active
            ):
                auto_afk += " | Currently active"
        else:
            auto_afk = (
                f"Disabled | {idle_text}"
            )

        try:
            track_count = (
                self.library_page
                .history_store
                .count_tracks()
            )

            total_plays = (
                self.library_page
                .history_store
                .total_plays()
            )

            database_path = (
                self.library_page
                .history_store
                .database_path
            )

            database_status = (
                "Healthy"
                if database_path.exists()
                else "Not created"
            )

            library_status = (
                f"{database_status} | "
                f"{track_count} tracks | "
                f"{total_plays} plays"
            )

        except Exception as error:
            library_status = (
                f"Database error: {error}"
            )

        media_error = str(
            getattr(
                self.dashboard_page,
                "_last_worker_error",
                "",
            )
            or "None"
        )

        return {
            "app_version": (
                f"v{APP_VERSION} — "
                f"{RELEASE_NAME}"
            ),
            "discord": discord_status,
            "presence_mode": active_mode,
            "media": media_description,
            "media_source": media_source,
            "enabled_sources": enabled_sources,
            "auto_afk": auto_afk,
            "library": library_status,
            "media_error": media_error,
        }

    def change_sidebar_compact_mode(
        self,
        checked: bool,
    ):
        self.theme_manager.set_theme_value(
            "compact",
            checked,
        )

    @pyqtSlot(dict)
    def apply_theme(
        self,
        theme: dict,
    ):
        compact = bool(
            theme.get(
                "compact",
                True,
            )
        )

        self.compact_mode_button.blockSignals(
            True
        )
        self.compact_mode_button.setChecked(
            compact
        )
        self.compact_mode_button.blockSignals(
            False
        )

        self.setStyleSheet(
            f"""
            QMainWindow,
            QWidget#root {{
                background: {theme["background"]};
            }}

            QFrame#sidebar {{
                background: {theme["sidebar"]};
                border-right: 1px solid {theme["border"]};
            }}

            QLabel#yunoPicture {{
                background: {theme["background"]};
                color: {theme["accent"]};
                border: 1px solid {theme["border"]};
                border-radius: 10px;
            }}

            QLabel#logo {{
                color: {theme["text"]};
                font-size: 19px;
                font-weight: 750;
            }}

            QLabel#subtitle {{
                color: {theme["muted"]};
                font-size: 10px;
                letter-spacing: 1px;
            }}

            QLabel#tagline {{
                color: {theme["muted"]};
                font-size: 9px;
                padding: 5px;
            }}

            QLabel#versionLabel {{
                color: {theme["muted"]};
                font-size: 9px;
                padding-top: 2px;
            }}

            QPushButton#navigationButton {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 10px;
            }}

            QPushButton#navigationButton:hover {{
                background: {theme["card"]};
                border: 1px solid {theme["border"]};
            }}

            QPushButton#navigationButton:checked {{
                background: {theme["card_alt"]};
                border: 1px solid {theme["accent"]};
            }}

            QLabel#navigationEmoji,
            QLabel#navigationText {{
                color: {theme["text"]};
                background: transparent;
            }}

            QLabel#navigationEmoji {{
                color: {theme["accent"]};
                font-size: 14px;
            }}

            QLabel#navigationText {{
                font-size: 12px;
                font-weight: 650;
            }}

            QFrame#compactPanel {{
                background: {theme["card"]};
                border: 1px solid {theme["border"]};
                border-radius: 10px;
            }}

            QLabel#sidebarCompactLabel {{
                color: {theme["text"]};
                font-size: 9px;
                font-weight: 700;
            }}

            QLabel#sidebarThemeLabel {{
                color: {theme["muted"]};
                font-size: 8px;
            }}

            QCheckBox#sidebarToggle {{
                background: transparent;
                border: none;
                spacing: 0px;
            }}

            QCheckBox#sidebarToggle::indicator {{
                width: 34px;
                height: 17px;
                border-radius: 8px;
                background: {theme["card_alt"]};
                border: 1px solid {theme["border"]};
            }}

            QCheckBox#sidebarToggle::indicator:checked {{
                background: {theme["accent"]};
                border: 1px solid {theme["accent"]};
            }}

            QPushButton#sidebarThemeButton {{
                color: {theme["text"]};
                background: {theme["card_alt"]};
                border: 1px solid {theme["border"]};
                border-radius: 8px;
                font-size: 8px;
                font-weight: 700;
            }}

            QPushButton#sidebarThemeButton:hover {{
                border: 1px solid {theme["accent"]};
            }}

            QStackedWidget#pages {{
                background: {theme["background"]};
            }}
            """
        )

    @pyqtSlot(dict)
    def apply_branding(
        self,
        branding: dict,
    ):
        title = (
            branding.get(
                "title",
                "",
            )
            or "03:37am Presence"
        )

        subtitle = (
            branding.get(
                "subtitle",
                "",
            )
            or "Yuno Presence"
        )

        footer = (
            branding.get(
                "footer",
                "",
            )
            or (
                "Love is the strongest "
                "signal. \u2661"
            )
        )

        self.logo.setText(
            title
        )
        self.subtitle.setText(
            subtitle
        )
        self.tagline.setText(
            footer
        )

        self.logo.setVisible(
            bool(
                branding.get(
                    "show_title",
                    True,
                )
            )
        )

        self.subtitle.setVisible(
            bool(
                branding.get(
                    "show_subtitle",
                    True,
                )
            )
        )

        self.tagline.setVisible(
            False
        )

        self.setWindowTitle(
            title
        )

        selected_path = str(
            branding.get(
                "image_path",
                "",
            )
            or ""
        )

        if selected_path:
            image_path = Path(
                selected_path
            )
        else:
            image_path = (
                YUNO_IMAGE_PATH
            )

        if not image_path.exists():
            image_path = (
                YUNO_IMAGE_PATH
            )

        pixmap = QPixmap(
            str(image_path)
        )

        if pixmap.isNull():
            self.yuno_picture.clear()

            self.yuno_picture.setText(
                "Branding image\n"
                "not found"
            )
            return

        self.yuno_picture.setText("")

        self.yuno_picture.setPixmap(
            pixmap.scaled(
                40,
                40,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def connect_services(self):
        self.dashboard_page.media_worker.song_ready.connect(
            self.handle_song_update
        )

        self.dashboard_page.navigate_requested.connect(
            self.switch_page
        )

        self.dashboard_page.settings_section_requested.connect(
            self.open_settings_section
        )

        self.settings_page.show_portrait_changed.connect(
            self.apply_show_portrait
        )

        self.settings_page.always_on_top_changed.connect(
            self.apply_always_on_top
        )

        self.settings_page.storage_changed.connect(
            self.refresh_storage_views
        )

        self.theme_manager.theme_changed.connect(
            self.apply_theme
        )

        self.theme_manager.branding_changed.connect(
            self.apply_branding
        )

        self.discord.connect()

        QTimer.singleShot(
            0,
            self.presence_controller.apply_saved_mode,
        )

        self.discord_status_timer = QTimer(
            self
        )

        self.discord_status_timer.timeout.connect(
            self.refresh_discord_status
        )

        self.discord_status_timer.start(
            500
        )

        self.auto_afk_timer = QTimer(
            self
        )

        self.auto_afk_timer.timeout.connect(
            self.check_auto_afk
        )

        self.auto_afk_timer.start(
            1000
        )

        self.refresh_discord_status()

        app = QApplication.instance()

        if app is not None:
            app.aboutToQuit.connect(
                self.shutdown
            )

    def apply_saved_settings(self):
        self.apply_show_portrait(
            self.settings_page.show_yuno_portrait
        )

        self.apply_always_on_top(
            self.settings_page.always_on_top
        )

    @pyqtSlot(object)
    def handle_song_update(
        self,
        song,
    ):
        self.presence_controller.handle_song(
            song
        )

        self.library_page.add_song(
            song
        )

    @pyqtSlot(bool)
    def apply_show_portrait(
        self,
        enabled: bool,
    ):
        self.yuno_picture.setVisible(
            enabled
        )

    @pyqtSlot(bool)
    def apply_always_on_top(
        self,
        enabled: bool,
    ):
        was_visible = self.isVisible()

        self.setWindowFlag(
            Qt.WindowType.WindowStaysOnTopHint,
            enabled,
        )

        if was_visible:
            self.show()

    def check_auto_afk(self):
        preferences = (
            self.afk_preferences_store.load()
        )

        if not preferences.enabled:
            self.presence_controller.leave_auto_afk()
            return

        threshold_seconds = (
            preferences.timeout_minutes
            * 60
        )

        if WindowsIdleMonitor.is_idle(
            threshold_seconds
        ):
            self.presence_controller.enter_auto_afk()
        else:
            self.presence_controller.leave_auto_afk()

    def refresh_discord_status(self):
        status_label = getattr(
            self.dashboard_page,
            "discord_status",
            None,
        )

        if status_label is None:
            return

        if self.discord.is_connected:
            status_label.setText(
                "Connected"
            )

        elif self.discord.is_running:
            status_label.setText(
                "Waiting for Discord"
            )

        else:
            status_label.setText(
                "Stopped"
            )

    def shutdown(self):
        if self._shutting_down:
            return

        self._shutting_down = True

        timer = getattr(
            self,
            "discord_status_timer",
            None,
        )

        if timer is not None:
            timer.stop()

        auto_afk_timer = getattr(
            self,
            "auto_afk_timer",
            None,
        )

        if auto_afk_timer is not None:
            auto_afk_timer.stop()

        self.discord.close()

    def closeEvent(
        self,
        event,
    ):
        self.shutdown()

        super().closeEvent(
            event
        )