from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QFrame,
)
from PyQt6.QtCore import (
    Qt,
    QTimer,
    pyqtSlot,
)
from PyQt6.QtGui import QFont

from src.discord.presence import DiscordPresence
from src.ui.dashboard import DashboardPage


class Page(QWidget):

    def __init__(self, title):
        super().__init__()

        layout = QVBoxLayout(self)

        title_label = QLabel(title)
        title_label.setFont(
            QFont(
                "Segoe UI",
                22,
                QFont.Weight.Bold,
            )
        )
        title_label.setStyleSheet(
            "color: white;"
        )

        layout.addWidget(title_label)
        layout.addStretch()


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self._shutting_down = False

        self.setWindowTitle("03:37am Presence")
        self.resize(1200, 720)

        self.discord = DiscordPresence()

        root = QWidget()
        self.setCentralWidget(root)

        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("""
            background: #1b1b26;
        """)

        side_layout = QVBoxLayout(sidebar)

        logo = QLabel("03:37am")
        logo.setFont(
            QFont(
                "Segoe UI",
                20,
                QFont.Weight.Bold,
            )
        )
        logo.setStyleSheet(
            "color:#ff8fcf; padding:20px;"
        )

        side_layout.addWidget(logo)

        self.dashboard_button = QPushButton(
            "🏠 Dashboard"
        )
        self.library_button = QPushButton(
            "🎵 Library"
        )
        self.settings_button = QPushButton(
            "⚙ Settings"
        )
        self.about_button = QPushButton(
            "ℹ About"
        )

        buttons = [
            self.dashboard_button,
            self.library_button,
            self.settings_button,
            self.about_button,
        ]

        for button in buttons:
            button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )
            button.setMinimumHeight(45)

            button.setStyleSheet("""
                QPushButton {
                    color: white;
                    background: transparent;
                    border: none;
                    text-align: left;
                    padding-left: 20px;
                    font-size: 15px;
                }

                QPushButton:hover {
                    background: #303042;
                }
            """)

            side_layout.addWidget(button)

        side_layout.addStretch()

        # Pages
        self.pages = QStackedWidget()

        self.dashboard_page = DashboardPage()
        self.library_page = Page("Library")
        self.settings_page = Page("Settings")
        self.about_page = Page("About")

        self.pages.addWidget(
            self.dashboard_page
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

        layout.addWidget(sidebar)
        layout.addWidget(self.pages)

        # Navigation
        self.dashboard_button.clicked.connect(
            lambda: self.pages.setCurrentIndex(0)
        )

        self.library_button.clicked.connect(
            lambda: self.pages.setCurrentIndex(1)
        )

        self.settings_button.clicked.connect(
            lambda: self.pages.setCurrentIndex(2)
        )

        self.about_button.clicked.connect(
            lambda: self.pages.setCurrentIndex(3)
        )

        self.setStyleSheet("""
            QMainWindow {
                background: #20202B;
            }

            QWidget {
                background: #20202B;
            }
        """)

        self.connect_services()

    def connect_services(self):
        """
        Connects the dashboard's existing media worker to Discord.

        This reuses the same Song object already powering the dashboard,
        so Windows Media is not queried a second time.
        """

        self.dashboard_page.media_worker.song_ready.connect(
            self.handle_song_update
        )

        self.discord.connect()

        self.discord_status_timer = QTimer(self)
        self.discord_status_timer.timeout.connect(
            self.refresh_discord_status
        )
        self.discord_status_timer.start(500)

        self.refresh_discord_status()

        app = QApplication.instance()

        if app is not None:
            app.aboutToQuit.connect(
                self.shutdown
            )

    @pyqtSlot(object)
    def handle_song_update(self, song):
        self.discord.update_song(song)

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

        timer = getattr(
            self,
            "discord_status_timer",
            None,
        )

        if timer is not None:
            timer.stop()

        self.discord.close()

    def closeEvent(self, event):
        self.shutdown()
        super().closeEvent(event)