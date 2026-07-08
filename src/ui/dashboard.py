from PyQt6.QtCore import (
    Qt,
    QThread,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.music.manager import MusicManager
from src.music.song import Song
from src.ui.theme import ThemeManager


class MediaWorker(QThread):
    song_ready = pyqtSignal(object)
    worker_error = pyqtSignal(str)

    def run(self):
        music = MusicManager()

        try:
            music.connect()
        except Exception as error:
            self.worker_error.emit(
                f"Music connection failed: {error}"
            )

        while not self.isInterruptionRequested():
            try:
                song = music.get_current_song()
                self.song_ready.emit(song)

            except Exception as error:
                self.worker_error.emit(str(error))

            for _ in range(10):
                if self.isInterruptionRequested():
                    return

                self.msleep(100)

    def stop(self):
        self.requestInterruption()

class DashboardPage(QWidget):
    def __init__(
        self,
        theme_manager=None,
    ):
        super().__init__()

        self.setObjectName("dashboardRoot")

        self.theme_manager = (
            theme_manager
            or ThemeManager(self)
        )

        self.song = Song(
            title="Waiting for media...",
            artist="",
            album="",
        )

        self._last_artwork_signature = None
        self._artwork_size = 112
        self._preview_artwork_size = 58
        self._branding_title = "03:37am Presence"

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

        self.start_media_worker()

    def start_media_worker(self):
        self.media_worker = MediaWorker()

        self.media_worker.song_ready.connect(
            self.apply_song
        )
        self.media_worker.worker_error.connect(
            self.show_worker_error
        )

        app = QApplication.instance()

        if app is not None:
            app.aboutToQuit.connect(
                self.stop_media_worker
            )

        self.media_worker.start()

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

        title_group = QVBoxLayout()
        title_group.setSpacing(1)

        self.page_title = QLabel("Dashboard")
        self.page_title.setObjectName(
            "pageTitle"
        )

        self.page_subtitle = QLabel(
            "Media, Discord preview, and service status"
        )
        self.page_subtitle.setObjectName(
            "pageSubtitle"
        )

        title_group.addWidget(
            self.page_title
        )
        title_group.addWidget(
            self.page_subtitle
        )

        self.activity_badge = QLabel("Waiting")
        self.activity_badge.setObjectName(
            "activityBadge"
        )
        self.activity_badge.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        header.addLayout(title_group)
        header.addStretch()
        header.addWidget(
            self.activity_badge,
            alignment=Qt.AlignmentFlag.AlignVCenter,
        )

        self.root_layout.addLayout(header)

        self.top_row = QHBoxLayout()
        self.top_row.setSpacing(12)

        self.build_now_playing_card()
        self.build_discord_preview_card()

        self.top_row.addWidget(
            self.now_playing_card,
            stretch=3,
        )
        self.top_row.addWidget(
            self.preview_card,
            stretch=2,
        )

        self.root_layout.addLayout(
            self.top_row
        )

        self.status_row = QHBoxLayout()
        self.status_row.setSpacing(9)

        discord_pill, self.discord_status = (
            self.make_status_pill(
                "Discord",
                "Not connected",
            )
        )

        music_pill, self.music_status = (
            self.make_status_pill(
                "Music",
                "Starting",
            )
        )

        artwork_pill, self.artwork_status = (
            self.make_status_pill(
                "Artwork",
                "Waiting",
            )
        )

        self.status_row.addWidget(
            discord_pill
        )
        self.status_row.addWidget(
            music_pill
        )
        self.status_row.addWidget(
            artwork_pill
        )

        self.root_layout.addLayout(
            self.status_row
        )

        self.info_card = QFrame()
        self.info_card.setObjectName(
            "infoCard"
        )

        info_layout = QHBoxLayout(
            self.info_card
        )
        info_layout.setContentsMargins(
            14,
            11,
            14,
            11,
        )
        info_layout.setSpacing(10)

        info_title = QLabel("Tip")
        info_title.setObjectName(
            "infoTitle"
        )

        info_text = QLabel(
            "The preview mirrors your current music activity. "
            "Custom-mode previews can be added next."
        )
        info_text.setObjectName(
            "infoText"
        )
        info_text.setWordWrap(True)

        info_layout.addWidget(
            info_title
        )
        info_layout.addWidget(
            info_text,
            stretch=1,
        )

        self.root_layout.addWidget(
            self.info_card
        )
        self.root_layout.addStretch()

    def build_now_playing_card(self):
        self.now_playing_card = QFrame()
        self.now_playing_card.setObjectName(
            "nowPlayingCard"
        )

        self.now_playing_layout = QHBoxLayout(
            self.now_playing_card
        )
        self.now_playing_layout.setContentsMargins(
            14,
            14,
            14,
            14,
        )
        self.now_playing_layout.setSpacing(14)

        self.artwork = QLabel(
            "Album\nArtwork"
        )
        self.artwork.setObjectName(
            "artwork"
        )
        self.artwork.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.artwork.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )

        self.now_playing_layout.addWidget(
            self.artwork,
            alignment=Qt.AlignmentFlag.AlignVCenter,
        )

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        self.section_label = QLabel(
            "NOW PLAYING"
        )
        self.section_label.setObjectName(
            "sectionLabel"
        )

        self.song_title = QLabel(
            self.song.title
        )
        self.song_title.setObjectName(
            "songTitle"
        )
        self.song_title.setWordWrap(True)

        self.artist = QLabel(
            self.song.artist
        )
        self.artist.setObjectName(
            "artist"
        )

        self.album = QLabel(
            self.song.album
        )
        self.album.setObjectName(
            "album"
        )

        info_layout.addWidget(
            self.section_label
        )
        info_layout.addWidget(
            self.song_title
        )
        info_layout.addWidget(
            self.artist
        )
        info_layout.addWidget(
            self.album
        )
        info_layout.addStretch()

        self.progress = QProgressBar()
        self.progress.setObjectName(
            "playbackProgress"
        )
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)

        info_layout.addWidget(
            self.progress
        )

        times = QHBoxLayout()
        times.setSpacing(8)

        self.current_time = QLabel(
            self.song.position
        )
        self.current_time.setObjectName(
            "timeLabel"
        )

        self.total_time = QLabel(
            self.song.duration
        )
        self.total_time.setObjectName(
            "timeLabel"
        )

        times.addWidget(
            self.current_time
        )
        times.addStretch()
        times.addWidget(
            self.total_time
        )

        info_layout.addLayout(times)

        self.now_playing_layout.addLayout(
            info_layout,
            stretch=1,
        )

    def build_discord_preview_card(self):
        self.preview_card = QFrame()
        self.preview_card.setObjectName(
            "previewCard"
        )

        preview_layout = QVBoxLayout(
            self.preview_card
        )
        preview_layout.setContentsMargins(
            14,
            13,
            14,
            13,
        )
        preview_layout.setSpacing(8)

        preview_top = QHBoxLayout()
        preview_top.setSpacing(8)

        preview_heading = QLabel(
            "DISCORD PREVIEW"
        )
        preview_heading.setObjectName(
            "previewHeading"
        )

        self.preview_mode = QLabel(
            "MUSIC"
        )
        self.preview_mode.setObjectName(
            "previewMode"
        )

        preview_top.addWidget(
            preview_heading
        )
        preview_top.addStretch()
        preview_top.addWidget(
            self.preview_mode
        )

        preview_layout.addLayout(
            preview_top
        )

        self.preview_app = QLabel(
            "Listening to 03:37am Presence"
        )
        self.preview_app.setObjectName(
            "previewApp"
        )
        self.preview_app.setWordWrap(True)

        preview_layout.addWidget(
            self.preview_app
        )

        activity_row = QHBoxLayout()
        activity_row.setSpacing(10)

        self.preview_artwork = QLabel(
            "Art"
        )
        self.preview_artwork.setObjectName(
            "previewArtwork"
        )
        self.preview_artwork.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.preview_artwork.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )

        activity_row.addWidget(
            self.preview_artwork,
            alignment=Qt.AlignmentFlag.AlignTop,
        )

        activity_text = QVBoxLayout()
        activity_text.setSpacing(2)

        self.preview_title = QLabel(
            "Waiting for media..."
        )
        self.preview_title.setObjectName(
            "previewTitle"
        )
        self.preview_title.setWordWrap(True)

        self.preview_state = QLabel("")
        self.preview_state.setObjectName(
            "previewState"
        )
        self.preview_state.setWordWrap(True)

        self.preview_album = QLabel("")
        self.preview_album.setObjectName(
            "previewAlbum"
        )
        self.preview_album.setWordWrap(True)

        self.preview_time = QLabel(
            "Waiting"
        )
        self.preview_time.setObjectName(
            "previewTime"
        )

        activity_text.addWidget(
            self.preview_title
        )
        activity_text.addWidget(
            self.preview_state
        )
        activity_text.addWidget(
            self.preview_album
        )
        activity_text.addStretch()
        activity_text.addWidget(
            self.preview_time
        )

        activity_row.addLayout(
            activity_text,
            stretch=1,
        )

        preview_layout.addLayout(
            activity_row
        )
        preview_layout.addStretch()

    def make_status_pill(
        self,
        title: str,
        value: str,
    ):
        card = QFrame()
        card.setObjectName(
            "statusPill"
        )

        layout = QHBoxLayout(card)
        layout.setContentsMargins(
            12,
            8,
            12,
            8,
        )
        layout.setSpacing(7)

        dot = QLabel("●")
        dot.setObjectName(
            "statusDot"
        )

        label = QLabel(title)
        label.setObjectName(
            "statusTitle"
        )

        status = QLabel(value)
        status.setObjectName(
            "statusValue"
        )
        status.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )

        layout.addWidget(dot)
        layout.addWidget(label)
        layout.addStretch()
        layout.addWidget(status)

        return card, status

    @pyqtSlot(dict)
    def apply_theme(self, theme: dict):
        compact = theme.get(
            "compact",
            True,
        )

        self._artwork_size = (
            108 if compact else 124
        )
        self._preview_artwork_size = (
            54 if compact else 64
        )

        margin = 18 if compact else 24
        spacing = 10 if compact else 14
        title_size = 23 if compact else 26
        song_size = 17 if compact else 20

        self.root_layout.setContentsMargins(
            margin,
            margin,
            margin,
            margin,
        )
        self.root_layout.setSpacing(
            spacing
        )

        self.artwork.setFixedSize(
            self._artwork_size,
            self._artwork_size,
        )

        self.preview_artwork.setFixedSize(
            self._preview_artwork_size,
            self._preview_artwork_size,
        )

        self.progress.setFixedHeight(
            5 if compact else 7
        )

        self.setStyleSheet(
            f"""
            QWidget#dashboardRoot {{
                background: {theme["background"]};
            }}

            QLabel#pageTitle {{
                color: {theme["text"]};
                font-size: {title_size}px;
                font-weight: 700;
            }}

            QLabel#pageSubtitle {{
                color: {theme["muted"]};
                font-size: 11px;
            }}

            QLabel#activityBadge {{
                color: {theme["text"]};
                background: {theme["card_alt"]};
                border: 1px solid {theme["border"]};
                border-radius: 9px;
                padding: 5px 10px;
                font-size: 10px;
                font-weight: 700;
            }}

            QFrame#nowPlayingCard,
            QFrame#previewCard {{
                background: {theme["card"]};
                border: 1px solid {theme["border"]};
                border-radius: 14px;
            }}

            QLabel#artwork,
            QLabel#previewArtwork {{
                color: {theme["muted"]};
                background: {theme["background"]};
                border: 1px solid {theme["border"]};
                border-radius: 10px;
            }}

            QLabel#sectionLabel,
            QLabel#previewHeading {{
                color: {theme["accent"]};
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 1px;
            }}

            QLabel#songTitle {{
                color: {theme["text"]};
                font-size: {song_size}px;
                font-weight: 700;
            }}

            QLabel#artist,
            QLabel#previewTitle {{
                color: {theme["text"]};
                font-size: 12px;
                font-weight: 650;
            }}

            QLabel#album,
            QLabel#previewState,
            QLabel#previewAlbum,
            QLabel#previewTime,
            QLabel#timeLabel {{
                color: {theme["muted"]};
                font-size: 10px;
            }}

            QLabel#previewApp {{
                color: {theme["text"]};
                font-size: 11px;
                font-weight: 650;
            }}

            QLabel#previewMode {{
                color: {theme["accent"]};
                background: {theme["card_alt"]};
                border: 1px solid {theme["border"]};
                border-radius: 7px;
                padding: 3px 7px;
                font-size: 9px;
                font-weight: 700;
            }}

            QProgressBar#playbackProgress {{
                background: {theme["background"]};
                border: none;
                border-radius: 2px;
            }}

            QProgressBar#playbackProgress::chunk {{
                background: {theme["accent"]};
                border-radius: 2px;
            }}

            QFrame#statusPill {{
                background: {theme["card_alt"]};
                border: 1px solid {theme["border"]};
                border-radius: 10px;
            }}

            QLabel#statusDot {{
                color: {theme["accent"]};
                font-size: 9px;
            }}

            QLabel#statusTitle {{
                color: {theme["muted"]};
                font-size: 10px;
            }}

            QLabel#statusValue {{
                color: {theme["text"]};
                font-size: 10px;
                font-weight: 700;
            }}

            QFrame#infoCard {{
                background: transparent;
                border: 1px dashed {theme["border"]};
                border-radius: 10px;
            }}

            QLabel#infoTitle {{
                color: {theme["accent"]};
                font-size: 10px;
                font-weight: 700;
            }}

            QLabel#infoText {{
                color: {theme["muted"]};
                font-size: 10px;
            }}
            """
        )

        if getattr(
            self.song,
            "artwork_bytes",
            None,
        ):
            self._last_artwork_signature = None
            self.update_artwork(self.song)

    @pyqtSlot(dict)
    def apply_branding(self, branding: dict):
        title = (
            branding.get("title", "")
            or "03:37am Presence"
        )

        self._branding_title = title

        self.preview_app.setText(
            f"Listening to {title}"
        )

    @pyqtSlot(object)
    def apply_song(self, song):
        if song is None or not song.title:
            self.show_nothing_playing()
            return

        self.song = song

        self.song_title.setText(song.title)
        self.artist.setText(song.artist)
        self.album.setText(song.album)

        self.current_time.setText(
            song.position
        )
        self.total_time.setText(
            song.duration
        )

        self.preview_title.setText(
            song.title
        )
        self.preview_state.setText(
            song.artist or "Unknown artist"
        )
        self.preview_album.setText(
            song.album or "No album"
        )

        if song.playing:
            self.music_status.setText(
                "Playing"
            )
            self.activity_badge.setText(
                "Playing"
            )
            self.preview_time.setText(
                f"{song.position} elapsed"
            )
        else:
            self.music_status.setText(
                "Paused"
            )
            self.activity_badge.setText(
                "Paused"
            )
            self.preview_time.setText(
                "Paused"
            )

        self.update_artwork(song)
        self.update_progress(song)

    def update_artwork(self, song: Song):
        artwork_bytes = song.artwork_bytes or b""

        signature = (
            song.title,
            song.artist,
            song.album,
            len(artwork_bytes),
            self._artwork_size,
            self._preview_artwork_size,
        )

        if signature == self._last_artwork_signature:
            return

        self._last_artwork_signature = signature

        if not artwork_bytes:
            self.artwork.clear()
            self.artwork.setText(
                "No\nArtwork"
            )

            self.preview_artwork.clear()
            self.preview_artwork.setText(
                "No art"
            )

            self.artwork_status.setText(
                "Missing"
            )
            return

        pixmap = QPixmap()

        loaded = pixmap.loadFromData(
            artwork_bytes
        )

        if not loaded or pixmap.isNull():
            self.artwork.clear()
            self.artwork.setText(
                "Invalid\nArtwork"
            )

            self.preview_artwork.clear()
            self.preview_artwork.setText(
                "Invalid"
            )

            self.artwork_status.setText(
                "Invalid"
            )
            return

        main_pixmap = pixmap.scaled(
            self._artwork_size,
            self._artwork_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        preview_pixmap = pixmap.scaled(
            self._preview_artwork_size,
            self._preview_artwork_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.artwork.setText("")
        self.artwork.setPixmap(
            main_pixmap
        )

        self.preview_artwork.setText("")
        self.preview_artwork.setPixmap(
            preview_pixmap
        )

        self.artwork_status.setText(
            "Loaded"
        )

    def update_progress(self, song: Song):
        current = self.time_to_seconds(
            song.position
        )
        total = self.time_to_seconds(
            song.duration
        )

        if total <= 0:
            self.progress.setValue(0)
            return

        percentage = int(
            (current / total) * 100
        )

        percentage = max(
            0,
            min(100, percentage),
        )

        self.progress.setValue(
            percentage
        )

    def show_nothing_playing(self):
        self.song_title.setText(
            "Nothing playing"
        )
        self.artist.setText(
            "Open Spotify and play a song"
        )
        self.album.setText("")

        self.current_time.setText("0:00")
        self.total_time.setText("0:00")
        self.progress.setValue(0)

        self.preview_title.setText(
            "Nothing playing"
        )
        self.preview_state.setText(
            "Waiting for Spotify"
        )
        self.preview_album.setText("")
        self.preview_time.setText(
            "Waiting"
        )

        self.music_status.setText(
            "Waiting"
        )
        self.artwork_status.setText(
            "Waiting"
        )
        self.activity_badge.setText(
            "Waiting"
        )

        self.artwork.clear()
        self.artwork.setText(
            "Album\nArtwork"
        )

        self.preview_artwork.clear()
        self.preview_artwork.setText(
            "Art"
        )

        self._last_artwork_signature = None

    @pyqtSlot(str)
    def show_worker_error(self, message):
        print("Media worker error:")
        print(message)

        self.music_status.setText(
            "Error"
        )
        self.activity_badge.setText(
            "Error"
        )
        self.preview_time.setText(
            "Media error"
        )

    def stop_media_worker(self):
        worker = getattr(
            self,
            "media_worker",
            None,
        )

        if worker is None:
            return

        if not worker.isRunning():
            return

        worker.stop()
        worker.wait(7000)

    @staticmethod
    def time_to_seconds(
        value: str,
    ) -> int:
        try:
            parts = [
                int(part)
                for part in value.split(":")
            ]

            total = 0

            for part in parts:
                total = total * 60 + part

            return total

        except (TypeError, ValueError):
            return 0