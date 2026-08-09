from pathlib import Path

from PyQt6.QtCore import (
    Qt,
    QTimer,
    QRectF,
    pyqtSlot,
)
from PyQt6.QtGui import (
    QColor,
    QPainter,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QCheckBox,
    QApplication,
    QFrame,
    QGraphicsBlurEffect,
    QGraphicsPixmapItem,
    QGraphicsScene,
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
from src.media.local_candidate_snapshot import (
    LocalCandidateSnapshot,
)
from src.spotify.connection_controller import (
    SpotifyConnectionController,
)
from src.spotify.playlist_service import (
    SpotifyPlaylistService,
)
from src.spotify.liked_songs_service import (
    SpotifyLikedSongsService,
)
from src.spotify.resolved_playlist_service import (
    SpotifyResolvedPlaylistService,
)
from src.spotify.session_manager import (
    SpotifySessionManager,
)
from src.spotify.constants import (
    SPOTIFY_PUBLIC_CLIENT_ID,
)
from src.spotify.qt_connection_runtime import (
    SpotifyQtConnectionRuntime,
)
from src.spotify.qt_playlist_runtime import (
    SpotifyQtPlaylistRuntime,
)
from src.spotify.qt_liked_songs_runtime import (
    SpotifyQtLikedSongsRuntime,
)
from src.spotify.qt_search_runtime import (
    SpotifyQtSearchRuntime,
)
from src.spotify.search_service import (
    SpotifySearchService,
)
from src.ui.spotify_page import SpotifyPage
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

LAST_PAGE_SETTING_KEY = (
    "navigation/last_page"
)

DEFAULT_PAGE_INDEX = 0


class AtmosphereLayer(QWidget):
    def __init__(
        self,
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName(
            "atmosphereLayer"
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )

        self._atmosphere = {}
        self._source_image_path = ""
        self._source_pixmap = QPixmap()
        self._background_cache_key = None
        self._background_cache = QPixmap()

    def set_atmosphere(
        self,
        atmosphere: dict,
    ):
        old_image_path = str(
            self._atmosphere.get(
                "image_path",
                "",
            )
            or ""
        )

        self._atmosphere = dict(
            atmosphere or {}
        )

        new_image_path = str(
            self._atmosphere.get(
                "image_path",
                "",
            )
            or ""
        )

        if new_image_path != old_image_path:
            self._source_image_path = ""
            self._source_pixmap = QPixmap()
            self._background_cache_key = None
            self._background_cache = QPixmap()

        self.setVisible(
            self.has_active_atmosphere()
        )
        self.update()

    def has_active_atmosphere(self) -> bool:
        if not bool(
            self._atmosphere.get(
                "enabled",
                False,
            )
        ):
            return False

        image_path = str(
            self._atmosphere.get(
                "image_path",
                "",
            )
            or ""
        )

        return bool(
            image_path
            and Path(image_path).exists()
        )

    def _blur_pixmap(
        self,
        pixmap: QPixmap,
        radius: int,
    ) -> QPixmap:
        if radius <= 0 or pixmap.isNull():
            return pixmap

        scene = QGraphicsScene()
        item = QGraphicsPixmapItem(pixmap)

        effect = QGraphicsBlurEffect()
        effect.setBlurRadius(radius)
        item.setGraphicsEffect(effect)

        scene.addItem(item)

        result = QPixmap(
            pixmap.size()
        )
        result.fill(
            Qt.GlobalColor.transparent
        )

        painter = QPainter(result)
        scene.render(
            painter,
            QRectF(result.rect()),
            QRectF(pixmap.rect()),
        )
        painter.end()

        return result

    def _background_pixmap(self) -> QPixmap:
        if not self.has_active_atmosphere():
            return QPixmap()

        image_path = Path(
            str(
                self._atmosphere.get(
                    "image_path",
                    "",
                )
                or ""
            )
        )

        rect = self.rect()

        if rect.isEmpty():
            return QPixmap()

        current_path = str(image_path)

        if current_path != self._source_image_path:
            self._source_image_path = current_path
            self._source_pixmap = QPixmap(
                current_path
            )
            self._background_cache_key = None
            self._background_cache = QPixmap()

        if self._source_pixmap.isNull():
            return QPixmap()

        blur = int(
            self._atmosphere.get(
                "blur",
                0,
            )
            or 0
        )

        cache_key = (
            current_path,
            rect.width(),
            rect.height(),
            blur,
        )

        if (
            cache_key == self._background_cache_key
            and not self._background_cache.isNull()
        ):
            return self._background_cache

        scaled = self._source_pixmap.scaled(
            rect.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )

        scaled = self._blur_pixmap(
            scaled,
            blur,
        )

        self._background_cache_key = cache_key
        self._background_cache = scaled

        return scaled

    def paintEvent(self, event):
        if not self.has_active_atmosphere():
            return

        scaled = self._background_pixmap()

        if scaled.isNull():
            return

        rect = self.rect()

        if rect.isEmpty():
            return

        opacity = max(
            0,
            min(
                100,
                int(
                    self._atmosphere.get(
                        "opacity",
                        45,
                    )
                    or 0
                ),
            ),
        )

        dim = max(
            0,
            min(
                90,
                int(
                    self._atmosphere.get(
                        "dim",
                        55,
                    )
                    or 0
                ),
            ),
        )

        x = int(
            (rect.width() - scaled.width()) / 2
        )
        y = int(
            (rect.height() - scaled.height()) / 2
        )

        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.RenderHint.SmoothPixmapTransform,
            True,
        )
        painter.setOpacity(
            opacity / 100
        )
        painter.drawPixmap(
            x,
            y,
            scaled,
        )
        painter.setOpacity(1)

        if dim:
            painter.fillRect(
                rect,
                QColor(
                    0,
                    0,
                    0,
                    int(255 * (dim / 100)),
                ),
            )

        painter.end()


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

        self.atmosphere_layer = AtmosphereLayer(root)
        self.atmosphere_layer.setGeometry(
            root.rect()
        )
        self.atmosphere_layer.lower()

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
        self.apply_atmosphere(
            self.theme_manager.atmosphere()
        )

        self.connect_services()
        self.apply_saved_settings()
        self.restore_last_page()

        self._schedule_local_music_startup_scan()

    def _schedule_local_music_startup_scan(
        self,
    ) -> None:
        QTimer.singleShot(
            0,
            self._start_local_music_startup_scan,
        )

    def _start_local_music_startup_scan(
        self,
    ) -> bool:
        if self._shutting_down:
            return False

        settings_page = getattr(
            self,
            "settings_page",
            None,
        )

        if settings_page is None:
            return False

        local_music_card = getattr(
            settings_page,
            "local_music_card",
            None,
        )

        if local_music_card is None:
            return False

        startup_scan = getattr(
            local_music_card,
            "scan_on_startup",
            None,
        )

        if not callable(
            startup_scan
        ):
            return False

        try:
            return bool(
                startup_scan()
            )

        except Exception:
            return False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_atmosphere_geometry()

    def update_atmosphere_geometry(self):
        layer = getattr(
            self,
            "atmosphere_layer",
            None,
        )
        root = self.centralWidget()

        if layer is None or root is None:
            return

        layer.setGeometry(
            root.rect()
        )
        layer.lower()

    @staticmethod
    def _with_alpha(
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

    def atmosphere_is_active(self) -> bool:
        layer = getattr(
            self,
            "atmosphere_layer",
            None,
        )

        return bool(
            layer is not None
            and layer.has_active_atmosphere()
        )

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

        self.spotify_button = NavigationButton(
            "🎧",
            "Spotify",
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
            self.spotify_button,
            self.settings_button,
            self.about_button,
        ]

        self.navigation_page_indexes = [
            0,
            1,
            2,
            5,
            3,
            4,
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

    def _create_spotify_connection_controller(
        self,
        client_id: str,
        *,
        browser_opener,
    ):
        return SpotifyConnectionController(
            client_id,
            session_manager=(
                self.spotify_session_manager
            ),
            browser_opener=browser_opener,
        )

    def _spotify_local_candidates(
        self,
    ):
        snapshot = getattr(
            self,
            "spotify_local_candidate_snapshot",
            None,
        )

        if snapshot is None:
            return None

        getter = getattr(
            snapshot,
            "get",
            None,
        )

        if not callable(
            getter
        ):
            return None

        return getter()

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

        self.spotify_session_manager = (
            SpotifySessionManager(
                SPOTIFY_PUBLIC_CLIENT_ID
            )
        )

        self.spotify_connection_runtime = (
            SpotifyQtConnectionRuntime(
                SPOTIFY_PUBLIC_CLIENT_ID,
                controller_factory=(
                    self._create_spotify_connection_controller
                ),
                parent=self,
            )
        )

        spotify_session_manager = (
            self.spotify_session_manager
        )

        self.spotify_search_runtime = (
            SpotifyQtSearchRuntime(
                lambda manager=spotify_session_manager:
                SpotifySearchService(
                    manager
                ),
                parent=self,
            )
        )

        self.settings_page = SettingsPage(
            self.theme_manager,
            spotify_runtime=(
                self.spotify_connection_runtime
            ),
        )

        self.spotify_local_candidate_snapshot = (
            LocalCandidateSnapshot()
        )

        local_music_runtime = (
            self.settings_page.local_music_runtime
        )

        local_music_runtime.result_ready.connect(
            self.spotify_local_candidate_snapshot
            .replace_scan_result
        )

        local_music_runtime.result_cleared.connect(
            self.spotify_local_candidate_snapshot
            .clear
        )

        existing_local_result = (
            local_music_runtime.latest_result
        )

        if existing_local_result is not None:
            self.spotify_local_candidate_snapshot.replace_scan_result(
                existing_local_result
            )

        self.spotify_playlist_service = (
            SpotifyPlaylistService(
                self.spotify_session_manager
            )
        )

        self.spotify_liked_songs_service = (
            SpotifyLikedSongsService(
                self.spotify_session_manager
            )
        )

        self.spotify_resolved_playlist_service = (
            SpotifyResolvedPlaylistService(
                self.spotify_playlist_service,
                candidate_provider=(
                    self._spotify_local_candidates
                ),
            )
        )

        spotify_playlist_service = (
            self.spotify_playlist_service
        )

        spotify_resolved_playlist_service = (
            self.spotify_resolved_playlist_service
        )

        spotify_liked_songs_service = (
            self.spotify_liked_songs_service
        )

        self.spotify_liked_songs_runtime = (
            SpotifyQtLikedSongsRuntime(
                (
                    lambda service=spotify_liked_songs_service:
                    service
                ),
                parent=self,
            )
        )

        self.spotify_playlist_runtime = (
            SpotifyQtPlaylistRuntime(
                (
                    lambda service=spotify_playlist_service:
                    service
                ),
                (
                    lambda service=spotify_resolved_playlist_service:
                    service
                ),
                parent=self,
            )
        )

        self.spotify_page = SpotifyPage(
            search_runtime=(
                self.spotify_search_runtime
            ),
            playlist_runtime=(
                self.spotify_playlist_runtime
            ),
            liked_songs_runtime=(
                self.spotify_liked_songs_runtime
            ),
            theme_manager=(
                self.theme_manager
            ),
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

        self.pages.addWidget(
            self.spotify_page
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

        self.spotify_button.clicked.connect(
            lambda: self.switch_page(5)
        )

        self.settings_button.clicked.connect(
            lambda: self.switch_page(3)
        )

        self.about_button.clicked.connect(
            lambda: self.switch_page(4)
        )

    def set_update_quit_callback(
        self,
        callback,
    ):
        self.settings_page.set_update_quit_callback(
            callback
        )

    def set_media_hotkey_reload_callback(
        self,
        callback,
    ):
        self.settings_page.set_media_hotkey_reload_callback(
            callback
        )

    def restore_spotify_connection(
        self,
    ) -> None:
        self.settings_page.restore_spotify_connection()

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

    def refresh_dashboard_quick_access(self):
        refresh_quick_access = getattr(
            self.dashboard_page,
            "refresh_quick_access_buttons",
            None,
        )

        if callable(refresh_quick_access):
            refresh_quick_access(force=True)

    def apply_presence_preset_from_dashboard(
        self,
        preset_id: str,
    ):
        preset = self.dashboard_page.presence_preset_store.get(
            preset_id
        )

        if preset is None:
            refresh_quick_access = getattr(
                self.dashboard_page,
                "refresh_quick_access_buttons",
                None,
            )

            if callable(refresh_quick_access):
                refresh_quick_access(force=True)

            return

        presence_mode = preset.to_presence_mode()
        self.presence_controller.apply_mode(
            presence_mode
        )

        self.presence_page.load_active_mode()
        self.presence_page.refresh_preset_box(
            preset.preset_id
        )
        self.dashboard_page.refresh_quick_access_buttons(
            force=True
        )
        self.refresh_discord_status()

    def saved_page_index(
        self,
    ) -> int:
        raw_index = (
            self.settings_page.store.value(
                LAST_PAGE_SETTING_KEY,
                DEFAULT_PAGE_INDEX,
            )
        )

        invalid_saved_value = False

        try:
            page_index = int(
                raw_index
            )
        except (
            TypeError,
            ValueError,
        ):
            page_index = (
                DEFAULT_PAGE_INDEX
            )
            invalid_saved_value = True

        if not (
            0
            <= page_index
            < self.pages.count()
        ):
            page_index = (
                DEFAULT_PAGE_INDEX
            )
            invalid_saved_value = True

        if invalid_saved_value:
            self.settings_page.store.setValue(
                LAST_PAGE_SETTING_KEY,
                page_index,
            )

            self.settings_page.store.sync()

        return page_index

    def restore_last_page(
        self,
    ):
        self.switch_page(
            self.saved_page_index(),
            remember=False,
        )

    def switch_page(
        self,
        page_index: int,
        remember: bool = True,
    ):
        try:
            page_index = int(
                page_index
            )
        except (
            TypeError,
            ValueError,
        ):
            page_index = (
                DEFAULT_PAGE_INDEX
            )

        if not (
            0
            <= page_index
            < self.pages.count()
        ):
            page_index = (
                DEFAULT_PAGE_INDEX
            )

        self.pages.setCurrentIndex(
            page_index
        )

        if page_index == 5:
            spotify_page = getattr(
                self,
                "spotify_page",
                None,
            )

            activate_spotify = getattr(
                spotify_page,
                "activate",
                None,
            )

            if callable(
                activate_spotify
            ):
                activate_spotify()

        navigation_page_indexes = getattr(
            self,
            "navigation_page_indexes",
            list(
                range(
                    len(
                        self.navigation_buttons
                    )
                )
            ),
        )

        for (
            button,
            navigation_page_index,
        ) in zip(
            self.navigation_buttons,
            navigation_page_indexes,
        ):
            button.setChecked(
                navigation_page_index
                == page_index
            )

        if remember:
            self.settings_page.store.setValue(
                LAST_PAGE_SETTING_KEY,
                page_index,
            )

            self.settings_page.store.sync()

        if page_index == 0:
            refresh_quick_access = getattr(
                self.dashboard_page,
                "refresh_quick_access_buttons",
                None,
            )

            if callable(
                refresh_quick_access
            ):
                refresh_quick_access(
                    force=True
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
    def apply_atmosphere(
        self,
        atmosphere: dict,
    ):
        was_active = self.atmosphere_is_active()

        self.atmosphere_layer.set_atmosphere(
            atmosphere
        )
        self.update_atmosphere_geometry()

        is_active = self.atmosphere_is_active()

        if was_active != is_active:
            self.apply_theme(
                self.theme_manager.theme()
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

        atmosphere_active = self.atmosphere_is_active()
        root_background = (
            "transparent"
            if atmosphere_active
            else theme["background"]
        )
        pages_background = root_background
        sidebar_background = (
            self._with_alpha(
                theme["sidebar"],
                0.80,
            )
            if atmosphere_active
            else theme["sidebar"]
        )
        panel_background = (
            self._with_alpha(
                theme["card"],
                0.66,
            )
            if atmosphere_active
            else theme["card"]
        )
        panel_alt_background = (
            self._with_alpha(
                theme["card_alt"],
                0.72,
            )
            if atmosphere_active
            else theme["card_alt"]
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
            QMainWindow {{
                background: {theme["background"]};
            }}

            QWidget#root {{
                background: {root_background};
            }}

            QFrame#sidebar {{
                background: {sidebar_background};
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
                background: {panel_background};
                border: 1px solid {theme["border"]};
            }}

            QPushButton#navigationButton:checked {{
                background: {panel_alt_background};
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
                background: {panel_background};
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
                background: {panel_alt_background};
                border: 1px solid {theme["border"]};
                border-radius: 8px;
                font-size: 8px;
                font-weight: 700;
            }}

            QPushButton#sidebarThemeButton:hover {{
                border: 1px solid {theme["accent"]};
            }}

            QStackedWidget#pages {{
                background: {pages_background};
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

        self.dashboard_page.apply_presence_preset_requested.connect(
            self.apply_presence_preset_from_dashboard
        )
        self.presence_page.presets_changed.connect(
            self.refresh_dashboard_quick_access
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

        self.theme_manager.atmosphere_changed.connect(
            self.apply_atmosphere
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
        self.dashboard_page.restore_cached_song_artwork(
            song
        )

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

        settings_page = getattr(
            self,
            "settings_page",
            None,
        )

        if settings_page is not None:
            shutdown_local_music = getattr(
                settings_page,
                "shutdown_local_music",
                None,
            )

            if callable(
                shutdown_local_music
            ):
                try:
                    shutdown_local_music()
                except Exception:
                    pass

        for spotify_runtime_name in (
            "spotify_playlist_runtime",
            "spotify_liked_songs_runtime",
            "spotify_search_runtime",
        ):
            feature_runtime = getattr(
                self,
                spotify_runtime_name,
                None,
            )

            if feature_runtime is None:
                continue

            shutdown_feature_runtime = getattr(
                feature_runtime,
                "shutdown",
                None,
            )

            if callable(
                shutdown_feature_runtime
            ):
                try:
                    shutdown_feature_runtime()
                except Exception:
                    pass

        spotify_runtime = getattr(
            self,
            "spotify_connection_runtime",
            None,
        )

        if spotify_runtime is not None:
            shutdown_spotify = getattr(
                spotify_runtime,
                "shutdown",
                None,
            )

            if callable(
                shutdown_spotify
            ):
                try:
                    shutdown_spotify()
                except Exception:
                    pass

        self.discord.close()

    def closeEvent(
        self,
        event,
    ):
        self.shutdown()

        super().closeEvent(
            event
        )
