from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from src.ui.dashboard import DashboardPage

class Page(QWidget):
    def __init__(self, title):
        super().__init__()

        layout = QVBoxLayout(self)

        titleLabel = QLabel(title)
        titleLabel.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        titleLabel.setStyleSheet("color: white;")

        layout.addWidget(titleLabel)
        layout.addStretch()


class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        title = QLabel("Dashboard")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setStyleSheet("color:white;")

        card = QFrame()
        card.setStyleSheet("""
            QFrame{
                background:#242430;
                border-radius:15px;
            }
        """)

        cardLayout = QVBoxLayout(card)

        artwork = QLabel("Album Artwork")
        artwork.setFixedSize(220,220)
        artwork.setAlignment(Qt.AlignmentFlag.AlignCenter)
        artwork.setStyleSheet("""
            background:#31313F;
            border-radius:12px;
            color:#aaaaaa;
        """)

        song = QLabel("No song playing")
        song.setFont(QFont("Segoe UI",18,QFont.Weight.Bold))
        song.setStyleSheet("color:white;")

        artist = QLabel("Waiting for Spotify...")
        artist.setStyleSheet("color:#bbbbbb;")

        cardLayout.addWidget(artwork)
        cardLayout.addSpacing(15)
        cardLayout.addWidget(song)
        cardLayout.addWidget(artist)

        layout.addWidget(title)
        layout.addWidget(card)
        layout.addStretch()


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("03:37am Presence")
        self.resize(1200, 720)

        root = QWidget()
        self.setCentralWidget(root)

        layout = QHBoxLayout(root)
        layout.setContentsMargins(0,0,0,0)

        # Sidebar

        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("""
            background:#1b1b26;
        """)

        sideLayout = QVBoxLayout(sidebar)

        logo = QLabel("03:37am")
        logo.setFont(QFont("Segoe UI",20,QFont.Weight.Bold))
        logo.setStyleSheet("color:#ff8fcf;padding:20px;")

        sideLayout.addWidget(logo)

        self.dashboardBtn = QPushButton("🏠 Dashboard")
        self.libraryBtn = QPushButton("🎵 Library")
        self.settingsBtn = QPushButton("⚙ Settings")
        self.aboutBtn = QPushButton("ℹ About")

        buttons = [
            self.dashboardBtn,
            self.libraryBtn,
            self.settingsBtn,
            self.aboutBtn
        ]

        for button in buttons:
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setMinimumHeight(45)
            button.setStyleSheet("""
                QPushButton{
                    color:white;
                    background:transparent;
                    border:none;
                    text-align:left;
                    padding-left:20px;
                    font-size:15px;
                }

                QPushButton:hover{
                    background:#303042;
                }
            """)
            sideLayout.addWidget(button)

        sideLayout.addStretch()

        # Pages

        self.pages = QStackedWidget()

        self.pages.addWidget(DashboardPage())
        self.pages.addWidget(Page("Library"))
        self.pages.addWidget(Page("Settings"))
        self.pages.addWidget(Page("About"))

        layout.addWidget(sidebar)
        layout.addWidget(self.pages)

        # Connections

        self.dashboardBtn.clicked.connect(
            lambda: self.pages.setCurrentIndex(0)
        )

        self.libraryBtn.clicked.connect(
            lambda: self.pages.setCurrentIndex(1)
        )

        self.settingsBtn.clicked.connect(
            lambda: self.pages.setCurrentIndex(2)
        )

        self.aboutBtn.clicked.connect(
            lambda: self.pages.setCurrentIndex(3)
        )

        self.setStyleSheet("""
            QMainWindow{
                background:#20202B;
            }

            QWidget{
                background:#20202B;
            }
        """)