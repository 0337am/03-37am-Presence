from pathlib import Path

from PyQt6.QtCore import (
    Qt,
    QUrl,
    pyqtSlot,
)
from PyQt6.QtGui import (
    QDesktopServices,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.ui.theme import ThemeManager
from src.version import DISPLAY_VERSION


PROJECT_ROOT = Path(__file__).resolve().parents[2]
YUNO_IMAGE_PATH = (
    PROJECT_ROOT
    / "assets"
    / "yuno.png"
)


class AboutPage(QWidget):
    def __init__(
        self,
        theme_manager=None,
    ):
        super().__init__()

        self.setObjectName("aboutRoot")

        self.theme_manager = (
            theme_manager
            or ThemeManager(self)
        )

        self._portrait_size = 150
        self._branding_image_path = ""

        self.build_ui()

        self.theme_manager.theme_changed.connect(
            self.apply_theme
        )
        self.theme_manager.branding_changed.connect(
            self.apply_branding
        )

        self.apply_branding(
            self.theme_manager.branding()
        )
        self.apply_theme(
            self.theme_manager.theme()
        )

    def build_ui(self):
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(
            20,
            18,
            20,
            18,
        )
        self.root_layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(10)

        heading_group = QVBoxLayout()
        heading_group.setSpacing(1)

        self.page_title = QLabel("About")
        self.page_title.setObjectName(
            "aboutTitle"
        )

        self.page_subtitle = QLabel(
            "A customizable Spotify and Discord companion"
        )
        self.page_subtitle.setObjectName(
            "aboutSubtitle"
        )

        heading_group.addWidget(
            self.page_title
        )
        heading_group.addWidget(
            self.page_subtitle
        )

        self.build_badge = QLabel(
            DISPLAY_VERSION
        )
        self.build_badge.setObjectName(
            "buildBadge"
        )
        self.build_badge.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        header.addLayout(
            heading_group
        )
        header.addStretch()
        header.addWidget(
            self.build_badge,
            alignment=Qt.AlignmentFlag.AlignVCenter,
        )

        self.root_layout.addLayout(
            header
        )

        self.hero_card = QFrame()
        self.hero_card.setObjectName(
            "aboutCard"
        )

        hero_layout = QHBoxLayout(
            self.hero_card
        )
        hero_layout.setContentsMargins(
            18,
            18,
            18,
            18,
        )
        hero_layout.setSpacing(18)

        self.portrait = QLabel()
        self.portrait.setObjectName(
            "aboutPortrait"
        )
        self.portrait.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.portrait.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )

        hero_layout.addWidget(
            self.portrait,
            alignment=Qt.AlignmentFlag.AlignTop,
        )

        information = QVBoxLayout()
        information.setSpacing(6)

        self.app_name = QLabel(
            "03:37am Presence"
        )
        self.app_name.setObjectName(
            "appName"
        )
        self.app_name.setWordWrap(True)

        self.branding_subtitle = QLabel(
            "Spotify and Discord companion"
        )
        self.branding_subtitle.setObjectName(
            "brandingSubtitle"
        )
        self.branding_subtitle.setWordWrap(True)

        description = QLabel(
            "A desktop application that detects Spotify "
            "playback, displays album artwork, manages "
            "custom activities, and updates Discord "
            "Rich Presence."
        )
        description.setObjectName(
            "aboutDescription"
        )
        description.setWordWrap(True)

        information.addWidget(
            self.app_name
        )
        information.addWidget(
            self.branding_subtitle
        )
        information.addSpacing(5)
        information.addWidget(
            description
        )
        information.addStretch()

        hero_layout.addLayout(
            information,
            stretch=1,
        )

        self.root_layout.addWidget(
            self.hero_card
        )

        self.feature_row = QHBoxLayout()
        self.feature_row.setSpacing(10)

        media_card = self.make_feature_card(
            "MEDIA",
            "Spotify playback",
            "Track details, progress, "
            "local files, and artwork.",
        )

        discord_card = self.make_feature_card(
            "DISCORD",
            "Rich Presence",
            "Music and custom activity "
            "modes with dynamic images.",
        )

        vanity_card = self.make_feature_card(
            "VANITY",
            "Personal styling",
            "Branding, themes, colours, "
            "and compact layouts.",
        )

        self.feature_row.addWidget(
            media_card
        )
        self.feature_row.addWidget(
            discord_card
        )
        self.feature_row.addWidget(
            vanity_card
        )

        self.root_layout.addLayout(
            self.feature_row
        )

        self.action_card = QFrame()
        self.action_card.setObjectName(
            "actionCard"
        )

        action_layout = QHBoxLayout(
            self.action_card
        )
        action_layout.setContentsMargins(
            14,
            11,
            14,
            11,
        )
        action_layout.setSpacing(10)

        action_text = QVBoxLayout()
        action_text.setSpacing(1)

        action_title = QLabel(
            "Project files"
        )
        action_title.setObjectName(
            "actionTitle"
        )

        action_help = QLabel(
            "Open the application folder to view "
            "assets, logs, and configuration files."
        )
        action_help.setObjectName(
            "actionHelp"
        )
        action_help.setWordWrap(True)

        action_text.addWidget(
            action_title
        )
        action_text.addWidget(
            action_help
        )

        self.open_folder_button = QPushButton(
            "Open project folder"
        )
        self.open_folder_button.setObjectName(
            "openFolderButton"
        )
        self.open_folder_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.open_folder_button.clicked.connect(
            self.open_project_folder
        )

        action_layout.addLayout(
            action_text,
            stretch=1,
        )
        action_layout.addWidget(
            self.open_folder_button,
            alignment=Qt.AlignmentFlag.AlignVCenter,
        )

        self.root_layout.addWidget(
            self.action_card
        )

        self.footer_label = QLabel(
            "Made with pink pixels and far too much music."
        )
        self.footer_label.setObjectName(
            "aboutFooter"
        )
        self.footer_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.footer_label.setWordWrap(True)

        self.root_layout.addWidget(
            self.footer_label
        )
        self.root_layout.addStretch()

    def make_feature_card(
        self,
        badge_text: str,
        title_text: str,
        description_text: str,
    ) -> QFrame:
        card = QFrame()
        card.setObjectName(
            "featureCard"
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(
            13,
            12,
            13,
            12,
        )
        layout.setSpacing(5)

        badge = QLabel(
            badge_text
        )
        badge.setObjectName(
            "featureBadge"
        )

        title = QLabel(
            title_text
        )
        title.setObjectName(
            "featureTitle"
        )
        title.setWordWrap(True)

        description = QLabel(
            description_text
        )
        description.setObjectName(
            "featureDescription"
        )
        description.setWordWrap(True)

        layout.addWidget(
            badge
        )
        layout.addWidget(
            title
        )
        layout.addWidget(
            description
        )
        layout.addStretch()

        return card

    @pyqtSlot(dict)
    def apply_theme(self, theme: dict):
        compact = theme.get(
            "compact",
            True,
        )

        margin = 18 if compact else 24
        spacing = 10 if compact else 14
        title_size = 23 if compact else 27
        app_name_size = 20 if compact else 24

        self._portrait_size = (
            138 if compact else 168
        )

        self.root_layout.setContentsMargins(
            margin,
            margin,
            margin,
            margin,
        )
        self.root_layout.setSpacing(
            spacing
        )

        self.portrait.setFixedSize(
            self._portrait_size,
            self._portrait_size,
        )

        self.setStyleSheet(
            f"""
            QWidget#aboutRoot {{
                background: {theme["background"]};
            }}

            QLabel#aboutTitle {{
                color: {theme["text"]};
                font-size: {title_size}px;
                font-weight: 700;
            }}

            QLabel#aboutSubtitle {{
                color: {theme["muted"]};
                font-size: 11px;
            }}

            QLabel#buildBadge {{
                color: {theme["accent"]};
                background: {theme["card_alt"]};
                border: 1px solid {theme["border"]};
                border-radius: 9px;
                padding: 5px 10px;
                font-size: 10px;
                font-weight: 700;
            }}

            QFrame#aboutCard {{
                background: {theme["card"]};
                border: 1px solid {theme["border"]};
                border-radius: 14px;
            }}

            QLabel#aboutPortrait {{
                color: {theme["muted"]};
                background: {theme["background"]};
                border: 1px solid {theme["accent"]};
                border-radius: 12px;
            }}

            QLabel#appName {{
                color: {theme["text"]};
                font-size: {app_name_size}px;
                font-weight: 700;
            }}

            QLabel#brandingSubtitle {{
                color: {theme["accent"]};
                font-size: 11px;
                font-weight: 650;
            }}

            QLabel#aboutDescription {{
                color: {theme["muted"]};
                font-size: 11px;
                line-height: 1.4;
            }}

            QFrame#featureCard {{
                background: {theme["card_alt"]};
                border: 1px solid {theme["border"]};
                border-radius: 11px;
            }}

            QLabel#featureBadge {{
                color: {theme["accent"]};
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 1px;
            }}

            QLabel#featureTitle {{
                color: {theme["text"]};
                font-size: 12px;
                font-weight: 700;
            }}

            QLabel#featureDescription {{
                color: {theme["muted"]};
                font-size: 10px;
            }}

            QFrame#actionCard {{
                background: {theme["card_alt"]};
                border: 1px solid {theme["border"]};
                border-radius: 11px;
            }}

            QLabel#actionTitle {{
                color: {theme["text"]};
                font-size: 11px;
                font-weight: 700;
            }}

            QLabel#actionHelp {{
                color: {theme["muted"]};
                font-size: 10px;
            }}

            QPushButton#openFolderButton {{
                color: {theme["text"]};
                background: {theme["card"]};
                border: 1px solid {theme["border"]};
                border-radius: 8px;
                padding: 8px 13px;
                font-size: 10px;
                font-weight: 650;
            }}

            QPushButton#openFolderButton:hover {{
                border: 1px solid {theme["accent"]};
            }}

            QPushButton#openFolderButton:pressed {{
                background: {theme["background"]};
            }}

            QLabel#aboutFooter {{
                color: {theme["muted"]};
                font-size: 10px;
                padding: 5px;
            }}
            """
        )

        self.update_portrait()

    @pyqtSlot(dict)
    def apply_branding(self, branding: dict):
        title = (
            branding.get("title", "")
            or "03:37am Presence"
        )

        subtitle = (
            branding.get("subtitle", "")
            or "Spotify and Discord companion"
        )

        footer = (
            branding.get("footer", "")
            or "Made with pink pixels "
            "and far too much music."
        )

        self._branding_image_path = str(
            branding.get("image_path", "")
            or ""
        )

        self.app_name.setText(title)
        self.branding_subtitle.setText(
            subtitle
        )
        self.footer_label.setText(
            footer
        )

        self.app_name.setVisible(
            bool(
                branding.get(
                    "show_title",
                    True,
                )
            )
        )

        self.branding_subtitle.setVisible(
            bool(
                branding.get(
                    "show_subtitle",
                    True,
                )
            )
        )

        self.footer_label.setVisible(
            bool(
                branding.get(
                    "show_footer",
                    True,
                )
            )
        )

        self.update_portrait()

    def update_portrait(self):
        custom_path = Path(
            self._branding_image_path
        )

        if custom_path.exists():
            image_path = custom_path
        else:
            image_path = YUNO_IMAGE_PATH

        pixmap = QPixmap(
            str(image_path)
        )

        if pixmap.isNull():
            self.portrait.clear()
            self.portrait.setText(
                "Branding image\nnot found"
            )
            return

        scaled_pixmap = pixmap.scaled(
            self._portrait_size,
            self._portrait_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.portrait.setText("")
        self.portrait.setPixmap(
            scaled_pixmap
        )

    def open_project_folder(self):
        QDesktopServices.openUrl(
            QUrl.fromLocalFile(
                str(PROJECT_ROOT)
            )
        )