from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QProgressBar,
)
from PyQt6.QtCore import (
    Qt,
    QThread,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QFont, QPixmap

from src.music.manager import MusicManager
from src.music.song import Song

print(">>> DASHBOARD.PY LOADED <<<")


class MediaWorker(QThread):
    """
    Reads Windows Media in a background thread.

    Only ordinary Song objects and image bytes are sent back to
    the dashboard. Qt widgets and QPixmap remain on the UI thread.
    """

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

            # Sleep for approximately one second while still allowing
            # the worker to stop promptly during application shutdown.
            for _ in range(10):
                if self.isInterruptionRequested():
                    return

                self.msleep(100)

    def stop(self):
        self.requestInterruption()


class DashboardPage(QWidget):

    def __init__(self):
        super().__init__()

        self.song = Song(
            title="Waiting for media...",
            artist="",
            album="",
        )

        self._last_artwork_signature = None

        self.build_ui()
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
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 30, 30, 30)
        root.setSpacing(25)

        title = QLabel("Dashboard")
        title.setFont(
            QFont(
                "Segoe UI",
                24,
                QFont.Weight.Bold,
            )
        )
        title.setStyleSheet("color:white;")
        root.addWidget(title)

        card = QFrame()
        card.setObjectName("card")

        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(
            25,
            25,
            25,
            25,
        )
        card_layout.setSpacing(30)

        self.artwork = QLabel("Album\nArtwork")
        self.artwork.setFixedSize(220, 220)
        self.artwork.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.artwork.setObjectName("artwork")

        card_layout.addWidget(self.artwork)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(10)

        self.song_title = QLabel(self.song.title)
        self.song_title.setFont(
            QFont(
                "Segoe UI",
                22,
                QFont.Weight.Bold,
            )
        )
        self.song_title.setStyleSheet(
            "color:white;"
        )

        self.artist = QLabel(self.song.artist)
        self.artist.setStyleSheet(
            "color:#BBBBBB; font-size:15px;"
        )

        self.album = QLabel(self.song.album)
        self.album.setStyleSheet(
            "color:#888888; font-size:14px;"
        )

        info_layout.addStretch()
        info_layout.addWidget(self.song_title)
        info_layout.addWidget(self.artist)
        info_layout.addWidget(self.album)
        info_layout.addSpacing(20)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)

        self.progress.setStyleSheet("""
            QProgressBar {
                background: #2d2d39;
                border-radius: 4px;
            }

            QProgressBar::chunk {
                background: #ff8fcf;
                border-radius: 4px;
            }
        """)

        info_layout.addWidget(self.progress)

        times = QHBoxLayout()

        self.current_time = QLabel(
            self.song.position
        )
        self.total_time = QLabel(
            self.song.duration
        )

        self.current_time.setStyleSheet(
            "color:#aaaaaa;"
        )
        self.total_time.setStyleSheet(
            "color:#aaaaaa;"
        )

        times.addWidget(self.current_time)
        times.addStretch()
        times.addWidget(self.total_time)

        info_layout.addLayout(times)
        info_layout.addStretch()

        card_layout.addLayout(info_layout)
        root.addWidget(card)

        status_layout = QHBoxLayout()
        status_layout.setSpacing(20)

        discord_card, self.discord_status = (
            self.make_status_card(
                "Discord",
                "Not connected",
            )
        )

        music_card, self.music_status = (
            self.make_status_card(
                "Music",
                "Starting",
            )
        )

        artwork_card, self.artwork_status = (
            self.make_status_card(
                "Artwork",
                "Waiting",
            )
        )

        status_layout.addWidget(discord_card)
        status_layout.addWidget(music_card)
        status_layout.addWidget(artwork_card)

        root.addLayout(status_layout)
        root.addStretch()

        self.setStyleSheet("""
            QFrame#card {
                background: #352747;
                border-radius: 18px;
            }

            QLabel#artwork {
                background: #313140;
                border-radius: 15px;
                color: #888888;
                font-size: 15px;
            }
        """)

    def make_status_card(self, title, value):
        card = QFrame()

        card.setStyleSheet("""
            QFrame {
                background: #3E2E54;
                border-radius: 14px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(
            20,
            18,
            20,
            18,
        )

        label = QLabel(title)
        label.setStyleSheet(
            "color:#aaaaaa; font-size:13px;"
        )

        status = QLabel(value)
        status.setStyleSheet(
            "color:white;"
            "font-size:16px;"
            "font-weight:bold;"
        )

        layout.addWidget(label)
        layout.addWidget(status)

        return card, status

    @pyqtSlot(object)
    def apply_song(self, song):
        if song is None or not song.title:
            self.show_nothing_playing()
            return

        self.song = song

        self.song_title.setText(song.title)
        self.artist.setText(song.artist)
        self.album.setText(song.album)

        self.current_time.setText(song.position)
        self.total_time.setText(song.duration)

        if song.playing:
            self.music_status.setText("Playing")
        else:
            self.music_status.setText("Paused")

        self.update_artwork(song)
        self.update_progress(song)

    def update_artwork(self, song: Song):
        artwork_size = len(
            song.artwork_bytes or b""
        )

        signature = (
            song.title,
            song.artist,
            song.album,
            artwork_size,
        )

        if signature == self._last_artwork_signature:
            return

        self._last_artwork_signature = signature

        if not song.artwork_bytes:
            self.artwork.clear()
            self.artwork.setText("No\nArtwork")
            self.artwork_status.setText("Missing")
            return

        # QPixmap is deliberately created here on the UI thread.
        pixmap = QPixmap()

        loaded = pixmap.loadFromData(
            song.artwork_bytes
        )

        if not loaded or pixmap.isNull():
            self.artwork.clear()
            self.artwork.setText("Invalid\nArtwork")
            self.artwork_status.setText("Invalid")
            return

        scaled_pixmap = pixmap.scaled(
            220,
            220,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.artwork.setText("")
        self.artwork.setPixmap(scaled_pixmap)
        self.artwork_status.setText("Loaded")

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

        self.progress.setValue(percentage)

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

        self.music_status.setText("Waiting")
        self.artwork_status.setText("Waiting")

        self.artwork.clear()
        self.artwork.setText("Album\nArtwork")

        self._last_artwork_signature = None

    @pyqtSlot(str)
    def show_worker_error(self, message):
        print("Media worker error:")
        print(message)

        self.music_status.setText("Error")

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
    def time_to_seconds(value: str) -> int:
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