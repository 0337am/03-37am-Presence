from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class DiscordProfilePreview(QFrame):
    """
    Pure presentation widget for a Discord-style profile/activity preview.

    The widget deliberately owns no Discord RPC, networking, account
    credentials, media polling, or persistence. Production callers provide
    profile and activity state that the widget renders locally.
    """

    open_discord_requested = pyqtSignal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self.setObjectName("discordProfilePreview")
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        self._compact = False
        self._avatar_size = 88
        self._artwork_size = 96

        self._build_ui()
        self.set_profile(
            display_name="Discord profile",
            username="",
            status="Offline",
        )
        self.clear_activity()
        self.apply_theme({})

    def _build_ui(self):
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(
            18,
            16,
            18,
            16,
        )
        self.root_layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(8)

        self.preview_heading = QLabel(
            "DISCORD PREVIEW"
        )
        self.preview_heading.setObjectName(
            "discordPreviewHeading"
        )

        self.preview_badge = QLabel(
            "LIVE PREVIEW"
        )
        self.preview_badge.setObjectName(
            "discordPreviewBadge"
        )
        self.preview_badge.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        header.addWidget(
            self.preview_heading
        )
        header.addStretch()
        header.addWidget(
            self.preview_badge
        )

        self.preview_body = QFrame()
        self.preview_body.setObjectName(
            "discordPreviewBody"
        )

        body_layout = QHBoxLayout(
            self.preview_body
        )
        body_layout.setContentsMargins(
            18,
            18,
            18,
            18,
        )
        body_layout.setSpacing(22)

        self.profile_panel = QFrame()
        self.profile_panel.setObjectName(
            "discordProfilePanel"
        )

        profile_layout = QVBoxLayout(
            self.profile_panel
        )
        profile_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        profile_layout.setSpacing(8)

        self.profile_avatar = QLabel("?")
        self.profile_avatar.setObjectName(
            "discordProfileAvatar"
        )
        self.profile_avatar.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.profile_name = QLabel(
            "Discord profile"
        )
        self.profile_name.setObjectName(
            "discordProfileName"
        )
        self.profile_name.setWordWrap(True)

        self.profile_username = QLabel("")
        self.profile_username.setObjectName(
            "discordProfileUsername"
        )
        self.profile_username.setWordWrap(True)

        self.profile_status = QLabel(
            "Offline"
        )
        self.profile_status.setObjectName(
            "discordProfileStatus"
        )
        self.profile_status.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        profile_layout.addWidget(
            self.profile_avatar,
            alignment=Qt.AlignmentFlag.AlignLeft,
        )
        profile_layout.addWidget(
            self.profile_name
        )
        profile_layout.addWidget(
            self.profile_username
        )
        profile_layout.addWidget(
            self.profile_status,
            alignment=Qt.AlignmentFlag.AlignLeft,
        )
        profile_layout.addStretch()

        self.activity_panel = QFrame()
        self.activity_panel.setObjectName(
            "discordActivityPreviewPanel"
        )

        activity_layout = QVBoxLayout(
            self.activity_panel
        )
        activity_layout.setContentsMargins(
            16,
            14,
            16,
            14,
        )
        activity_layout.setSpacing(9)

        activity_header = QHBoxLayout()
        activity_header.setSpacing(8)

        self.activity_heading = QLabel(
            "CURRENT ACTIVITY"
        )
        self.activity_heading.setObjectName(
            "discordActivityHeading"
        )

        self.activity_source_badge = QLabel(
            "DISCORD"
        )
        self.activity_source_badge.setObjectName(
            "discordActivitySourceBadge"
        )
        self.activity_source_badge.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        activity_header.addWidget(
            self.activity_heading
        )
        activity_header.addStretch()
        activity_header.addWidget(
            self.activity_source_badge
        )

        self.activity_application = QLabel(
            "03:37am Presence"
        )
        self.activity_application.setObjectName(
            "discordActivityApplication"
        )
        self.activity_application.setWordWrap(True)

        activity_content = QHBoxLayout()
        activity_content.setSpacing(14)

        self.activity_artwork = QLabel("?")
        self.activity_artwork.setObjectName(
            "discordActivityArtwork"
        )
        self.activity_artwork.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        activity_text = QVBoxLayout()
        activity_text.setSpacing(3)

        self.activity_title = QLabel(
            "Nothing playing"
        )
        self.activity_title.setObjectName(
            "discordActivityTitle"
        )
        self.activity_title.setWordWrap(True)

        self.activity_artist = QLabel("")
        self.activity_artist.setObjectName(
            "discordActivityArtist"
        )
        self.activity_artist.setWordWrap(True)

        self.activity_album = QLabel("")
        self.activity_album.setObjectName(
            "discordActivityAlbum"
        )
        self.activity_album.setWordWrap(True)

        self.activity_progress = QProgressBar()
        self.activity_progress.setObjectName(
            "discordActivityProgress"
        )
        self.activity_progress.setRange(
            0,
            100,
        )
        self.activity_progress.setTextVisible(
            False
        )
        self.activity_progress.setFixedHeight(
            6
        )

        self.activity_time = QLabel("")
        self.activity_time.setObjectName(
            "discordActivityTime"
        )

        activity_text.addWidget(
            self.activity_title
        )
        activity_text.addWidget(
            self.activity_artist
        )
        activity_text.addWidget(
            self.activity_album
        )
        activity_text.addStretch()
        activity_text.addWidget(
            self.activity_progress
        )
        activity_text.addWidget(
            self.activity_time
        )

        activity_content.addWidget(
            self.activity_artwork,
            alignment=Qt.AlignmentFlag.AlignTop,
        )
        activity_content.addLayout(
            activity_text,
            stretch=1,
        )

        activity_layout.addLayout(
            activity_header
        )
        activity_layout.addWidget(
            self.activity_application
        )
        activity_layout.addLayout(
            activity_content
        )

        body_layout.addWidget(
            self.profile_panel,
            stretch=2,
        )
        body_layout.addWidget(
            self.activity_panel,
            stretch=5,
        )

        self.open_discord_button = QPushButton(
            "Open in Discord"
        )
        self.open_discord_button.setObjectName(
            "discordPreviewOpenButton"
        )
        self.open_discord_button.clicked.connect(
            self.open_discord_requested.emit
        )

        self.root_layout.addLayout(
            header
        )
        self.root_layout.addWidget(
            self.preview_body
        )
        self.root_layout.addWidget(
            self.open_discord_button
        )

        self._apply_sizes()

    def _apply_sizes(self):
        self.profile_avatar.setFixedSize(
            self._avatar_size,
            self._avatar_size,
        )

        self.activity_artwork.setFixedSize(
            self._artwork_size,
            self._artwork_size,
        )

        self.profile_panel.setMinimumWidth(
            150 if self._compact else 180
        )

    @staticmethod
    def _clean_text(
        value,
        fallback: str = "",
    ) -> str:
        text = str(
            value or ""
        ).strip()

        return text or fallback

    @staticmethod
    def _scaled_square(
        pixmap: QPixmap,
        size: int,
    ) -> QPixmap:
        scaled = pixmap.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )

        x_offset = max(
            0,
            (scaled.width() - size) // 2,
        )
        y_offset = max(
            0,
            (scaled.height() - size) // 2,
        )

        return scaled.copy(
            x_offset,
            y_offset,
            size,
            size,
        )

    def _set_pixmap_or_text(
        self,
        label: QLabel,
        pixmap: Optional[QPixmap],
        size: int,
        fallback: str,
    ):
        if (
            pixmap is not None
            and not pixmap.isNull()
        ):
            label.setText("")
            label.setPixmap(
                self._scaled_square(
                    pixmap,
                    size,
                )
            )
            return

        label.clear()
        label.setText(
            fallback
        )

    def set_compact(
        self,
        compact: bool,
    ):
        self._compact = bool(compact)

        if self._compact:
            self._avatar_size = 72
            self._artwork_size = 78
        else:
            self._avatar_size = 88
            self._artwork_size = 96

        self._apply_sizes()

    def set_profile(
        self,
        display_name: str,
        username: str = "",
        status: str = "Offline",
        avatar: Optional[QPixmap] = None,
    ):
        display_name = self._clean_text(
            display_name,
            "Discord profile",
        )
        username = self._clean_text(
            username
        )
        status = self._clean_text(
            status,
            "Offline",
        )

        self.profile_name.setText(
            display_name
        )
        self.profile_username.setText(
            username
        )
        self.profile_username.setHidden(
            not bool(username)
        )
        self.profile_status.setText(
            status
        )

        fallback = (
            display_name[:1].upper()
            if display_name
            else "?"
        )

        self._set_pixmap_or_text(
            self.profile_avatar,
            avatar,
            self._avatar_size,
            fallback,
        )

    def set_activity(
        self,
        *,
        title: str,
        artist: str = "",
        album: str = "",
        time_text: str = "",
        source_label: str = "DISCORD",
        application_name: str = "03:37am Presence",
        artwork: Optional[QPixmap] = None,
        progress_percent: Optional[int] = None,
    ):
        title = self._clean_text(
            title,
            "Unknown activity",
        )
        artist = self._clean_text(
            artist
        )
        album = self._clean_text(
            album
        )
        time_text = self._clean_text(
            time_text
        )
        source_label = self._clean_text(
            source_label,
            "DISCORD",
        )
        application_name = self._clean_text(
            application_name,
            "03:37am Presence",
        )

        self.activity_title.setText(
            title
        )
        self.activity_artist.setText(
            artist
        )
        self.activity_album.setText(
            album
        )
        self.activity_time.setText(
            time_text
        )

        self.activity_artist.setHidden(
            not bool(artist)
        )
        self.activity_album.setHidden(
            not bool(album)
        )
        self.activity_time.setHidden(
            not bool(time_text)
        )

        self.activity_source_badge.setText(
            source_label.upper()
        )
        self.activity_application.setText(
            application_name
        )

        artwork_fallback = (
            source_label[:1].upper()
            if source_label
            else "?"
        )

        self._set_pixmap_or_text(
            self.activity_artwork,
            artwork,
            self._artwork_size,
            artwork_fallback,
        )

        if progress_percent is None:
            self.activity_progress.setHidden(
                True
            )
        else:
            bounded_progress = max(
                0,
                min(
                    100,
                    int(progress_percent),
                ),
            )
            self.activity_progress.setValue(
                bounded_progress
            )
            self.activity_progress.setHidden(
                False
            )

    def clear_activity(
        self,
        message: str = "Nothing playing",
    ):
        self.set_activity(
            title=message,
            artist="Waiting for activity",
            album="",
            time_text="",
            source_label="DISCORD",
            application_name="03:37am Presence",
            artwork=None,
            progress_percent=None,
        )

    def apply_theme(
        self,
        theme: dict,
    ):
        background = theme.get(
            "background",
            "#151218",
        )
        card = theme.get(
            "card",
            "#211923",
        )
        card_alt = theme.get(
            "card_alt",
            "#2a202c",
        )
        border = theme.get(
            "border",
            "#513449",
        )
        text = theme.get(
            "text",
            "#f4edf2",
        )
        muted = theme.get(
            "muted",
            "#b7aab3",
        )
        accent = theme.get(
            "accent",
            "#ff6fab",
        )

        self.setStyleSheet(
            f"""
            QFrame#discordProfilePreview {{
                background: transparent;
            }}

            QLabel#discordPreviewHeading {{
                color: {accent};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
            }}

            QLabel#discordPreviewBadge,
            QLabel#discordActivitySourceBadge {{
                color: {accent};
                background: {card_alt};
                border: 1px solid {border};
                border-radius: 7px;
                padding: 3px 8px;
                font-size: 9px;
                font-weight: 700;
            }}

            QFrame#discordPreviewBody {{
                background: {card};
                border: 1px solid {border};
                border-radius: 14px;
            }}

            QFrame#discordProfilePanel {{
                background: transparent;
                border: none;
            }}

            QLabel#discordProfileAvatar,
            QLabel#discordActivityArtwork {{
                color: {muted};
                background: {background};
                border: 1px solid {border};
                border-radius: 12px;
                font-size: 22px;
                font-weight: 700;
            }}

            QLabel#discordProfileName {{
                color: {text};
                font-size: 18px;
                font-weight: 700;
            }}

            QLabel#discordProfileUsername {{
                color: {muted};
                font-size: 10px;
            }}

            QLabel#discordProfileStatus {{
                color: {text};
                background: {card_alt};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 4px 9px;
                font-size: 10px;
                font-weight: 650;
            }}

            QFrame#discordActivityPreviewPanel {{
                background: {card_alt};
                border: 1px solid {border};
                border-radius: 13px;
            }}

            QLabel#discordActivityHeading {{
                color: {muted};
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1px;
            }}

            QLabel#discordActivityApplication {{
                color: {accent};
                font-size: 10px;
                font-weight: 650;
            }}

            QLabel#discordActivityTitle {{
                color: {text};
                font-size: 16px;
                font-weight: 700;
            }}

            QLabel#discordActivityArtist {{
                color: {text};
                font-size: 12px;
            }}

            QLabel#discordActivityAlbum,
            QLabel#discordActivityTime {{
                color: {muted};
                font-size: 10px;
            }}

            QProgressBar#discordActivityProgress {{
                background: {background};
                border: none;
                border-radius: 3px;
            }}

            QProgressBar#discordActivityProgress::chunk {{
                background: {accent};
                border-radius: 3px;
            }}

            QPushButton#discordPreviewOpenButton {{
                color: {text};
                background: {card};
                border: 1px solid {border};
                border-radius: 10px;
                padding: 9px 12px;
                text-align: left;
                font-size: 11px;
                font-weight: 650;
            }}

            QPushButton#discordPreviewOpenButton:hover {{
                border: 1px solid {accent};
            }}
            """
        )
