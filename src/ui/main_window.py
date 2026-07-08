from pathlib import Path

from PyQt6.QtCore import (
    Qt,
    QTimer,
    pyqtSlot,
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
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
from src.ui.about import AboutPage
from src.ui.dashboard import DashboardPage
from src.ui.library import LibraryPage
from src.ui.presence_page import PresencePage
from src.ui.settings import SettingsPage
from src.ui.theme import ThemeManager


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

        self.setMinimumHeight(46)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            16,
            0,
            14,
            0,
        )
        layout.setSpacing(10)

        icon_label = QLabel(
            icon_text
        )
        icon_label.setObjectName(
            "navigationEmoji"
        )
        icon_label.setFixedWidth(28)

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
        self.resize(1200, 720)
        self.setMinimumSize(
            950,
            650,
        )

        self.discord = (
            ExtendedDiscordPresence()
        )

        self.presence_controller = (
            PresenceController(
                self.discord
            )
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
        self.sidebar = QFrame()
        self.sidebar.setObjectName(
            "sidebar"
        )
        self.sidebar.setFixedWidth(245)

        sidebar_layout = QVBoxLayout(
            self.sidebar
        )
        sidebar_layout.setContentsMargins(
            18,
            20,
            18,
            20,
        )
        sidebar_layout.setSpacing(8)

        self.yuno_picture = QLabel()
        self.yuno_picture.setObjectName(
            "yunoPicture"
        )
        self.yuno_picture.setFixedSize(
            205,
            205,
        )
        self.yuno_picture.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        sidebar_layout.addWidget(
            self.yuno_picture,
            alignment=(
                Qt.AlignmentFlag.AlignCenter
            ),
        )

        self.logo = QLabel(
            "03:37am \u2661"
        )
        self.logo.setObjectName("logo")
        self.logo.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.subtitle = QLabel(
            "Yuno Presence"
        )
        self.subtitle.setObjectName(
            "subtitle"
        )
        self.subtitle.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        sidebar_layout.addWidget(
            self.logo
        )
        sidebar_layout.addWidget(
            self.subtitle
        )
        sidebar_layout.addSpacing(18)

        self.dashboard_button = NavigationButton(
            "\u2661",
            "Dashboard",
        )

        self.presence_button = NavigationButton(
            "\u25C8",
            "Presence",
        )

        self.library_button = NavigationButton(
            "\u266B",
            "Library",
        )

        self.settings_button = NavigationButton(
            "\u2699",
            "Settings",
        )

        self.about_button = NavigationButton(
            "\u24D8",
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

        self.tagline = QLabel(
            "Love is the strongest signal. \u2661"
        )
        self.tagline.setObjectName(
            "tagline"
        )
        self.tagline.setWordWrap(True)

        self.tagline.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        sidebar_layout.addWidget(
            self.tagline
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

    @pyqtSlot(dict)
    def apply_theme(
        self,
        theme: dict,
    ):
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
                border: 2px solid {theme["accent"]};
                border-radius: 18px;
            }}

            QLabel#logo {{
                color: {theme["accent"]};
                font-size: 28px;
                font-weight: 700;
                padding-top: 5px;
            }}

            QLabel#subtitle {{
                color: {theme["muted"]};
                font-size: 12px;
                letter-spacing: 1px;
            }}

            QLabel#tagline {{
                color: {theme["muted"]};
                font-size: 11px;
                padding: 8px;
            }}

            QPushButton#navigationButton {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 12px;
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
                font-size: 15px;
            }}

            QLabel#navigationText {{
                font-size: 14px;
                font-weight: 600;
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
            bool(
                branding.get(
                    "show_footer",
                    True,
                )
            )
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
                195,
                195,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def connect_services(self):
        self.dashboard_page.media_worker.song_ready.connect(
            self.handle_song_update
        )

        self.settings_page.show_portrait_changed.connect(
            self.apply_show_portrait
        )

        self.settings_page.always_on_top_changed.connect(
            self.apply_always_on_top
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

        self.discord.close()

    def closeEvent(
        self,
        event,
    ):
        self.shutdown()

        super().closeEvent(
            event
        )