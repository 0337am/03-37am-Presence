from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
YUNO_IMAGE_PATH = PROJECT_ROOT / "assets" / "yuno.png"


class AboutPage(QWidget):
    def __init__(self):
        super().__init__()
        self.build_ui()

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 30, 30, 30)
        root.setSpacing(18)

        title = QLabel("About")
        title.setObjectName("aboutTitle")

        subtitle = QLabel(
            "A Yuno-themed Spotify and Discord companion"
        )
        subtitle.setObjectName("aboutSubtitle")

        root.addWidget(title)
        root.addWidget(subtitle)

        card = QFrame()
        card.setObjectName("aboutCard")

        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(25)

        portrait = QLabel()
        portrait.setObjectName("aboutPortrait")
        portrait.setFixedSize(190, 190)
        portrait.setAlignment(Qt.AlignmentFlag.AlignCenter)

        pixmap = QPixmap(str(YUNO_IMAGE_PATH))

        if pixmap.isNull():
            portrait.setText("Yuno image\nnot found")
        else:
            portrait.setPixmap(
                pixmap.scaled(
                    180,
                    180,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        information = QVBoxLayout()
        information.setSpacing(8)

        app_name = QLabel("03:37am Presence ♡")
        app_name.setObjectName("appName")

        build = QLabel("Development build")
        build.setObjectName("buildLabel")

        description = QLabel(
            "A desktop application that displays Spotify and "
            "local-file playback in the dashboard and through "
            "Discord Rich Presence."
        )
        description.setObjectName("aboutDescription")
        description.setWordWrap(True)

        features = QLabel(
            "♡ Spotify-only media detection\n"
            "♡ Spotify local-file support\n"
            "♡ Native album artwork\n"
            "♡ Dynamic Discord artwork\n"
            "♡ Session listening history\n"
            "♡ Yuno-inspired interface"
        )
        features.setObjectName("featureList")

        open_folder_button = QPushButton("Open project folder")
        open_folder_button.setObjectName("openFolderButton")
        open_folder_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        open_folder_button.clicked.connect(
            self.open_project_folder
        )

        information.addWidget(app_name)
        information.addWidget(build)
        information.addSpacing(5)
        information.addWidget(description)
        information.addSpacing(8)
        information.addWidget(features)
        information.addStretch()
        information.addWidget(
            open_folder_button,
            alignment=Qt.AlignmentFlag.AlignLeft,
        )

        card_layout.addWidget(portrait)
        card_layout.addLayout(information, stretch=1)

        footer = QLabel(
            "Made with pink pixels and far too much music. ♡"
        )
        footer.setObjectName("aboutFooter")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        root.addWidget(card)
        root.addWidget(footer)
        root.addStretch()

        self.setStyleSheet(
            """
            QLabel#aboutTitle {
                color: #fff0f7;
                font-size: 28px;
                font-weight: bold;
            }

            QLabel#aboutSubtitle {
                color: #b96f94;
                font-size: 13px;
            }

            QFrame#aboutCard {
                background: #352747;
                border: 1px solid #5c4777;
                border-radius: 18px;
            }

            QLabel#aboutPortrait {
                color: #ff9dca;
                background: #120710;
                border: 2px solid #ff6caf;
                border-radius: 18px;
            }

            QLabel#appName {
                color: #fff5fb;
                font-size: 24px;
                font-weight: bold;
            }

            QLabel#buildLabel {
                color: #ff8fcf;
                font-size: 12px;
                font-weight: bold;
            }

            QLabel#aboutDescription {
                color: #d8c9e8;
                font-size: 14px;
            }

            QLabel#featureList {
                color: #c7b4d8;
                font-size: 14px;
            }

            QLabel#aboutFooter {
                color: #9f607e;
                font-size: 12px;
                padding: 8px;
            }

            QPushButton#openFolderButton {
                color: #ffeaf4;
                background: #6d234e;
                border: 1px solid #ff79b9;
                border-radius: 10px;
                padding: 9px 16px;
                font-weight: bold;
            }

            QPushButton#openFolderButton:hover {
                background: #873062;
            }
            """
        )

    def open_project_folder(self):
        QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(PROJECT_ROOT))
        )