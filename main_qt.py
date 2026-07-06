import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFrame
)
from PySide6.QtCore import Qt


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("03:37am Presence")
        self.resize(1100, 700)

        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("""
            background:#23182d;
            border-right:1px solid #3d2d49;
        """)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20,20,20,20)

        title = QLabel("03:37am")
        title.setStyleSheet("""
            color:#ff7eb6;
            font-size:28px;
            font-weight:bold;
        """)
        sidebar_layout.addWidget(title)

        subtitle = QLabel("Presence")
        subtitle.setStyleSheet("""
            color:white;
            font-size:18px;
        """)
        sidebar_layout.addWidget(subtitle)

        sidebar_layout.addSpacing(30)

        for text in ["🏠 Dashboard", "🎵 Library", "⚙ Settings", "ℹ About"]:
            button = QPushButton(text)
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet("""
                QPushButton{
                    background:#2d2037;
                    color:white;
                    border:none;
                    border-radius:10px;
                    padding:12px;
                    text-align:left;
                }

                QPushButton:hover{
                    background:#ff7eb6;
                }
            """)
            sidebar_layout.addWidget(button)

        sidebar_layout.addStretch()

        # Main area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(40,40,40,40)

        artwork = QFrame()
        artwork.setFixedSize(280,280)
        artwork.setStyleSheet("""
            background:#2a2035;
            border-radius:20px;
            border:2px solid #ff7eb6;
        """)

        artwork_layout = QVBoxLayout(artwork)

        cover = QLabel("Album Artwork")
        cover.setAlignment(Qt.AlignCenter)
        cover.setStyleSheet("""
            color:#888;
            font-size:20px;
        """)

        artwork_layout.addWidget(cover)

        content_layout.addWidget(artwork, alignment=Qt.AlignCenter)

        song = QLabel("Waiting for Spotify...")
        song.setAlignment(Qt.AlignCenter)
        song.setStyleSheet("""
            color:white;
            font-size:24px;
            font-weight:bold;
        """)

        content_layout.addWidget(song)

        artist = QLabel("03:37am Presence")
        artist.setAlignment(Qt.AlignCenter)
        artist.setStyleSheet("""
            color:#ff7eb6;
            font-size:18px;
        """)

        content_layout.addWidget(artist)

        content_layout.addStretch()

        layout.addWidget(sidebar)
        layout.addWidget(content)

        self.setStyleSheet("""
            QMainWindow{
                background:#1d1525;
            }
        """)


app = QApplication(sys.argv)

window = MainWindow()
window.show()

sys.exit(app.exec())