from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QProgressBar,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class DashboardPage(QWidget):

    def __init__(self):
        super().__init__()

        self.build_ui()

    def build_ui(self):

        root = QVBoxLayout(self)
        root.setContentsMargins(30, 30, 30, 30)
        root.setSpacing(25)

        # --------------------------
        # Title
        # --------------------------

        title = QLabel("Dashboard")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setStyleSheet("color:white;")

        root.addWidget(title)

        # --------------------------
        # Now Playing Card
        # --------------------------

        card = QFrame()
        card.setObjectName("card")

        cardLayout = QHBoxLayout(card)
        cardLayout.setContentsMargins(25, 25, 25, 25)
        cardLayout.setSpacing(30)

        # Album artwork

        self.artwork = QLabel("Album\nArtwork")
        self.artwork.setFixedSize(220, 220)
        self.artwork.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.artwork.setObjectName("artwork")

        cardLayout.addWidget(self.artwork)

        # Song information

        infoLayout = QVBoxLayout()
        infoLayout.setSpacing(10)

        self.songTitle = QLabel("No song playing")
        self.songTitle.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        self.songTitle.setStyleSheet("color:white;")

        self.artist = QLabel("Waiting for Spotify...")
        self.artist.setStyleSheet("""
            color:#BBBBBB;
            font-size:15px;
        """)

        self.album = QLabel("Album")
        self.album.setStyleSheet("""
            color:#888888;
            font-size:14px;
        """)

        infoLayout.addStretch()
        infoLayout.addWidget(self.songTitle)
        infoLayout.addWidget(self.artist)
        infoLayout.addWidget(self.album)
        infoLayout.addSpacing(20)

        # Progress Bar

        self.progress = QProgressBar()
        self.progress.setValue(35)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)

        self.progress.setStyleSheet("""
            QProgressBar{
                background:#2d2d39;
                border-radius:4px;
            }

            QProgressBar::chunk{
                background:#ff8fcf;
                border-radius:4px;
            }
        """)

        infoLayout.addWidget(self.progress)

        # Times

        times = QHBoxLayout()

        self.currentTime = QLabel("0:00")
        self.totalTime = QLabel("0:00")

        self.currentTime.setStyleSheet("color:#aaaaaa;")
        self.totalTime.setStyleSheet("color:#aaaaaa;")

        times.addWidget(self.currentTime)
        times.addStretch()
        times.addWidget(self.totalTime)

        infoLayout.addLayout(times)

        infoLayout.addStretch()

        cardLayout.addLayout(infoLayout)

        root.addWidget(card)

        # --------------------------
        # Status Cards
        # --------------------------

        statusLayout = QHBoxLayout()
        statusLayout.setSpacing(20)

        statusLayout.addWidget(self.makeStatusCard("Discord", "Waiting"))
        statusLayout.addWidget(self.makeStatusCard("Spotify", "Waiting"))
        statusLayout.addWidget(self.makeStatusCard("Library", "Not Scanned"))

        root.addLayout(statusLayout)

        root.addStretch()

        self.setStyleSheet("""
            QFrame#card{
                background:#252533;
                border-radius:18px;
            }

            QLabel#artwork{
                background:#313140;
                border-radius:15px;
                color:#888888;
                font-size:15px;
            }
        """)

    def makeStatusCard(self, title, value):

        card = QFrame()
        card.setStyleSheet("""
            QFrame{
                background:#252533;
                border-radius:14px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)

        label = QLabel(title)
        label.setStyleSheet("""
            color:#aaaaaa;
            font-size:13px;
        """)

        status = QLabel(value)
        status.setStyleSheet("""
            color:white;
            font-size:16px;
            font-weight:bold;
        """)

        layout.addWidget(label)
        layout.addWidget(status)

        return card