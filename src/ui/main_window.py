from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSlot
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

from src.discord.extended_presence import ExtendedDiscordPresence
from src.discord.presence_controller import PresenceController
from src.ui.about import AboutPage
from src.ui.dashboard import DashboardPage
from src.ui.library import LibraryPage
from src.ui.presence_page import PresencePage
from src.ui.settings import SettingsPage


PROJECT_ROOT = Path(__file__).resolve().parents[2]
YUNO_IMAGE_PATH = PROJECT_ROOT / "assets" / "yuno.png"


class NavigationButton(QPushButton):
    def __init__(self, emoji: str, text: str):
        super().__init__()

        self.setObjectName("navigationButton")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(46)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 14, 0)
        layout.setSpacing(10)

        emoji_label = QLabel(emoji)
        emoji_label.setObjectName("navigationEmoji")
        emoji_label.setFixedWidth(28)
        emoji_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        text_label = QLabel(text)
        text_label.setObjectName("navigationText")
        text_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
        )

        emoji_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )
        text_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )

        layout.addWidget(emoji_label)
        layout.addWidget(text_label, stretch=1)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self._shutting_down = False

        self.setWindowTitle("03:37am Presence")
        self.resize(1200, 720)
        self.setMinimumSize(950, 650)

        self.discord = ExtendedDiscordPresence()
        self.presence_controller = PresenceController(
            self.discord
        )

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)

        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.build_sidebar(main_layout)
        self.build_pages(main_layout)
        self.apply_theme()
        self.connect_services()
        self.apply_saved_settings()
        self.switch_page(0)

    def build_sidebar(self, main_layout):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(245)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(18, 20, 18, 20)
        sidebar_layout.setSpacing(8)

        self.yuno_picture = QLabel()
        self.yuno_picture.setObjectName("yunoPicture")
        self.yuno_picture.setFixedSize(205, 205)
        self.yuno_picture.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        yuno_pixmap = QPixmap(str(YUNO_IMAGE_PATH))

        if yuno_pixmap.isNull():
            self.yuno_picture.setText(
                "Yuno image\nnot found"
            )
        else:
            self.yuno_picture.setPixmap(
                yuno_pixmap.scaled(
                    195,
                    195,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        sidebar_layout.addWidget(
            self.yuno_picture,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )

        logo = QLabel("03:37am ♡")
        logo.setObjectName("logo")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Yuno Presence")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sidebar_layout.addWidget(logo)
        sidebar_layout.addWidget(subtitle)
        sidebar_layout.addSpacing(18)

        self.dashboard_button = NavigationButton(
            "♡",
            "Dashboard",
        )
        self.presence_button = NavigationButton(
            "?",
            "Presence",
        )
        self.library_button = NavigationButton(
            "♫",
            "Library",
        )
        self.settings_button = NavigationButton(
            "⚙",
            "Settings",
        )
        self.about_button = NavigationButton(
            "ⓘ",
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
            sidebar_layout.addWidget(button)

        sidebar_layout.addStretch()

        tagline = QLabel(
            "Love is the strongest signal. ♡"
        )
        tagline.setObjectName("tagline")
        tagline.setWordWrap(True)
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sidebar_layout.addWidget(tagline)

        main_layout.addWidget(sidebar)

    def build_pages(self, main_layout):
        self.pages = QStackedWidget()
        self.pages.setObjectName("pages")

        self.dashboard_page = DashboardPage()
        self.presence_page = PresencePage(
            self.presence_controller
        )
        self.library_page = LibraryPage()
        self.settings_page = SettingsPage()
        self.about_page = AboutPage()

        self.pages.addWidget(self.dashboard_page)
        self.pages.addWidget(self.presence_page)
        self.pages.addWidget(self.library_page)
        self.pages.addWidget(self.settings_page)
        self.pages.addWidget(self.about_page)

        main_layout.addWidget(self.pages, stretch=1)

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

    def switch_page(self, page_index: int):
        self.pages.setCurrentIndex(page_index)

        for index, button in enumerate(
            self.navigation_buttons
        ):
            button.setChecked(index == page_index)

    def apply_theme(self):
        self.setStyleSheet(
            """
            QMainWindow,
            QWidget#root {
                background: #140812;
            }

            QFrame#sidebar {
                background: #210b1a;
                border-right: 1px solid #6a284d;
            }

            QLabel#yunoPicture {
                background: #090307;
                color: #ff9dca;
                border: 2px solid #ff6caf;
                border-radius: 18px;
            }

            QLabel#logo {
                color: #ff8fc5;
                font-size: 28px;
                font-weight: bold;
                padding-top: 5px;
            }

            QLabel#subtitle {
                color: #b96f94;
                font-size: 12px;
                letter-spacing: 1px;
            }

            QLabel#tagline {
                color: #9f607e;
                font-size: 11px;
                padding: 8px;
            }

            QPushButton#navigationButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 12px;
            }

            QPushButton#navigationButton:hover {
                background: #3b142c;
                border: 1px solid #70284f;
            }

            QPushButton#navigationButton:checked {
                background: #6d234e;
                border: 1px solid #ff79b9;
            }

            QLabel#navigationEmoji {
                color: #f8dce9;
                background: transparent;
                font-size: 15px;
            }

            QLabel#navigationText {
                color: #f8dce9;
                background: transparent;
                font-size: 14px;
                font-weight: 600;
            }

            QStackedWidget#pages {
                background: #140812;
            }
            """
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

        self.discord.connect()

        QTimer.singleShot(
            0,
            self.presence_controller.apply_saved_mode,
        )

        self.discord_status_timer = QTimer(self)
        self.discord_status_timer.timeout.connect(
            self.refresh_discord_status
        )
        self.discord_status_timer.start(500)

        self.refresh_discord_status()

        app = QApplication.instance()

        if app is not None:
            app.aboutToQuit.connect(self.shutdown)

    def apply_saved_settings(self):
        self.apply_show_portrait(
            self.settings_page.show_yuno_portrait
        )
        self.apply_always_on_top(
            self.settings_page.always_on_top
        )

    @pyqtSlot(object)
    def handle_song_update(self, song):
        self.presence_controller.handle_song(song)
        self.library_page.add_song(song)

    @pyqtSlot(bool)
    def apply_show_portrait(self, enabled: bool):
        self.yuno_picture.setVisible(enabled)

    @pyqtSlot(bool)
    def apply_always_on_top(self, enabled: bool):
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
            status_label.setText("Connected")
        elif self.discord.is_running:
            status_label.setText(
                "Waiting for Discord"
            )
        else:
            status_label.setText("Stopped")

    def shutdown(self):
        if self._shutting_down:
            return

        self._shutting_down = True
        self.discord_status_timer.stop()
        self.discord.close()

    def closeEvent(self, event):
        self.shutdown()
        super().closeEvent(event)