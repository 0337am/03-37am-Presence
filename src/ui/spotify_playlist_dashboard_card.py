"""Static Spotify Playlist Dashboard-card presentation.

This module renders playlist metadata and track rows only.

It deliberately owns no Spotify network access, authentication state,
playback routing, polling, media control, or Dashboard persistence.
Those responsibilities remain with the existing production layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from PyQt6.QtCore import (
    QRectF,
    QSize,
    Qt,
)
from PyQt6.QtGui import (
    QPainter,
    QPainterPath,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from src.system.spotify_playlist_card_preferences import (
    normalise_spotify_playlist_id,
)


MAX_TITLE_LENGTH = 256
MAX_OWNER_LENGTH = 192
MAX_TRACK_TITLE_LENGTH = 384
MAX_ARTIST_LENGTH = 384
MAX_RENDERED_TRACKS = 500


class SpotifyPlaylistDashboardCardError(
    ValueError
):
    """Raised when static Playlist Card presentation data is invalid."""


def _required_text(
    value: object,
    *,
    field: str,
    maximum: int,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise SpotifyPlaylistDashboardCardError(
            f"{field} must be a string."
        )

    value = value.strip()

    if not value:
        raise SpotifyPlaylistDashboardCardError(
            f"{field} must not be empty."
        )

    if "\x00" in value:
        raise SpotifyPlaylistDashboardCardError(
            f"{field} contains an invalid NUL character."
        )

    if len(value) > maximum:
        raise SpotifyPlaylistDashboardCardError(
            f"{field} is too long."
        )

    return value


def format_playlist_duration(
    seconds: object,
) -> str:
    if (
        not isinstance(seconds, int)
        or isinstance(seconds, bool)
        or seconds < 0
    ):
        raise SpotifyPlaylistDashboardCardError(
            "duration_seconds must be a non-negative integer."
        )

    hours, remainder = divmod(
        seconds,
        3600,
    )

    minutes, seconds = divmod(
        remainder,
        60,
    )

    if hours:
        return (
            f"{hours}:"
            f"{minutes:02}:"
            f"{seconds:02}"
        )

    return (
        f"{minutes}:"
        f"{seconds:02}"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class SpotifyPlaylistDashboardTrack:
    """One static row shown by the Playlist Dashboard card."""

    position: int
    title: str
    artists: str
    duration_seconds: int
    is_local: bool = False
    available: bool = True

    def __post_init__(self) -> None:
        if (
            not isinstance(
                self.position,
                int,
            )
            or isinstance(
                self.position,
                bool,
            )
            or self.position < 0
        ):
            raise SpotifyPlaylistDashboardCardError(
                "position must be a non-negative integer."
            )

        title = _required_text(
            self.title,
            field="title",
            maximum=MAX_TRACK_TITLE_LENGTH,
        )

        artists = _required_text(
            self.artists,
            field="artists",
            maximum=MAX_ARTIST_LENGTH,
        )

        if (
            not isinstance(
                self.duration_seconds,
                int,
            )
            or isinstance(
                self.duration_seconds,
                bool,
            )
            or self.duration_seconds < 0
        ):
            raise SpotifyPlaylistDashboardCardError(
                "duration_seconds must be a non-negative integer."
            )

        if not isinstance(
            self.is_local,
            bool,
        ):
            raise SpotifyPlaylistDashboardCardError(
                "is_local must be boolean."
            )

        if not isinstance(
            self.available,
            bool,
        ):
            raise SpotifyPlaylistDashboardCardError(
                "available must be boolean."
            )

        object.__setattr__(
            self,
            "title",
            title,
        )

        object.__setattr__(
            self,
            "artists",
            artists,
        )

    @property
    def display_number(self) -> str:
        return str(
            self.position + 1
        )

    @property
    def display_duration(self) -> str:
        return format_playlist_duration(
            self.duration_seconds
        )


@dataclass(
    frozen=True,
    slots=True,
)
class SpotifyPlaylistDashboardSnapshot:
    """Credential-free static playlist information for the card."""

    playlist_id: str
    title: str
    owner: str
    track_count: int
    tracks: tuple[
        SpotifyPlaylistDashboardTrack,
        ...,
    ]

    def __post_init__(self) -> None:
        playlist_id = (
            normalise_spotify_playlist_id(
                self.playlist_id
            )
        )

        title = _required_text(
            self.title,
            field="title",
            maximum=MAX_TITLE_LENGTH,
        )

        owner = _required_text(
            self.owner,
            field="owner",
            maximum=MAX_OWNER_LENGTH,
        )

        if (
            not isinstance(
                self.track_count,
                int,
            )
            or isinstance(
                self.track_count,
                bool,
            )
            or self.track_count < 0
        ):
            raise SpotifyPlaylistDashboardCardError(
                "track_count must be a non-negative integer."
            )

        tracks = tuple(
            self.tracks
        )

        if len(tracks) > MAX_RENDERED_TRACKS:
            raise SpotifyPlaylistDashboardCardError(
                "Too many Playlist Card rows."
            )

        for track in tracks:
            if not isinstance(
                track,
                SpotifyPlaylistDashboardTrack,
            ):
                raise SpotifyPlaylistDashboardCardError(
                    "tracks must contain Playlist Dashboard tracks."
                )

        if self.track_count < len(tracks):
            raise SpotifyPlaylistDashboardCardError(
                "track_count cannot be smaller than the rendered track list."
            )

        object.__setattr__(
            self,
            "playlist_id",
            playlist_id,
        )

        object.__setattr__(
            self,
            "title",
            title,
        )

        object.__setattr__(
            self,
            "owner",
            owner,
        )

        object.__setattr__(
            self,
            "tracks",
            tracks,
        )

    @classmethod
    def build(
        cls,
        *,
        playlist_id: str,
        title: str,
        owner: str,
        track_count: int,
        tracks: Iterable[
            SpotifyPlaylistDashboardTrack
        ],
    ) -> "SpotifyPlaylistDashboardSnapshot":
        return cls(
            playlist_id=playlist_id,
            title=title,
            owner=owner,
            track_count=track_count,
            tracks=tuple(tracks),
        )


class SpotifyPlaylistDashboardTrackRow(
    QFrame
):
    """Presentation-only row for one playlist item."""

    def __init__(
        self,
        track: SpotifyPlaylistDashboardTrack,
        parent: QWidget | None = None,
    ) -> None:
        if not isinstance(
            track,
            SpotifyPlaylistDashboardTrack,
        ):
            raise SpotifyPlaylistDashboardCardError(
                "track must be SpotifyPlaylistDashboardTrack."
            )

        super().__init__(
            parent
        )

        self.track = track

        self.setObjectName(
            "spotifyPlaylistDashboardTrackRow"
        )

        self.setProperty(
            "isLocal",
            track.is_local,
        )

        self.setProperty(
            "available",
            track.available,
        )

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        self.setMinimumHeight(
            54
        )

        layout = QHBoxLayout(
            self
        )

        layout.setContentsMargins(
            8,
            6,
            8,
            6,
        )

        layout.setSpacing(
            10
        )

        self.number_label = QLabel(
            track.display_number,
            self,
        )

        self.number_label.setObjectName(
            "spotifyPlaylistDashboardTrackNumber"
        )

        self.number_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.number_label.setFixedWidth(
            26
        )

        layout.addWidget(
            self.number_label
        )

        text_widget = QWidget(
            self
        )

        text_widget.setObjectName(
            "spotifyPlaylistDashboardTrackText"
        )

        text_layout = QVBoxLayout(
            text_widget
        )

        text_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        text_layout.setSpacing(
            1
        )

        self.title_label = QLabel(
            track.title,
            text_widget,
        )

        self.title_label.setObjectName(
            "spotifyPlaylistDashboardTrackTitle"
        )

        self.title_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )

        self.artist_label = QLabel(
            track.artists,
            text_widget,
        )

        self.artist_label.setObjectName(
            "spotifyPlaylistDashboardTrackArtist"
        )

        text_layout.addWidget(
            self.title_label
        )

        text_layout.addWidget(
            self.artist_label
        )

        layout.addWidget(
            text_widget,
            1,
        )

        self.local_badge = QLabel(
            "LOCAL",
            self,
        )

        self.local_badge.setObjectName(
            "spotifyPlaylistDashboardLocalBadge"
        )

        self.local_badge.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        layout.addWidget(
            self.local_badge
        )

        self.local_badge.setVisible(
            track.is_local
        )

        self.unavailable_badge = QLabel(
            "UNAVAILABLE",
            self,
        )

        self.unavailable_badge.setObjectName(
            "spotifyPlaylistDashboardUnavailableBadge"
        )

        self.unavailable_badge.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        layout.addWidget(
            self.unavailable_badge
        )

        self.unavailable_badge.setVisible(
            not track.available
        )

        self.duration_label = QLabel(
            track.display_duration,
            self,
        )

        self.duration_label.setObjectName(
            "spotifyPlaylistDashboardTrackDuration"
        )

        self.duration_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )

        self.duration_label.setFixedWidth(
            58
        )

        layout.addWidget(
            self.duration_label
        )


class SpotifyPlaylistDashboardCard(
    QFrame
):
    """Reusable static Playlist Card surface for the Dashboard."""

    ARTWORK_SIZE = 118

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            parent
        )

        self._snapshot = None
        self._track_rows = []

        self.setObjectName(
            "spotifyPlaylistDashboardCard"
        )

        self.setMinimumSize(
            470,
            330,
        )

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        root = QVBoxLayout(
            self
        )

        root.setContentsMargins(
            16,
            16,
            16,
            14,
        )

        root.setSpacing(
            12
        )

        self.header = QFrame(
            self
        )

        self.header.setObjectName(
            "spotifyPlaylistDashboardHeader"
        )

        header_layout = QHBoxLayout(
            self.header
        )

        header_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        header_layout.setSpacing(
            16
        )

        self.artwork_label = QLabel(
            "PLAYLIST"
        )

        self.artwork_label.setObjectName(
            "spotifyPlaylistDashboardArtwork"
        )

        self.artwork_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.artwork_label.setFixedSize(
            self.ARTWORK_SIZE,
            self.ARTWORK_SIZE,
        )

        header_layout.addWidget(
            self.artwork_label,
            0,
            Qt.AlignmentFlag.AlignTop,
        )

        information = QWidget(
            self.header
        )

        information.setObjectName(
            "spotifyPlaylistDashboardInformation"
        )

        information_layout = QVBoxLayout(
            information
        )

        information_layout.setContentsMargins(
            0,
            2,
            0,
            0,
        )

        information_layout.setSpacing(
            4
        )

        self.kind_label = QLabel(
            "SPOTIFY PLAYLIST"
        )

        self.kind_label.setObjectName(
            "spotifyPlaylistDashboardKind"
        )

        information_layout.addWidget(
            self.kind_label
        )

        self.title_label = QLabel(
            "Choose a playlist"
        )

        self.title_label.setObjectName(
            "spotifyPlaylistDashboardTitle"
        )

        self.title_label.setWordWrap(
            True
        )

        information_layout.addWidget(
            self.title_label
        )

        self.owner_label = QLabel(
            "No playlist selected"
        )

        self.owner_label.setObjectName(
            "spotifyPlaylistDashboardOwner"
        )

        information_layout.addWidget(
            self.owner_label
        )

        self.count_label = QLabel(
            "0 tracks"
        )

        self.count_label.setObjectName(
            "spotifyPlaylistDashboardCount"
        )

        information_layout.addWidget(
            self.count_label
        )

        information_layout.addStretch(
            1
        )

        self.more_label = QLabel(
            "..."
        )

        self.more_label.setObjectName(
            "spotifyPlaylistDashboardMore"
        )

        self.more_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
        )

        self.more_label.setFixedWidth(
            30
        )

        information_layout.addWidget(
            self.more_label
        )

        header_layout.addWidget(
            information,
            1,
        )

        right_column = QVBoxLayout()

        right_column.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        right_column.setSpacing(
            10
        )

        self.brand_label = QLabel(
            "Spotify"
        )

        self.brand_label.setObjectName(
            "spotifyPlaylistDashboardBrand"
        )

        self.brand_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )

        right_column.addWidget(
            self.brand_label
        )

        right_column.addStretch(
            1
        )

        self.play_button = QPushButton(
            self.header
        )

        self.play_button.setObjectName(
            "spotifyPlaylistDashboardPlayButton"
        )

        self.play_button.setAccessibleName(
            "Play playlist"
        )

        self.play_button.setIcon(
            self.style().standardIcon(
                QStyle.StandardPixmap.SP_MediaPlay
            )
        )

        self.play_button.setIconSize(
            QSize(
                24,
                24,
            )
        )

        self.play_button.setFixedSize(
            52,
            52,
        )

        self.play_button.setEnabled(
            False
        )

        right_column.addWidget(
            self.play_button,
            0,
            Qt.AlignmentFlag.AlignRight,
        )

        header_layout.addLayout(
            right_column
        )

        root.addWidget(
            self.header
        )

        self.divider = QFrame(
            self
        )

        self.divider.setObjectName(
            "spotifyPlaylistDashboardDivider"
        )

        self.divider.setFrameShape(
            QFrame.Shape.HLine
        )

        root.addWidget(
            self.divider
        )

        self.scroll_area = QScrollArea(
            self
        )

        self.scroll_area.setObjectName(
            "spotifyPlaylistDashboardScroll"
        )

        self.scroll_area.viewport().setObjectName(
            "spotifyPlaylistDashboardViewport"
        )

        self.scroll_area.setWidgetResizable(
            True
        )

        self.scroll_area.setFrameShape(
            QFrame.Shape.NoFrame
        )

        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self.track_container = QWidget()

        self.track_container.setObjectName(
            "spotifyPlaylistDashboardTrackContainer"
        )

        self.track_layout = QVBoxLayout(
            self.track_container
        )

        self.track_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.track_layout.setSpacing(
            2
        )

        self.empty_label = QLabel(
            "Playlist tracks will appear here."
        )

        self.empty_label.setObjectName(
            "spotifyPlaylistDashboardEmpty"
        )

        self.empty_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.empty_label.setWordWrap(
            True
        )

        self.track_layout.addWidget(
            self.empty_label,
            1,
        )

        self.scroll_area.setWidget(
            self.track_container
        )

        root.addWidget(
            self.scroll_area,
            1,
        )

    def apply_theme(
        self,
        theme: dict,
    ) -> None:
        if not isinstance(
            theme,
            dict,
        ):
            return

        def theme_value(
            key: str,
            fallback: str,
        ) -> str:
            value = str(
                theme.get(
                    key,
                    fallback,
                )
                or fallback
            ).strip()

            return (
                value
                or fallback
            )

        background = theme_value(
            "background",
            "#101014",
        )

        card = theme_value(
            "card",
            "#18181f",
        )

        card_alt = theme_value(
            "card_alt",
            "#202028",
        )

        border = theme_value(
            "border",
            "#34343e",
        )

        accent = theme_value(
            "accent",
            "#ff4f91",
        )

        text = theme_value(
            "text",
            "#f4f4f6",
        )

        muted = theme_value(
            "muted",
            "#a6a6b1",
        )

        self.setStyleSheet(
            f"""
            QFrame#spotifyPlaylistDashboardCard {{
                background: {card};
                border: 1px solid {border};
                border-radius: 14px;
            }}

            QFrame#spotifyPlaylistDashboardHeader,
            QWidget#spotifyPlaylistDashboardInformation,
            QWidget#spotifyPlaylistDashboardTransport {{
                background: transparent;
                border: none;
            }}

            QLabel#spotifyPlaylistDashboardArtwork {{
                background: {card_alt};
                color: {muted};
                border: 1px solid {border};
                border-radius: 10px;
                font-size: 8pt;
                font-weight: 700;
            }}

            QLabel#spotifyPlaylistDashboardKind {{
                color: {accent};
                font-size: 8pt;
                font-weight: 700;
            }}

            QLabel#spotifyPlaylistDashboardTitle {{
                color: {text};
                font-size: 18pt;
                font-weight: 700;
            }}

            QLabel#spotifyPlaylistDashboardOwner {{
                color: {text};
                font-size: 10pt;
            }}

            QLabel#spotifyPlaylistDashboardCount {{
                color: {muted};
                font-size: 9pt;
            }}

            QLabel#spotifyPlaylistDashboardBrand {{
                color: {text};
                font-size: 9pt;
                font-weight: 700;
            }}

            QLabel#spotifyPlaylistDashboardMore {{
                color: {muted};
                background: transparent;
                border: none;
                font-size: 15pt;
                font-weight: 700;
            }}

            QPushButton#spotifyPlaylistDashboardPlayButton {{
                color: {background};
                background: {accent};
                border: none;
                border-radius: 26px;
            }}

            QPushButton#spotifyPlaylistDashboardPlayButton:hover {{
                border: 1px solid {text};
            }}

            QPushButton#spotifyPlaylistDashboardPlayButton:disabled {{
                color: {background};
                background: {accent};
                border: none;
            }}

            QFrame#spotifyPlaylistDashboardDivider {{
                color: {border};
                background: {border};
                border: none;
                max-height: 1px;
            }}

            QScrollArea#spotifyPlaylistDashboardScroll {{
                background: transparent;
                border: none;
            }}

            QWidget#spotifyPlaylistDashboardViewport {{
                background: transparent;
                border: none;
            }}

            QWidget#spotifyPlaylistDashboardTrackContainer {{
                background: transparent;
                border: none;
            }}

            QFrame#spotifyPlaylistDashboardTrackRow {{
                background: transparent;
                border: none;
                border-radius: 8px;
            }}

            QFrame#spotifyPlaylistDashboardTrackRow:hover {{
                background: {card_alt};
            }}

            QLabel#spotifyPlaylistDashboardTrackNumber {{
                color: {muted};
                font-size: 9pt;
            }}

            QLabel#spotifyPlaylistDashboardTrackTitle {{
                color: {text};
                font-size: 10pt;
                font-weight: 650;
            }}

            QLabel#spotifyPlaylistDashboardTrackArtist {{
                color: {muted};
                font-size: 8.5pt;
            }}

            QLabel#spotifyPlaylistDashboardTrackDuration {{
                color: {text};
                font-size: 9pt;
            }}

            QLabel#spotifyPlaylistDashboardLocalBadge {{
                color: {accent};
                background: {background};
                border: 1px solid {accent};
                border-radius: 6px;
                padding: 2px 5px;
                font-size: 7pt;
                font-weight: 700;
            }}

            QLabel#spotifyPlaylistDashboardUnavailableBadge {{
                color: {muted};
                background: {background};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 2px 5px;
                font-size: 7pt;
                font-weight: 700;
            }}

            QLabel#spotifyPlaylistDashboardEmpty {{
                color: {muted};
                background: transparent;
                border: none;
            }}

            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 2px;
            }}

            QScrollBar::handle:vertical {{
                background: {border};
                border: none;
                border-radius: 4px;
                min-height: 28px;
            }}

            QScrollBar::handle:vertical:hover {{
                background: {muted};
            }}

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
            """
        )

    @property
    def snapshot(
        self,
    ) -> SpotifyPlaylistDashboardSnapshot | None:
        return self._snapshot

    @property
    def track_rows(
        self,
    ) -> tuple[
        SpotifyPlaylistDashboardTrackRow,
        ...,
    ]:
        return tuple(
            self._track_rows
        )

    def set_snapshot(
        self,
        snapshot: SpotifyPlaylistDashboardSnapshot,
    ) -> None:
        if not isinstance(
            snapshot,
            SpotifyPlaylistDashboardSnapshot,
        ):
            raise SpotifyPlaylistDashboardCardError(
                "snapshot must be SpotifyPlaylistDashboardSnapshot."
            )

        previous = (
            self._snapshot
        )

        previous_tracks = (
            previous.tracks
            if isinstance(
                previous,
                SpotifyPlaylistDashboardSnapshot,
            )
            else ()
        )

        same_playlist = bool(
            isinstance(
                previous,
                SpotifyPlaylistDashboardSnapshot,
            )
            and previous.playlist_id
            == snapshot.playlist_id
        )

        extends_existing_rows = bool(
            same_playlist
            and len(
                snapshot.tracks
            )
            >= len(
                previous_tracks
            )
            and snapshot.tracks[
                :len(
                    previous_tracks
                )
            ]
            == previous_tracks
        )

        self._snapshot = snapshot

        self.title_label.setText(
            snapshot.title
        )

        self.owner_label.setText(
            snapshot.owner
        )

        word = (
            "track"
            if snapshot.track_count == 1
            else "tracks"
        )

        self.count_label.setText(
            f"{snapshot.track_count} {word}"
        )

        if extends_existing_rows:
            new_tracks = (
                snapshot.tracks[
                    len(
                        previous_tracks
                    ):
                ]
            )

            if new_tracks:
                self._append_tracks(
                    new_tracks
                )

            return

        self._replace_tracks(
            snapshot.tracks
        )

    def clear_snapshot(
        self,
    ) -> None:
        self._snapshot = None

        self.title_label.setText(
            "Choose a playlist"
        )

        self.owner_label.setText(
            "No playlist selected"
        )

        self.count_label.setText(
            "0 tracks"
        )

        self._replace_tracks(
            ()
        )

    def set_artwork_pixmap(
        self,
        pixmap: QPixmap,
    ) -> bool:
        if (
            not isinstance(
                pixmap,
                QPixmap,
            )
            or pixmap.isNull()
        ):
            return False

        rounded = self._rounded_square_pixmap(
            pixmap,
            self.ARTWORK_SIZE,
        )

        if rounded.isNull():
            return False

        self.artwork_label.setText(
            ""
        )

        self.artwork_label.setPixmap(
            rounded
        )

        return True

    def clear_artwork(
        self,
    ) -> None:
        self.artwork_label.clear()

        self.artwork_label.setText(
            "PLAYLIST"
        )

    def _replace_tracks(
        self,
        tracks: Iterable[
            SpotifyPlaylistDashboardTrack
        ],
    ) -> None:
        tracks = tuple(
            tracks
        )

        self.track_container.setUpdatesEnabled(
            False
        )

        try:
            while self.track_layout.count():
                item = (
                    self.track_layout
                    .takeAt(0)
                )

                widget = (
                    item.widget()
                )

                if widget is not None:
                    # deleteLater() is deferred until Qt returns to
                    # the event loop. Hide first so a genuinely
                    # replaced row can never remain visibly painted
                    # during that deferred lifetime.
                    widget.hide()

                    widget.deleteLater()

            self._track_rows.clear()

            if not tracks:
                self.empty_label = QLabel(
                    "Playlist tracks will appear here.",
                    self.track_container,
                )

                self.empty_label.setObjectName(
                    "spotifyPlaylistDashboardEmpty"
                )

                self.empty_label.setAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )

                self.empty_label.setWordWrap(
                    True
                )

                self.track_layout.addWidget(
                    self.empty_label,
                    1,
                )

                return

            for track in tracks:
                row = (
                    SpotifyPlaylistDashboardTrackRow(
                        track,
                        self.track_container,
                    )
                )

                # Keep construction invisible until the whole batch
                # has a parent and layout position.
                row.hide()

                self._track_rows.append(
                    row
                )

                self.track_layout.addWidget(
                    row
                )

            self.track_layout.addStretch(
                1
            )

        finally:
            self.track_container.setUpdatesEnabled(
                True
            )

        for row in self._track_rows:
            row.show()

        self.track_container.updateGeometry()
        self.track_container.update()

    def _append_tracks(
        self,
        tracks: Iterable[
            SpotifyPlaylistDashboardTrack
        ],
    ) -> None:
        """Append one pagination batch without rebuilding existing rows."""

        tracks = tuple(
            tracks
        )

        if not tracks:
            return

        # The first non-empty page replaces the static empty-state
        # label once. Every later pagination page follows the
        # incremental path below.
        if not self._track_rows:
            self._replace_tracks(
                tracks
            )

            return

        new_rows = []

        self.track_container.setUpdatesEnabled(
            False
        )

        try:
            last_index = (
                self.track_layout.count()
                - 1
            )

            if last_index >= 0:
                last_item = (
                    self.track_layout
                    .itemAt(
                        last_index
                    )
                )

                if (
                    last_item is not None
                    and last_item.spacerItem()
                    is not None
                ):
                    self.track_layout.takeAt(
                        last_index
                    )

            for track in tracks:
                row = (
                    SpotifyPlaylistDashboardTrackRow(
                        track,
                        self.track_container,
                    )
                )

                row.hide()

                self._track_rows.append(
                    row
                )

                new_rows.append(
                    row
                )

                self.track_layout.addWidget(
                    row
                )

            self.track_layout.addStretch(
                1
            )

        finally:
            self.track_container.setUpdatesEnabled(
                True
            )

        for row in new_rows:
            row.show()

        self.track_container.updateGeometry()
        self.track_container.update()

    @staticmethod
    def _rounded_square_pixmap(
        pixmap: QPixmap,
        size: int,
    ) -> QPixmap:
        width = pixmap.width()
        height = pixmap.height()

        if (
            width <= 0
            or height <= 0
            or size <= 0
        ):
            return QPixmap()

        side = min(
            width,
            height,
        )

        left = (
            width - side
        ) // 2

        top = (
            height - side
        ) // 2

        cropped = pixmap.copy(
            left,
            top,
            side,
            side,
        )

        scaled = cropped.scaled(
            size,
            size,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        result = QPixmap(
            size,
            size,
        )

        result.fill(
            Qt.GlobalColor.transparent
        )

        painter = QPainter(
            result
        )

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )

        path = QPainterPath()

        path.addRoundedRect(
            QRectF(
                0,
                0,
                size,
                size,
            ),
            10,
            10,
        )

        painter.setClipPath(
            path
        )

        painter.drawPixmap(
            0,
            0,
            scaled,
        )

        painter.end()

        return result
