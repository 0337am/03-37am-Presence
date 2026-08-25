from dataclasses import replace
from datetime import datetime
import hashlib
from pathlib import Path
import os
import subprocess
import time

from PyQt6.QtCore import (
    Qt,
    QEvent,
    QPoint,
    QUrl,
    QThread,
    QTimer,
    QSettings,
    QSignalBlocker,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import (
    QAction,
    QDesktopServices,
    QPixmap,
    QKeySequence,
    QShortcut,
    QColor,
    QIcon,
    QPainter,
    QPainterPath,
)
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QSizePolicy,
    QStyle,
    QVBoxLayout,
    QWidget,
    QAbstractSpinBox,
    QLineEdit,
    QPlainTextEdit,
    QTextEdit,
)

from src.library.history_store import (
    HistoryStore,
    HistoryTrack,
)
from src.music.manager import MusicManager
from src.music.artwork_cache_policy import (
    should_upgrade_artwork,
)
from src.music.song import Song
from src.ui.playback_presentation_clock import (
    PlaybackPresentationClock,
    format_playback_time,
)
from src.media.audio_spectrum import (
    spectrum_levels_to_text,
)
from src.media.windows_process_audio import (
    SpotifyAudioSpectrumService,
)
from src.music.source_preferences import (
    SourcePreferencesStore,
)
from src.discord.presence_modes import (
    MODE_NAMES,
)
from src.discord.presence_presets import (
    PresencePresetStore,
)
from src.system.afk_preferences import (
    AfkPreferencesStore,
)
from src.system.idle_monitor import (
    WindowsIdleMonitor,
)
from src.ui.custom_cards import (
    CustomCardStore,
    LauncherCardData,
    LinkCardData,
    duplicate_launcher_card as duplicate_launcher_card_data,
    duplicate_link_card as duplicate_link_card_data,
    normalize_web_url,
)
from src.ui.dashboard_layout import (
    CANVAS_UNITS,
    CARD_ORDER,
    CARD_SPECS,
    DashboardCardLayout,
    DashboardLayout,
    DashboardLayoutStore,
    available_presets,
    dashboard_card_spec,
    is_custom_dashboard_card_id,
    move_card_freeform,
    preset_layout,
    resize_card_freeform,
    validate_layout,
)
from src.ui.dashboard_alignment import (
    AlignmentRect,
    snap_moving_rect,
    snap_resizing_rect,
)
from src.ui.dashboard_profiles import (
    DashboardLayoutProfile,
    DashboardLayoutProfileStore,
    validate_profile_name,
)
from src.ui.link_cards import (
    LinkCardDialog,
    LinkCardWidget,
)
from src.ui.launcher_cards import (
    LauncherCardDialog,
    LauncherCardWidget,
)
from src.ui.launcher_card_images import (
    prune_launcher_card_images,
)
from src.system.launcher_open import (
    open_prepared_launcher_target,
    prepare_launcher_target,
)
from src.ui.discord_avatar_loader import (
    DiscordAvatarLoader,
)
from src.ui.discord_profile_preview import (
    DiscordProfilePreview,
)
from src.ui.theme import ThemeManager

from src.spotify.queue_service import (
    SpotifyQueueServiceResult,
    SpotifyQueueServiceStatus,
)

from src.spotify.queue_models import (
    QUEUE_PARTIAL_REASON_SHUFFLE_LOCAL_ORDER,
)


def colour_with_alpha(
    colour: str,
    alpha: float,
) -> str:
    value = str(colour or "").strip()

    if value.startswith("#"):
        value = value[1:]

    if len(value) != 6:
        return colour

    try:
        red = int(value[0:2], 16)
        green = int(value[2:4], 16)
        blue = int(value[4:6], 16)
    except ValueError:
        return colour

    channel = max(
        0,
        min(
            255,
            int(255 * alpha),
        ),
    )

    return (
        f"rgba({red}, {green}, {blue}, {channel})"
    )


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

class DashboardCanvas(QFrame):
    def __init__(
        self,
        parent=None,
    ):
        super().__init__(parent)

        self._grid_spacing = 24
        self._snap_enabled = True
        self._editor_accent = "#ffffff"
        self._editor_border = "#808080"

        self.setProperty(
            "editing",
            False,
        )
        self.setProperty(
            "snapEnabled",
            True,
        )
        self.setProperty(
            "gridSpacing",
            self._grid_spacing,
        )

    def set_editor_theme(
        self,
        accent: str,
        border: str,
    ):
        self._editor_accent = str(
            accent
            or "#ffffff"
        )
        self._editor_border = str(
            border
            or "#808080"
        )

        self.setProperty(
            "editorAccent",
            self._editor_accent,
        )
        self.setProperty(
            "editorBorder",
            self._editor_border,
        )

        self.update()

    def set_grid_spacing(
        self,
        spacing: int,
    ):
        self._grid_spacing = max(
            8,
            int(spacing),
        )

        self.setProperty(
            "gridSpacing",
            self._grid_spacing,
        )

        self.update()

    def set_snap_enabled(
        self,
        enabled: bool,
    ):
        self._snap_enabled = bool(
            enabled
        )

        self.setProperty(
            "snapEnabled",
            self._snap_enabled,
        )

        if not self._snap_enabled:
            self.clear_alignment_guides()

        self.update()

    def set_alignment_guides(
        self,
        guides,
    ):
        self._alignment_guides = tuple(
            guides
            or ()
        )

        self.setProperty(
            "alignmentGuideCount",
            len(
                self._alignment_guides
            ),
        )

        self.setProperty(
            "hasAlignmentGuides",
            bool(
                self._alignment_guides
            ),
        )

        self.update()

    def clear_alignment_guides(self):
        self._alignment_guides = ()

        self.setProperty(
            "alignmentGuideCount",
            0,
        )

        self.setProperty(
            "hasAlignmentGuides",
            False,
        )

        self.update()

    def paintEvent(
        self,
        event,
    ):
        super().paintEvent(event)

        if (
            not bool(
                self.property(
                    "editing"
                )
            )
            or not self._snap_enabled
        ):
            return

        from PyQt6.QtGui import (
            QColor,
            QPainter,
            QPen,
        )

        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            False,
        )

        spacing = max(
            8,
            self._grid_spacing,
        )

        rectangle = self.rect().adjusted(
            1,
            1,
            -1,
            -1,
        )

        minor_colour = QColor(
            self._editor_border
        )

        if not minor_colour.isValid():
            minor_colour = QColor(
                "#808080"
            )

        minor_colour.setAlpha(28)

        minor_pen = QPen(
            minor_colour
        )
        minor_pen.setWidth(1)

        painter.setPen(
            minor_pen
        )

        for x in range(
            rectangle.left() + spacing,
            rectangle.right(),
            spacing,
        ):
            painter.drawLine(
                x,
                rectangle.top(),
                x,
                rectangle.bottom(),
            )

        for y in range(
            rectangle.top() + spacing,
            rectangle.bottom(),
            spacing,
        ):
            painter.drawLine(
                rectangle.left(),
                y,
                rectangle.right(),
                y,
            )

        major_spacing = (
            spacing * 4
        )

        major_colour = QColor(
            self._editor_accent
        )

        if not major_colour.isValid():
            major_colour = QColor(
                "#ffffff"
            )

        major_colour.setAlpha(48)

        major_pen = QPen(
            major_colour
        )
        major_pen.setWidth(1)

        painter.setPen(
            major_pen
        )

        for x in range(
            rectangle.left() + major_spacing,
            rectangle.right(),
            major_spacing,
        ):
            painter.drawLine(
                x,
                rectangle.top(),
                x,
                rectangle.bottom(),
            )

        for y in range(
            rectangle.top() + major_spacing,
            rectangle.bottom(),
            major_spacing,
        ):
            painter.drawLine(
                rectangle.left(),
                y,
                rectangle.right(),
                y,
            )

        guides = tuple(
            getattr(
                self,
                "_alignment_guides",
                (),
            )
        )

        if guides:
            guide_colour = QColor(
                self._editor_accent
            )

            if not guide_colour.isValid():
                guide_colour = QColor(
                    "#ffffff"
                )

            guide_colour.setAlpha(220)

            guide_pen = QPen(
                guide_colour
            )
            guide_pen.setWidth(2)
            guide_pen.setStyle(
                Qt.PenStyle.DashLine
            )

            painter.setPen(
                guide_pen
            )

            for guide in guides:
                orientation = str(
                    getattr(
                        guide,
                        "orientation",
                        "",
                    )
                )

                position = int(
                    getattr(
                        guide,
                        "position",
                        0,
                    )
                )

                if orientation == "vertical":
                    position = min(
                        rectangle.right(),
                        max(
                            rectangle.left(),
                            position,
                        ),
                    )

                    painter.drawLine(
                        position,
                        rectangle.top(),
                        position,
                        rectangle.bottom(),
                    )

                elif orientation == "horizontal":
                    position = min(
                        rectangle.bottom(),
                        max(
                            rectangle.top(),
                            position,
                        ),
                    )

                    painter.drawLine(
                        rectangle.left(),
                        position,
                        rectangle.right(),
                        position,
                    )

        painter.end()


PLAYBACK_SEEK_PENDING_TIMEOUT_MS = 2000
PLAYBACK_SEEK_CONFIRM_TOLERANCE_SECONDS = 4.0
PLAYBACK_SEEK_HANDLE_WIDTH_PX = 8


class PlaybackProgressVisual(
    QFrame
):
    def __init__(
        self,
        parent=None,
    ) -> None:
        super().__init__(
            parent
        )

        self._minimum = 0
        self._maximum = 10000
        self._value = 0

        self.played = QFrame(
            self
        )
        self.played.setObjectName(
            "playbackProgressPlayed"
        )
        self.played.setMinimumWidth(
            0
        )

        self.remaining = QFrame(
            self
        )
        self.remaining.setObjectName(
            "playbackProgressRemaining"
        )
        self.remaining.setMinimumWidth(
            0
        )

        self._segments_layout = QHBoxLayout(
            self
        )
        self._segments_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        self._segments_layout.setSpacing(
            0
        )

        self._segments_layout.addWidget(
            self.played
        )
        self._segments_layout.addWidget(
            self.remaining
        )

        self._refresh_segments()

    def setRange(
        self,
        minimum,
        maximum,
    ) -> None:
        minimum = int(
            minimum
        )
        maximum = int(
            maximum
        )

        if maximum < minimum:
            maximum = minimum

        self._minimum = minimum
        self._maximum = maximum

        self.setValue(
            self._value
        )

    def setValue(
        self,
        value,
    ) -> None:
        value = int(
            value
        )

        self._value = max(
            self._minimum,
            min(
                self._maximum,
                value,
            ),
        )

        self._refresh_segments()

    def value(
        self,
    ) -> int:
        return self._value

    def _refresh_segments(
        self,
    ) -> None:
        span = max(
            0,
            self._maximum
            - self._minimum,
        )

        played = max(
            0,
            self._value
            - self._minimum,
        )

        remaining = max(
            0,
            self._maximum
            - self._value,
        )

        self.played.setVisible(
            played > 0
        )

        self.remaining.setVisible(
            remaining > 0
        )

        if span <= 0:
            self._segments_layout.setStretch(
                0,
                0,
            )
            self._segments_layout.setStretch(
                1,
                1,
            )
            return

        self._segments_layout.setStretch(
            0,
            played,
        )
        self._segments_layout.setStretch(
            1,
            remaining,
        )


class PlaybackSeekSlider(
    QSlider
):
    scrub_started = pyqtSignal()
    scrub_moved = pyqtSignal(
        int
    )
    scrub_committed = pyqtSignal(
        int
    )

    def __init__(
        self,
        parent=None,
    ) -> None:
        super().__init__(
            Qt.Orientation.Horizontal,
            parent,
        )

        self._pointer_scrubbing = False

        self.setAutoFillBackground(
            False
        )

    def paintEvent(
        self,
        event,
    ) -> None:
        # This slider is input-only. The visible
        # playback rail is rendered underneath it.
        event.accept()

    def _value_from_pointer(
        self,
        x,
    ) -> int:
        minimum = self.minimum()
        maximum = self.maximum()

        value_span = max(
            0,
            maximum - minimum,
        )

        half_handle = (
            PLAYBACK_SEEK_HANDLE_WIDTH_PX
            / 2.0
        )

        slider_start = (
            half_handle
        )

        slider_end = max(
            slider_start + 1.0,
            float(
                self.width()
                - 1
            )
            - half_handle,
        )

        try:
            pointer = float(
                x
            )

        except (
            TypeError,
            ValueError,
        ):
            pointer = slider_start

        ratio = (
            (
                pointer
                - slider_start
            )
            / (
                slider_end
                - slider_start
            )
        )

        ratio = max(
            0.0,
            min(
                1.0,
                ratio,
            ),
        )

        return int(
            round(
                minimum
                + (
                    value_span
                    * ratio
                )
            )
        )

    def _apply_pointer_position(
        self,
        x,
    ) -> int:
        value = (
            self._value_from_pointer(
                x
            )
        )

        self.setValue(
            value
        )

        self.scrub_moved.emit(
            value
        )

        return value

    def mousePressEvent(
        self,
        event,
    ) -> None:
        if (
            self.isEnabled()
            and event.button()
            == Qt.MouseButton.LeftButton
        ):
            self._pointer_scrubbing = True

            self.scrub_started.emit()

            self._apply_pointer_position(
                event.position().x()
            )

            event.accept()
            return

        super().mousePressEvent(
            event
        )

    def mouseMoveEvent(
        self,
        event,
    ) -> None:
        if self._pointer_scrubbing:
            self._apply_pointer_position(
                event.position().x()
            )

            event.accept()
            return

        super().mouseMoveEvent(
            event
        )

    def mouseReleaseEvent(
        self,
        event,
    ) -> None:
        if (
            self._pointer_scrubbing
            and event.button()
            == Qt.MouseButton.LeftButton
        ):
            value = (
                self._apply_pointer_position(
                    event.position().x()
                )
            )

            self._pointer_scrubbing = False

            self.scrub_committed.emit(
                value
            )

            event.accept()
            return

        super().mouseReleaseEvent(
            event
        )


class DashboardPage(QWidget):
    # ANIMATED_EQUALIZER
    # FINAL_GUIDE_DETAILS
    # HEADER_PREVIEW_POLISH
    # V2_DASHBOARD_PATCH
    # V2_THREE_COLUMN_POLISH
    navigate_requested = pyqtSignal(int)
    settings_section_requested = pyqtSignal(str)
    apply_presence_preset_requested = pyqtSignal(str)

    playback_control_requested = pyqtSignal(
        str,
        str,
        bool,
    )

    playback_seek_requested = pyqtSignal(
        float,
        str,
    )
    playback_shuffle_requested = pyqtSignal(bool, str)
    playback_repeat_requested = pyqtSignal(str, str)

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

        self.history_store = (
            HistoryStore()
        )

        self.source_preferences_store = (
            SourcePreferencesStore()
        )

        self.afk_preferences_store = (
            AfkPreferencesStore()
        )

        self.presence_preset_store = (
            PresencePresetStore()
        )

        self.dashboard_layout_store = (
            DashboardLayoutStore()
        )

        self.dashboard_profile_store = (
            DashboardLayoutProfileStore()
        )

        self.dashboard_layout_state = (
            self.dashboard_layout_store.load()
        )

        self._dashboard_layout_undo_stack = []
        self._dashboard_layout_redo_stack = []

        self._dashboard_layout_session_baseline = None
        self._dashboard_layout_session_card_ids = frozenset()
        self._dashboard_layout_session_valid = False

        self.custom_card_store = (
            CustomCardStore()
        )
        self.custom_cards = {
            card.card_id: card
            for card in self.custom_card_store.load()
        }

        self.song = Song(
            title="Waiting for media...",
            artist="",
            album="",
        )

        self._last_artwork_signature = None
        self._artwork_size = 112
        self._preview_artwork_size = 58
        self._branding_title = "03:37am Presence"
        self._last_worker_error = ""

        self.playback_presentation_clock = (
            PlaybackPresentationClock()
        )

        self.dashboard_drag_handles = {}
        self.dashboard_resize_handles = {}
        self.dashboard_action_handles = {}
        self.dashboard_delete_handles = {}

        self._dashboard_drag_card_id = None
        self._dashboard_drag_origin = None
        self._dashboard_drag_offset = QPoint()
        self._dashboard_drag_active = False
        self._dashboard_drag_original_layout = None
        self._dashboard_drag_original_geometry = None

        self._dashboard_resize_card_id = None
        self._dashboard_resize_origin = None
        self._dashboard_resize_active = False
        self._dashboard_resize_original_layout = None
        self._dashboard_resize_original_geometry = None

        self._dashboard_keyboard_card_id = None
        self._dashboard_keyboard_mode = None
        self._dashboard_keyboard_active = False
        self._dashboard_keyboard_original_layout = None
        self._dashboard_keyboard_original_geometry = None

        self._dashboard_editor_outline = None

        self.dashboard_snap_settings = QSettings()
        self.dashboard_snap_grid_size = 24
        self.dashboard_snap_to_grid = bool(
            self.dashboard_snap_settings.value(
                "dashboard/snap_to_grid",
                True,
                type=bool,
            )
        )

        self._recent_track_fetch_limit = 24
        self._recent_tracks = []
        self._recent_visible_capacity = 0
        self._quick_access_layout_mode = None

        self.build_ui()

        self.discord_avatar_loader = (
            DiscordAvatarLoader(
                self
            )
        )

        self.discord_avatar_loader.avatar_ready.connect(
            self.apply_discord_profile_avatar
        )

        self.spotify_audio_spectrum_service = (
            SpotifyAudioSpectrumService()
        )

        self.equalizer_timer = QTimer(
            self
        )
        self.equalizer_timer.setInterval(
            33
        )
        self.equalizer_timer.timeout.connect(
            self.advance_equalizer
        )

        self.playback_presentation_timer = QTimer(
            self
        )

        self.playback_presentation_timer.setInterval(
            250
        )

        self.playback_presentation_timer.timeout.connect(
            self.refresh_playback_presentation
        )

        self.playback_presentation_timer.start()

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

        self.refresh_dashboard_data()

        self.dashboard_timer = QTimer(
            self
        )

        self.dashboard_timer.timeout.connect(
            self.refresh_dashboard_data
        )

        self.dashboard_timer.start(
            5000
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
            18,
            16,
            18,
            12,
        )
        self.root_layout.setSpacing(9)

        header = QHBoxLayout()
        header.setSpacing(10)

        title_group = QVBoxLayout()
        title_group.setSpacing(1)

        self.page_title = QLabel(
            "Dashboard"
        )
        self.page_title.setObjectName(
            "pageTitle"
        )

        self.page_subtitle = QLabel(
            (
                "Overview of your activity "
                "and rich presence"
            )
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

        self.connection_card = QFrame()
        self.connection_card.setObjectName(
            "connectionCard"
        )

        connection_layout = QHBoxLayout(
            self.connection_card
        )
        connection_layout.setContentsMargins(
            12,
            7,
            12,
            7,
        )
        connection_layout.setSpacing(8)

        connection_dot = QLabel("●")
        connection_dot.setObjectName(
            "connectionDot"
        )

        connection_text = QVBoxLayout()
        connection_text.setSpacing(0)

        self.header_connection_status = QLabel(
            "Status: Waiting"
        )
        self.header_connection_status.setObjectName(
            "connectionStatus"
        )

        self.header_connection_detail = QLabel(
            "Discord connection"
        )
        self.header_connection_detail.setObjectName(
            "connectionDetail"
        )

        connection_text.addWidget(
            self.header_connection_status
        )
        connection_text.addWidget(
            self.header_connection_detail
        )

        connection_layout.addWidget(
            connection_dot
        )
        connection_layout.addLayout(
            connection_text
        )

        self.activity_badge = QLabel(
            "WAITING"
        )
        self.activity_badge.setObjectName(
            "activityBadge"
        )
        self.activity_badge.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        settings_shortcut = QPushButton("⚙")
        settings_shortcut.setObjectName(
            "headerSettingsButton"
        )
        settings_shortcut.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        settings_shortcut.setFixedSize(
            40,
            40,
        )
        settings_shortcut.clicked.connect(
            lambda:
            self.navigate_requested.emit(3)
        )

        header.addLayout(title_group)
        header.addStretch()
        header.addWidget(
            self.connection_card
        )
        header.addWidget(
            self.activity_badge
        )
        header.addWidget(
            settings_shortcut
        )

        self.root_layout.addLayout(header)

        self.build_dashboard_layout_toolbar()

        self.root_layout.addWidget(
            self.layout_toolbar
        )

        self.dashboard_canvas = DashboardCanvas()
        self.dashboard_canvas.setObjectName(
            "dashboardCanvas"
        )
        self.dashboard_canvas.setMinimumHeight(
            650
        )
        self.dashboard_canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self.build_now_playing_card()
        self.build_discord_preview_card()
        self.build_recent_card()
        self.build_quick_access_card()
        self.build_library_status_card()
        self.build_queue_card()

        self.now_playing_card.setMinimumHeight(
            220
        )
        self.preview_card.setMinimumHeight(
            220
        )
        self.recent_card.setMinimumHeight(
            270
        )
        self.quick_access_card.setMinimumHeight(
            270
        )
        self.library_status_card.setMinimumHeight(
            270
        )

        (
            self.discord_card,
            self.discord_status,
            self.discord_status_detail,
        ) = self.make_status_card(
            "💬",
            "DISCORD STATUS",
            "Not connected",
            "Ready to update rich presence",
        )

        (
            self.music_card,
            self.music_status,
            self.music_status_detail,
        ) = self.make_status_card(
            "🎵",
            "MUSIC STATUS",
            "Starting",
            "Listening for new tracks",
        )

        (
            self.afk_card,
            self.afk_status,
            self.afk_status_detail,
        ) = self.make_status_card(
            "⏱",
            "AUTO AFK",
            "Inactive",
            "Auto AFK is disabled",
            button_text="⚙  Configure",
            button_section="auto_afk",
        )

        self.artwork_status = QLabel("")

        self.dashboard_cards = {
            "now_playing": (
                self.now_playing_card
            ),
            "discord_preview": (
                self.preview_card
            ),
            "recently_played": (
                self.recent_card
            ),
            "quick_access": (
                self.quick_access_card
            ),
            "library_status": (
                self.library_status_card
            ),
            "discord_status": (
                self.discord_card
            ),
            "music_status": (
                self.music_card
            ),
            "auto_afk": (
                self.afk_card
            ),
            "queue": (
                self.queue_card
            ),
        }

        self.build_saved_custom_cards()
        self.reconcile_custom_card_layouts()

        for card in self.dashboard_cards.values():
            card.setParent(
                self.dashboard_canvas
            )

        self.create_dashboard_drag_handles()

        self.apply_dashboard_layout(
            self.dashboard_layout_state
        )

        self.root_layout.addWidget(
            self.dashboard_canvas,
            stretch=1,
        )

        footer = QFrame()
        footer.setObjectName(
            "dashboardFooter"
        )

        footer_layout = QHBoxLayout(
            footer
        )
        footer_layout.setContentsMargins(
            12,
            5,
            12,
            5,
        )

        footer_left = QLabel(
            "💜  Thank you for using "
            "03:37am Presence!"
        )
        footer_left.setObjectName(
            "footerText"
        )

        footer_right = QLabel(
            "Made with  💜  for your presence."
        )
        footer_right.setObjectName(
            "footerText"
        )

        footer_layout.addWidget(
            footer_left
        )
        footer_layout.addStretch()
        footer_layout.addWidget(
            footer_right
        )

        self.root_layout.addWidget(
            footer
        )


    def create_dashboard_drag_handles(self):
        for (
            card_id,
            card,
        ) in self.dashboard_cards.items():
            self.create_dashboard_card_handles(
                card_id,
                card,
            )

        self._dashboard_editor_outline = QFrame(
            self.dashboard_canvas
        )
        self._dashboard_editor_outline.setObjectName(
            "dashboardEditorOutline"
        )
        self._dashboard_editor_outline.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        self._dashboard_editor_outline.hide()

        self.sync_dashboard_drag_handles()

    def create_dashboard_card_handles(
        self,
        card_id: str,
        card,
    ):
        if card_id in self.dashboard_drag_handles:
            return

        card_title = dashboard_card_spec(
            card_id
        ).title

        move_handle = QLabel(
            "DRAG",
            self.dashboard_canvas,
        )
        move_handle.setObjectName(
            "dashboardDragHandle"
        )
        move_handle.setProperty(
            "cardId",
            card_id,
        )
        move_handle.setProperty(
            "editorAction",
            "move",
        )
        move_handle.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        move_handle.setCursor(
            Qt.CursorShape.OpenHandCursor
        )
        move_handle.setFixedSize(
            44,
            20,
        )
        move_handle.setFocusPolicy(
            Qt.FocusPolicy.StrongFocus
        )
        move_handle.setAccessibleName(
            f"Move {card_title}"
        )
        move_handle.setToolTip(
            (
                "Drag to move. Keyboard: Arrow keys "
                "move 1px, Shift plus Arrow moves "
                "24px, Enter saves, Escape cancels."
            )
        )
        move_handle.setStatusTip(
            move_handle.toolTip()
        )
        move_handle.setAttribute(
            Qt.WidgetAttribute.WA_Hover,
            True,
        )
        move_handle.installEventFilter(
            self
        )

        resize_handle = QLabel(
            "SIZE",
            self.dashboard_canvas,
        )
        resize_handle.setObjectName(
            "dashboardResizeHandle"
        )
        resize_handle.setProperty(
            "cardId",
            card_id,
        )
        resize_handle.setProperty(
            "editorAction",
            "resize",
        )
        resize_handle.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        resize_handle.setCursor(
            Qt.CursorShape.SizeFDiagCursor
        )
        resize_handle.setFixedSize(
            34,
            20,
        )
        resize_handle.setFocusPolicy(
            Qt.FocusPolicy.StrongFocus
        )
        resize_handle.setAccessibleName(
            f"Resize {card_title}"
        )
        resize_handle.setToolTip(
            (
                "Drag to resize. Keyboard: Arrow "
                "keys resize 1px, Shift plus Arrow "
                "resizes 24px, Enter saves, "
                "Escape cancels."
            )
        )
        resize_handle.setStatusTip(
            resize_handle.toolTip()
        )
        resize_handle.setAttribute(
            Qt.WidgetAttribute.WA_Hover,
            True,
        )
        resize_handle.installEventFilter(
            self
        )

        action_handle = None
        delete_handle = None

        if is_custom_dashboard_card_id(card_id):
            action_handle = QPushButton(
                "...",
                self.dashboard_canvas,
            )
            action_handle.setObjectName(
                "dashboardCustomActionHandle"
            )
            action_handle.setCursor(
                Qt.CursorShape.PointingHandCursor
            )
            action_handle.setFixedSize(
                30,
                20,
            )
            action_handle.setToolTip(
                "Edit or duplicate this custom card"
            )

            action_menu = QMenu(action_handle)

            card_data = self.custom_cards.get(
                card_id
            )

            if isinstance(
                card_data,
                LauncherCardData,
            ):
                card_kind = "Launcher"
            elif isinstance(
                card_data,
                LinkCardData,
            ):
                card_kind = "Link"
            else:
                card_kind = "Custom"

            edit_action = QAction(
                f"Edit {card_kind} card",
                action_menu,
            )
            edit_action.triggered.connect(
                lambda checked=False, current_card_id=card_id:
                self.edit_custom_card(
                    current_card_id
                )
            )
            action_menu.addAction(edit_action)

            duplicate_action = QAction(
                f"Duplicate {card_kind} card",
                action_menu,
            )
            duplicate_action.triggered.connect(
                lambda checked=False, current_card_id=card_id:
                self.duplicate_custom_card(
                    current_card_id
                )
            )
            action_menu.addAction(duplicate_action)

            action_handle.setMenu(action_menu)

            delete_handle = QPushButton(
                "X",
                self.dashboard_canvas,
            )
            delete_handle.setObjectName(
                "dashboardDeleteHandle"
            )
            delete_handle.setCursor(
                Qt.CursorShape.PointingHandCursor
            )
            delete_handle.setFixedSize(
                20,
                20,
            )
            delete_handle.setToolTip(
                "Delete this custom card"
            )
            delete_handle.clicked.connect(
                lambda checked=False, current_card_id=card_id:
                self.confirm_delete_custom_card(
                    current_card_id
                )
            )

        self.dashboard_drag_handles[
            card_id
        ] = move_handle
        self.dashboard_resize_handles[
            card_id
        ] = resize_handle

        if action_handle is not None:
            self.dashboard_action_handles[
                card_id
            ] = action_handle

        if delete_handle is not None:
            self.dashboard_delete_handles[
                card_id
            ] = delete_handle

        if card.parentWidget() is not self.dashboard_canvas:
            card.setParent(self.dashboard_canvas)

        self.sync_dashboard_card_handle_accessibility(
            card_id
        )

    def update_dashboard_canvas_editor_state(
        self,
    ):
        canvas = getattr(
            self,
            "dashboard_canvas",
            None,
        )

        if canvas is None:
            return

        locked = bool(
            self.dashboard_layout_state.locked
        )

        editing = not locked

        canvas.setProperty(
            "editing",
            editing,
        )

        if hasattr(
            canvas,
            "set_grid_spacing",
        ):
            canvas.set_grid_spacing(
                self.dashboard_snap_grid_size
            )

        if hasattr(
            canvas,
            "set_snap_enabled",
        ):
            canvas.set_snap_enabled(
                self.dashboard_snap_to_grid
            )

        self._refresh_dashboard_widget_style(
            canvas
        )

        canvas.update()

        for card in getattr(
            self,
            "dashboard_cards",
            {},
        ).values():
            card.setProperty(
                "dashboardEditing",
                editing,
            )

            self._refresh_dashboard_widget_style(
                card
            )

    def sync_dashboard_drag_handles(self):
        move_handles = getattr(
            self,
            "dashboard_drag_handles",
            {},
        )

        resize_handles = getattr(
            self,
            "dashboard_resize_handles",
            {},
        )

        action_handles = getattr(
            self,
            "dashboard_action_handles",
            {},
        )

        delete_handles = getattr(
            self,
            "dashboard_delete_handles",
            {},
        )

        self.update_dashboard_canvas_editor_state()

        if not move_handles:
            return

        locked = (
            self.dashboard_layout_state.locked
        )

        for card_id, move_handle in (
            move_handles.items()
        ):
            resize_handle = resize_handles.get(
                card_id
            )

            action_handle = action_handles.get(
                card_id
            )

            delete_handle = delete_handles.get(
                card_id
            )

            try:
                card_layout = (
                    self.dashboard_layout_state.card(
                        card_id
                    )
                )
            except KeyError:
                move_handle.hide()

                if resize_handle is not None:
                    resize_handle.hide()

                if action_handle is not None:
                    action_handle.hide()

                if delete_handle is not None:
                    delete_handle.hide()

                continue

            editable = (
                not locked
                and card_layout.visible
            )

            move_handle.setVisible(
                editable
            )
            move_handle.setEnabled(
                editable
            )

            move_handle.setCursor(
                (
                    Qt.CursorShape.OpenHandCursor
                    if editable
                    else Qt.CursorShape.ArrowCursor
                )
            )

            if resize_handle is not None:
                resize_editable = (
                    editable
                    and dashboard_card_spec(
                        card_id
                    ).resizable
                )

                resize_handle.setVisible(
                    resize_editable
                )
                resize_handle.setEnabled(
                    resize_editable
                )

                resize_handle.setCursor(
                    (
                        Qt.CursorShape.SizeFDiagCursor
                        if editable
                        else Qt.CursorShape.ArrowCursor
                    )
                )

            self.sync_dashboard_card_handle_accessibility(
                card_id
            )

            if action_handle is not None:
                action_handle.setVisible(
                    editable
                )
                action_handle.setEnabled(
                    editable
                )

            if delete_handle is not None:
                delete_handle.setVisible(
                    editable
                )
                delete_handle.setEnabled(
                    editable
                )

        if locked:
            self.clear_dashboard_alignment_guides()
            self.hide_dashboard_editor_outline()

        QTimer.singleShot(
            0,
            self.position_dashboard_drag_handles,
        )

    def position_dashboard_drag_handles(self):
        if not hasattr(
            self,
            "dashboard_canvas",
        ):
            return

        canvas_width = max(
            1,
            self.dashboard_canvas.width(),
        )

        canvas_height = max(
            1,
            self.dashboard_canvas.height(),
        )

        handle_inset = 6

        resize_handles = getattr(
            self,
            "dashboard_resize_handles",
            {},
        )

        action_handles = getattr(
            self,
            "dashboard_action_handles",
            {},
        )

        delete_handles = getattr(
            self,
            "dashboard_delete_handles",
            {},
        )

        for (
            card_id,
            move_handle,
        ) in getattr(
            self,
            "dashboard_drag_handles",
            {},
        ).items():
            card = self.dashboard_cards.get(
                card_id
            )

            if card is None:
                continue

            move_x = (
                card.x()
                + (
                    card.width()
                    - move_handle.width()
                )
                // 2
            )

            move_y = (
                card.y()
                + handle_inset
            )

            move_x = min(
                max(
                    0,
                    move_x,
                ),
                max(
                    0,
                    (
                        canvas_width
                        - move_handle.width()
                    ),
                ),
            )

            move_y = min(
                max(
                    0,
                    move_y,
                ),
                max(
                    0,
                    (
                        canvas_height
                        - move_handle.height()
                    ),
                ),
            )

            move_handle.move(
                move_x,
                move_y,
            )

            move_handle.raise_()

            action_handle = action_handles.get(
                card_id
            )

            if action_handle is not None:
                action_x = (
                    card.x()
                    + handle_inset
                )

                action_y = (
                    card.y()
                    + handle_inset
                )

                action_x = min(
                    max(
                        0,
                        action_x,
                    ),
                    max(
                        0,
                        (
                            canvas_width
                            - action_handle.width()
                        ),
                    ),
                )

                action_y = min(
                    max(
                        0,
                        action_y,
                    ),
                    max(
                        0,
                        (
                            canvas_height
                            - action_handle.height()
                        ),
                    ),
                )

                action_handle.move(
                    action_x,
                    action_y,
                )
                action_handle.raise_()

            delete_handle = delete_handles.get(
                card_id
            )

            if delete_handle is not None:
                delete_x = (
                    card.x()
                    + card.width()
                    - delete_handle.width()
                    - handle_inset
                )

                delete_y = (
                    card.y()
                    + handle_inset
                )

                delete_x = min(
                    max(
                        0,
                        delete_x,
                    ),
                    max(
                        0,
                        (
                            canvas_width
                            - delete_handle.width()
                        ),
                    ),
                )

                delete_y = min(
                    max(
                        0,
                        delete_y,
                    ),
                    max(
                        0,
                        (
                            canvas_height
                            - delete_handle.height()
                        ),
                    ),
                )

                delete_handle.move(
                    delete_x,
                    delete_y,
                )
                delete_handle.raise_()

            resize_handle = resize_handles.get(
                card_id
            )

            if resize_handle is not None:
                resize_x = (
                    card.x()
                    + card.width()
                    - resize_handle.width()
                    - handle_inset
                )

                resize_y = (
                    card.y()
                    + card.height()
                    - resize_handle.height()
                    - handle_inset
                )

                resize_x = min(
                    max(
                        0,
                        resize_x,
                    ),
                    max(
                        0,
                        (
                            canvas_width
                            - resize_handle.width()
                        ),
                    ),
                )

                resize_y = min(
                    max(
                        0,
                        resize_y,
                    ),
                    max(
                        0,
                        (
                            canvas_height
                            - resize_handle.height()
                        ),
                    ),
                )

                resize_handle.move(
                    resize_x,
                    resize_y,
                )

                resize_handle.raise_()

        self.update_dashboard_editor_outline()

    @staticmethod
    def _refresh_dashboard_widget_style(
        widget,
    ):
        style = widget.style()

        style.unpolish(
            widget
        )
        style.polish(
            widget
        )

        widget.update()

    def dashboard_editor_outline_geometry(
        self,
        card,
    ):
        canvas_rect = (
            self.dashboard_canvas.rect()
        )

        outline_rect = (
            card.geometry()
            .adjusted(
                -2,
                -2,
                2,
                2,
            )
        )

        return outline_rect.intersected(
            canvas_rect
        )

    def show_dashboard_editor_outline(
        self,
        card_id: str,
        mode: str,
    ):
        outline = (
            self._dashboard_editor_outline
        )

        card = self.dashboard_cards.get(
            card_id
        )

        if outline is None or card is None:
            return

        if (
            outline.parentWidget()
            is not self.dashboard_canvas
        ):
            outline.setParent(
                self.dashboard_canvas
            )

        outline.setProperty(
            "editorMode",
            str(
                mode
                or "move"
            ),
        )

        self._refresh_dashboard_widget_style(
            outline
        )

        outline.setGeometry(
            self.dashboard_editor_outline_geometry(
                card
            )
        )

        outline.show()
        outline.raise_()

        move_handle = (
            self.dashboard_drag_handles.get(
                card_id
            )
        )

        resize_handle = (
            self.dashboard_resize_handles.get(
                card_id
            )
        )

        if move_handle is not None:
            move_handle.raise_()

        if resize_handle is not None:
            resize_handle.raise_()

        action_handle = (
            self.dashboard_action_handles.get(
                card_id
            )
        )

        if action_handle is not None:
            action_handle.raise_()

        delete_handle = (
            self.dashboard_delete_handles.get(
                card_id
            )
        )

        if delete_handle is not None:
            delete_handle.raise_()

    def update_dashboard_editor_outline(self):
        outline = (
            self._dashboard_editor_outline
        )

        if outline is None or not outline.isVisible():
            return

        if self._dashboard_resize_active:
            card_id = (
                self._dashboard_resize_card_id
            )
        else:
            card_id = (
                self._dashboard_drag_card_id
            )

        card = self.dashboard_cards.get(
            card_id
        )

        if card is None:
            outline.hide()
            return

        if (
            outline.parentWidget()
            is not self.dashboard_canvas
        ):
            outline.setParent(
                self.dashboard_canvas
            )

        outline.setGeometry(
            self.dashboard_editor_outline_geometry(
                card
            )
        )

        outline.raise_()

        move_handle = (
            self.dashboard_drag_handles.get(
                card_id
            )
        )

        resize_handle = (
            self.dashboard_resize_handles.get(
                card_id
            )
        )

        if move_handle is not None:
            move_handle.raise_()

        if resize_handle is not None:
            resize_handle.raise_()

        action_handle = (
            self.dashboard_action_handles.get(
                card_id
            )
        )

        if action_handle is not None:
            action_handle.raise_()

        delete_handle = (
            self.dashboard_delete_handles.get(
                card_id
            )
        )

        if delete_handle is not None:
            delete_handle.raise_()

    def hide_dashboard_editor_outline(self):
        outline = (
            self._dashboard_editor_outline
        )

        if outline is not None:
            outline.hide()

    def schedule_dashboard_geometry_refresh(self):
        QTimer.singleShot(
            0,
            self.apply_dashboard_layout_geometry,
        )

    def apply_dashboard_layout_geometry(self):
        if (
            not hasattr(
                self,
                "dashboard_canvas",
            )
            or self._dashboard_drag_active
            or self._dashboard_resize_active
        ):
            return

        canvas_width = max(
            1,
            self.dashboard_canvas.width(),
        )

        canvas_height = max(
            1,
            self.dashboard_canvas.height(),
        )

        visible_cards = []

        for layout_order, card_layout in enumerate(
            self.dashboard_layout_state.cards
        ):
            card = self.dashboard_cards.get(
                card_layout.card_id
            )

            if card is None:
                continue

            x = round(
                (
                    card_layout.x
                    / CANVAS_UNITS
                )
                * canvas_width
            )

            y = round(
                (
                    card_layout.y
                    / CANVAS_UNITS
                )
                * canvas_height
            )

            width = max(
                1,
                round(
                    (
                        card_layout.width
                        / CANVAS_UNITS
                    )
                    * canvas_width
                ),
            )

            height = max(
                1,
                round(
                    (
                        card_layout.height
                        / CANVAS_UNITS
                    )
                    * canvas_height
                ),
            )

            width = min(
                width,
                canvas_width - x,
            )

            height = min(
                height,
                canvas_height - y,
            )

            card.setGeometry(
                x,
                y,
                max(
                    1,
                    width,
                ),
                max(
                    1,
                    height,
                ),
            )

            card.setVisible(
                card_layout.visible
            )

            if card_layout.visible:
                visible_cards.append(
                    (
                        card_layout.z_index,
                        layout_order,
                        card,
                    )
                )

        for (
            _,
            _,
            card,
        ) in sorted(
            visible_cards,
            key=lambda item: (
                item[0],
                item[1],
            ),
        ):
            card.raise_()

        self.update_responsive_dashboard_cards()
        self.position_dashboard_drag_handles()


    def dashboard_alignment_rectangles(
        self,
        exclude_card_id: str,
    ) -> tuple[
        AlignmentRect,
        ...,
    ]:
        rectangles = []

        for card_id, card in getattr(
            self,
            "dashboard_cards",
            {},
        ).items():
            if (
                card_id == exclude_card_id
                or card is None
                or card.isHidden()
            ):
                continue

            geometry = card.geometry()

            if (
                geometry.width() <= 0
                or geometry.height() <= 0
            ):
                continue

            rectangles.append(
                AlignmentRect(
                    x=geometry.x(),
                    y=geometry.y(),
                    width=geometry.width(),
                    height=geometry.height(),
                )
            )

        return tuple(rectangles)

    def set_dashboard_alignment_guides(
        self,
        guides,
    ):
        canvas = getattr(
            self,
            "dashboard_canvas",
            None,
        )

        if (
            canvas is not None
            and hasattr(
                canvas,
                "set_alignment_guides",
            )
        ):
            canvas.set_alignment_guides(
                guides
            )

    def clear_dashboard_alignment_guides(
        self,
    ):
        canvas = getattr(
            self,
            "dashboard_canvas",
            None,
        )

        if (
            canvas is not None
            and hasattr(
                canvas,
                "clear_alignment_guides",
            )
        ):
            canvas.clear_alignment_guides()

    def begin_dashboard_live_drag(
        self,
        card_id: str,
        global_position: QPoint,
    ) -> bool:
        if (
            self.dashboard_layout_state.locked
            or self._dashboard_drag_active
            or self._dashboard_resize_active
        ):
            return False

        card = self.dashboard_cards.get(
            card_id
        )

        if card is None:
            return False

        try:
            card_layout = (
                self.dashboard_layout_state.card(
                    card_id
                )
            )
        except KeyError:
            return False

        if not card_layout.visible:
            return False

        self._dashboard_drag_active = True
        self._dashboard_drag_original_layout = (
            self.dashboard_layout_state
        )
        self._dashboard_drag_original_geometry = (
            card.geometry()
        )

        card.raise_()

        self.show_dashboard_editor_outline(
            card_id,
            "move",
        )

        self.layout_status_label.setText(
            "Moving "
            + dashboard_card_spec(
                card_id
            ).title
        )

        return self.update_dashboard_live_drag(
            global_position
        )

    def update_dashboard_live_drag(
        self,
        global_position: QPoint,
    ) -> bool:
        if (
            not self._dashboard_drag_active
            or not self._dashboard_drag_card_id
        ):
            return False

        card = self.dashboard_cards.get(
            self._dashboard_drag_card_id
        )

        if card is None:
            return False

        cursor_position = (
            self.dashboard_canvas.mapFromGlobal(
                global_position
            )
        )

        requested_position = (
            cursor_position
            - self._dashboard_drag_offset
        )

        maximum_x = max(
            0,
            (
                self.dashboard_canvas.width()
                - card.width()
            ),
        )

        maximum_y = max(
            0,
            (
                self.dashboard_canvas.height()
                - card.height()
            ),
        )

        clamped_x = min(
            maximum_x,
            max(
                0,
                requested_position.x(),
            ),
        )

        clamped_y = min(
            maximum_y,
            max(
                0,
                requested_position.y(),
            ),
        )

        if self.dashboard_snap_to_grid:
            alignment = snap_moving_rect(
                requested_x=clamped_x,
                requested_y=clamped_y,
                width=card.width(),
                height=card.height(),
                canvas_width=(
                    self.dashboard_canvas.width()
                ),
                canvas_height=(
                    self.dashboard_canvas.height()
                ),
                other_rectangles=(
                    self.dashboard_alignment_rectangles(
                        self._dashboard_drag_card_id
                    )
                ),
            )

            clamped_x = (
                alignment.rect.x
                if alignment.snapped_x
                else self.snap_dashboard_pixel_value(
                    clamped_x,
                    0,
                    maximum_x,
                )
            )

            clamped_y = (
                alignment.rect.y
                if alignment.snapped_y
                else self.snap_dashboard_pixel_value(
                    clamped_y,
                    0,
                    maximum_y,
                )
            )

            self.set_dashboard_alignment_guides(
                alignment.guides
            )
        else:
            self.clear_dashboard_alignment_guides()

        card.move(
            clamped_x,
            clamped_y,
        )

        card.raise_()
        self.position_dashboard_drag_handles()

        return True

    def finish_dashboard_live_drag(
        self,
        commit: bool = True,
    ) -> bool:
        if not self._dashboard_drag_active:
            return False

        self.clear_dashboard_alignment_guides()

        card_id = (
            self._dashboard_drag_card_id
        )

        card = self.dashboard_cards.get(
            card_id
        )

        original_layout = (
            self._dashboard_drag_original_layout
        )

        original_geometry = (
            self._dashboard_drag_original_geometry
        )

        moved = bool(
            commit
            and card is not None
            and original_layout is not None
            and original_geometry is not None
            and card.pos()
            != original_geometry.topLeft()
        )

        self.hide_dashboard_editor_outline()

        self._dashboard_drag_active = False
        self._dashboard_drag_card_id = None
        self._dashboard_drag_origin = None
        self._dashboard_drag_offset = QPoint()
        self._dashboard_drag_original_layout = None
        self._dashboard_drag_original_geometry = None

        if not moved:
            if original_layout is not None:
                self.apply_dashboard_layout(
                    original_layout,
                    persist=False,
                    sync_controls=True,
                )
            else:
                self.sync_dashboard_layout_controls()

            return False

        canvas_width = max(
            1,
            self.dashboard_canvas.width(),
        )

        canvas_height = max(
            1,
            self.dashboard_canvas.height(),
        )

        current_layout = original_layout.card(
            card_id
        )

        x = round(
            (
                card.x()
                / canvas_width
            )
            * CANVAS_UNITS
        )

        y = round(
            (
                card.y()
                / canvas_height
            )
            * CANVAS_UNITS
        )

        x = min(
            CANVAS_UNITS
            - current_layout.width,
            max(
                0,
                x,
            ),
        )

        y = min(
            CANVAS_UNITS
            - current_layout.height,
            max(
                0,
                y,
            ),
        )

        highest_layer = max(
            card_layout.z_index
            for card_layout in (
                original_layout.cards
            )
        )

        try:
            updated = move_card_freeform(
                original_layout,
                card_id,
                x,
                y,
                z_index=min(
                    1000000,
                    highest_layer + 1,
                ),
            )

            self.apply_dashboard_layout(
                updated,
                persist=True,
                sync_controls=True,
                record_history=True,
                history_label="card move",
            )

        except ValueError as error:
            print(
                "Dashboard card move rejected: "
                f"{error}"
            )

            self.apply_dashboard_layout(
                original_layout,
                persist=False,
                sync_controls=True,
            )

            return False

        print(
            "Dashboard card moved freely: "
            f"{dashboard_card_spec(card_id).title}."
        )

        return True

    def cancel_dashboard_live_drag(self):
        self.finish_dashboard_live_drag(
            commit=False
        )

    def dashboard_minimum_card_size(
        self,
        card,
    ) -> tuple[int, int]:
        responsive_cards = {
            getattr(
                self,
                "recent_card",
                None,
            ),
            getattr(
                self,
                "quick_access_card",
                None,
            ),
        }

        custom_card_widgets = (
            LinkCardWidget,
            LauncherCardWidget,
        )

        if (
            card in responsive_cards
            or isinstance(
                card,
                custom_card_widgets,
            )
        ):
            hint_width = 0
            hint_height = 0
        else:
            hint = card.minimumSizeHint()
            hint_width = hint.width()
            hint_height = hint.height()

        if isinstance(
            card,
            custom_card_widgets,
        ):
            return (80, 70)

        minimum_width = max(
            180,
            card.minimumWidth(),
            hint_width,
        )

        minimum_height = max(
            68,
            card.minimumHeight(),
            hint_height,
        )

        return (
            minimum_width,
            minimum_height,
        )


    def begin_dashboard_live_resize(
        self,
        card_id: str,
        global_position: QPoint,
    ) -> bool:
        if (
            self.dashboard_layout_state.locked
            or self._dashboard_drag_active
            or self._dashboard_resize_active
        ):
            return False

        card = self.dashboard_cards.get(
            card_id
        )

        if card is None:
            return False

        try:
            card_layout = (
                self.dashboard_layout_state.card(
                    card_id
                )
            )
        except KeyError:
            return False

        if (
            not card_layout.visible
            or not dashboard_card_spec(
                card_id
            ).resizable
        ):
            return False

        self._dashboard_resize_active = True
        self._dashboard_resize_card_id = (
            card_id
        )
        self._dashboard_resize_origin = (
            global_position
        )
        self._dashboard_resize_original_layout = (
            self.dashboard_layout_state
        )
        self._dashboard_resize_original_geometry = (
            card.geometry()
        )

        card.raise_()

        self.show_dashboard_editor_outline(
            card_id,
            "resize",
        )

        self.layout_status_label.setText(
            "Resizing "
            + dashboard_card_spec(
                card_id
            ).title
        )

        return True

    def update_dashboard_live_resize(
        self,
        global_position: QPoint,
    ) -> bool:
        if (
            not self._dashboard_resize_active
            or not self._dashboard_resize_card_id
            or self._dashboard_resize_origin is None
            or self._dashboard_resize_original_geometry
            is None
        ):
            return False

        card = self.dashboard_cards.get(
            self._dashboard_resize_card_id
        )

        if card is None:
            return False

        delta = (
            global_position
            - self._dashboard_resize_origin
        )

        original_geometry = (
            self._dashboard_resize_original_geometry
        )

        minimum_width, minimum_height = (
            self.dashboard_minimum_card_size(
                card
            )
        )

        maximum_width = max(
            1,
            (
                self.dashboard_canvas.width()
                - card.x()
            ),
        )

        maximum_height = max(
            1,
            (
                self.dashboard_canvas.height()
                - card.y()
            ),
        )

        minimum_width = min(
            minimum_width,
            maximum_width,
        )

        minimum_height = min(
            minimum_height,
            maximum_height,
        )

        requested_width = (
            original_geometry.width()
            + delta.x()
        )

        requested_height = (
            original_geometry.height()
            + delta.y()
        )

        width = min(
            maximum_width,
            max(
                minimum_width,
                requested_width,
            ),
        )

        height = min(
            maximum_height,
            max(
                minimum_height,
                requested_height,
            ),
        )

        if self.dashboard_snap_to_grid:
            alignment = snap_resizing_rect(
                x=card.x(),
                y=card.y(),
                requested_width=width,
                requested_height=height,
                minimum_width=minimum_width,
                minimum_height=minimum_height,
                canvas_width=(
                    self.dashboard_canvas.width()
                ),
                canvas_height=(
                    self.dashboard_canvas.height()
                ),
                other_rectangles=(
                    self.dashboard_alignment_rectangles(
                        self._dashboard_resize_card_id
                    )
                ),
            )

            width = (
                alignment.rect.width
                if alignment.snapped_x
                else self.snap_dashboard_pixel_value(
                    width,
                    minimum_width,
                    maximum_width,
                )
            )

            height = (
                alignment.rect.height
                if alignment.snapped_y
                else self.snap_dashboard_pixel_value(
                    height,
                    minimum_height,
                    maximum_height,
                )
            )

            self.set_dashboard_alignment_guides(
                alignment.guides
            )
        else:
            self.clear_dashboard_alignment_guides()

        card.resize(
            width,
            height,
        )

        self.update_responsive_dashboard_cards(
            self._dashboard_resize_card_id
        )

        card.raise_()
        self.position_dashboard_drag_handles()

        return True

    def finish_dashboard_live_resize(
        self,
        commit: bool = True,
    ) -> bool:
        if not self._dashboard_resize_active:
            return False

        self.clear_dashboard_alignment_guides()

        card_id = (
            self._dashboard_resize_card_id
        )

        card = self.dashboard_cards.get(
            card_id
        )

        original_layout = (
            self._dashboard_resize_original_layout
        )

        original_geometry = (
            self._dashboard_resize_original_geometry
        )

        resized = bool(
            commit
            and card is not None
            and original_layout is not None
            and original_geometry is not None
            and card.size()
            != original_geometry.size()
        )

        self.hide_dashboard_editor_outline()

        self._dashboard_resize_active = False
        self._dashboard_resize_card_id = None
        self._dashboard_resize_origin = None
        self._dashboard_resize_original_layout = None
        self._dashboard_resize_original_geometry = None

        if not resized:
            if original_layout is not None:
                self.apply_dashboard_layout(
                    original_layout,
                    persist=False,
                    sync_controls=True,
                )
            else:
                self.sync_dashboard_layout_controls()

            return False

        canvas_width = max(
            1,
            self.dashboard_canvas.width(),
        )

        canvas_height = max(
            1,
            self.dashboard_canvas.height(),
        )

        current_layout = original_layout.card(
            card_id
        )

        width = round(
            (
                card.width()
                / canvas_width
            )
            * CANVAS_UNITS
        )

        height = round(
            (
                card.height()
                / canvas_height
            )
            * CANVAS_UNITS
        )

        width = min(
            CANVAS_UNITS
            - current_layout.x,
            max(
                1,
                width,
            ),
        )

        height = min(
            CANVAS_UNITS
            - current_layout.y,
            max(
                1,
                height,
            ),
        )

        highest_layer = max(
            card_layout.z_index
            for card_layout in (
                original_layout.cards
            )
        )

        try:
            updated = resize_card_freeform(
                original_layout,
                card_id,
                width,
                height,
                z_index=min(
                    1000000,
                    highest_layer + 1,
                ),
            )

            self.apply_dashboard_layout(
                updated,
                persist=True,
                sync_controls=True,
                record_history=True,
                history_label="card resize",
            )

        except ValueError as error:
            print(
                "Dashboard card resize rejected: "
                f"{error}"
            )

            self.apply_dashboard_layout(
                original_layout,
                persist=False,
                sync_controls=True,
            )

            return False

        print(
            "Dashboard card resized freely: "
            f"{dashboard_card_spec(card_id).title}."
        )

        return True

    def cancel_dashboard_live_resize(self):
        self.finish_dashboard_live_resize(
            commit=False
        )


    def sync_dashboard_card_handle_accessibility(
        self,
        card_id: str,
    ):
        card = getattr(
            self,
            "dashboard_cards",
            {},
        ).get(
            card_id
        )

        move_handle = getattr(
            self,
            "dashboard_drag_handles",
            {},
        ).get(
            card_id
        )

        resize_handle = getattr(
            self,
            "dashboard_resize_handles",
            {},
        ).get(
            card_id
        )

        if card is None:
            return

        title = dashboard_card_spec(
            card_id
        ).title

        geometry = card.geometry()

        summary = (
            f"Position {geometry.x()}, "
            f"{geometry.y()} pixels. "
            f"Size {geometry.width()} by "
            f"{geometry.height()} pixels."
        )

        step = max(
            1,
            int(
                getattr(
                    self,
                    "dashboard_snap_grid_size",
                    24,
                )
            ),
        )

        if move_handle is not None:
            move_handle.setAccessibleName(
                f"Move {title}"
            )
            move_handle.setAccessibleDescription(
                (
                    f"{summary} Use Arrow keys to "
                    "move by 1 pixel. Hold Shift to "
                    f"move by {step} pixels. "
                    "Hold Control to resize instead. "
                    "Press Enter to save or Escape "
                    "to cancel."
                )
            )
            move_handle.setStatusTip(
                move_handle.toolTip()
            )

        if resize_handle is not None:
            resize_handle.setAccessibleName(
                f"Resize {title}"
            )
            resize_handle.setAccessibleDescription(
                (
                    f"{summary} Use Arrow keys to "
                    "resize by 1 pixel. Hold Shift "
                    f"to resize by {step} pixels. "
                    "Press Enter to save or Escape "
                    "to cancel."
                )
            )
            resize_handle.setStatusTip(
                resize_handle.toolTip()
            )

    def reset_dashboard_keyboard_adjustment_state(
        self,
    ):
        self._dashboard_keyboard_card_id = None
        self._dashboard_keyboard_mode = None
        self._dashboard_keyboard_active = False
        self._dashboard_keyboard_original_layout = None
        self._dashboard_keyboard_original_geometry = None

    def begin_dashboard_keyboard_adjustment(
        self,
        card_id: str,
        mode: str,
    ) -> bool:
        if mode not in {
            "move",
            "resize",
        }:
            return False

        if (
            self.dashboard_layout_state.locked
            or getattr(
                self,
                "_dashboard_drag_active",
                False,
            )
            or getattr(
                self,
                "_dashboard_resize_active",
                False,
            )
        ):
            return False

        card = self.dashboard_cards.get(
            card_id
        )

        if card is None:
            return False

        try:
            card_layout = (
                self.dashboard_layout_state.card(
                    card_id
                )
            )
        except KeyError:
            return False

        if not card_layout.visible:
            return False

        if (
            mode == "resize"
            and not dashboard_card_spec(
                card_id
            ).resizable
        ):
            return False

        if getattr(
            self,
            "_dashboard_keyboard_active",
            False,
        ):
            if (
                self._dashboard_keyboard_card_id
                == card_id
                and self._dashboard_keyboard_mode
                == mode
            ):
                return True

            self.finish_dashboard_keyboard_adjustment(
                commit=True
            )

        self._dashboard_keyboard_card_id = (
            card_id
        )
        self._dashboard_keyboard_mode = mode
        self._dashboard_keyboard_active = True
        self._dashboard_keyboard_original_layout = (
            self.dashboard_layout_state
        )
        self._dashboard_keyboard_original_geometry = (
            card.geometry()
        )

        card.raise_()

        self.show_dashboard_editor_outline(
            card_id,
            mode,
        )

        return True

    def update_dashboard_keyboard_adjustment(
        self,
        card_id: str,
        mode: str,
        delta_x: int,
        delta_y: int,
    ) -> bool:
        if not self.begin_dashboard_keyboard_adjustment(
            card_id,
            mode,
        ):
            return False

        card = self.dashboard_cards.get(
            card_id
        )

        if card is None:
            return False

        geometry = card.geometry()

        canvas_width = max(
            1,
            self.dashboard_canvas.width(),
        )
        canvas_height = max(
            1,
            self.dashboard_canvas.height(),
        )

        if mode == "move":
            x = min(
                max(
                    0,
                    canvas_width
                    - geometry.width(),
                ),
                max(
                    0,
                    geometry.x()
                    + int(delta_x),
                ),
            )

            y = min(
                max(
                    0,
                    canvas_height
                    - geometry.height(),
                ),
                max(
                    0,
                    geometry.y()
                    + int(delta_y),
                ),
            )

            card.move(
                x,
                y,
            )

            status = (
                f"Moving "
                f"{dashboard_card_spec(card_id).title}: "
                f"{x}, {y} pixels. "
                "Enter saves; Escape cancels."
            )
        else:
            (
                requested_width,
                requested_height,
            ) = self.dashboard_minimum_card_size(
                card
            )

            maximum_width = max(
                1,
                canvas_width - geometry.x(),
            )
            maximum_height = max(
                1,
                canvas_height - geometry.y(),
            )

            minimum_width = min(
                maximum_width,
                max(
                    1,
                    requested_width,
                ),
            )

            minimum_height = min(
                maximum_height,
                max(
                    1,
                    requested_height,
                ),
            )

            width = min(
                maximum_width,
                max(
                    minimum_width,
                    geometry.width()
                    + int(delta_x),
                ),
            )

            height = min(
                maximum_height,
                max(
                    minimum_height,
                    geometry.height()
                    + int(delta_y),
                ),
            )

            card.resize(
                width,
                height,
            )

            status = (
                f"Resizing "
                f"{dashboard_card_spec(card_id).title}: "
                f"{width} by {height} pixels. "
                "Enter saves; Escape cancels."
            )

        card.raise_()

        self.position_dashboard_drag_handles()

        self.show_dashboard_editor_outline(
            card_id,
            mode,
        )

        self.sync_dashboard_card_handle_accessibility(
            card_id
        )

        self.layout_status_label.setText(
            status
        )

        return True

    def finish_dashboard_keyboard_adjustment(
        self,
        commit: bool = True,
    ) -> bool:
        if not getattr(
            self,
            "_dashboard_keyboard_active",
            False,
        ):
            return False

        card_id = (
            self._dashboard_keyboard_card_id
        )
        mode = (
            self._dashboard_keyboard_mode
        )
        original_layout = (
            self._dashboard_keyboard_original_layout
        )
        original_geometry = (
            self._dashboard_keyboard_original_geometry
        )

        card = self.dashboard_cards.get(
            card_id
        )

        if (
            card is None
            or original_layout is None
            or original_geometry is None
        ):
            self.reset_dashboard_keyboard_adjustment_state()
            self.hide_dashboard_editor_outline()
            return False

        final_geometry = card.geometry()

        changed = (
            final_geometry != original_geometry
        )

        self.reset_dashboard_keyboard_adjustment_state()
        self.hide_dashboard_editor_outline()

        if (
            not commit
            or not changed
        ):
            card.setGeometry(
                original_geometry
            )

            self.apply_dashboard_layout(
                original_layout,
                persist=False,
                sync_controls=True,
            )

            if not commit:
                self.layout_status_label.setText(
                    "Keyboard card adjustment cancelled."
                )

            self.sync_dashboard_card_handle_accessibility(
                card_id
            )

            return False

        canvas_width = max(
            1,
            self.dashboard_canvas.width(),
        )
        canvas_height = max(
            1,
            self.dashboard_canvas.height(),
        )

        original_card = original_layout.card(
            card_id
        )

        highest_layer = max(
            item.z_index
            for item in original_layout.cards
        )

        next_layer = min(
            1000000,
            highest_layer + 1,
        )

        try:
            if mode == "move":
                x = round(
                    (
                        final_geometry.x()
                        / canvas_width
                    )
                    * CANVAS_UNITS
                )
                y = round(
                    (
                        final_geometry.y()
                        / canvas_height
                    )
                    * CANVAS_UNITS
                )

                x = min(
                    CANVAS_UNITS
                    - original_card.width,
                    max(
                        0,
                        x,
                    ),
                )
                y = min(
                    CANVAS_UNITS
                    - original_card.height,
                    max(
                        0,
                        y,
                    ),
                )

                updated = move_card_freeform(
                    original_layout,
                    card_id,
                    x,
                    y,
                    z_index=next_layer,
                )

                history_label = "card move"
            else:
                width = round(
                    (
                        final_geometry.width()
                        / canvas_width
                    )
                    * CANVAS_UNITS
                )
                height = round(
                    (
                        final_geometry.height()
                        / canvas_height
                    )
                    * CANVAS_UNITS
                )

                width = min(
                    CANVAS_UNITS
                    - original_card.x,
                    max(
                        1,
                        width,
                    ),
                )
                height = min(
                    CANVAS_UNITS
                    - original_card.y,
                    max(
                        1,
                        height,
                    ),
                )

                updated = resize_card_freeform(
                    original_layout,
                    card_id,
                    width,
                    height,
                    z_index=next_layer,
                )

                history_label = "card resize"

            self.apply_dashboard_layout(
                updated,
                persist=True,
                sync_controls=True,
                record_history=True,
                history_label=history_label,
            )
        except (KeyError, ValueError) as error:
            print(
                "Dashboard keyboard adjustment "
                f"rejected: {error}"
            )

            card.setGeometry(
                original_geometry
            )

            self.apply_dashboard_layout(
                original_layout,
                persist=False,
                sync_controls=True,
            )

            return False

        print(
            "Dashboard card adjusted with "
            f"keyboard: "
            f"{dashboard_card_spec(card_id).title}."
        )

        return True

    def cancel_dashboard_keyboard_adjustment(
        self,
    ) -> bool:
        was_active = bool(
            getattr(
                self,
                "_dashboard_keyboard_active",
                False,
            )
        )

        self.finish_dashboard_keyboard_adjustment(
            commit=False
        )

        return was_active

    def handle_dashboard_keyboard_edit_event(
        self,
        watched,
        event,
        is_move_handle: bool,
        is_resize_handle: bool,
        card_id: str,
    ) -> bool:
        event_type = event.type()

        if event_type == QEvent.Type.FocusIn:
            if (
                getattr(
                    self,
                    "_dashboard_keyboard_active",
                    False,
                )
                and self._dashboard_keyboard_card_id
                != card_id
            ):
                self.finish_dashboard_keyboard_adjustment(
                    commit=True
                )

            mode = (
                "resize"
                if is_resize_handle
                else "move"
            )

            self.show_dashboard_editor_outline(
                card_id,
                mode,
            )

            self.sync_dashboard_card_handle_accessibility(
                card_id
            )

            self.layout_status_label.setText(
                (
                    f"Keyboard {mode} ready for "
                    f"{dashboard_card_spec(card_id).title}. "
                    "Arrow keys adjust, Shift uses "
                    "the grid step, Enter saves, "
                    "and Escape cancels."
                )
            )

            return False

        if event_type == QEvent.Type.FocusOut:
            if (
                getattr(
                    self,
                    "_dashboard_keyboard_active",
                    False,
                )
                and self._dashboard_keyboard_card_id
                == card_id
            ):
                self.finish_dashboard_keyboard_adjustment(
                    commit=True
                )
            else:
                self.hide_dashboard_editor_outline()

            return False

        handled_keys = {
            Qt.Key.Key_Left,
            Qt.Key.Key_Right,
            Qt.Key.Key_Up,
            Qt.Key.Key_Down,
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
            Qt.Key.Key_Escape,
        }

        if (
            event_type
            == QEvent.Type.ShortcutOverride
            and event.key() in handled_keys
        ):
            event.accept()
            return True

        if event_type != QEvent.Type.KeyPress:
            return False

        key = event.key()

        if key in {
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
        }:
            self.finish_dashboard_keyboard_adjustment(
                commit=True
            )
            return True

        if key == Qt.Key.Key_Escape:
            if not self.cancel_dashboard_keyboard_adjustment():
                self.hide_dashboard_editor_outline()

            return True

        if key not in {
            Qt.Key.Key_Left,
            Qt.Key.Key_Right,
            Qt.Key.Key_Up,
            Qt.Key.Key_Down,
        }:
            return False

        modifiers = event.modifiers()

        if modifiers & (
            Qt.KeyboardModifier.AltModifier
            | Qt.KeyboardModifier.MetaModifier
        ):
            return False

        step = (
            max(
                1,
                int(
                    self.dashboard_snap_grid_size
                ),
            )
            if modifiers
            & Qt.KeyboardModifier.ShiftModifier
            else 1
        )

        delta_x = 0
        delta_y = 0

        if key == Qt.Key.Key_Left:
            delta_x = -step
        elif key == Qt.Key.Key_Right:
            delta_x = step
        elif key == Qt.Key.Key_Up:
            delta_y = -step
        elif key == Qt.Key.Key_Down:
            delta_y = step

        mode = (
            "resize"
            if is_resize_handle
            or (
                modifiers
                & Qt.KeyboardModifier.ControlModifier
            )
            else "move"
        )

        return self.update_dashboard_keyboard_adjustment(
            card_id,
            mode,
            delta_x,
            delta_y,
        )

    def eventFilter(
        self,
        watched,
        event,
    ):
        move_handles = getattr(
            self,
            "dashboard_drag_handles",
            {},
        )

        resize_handles = getattr(
            self,
            "dashboard_resize_handles",
            {},
        )

        is_move_handle = (
            watched in move_handles.values()
        )

        is_resize_handle = (
            watched in resize_handles.values()
        )

        if (
            not is_move_handle
            and not is_resize_handle
        ):
            return super().eventFilter(
                watched,
                event,
            )

        card_id = str(
            watched.property(
                "cardId"
            )
            or ""
        )

        if (
            not card_id
            or self.dashboard_layout_state.locked
        ):
            return super().eventFilter(
                watched,
                event,
            )

        if self.handle_dashboard_keyboard_edit_event(
            watched,
            event,
            is_move_handle,
            is_resize_handle,
            card_id,
        ):
            return True

        event_type = event.type()

        if (
            event_type
            == QEvent.Type.MouseButtonPress
            and event.button()
            == Qt.MouseButton.LeftButton
        ):
            if getattr(
                self,
                "_dashboard_keyboard_active",
                False,
            ):
                self.finish_dashboard_keyboard_adjustment(
                    commit=True
                )

            card = self.dashboard_cards.get(
                card_id
            )

            if card is None:
                return True

            global_position = (
                event.globalPosition().toPoint()
            )

            if is_resize_handle:
                self._dashboard_resize_card_id = (
                    card_id
                )
                self._dashboard_resize_origin = (
                    global_position
                )
                self._dashboard_resize_active = False

                watched.setCursor(
                    Qt.CursorShape.SizeFDiagCursor
                )

            else:
                card_top_left = card.mapToGlobal(
                    QPoint(
                        0,
                        0,
                    )
                )

                self._dashboard_drag_card_id = (
                    card_id
                )
                self._dashboard_drag_origin = (
                    global_position
                )
                self._dashboard_drag_offset = (
                    global_position
                    - card_top_left
                )
                self._dashboard_drag_active = False

                watched.setCursor(
                    Qt.CursorShape.ClosedHandCursor
                )

            return True

        if (
            event_type
            == QEvent.Type.MouseMove
            and (
                event.buttons()
                & Qt.MouseButton.LeftButton
            )
        ):
            current_position = (
                event.globalPosition().toPoint()
            )

            if (
                is_resize_handle
                and self._dashboard_resize_card_id
                == card_id
            ):
                origin = (
                    self._dashboard_resize_origin
                )

                if (
                    not self._dashboard_resize_active
                    and origin is not None
                    and (
                        current_position
                        - origin
                    ).manhattanLength()
                    >= QApplication.startDragDistance()
                ):
                    self.begin_dashboard_live_resize(
                        card_id,
                        origin,
                    )

                    self.update_dashboard_live_resize(
                        current_position
                    )

                elif self._dashboard_resize_active:
                    self.update_dashboard_live_resize(
                        current_position
                    )

                return True

            if (
                is_move_handle
                and self._dashboard_drag_card_id
                == card_id
            ):
                origin = (
                    self._dashboard_drag_origin
                )

                if (
                    not self._dashboard_drag_active
                    and origin is not None
                    and (
                        current_position
                        - origin
                    ).manhattanLength()
                    >= QApplication.startDragDistance()
                ):
                    self.begin_dashboard_live_drag(
                        card_id,
                        current_position,
                    )

                elif self._dashboard_drag_active:
                    self.update_dashboard_live_drag(
                        current_position
                    )

                return True

        if (
            event_type
            == QEvent.Type.MouseButtonRelease
            and event.button()
            == Qt.MouseButton.LeftButton
        ):
            release_position = (
                event.globalPosition().toPoint()
            )

            if (
                is_resize_handle
                and self._dashboard_resize_card_id
                == card_id
            ):
                was_active = (
                    self._dashboard_resize_active
                )

                if was_active:
                    self.update_dashboard_live_resize(
                        release_position
                    )

                    self.finish_dashboard_live_resize(
                        commit=True
                    )
                else:
                    self._dashboard_resize_card_id = None
                    self._dashboard_resize_origin = None

                    self.sync_dashboard_layout_controls()

                watched.setCursor(
                    Qt.CursorShape.SizeFDiagCursor
                )

                return True

            if (
                is_move_handle
                and self._dashboard_drag_card_id
                == card_id
            ):
                was_active = (
                    self._dashboard_drag_active
                )

                if was_active:
                    self.update_dashboard_live_drag(
                        release_position
                    )

                    self.finish_dashboard_live_drag(
                        commit=True
                    )
                else:
                    self._dashboard_drag_card_id = None
                    self._dashboard_drag_origin = None
                    self._dashboard_drag_offset = QPoint()

                    self.sync_dashboard_layout_controls()

                watched.setCursor(
                    Qt.CursorShape.OpenHandCursor
                )

                return True

        return super().eventFilter(
            watched,
            event,
        )


    def resizeEvent(
        self,
        event,
    ):
        super().resizeEvent(
            event
        )

        self.update_dashboard_layout_toolbar_responsive_state()
        self.schedule_dashboard_geometry_refresh()


    def configure_dashboard_layout_toolbar_accessibility(
        self,
    ):
        self.layout_toolbar.setAccessibleName(
            "Dashboard layout controls"
        )
        self.layout_toolbar.setAccessibleDescription(
            (
                "Controls for choosing, editing, "
                "and protecting the dashboard layout."
            )
        )

        self.layout_toolbar_title.setAccessibleName(
            "Dashboard control room"
        )
        self.layout_toolbar_hint.setAccessibleName(
            "Dashboard editing guidance"
        )
        self.layout_status_label.setAccessibleName(
            "Dashboard layout status"
        )

        self.layout_primary_group.setAccessibleName(
            "Dashboard layouts"
        )
        self.layout_primary_group.setAccessibleDescription(
            (
                "Choose a preset or manage saved "
                "dashboard layout profiles."
            )
        )

        self.layout_secondary_group.setAccessibleName(
            "Dashboard editing actions"
        )
        self.layout_secondary_group.setAccessibleDescription(
            (
                "Undo, redo, revert, arrange, add, "
                "show, hide, or reset dashboard cards."
            )
        )

        controls = (
            (
                self.layout_lock_button,
                "Dashboard layout editing",
                (
                    "Enter or finish dashboard "
                    "layout editing."
                ),
            ),
            (
                self.layout_preset_combo,
                "Dashboard layout preset",
                (
                    "Choose a dashboard layout "
                    "preset."
                ),
            ),
            (
                self.layout_profiles_button,
                "Dashboard layout profiles",
                (
                    "Save, apply, or delete "
                    "dashboard layout profiles."
                ),
            ),
            (
                self.layout_undo_button,
                "Undo dashboard layout change",
                (
                    "Undo the most recent dashboard "
                    "layout change."
                ),
            ),
            (
                self.layout_redo_button,
                "Redo dashboard layout change",
                (
                    "Redo the most recently undone "
                    "dashboard layout change."
                ),
            ),
            (
                self.layout_revert_session_button,
                "Revert dashboard editing session",
                (
                    "Restore the dashboard layout "
                    "from when editing began."
                ),
            ),
            (
                self.layout_snap_button,
                "Dashboard grid snapping",
                (
                    "Turn dashboard card grid "
                    "snapping on or off."
                ),
            ),
            (
                self.layout_add_card_button,
                "Add dashboard card",
                (
                    "Add a custom link or launcher "
                    "card to the dashboard."
                ),
            ),
            (
                self.layout_visibility_button,
                "Dashboard card visibility",
                (
                    "Choose which dashboard cards "
                    "are visible."
                ),
            ),
            (
                self.layout_reset_button,
                "Reset dashboard layout",
                (
                    "Restore the default dashboard "
                    "layout."
                ),
            ),
        )

        for (
            control,
            accessible_name,
            description,
        ) in controls:
            control.setFocusPolicy(
                Qt.FocusPolicy.StrongFocus
            )
            control.setAccessibleName(
                accessible_name
            )
            control.setAccessibleDescription(
                description
            )
            control.setStatusTip(
                description
            )

        for decorative_widget in (
            self.layout_toolbar,
            self.layout_toolbar_title,
            self.layout_toolbar_hint,
            self.layout_status_label,
            self.layout_primary_group,
            self.layout_secondary_group,
        ):
            decorative_widget.setFocusPolicy(
                Qt.FocusPolicy.NoFocus
            )

        self.layout_profiles_menu.setAccessibleName(
            "Dashboard layout profiles menu"
        )
        self.layout_add_card_menu.setAccessibleName(
            "Add dashboard card menu"
        )
        self.layout_visibility_menu.setAccessibleName(
            "Dashboard card visibility menu"
        )

        tab_sequence = (
            self.layout_lock_button,
            self.layout_preset_combo,
            self.layout_profiles_button,
            self.layout_undo_button,
            self.layout_redo_button,
            self.layout_revert_session_button,
            self.layout_snap_button,
            self.layout_add_card_button,
            self.layout_visibility_button,
            self.layout_reset_button,
        )

        for (
            first_control,
            second_control,
        ) in zip(
            tab_sequence,
            tab_sequence[1:],
        ):
            QWidget.setTabOrder(
                first_control,
                second_control,
            )

        self.sync_dashboard_layout_accessibility()

    def sync_dashboard_layout_accessibility(
        self,
    ):
        layout = getattr(
            self,
            "dashboard_layout_state",
            None,
        )

        locked = bool(
            layout is None
            or layout.locked
        )

        toolbar = getattr(
            self,
            "layout_toolbar",
            None,
        )

        if toolbar is None:
            return

        toolbar.setAccessibleDescription(
            (
                "The dashboard layout is locked. "
                "Activate Edit layout to make changes."
            )
            if locked
            else (
                "The dashboard layout is being edited. "
                "Use the controls to arrange cards, "
                "then activate Finish editing."
            )
        )

        status_label = getattr(
            self,
            "layout_status_label",
            None,
        )

        if status_label is not None:
            status_label.setAccessibleDescription(
                (
                    "Dashboard layout is locked."
                    if locked
                    else (
                        "Dashboard layout editing "
                        "is active."
                    )
                )
            )

        lock_button = getattr(
            self,
            "layout_lock_button",
            None,
        )

        if lock_button is not None:
            lock_button.setAccessibleName(
                (
                    "Edit dashboard layout"
                    if locked
                    else (
                        "Finish dashboard layout "
                        "editing"
                    )
                )
            )

        dynamic_controls = (
            getattr(
                self,
                "layout_lock_button",
                None,
            ),
            getattr(
                self,
                "layout_preset_combo",
                None,
            ),
            getattr(
                self,
                "layout_profiles_button",
                None,
            ),
            getattr(
                self,
                "layout_undo_button",
                None,
            ),
            getattr(
                self,
                "layout_redo_button",
                None,
            ),
            getattr(
                self,
                "layout_revert_session_button",
                None,
            ),
            getattr(
                self,
                "layout_snap_button",
                None,
            ),
            getattr(
                self,
                "layout_add_card_button",
                None,
            ),
            getattr(
                self,
                "layout_visibility_button",
                None,
            ),
            getattr(
                self,
                "layout_reset_button",
                None,
            ),
        )

        for control in dynamic_controls:
            if control is None:
                continue

            description = str(
                control.toolTip()
                or control.accessibleDescription()
                or ""
            ).strip()

            if description:
                control.setAccessibleDescription(
                    description
                )
                control.setStatusTip(
                    description
                )

            if isinstance(
                control,
                QPushButton,
            ):
                control.setCursor(
                    (
                        Qt.CursorShape.PointingHandCursor
                        if control.isEnabled()
                        else Qt.CursorShape.ArrowCursor
                    )
                )

    def update_dashboard_layout_toolbar_responsive_state(
        self,
    ):
        if not hasattr(
            self,
            "layout_toolbar",
        ):
            return

        compact = self.width() < 930

        density = (
            "compact"
            if compact
            else "standard"
        )

        self.layout_toolbar.setProperty(
            "density",
            density,
        )

        self.layout_toolbar_title.setText(
            "LAYOUT"
            if compact
            else "CONTROL ROOM"
        )

        self.layout_toolbar_hint.setVisible(
            not compact
        )

        self.layout_preset_combo.setMinimumWidth(
            118
            if compact
            else 150
        )

        self.layout_profiles_button.setText(
            "Profiles"
        )

        self.layout_add_card_button.setText(
            "Add"
            if compact
            else "Add card"
        )

        self.layout_visibility_button.setText(
            "Cards"
        )

        locked = True

        if hasattr(
            self,
            "dashboard_layout_state",
        ):
            locked = bool(
                self.dashboard_layout_state.locked
            )

        if compact:
            lock_text = (
                "Edit"
                if locked
                else "Done"
            )
        else:
            lock_text = (
                "Edit layout"
                if locked
                else "Finish editing"
            )

        self.layout_lock_button.setText(
            lock_text
        )

        margin = (
            8
            if compact
            else 11
        )

        spacing = (
            6
            if compact
            else 8
        )

        self.layout_toolbar_layout.setContentsMargins(
            margin,
            7,
            margin,
            7,
        )

        self.layout_toolbar_layout.setSpacing(
            spacing
        )

        self.layout_toolbar_header_layout.setSpacing(
            spacing
        )

        self.layout_toolbar_controls_layout.setSpacing(
            spacing
        )

        self.layout_primary_group_layout.setSpacing(
            5
            if compact
            else 7
        )

        self.layout_secondary_group_layout.setSpacing(
            5
            if compact
            else 7
        )

    def build_dashboard_layout_toolbar(self):
        self.layout_toolbar = QFrame()
        self.layout_toolbar.setObjectName(
            "dashboardLayoutToolbar"
        )
        self.layout_toolbar.setProperty(
            "layoutState",
            "locked",
        )
        self.layout_toolbar.setProperty(
            "density",
            "standard",
        )

        self.layout_toolbar_layout = QVBoxLayout(
            self.layout_toolbar
        )
        self.layout_toolbar_layout.setContentsMargins(
            11,
            7,
            11,
            7,
        )
        self.layout_toolbar_layout.setSpacing(8)

        self.layout_toolbar_header_layout = (
            QHBoxLayout()
        )
        self.layout_toolbar_header_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        self.layout_toolbar_header_layout.setSpacing(
            8
        )

        title_stack = QVBoxLayout()
        title_stack.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        title_stack.setSpacing(1)

        self.layout_toolbar_title = QLabel(
            "CONTROL ROOM"
        )
        self.layout_toolbar_title.setObjectName(
            "layoutToolbarTitle"
        )

        self.layout_toolbar_hint = QLabel(
            "Your dashboard is protected "
            "from accidental changes."
        )
        self.layout_toolbar_hint.setObjectName(
            "layoutToolbarHint"
        )

        title_stack.addWidget(
            self.layout_toolbar_title
        )
        title_stack.addWidget(
            self.layout_toolbar_hint
        )

        self.layout_status_label = QLabel(
            "LOCKED"
        )
        self.layout_status_label.setObjectName(
            "layoutToolbarStatus"
        )
        self.layout_status_label.setProperty(
            "layoutState",
            "locked",
        )
        self.layout_status_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.layout_lock_button = QPushButton(
            "Edit layout"
        )
        self.layout_lock_button.setObjectName(
            "layoutLockButton"
        )
        self.layout_lock_button.setProperty(
            "layoutState",
            "locked",
        )
        self.layout_lock_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.layout_lock_button.setToolTip(
            "Enter dashboard layout editing"
        )
        self.layout_lock_button.clicked.connect(
            self.toggle_dashboard_layout_lock
        )

        self.layout_toolbar_header_layout.addLayout(
            title_stack
        )
        self.layout_toolbar_header_layout.addStretch()
        self.layout_toolbar_header_layout.addWidget(
            self.layout_status_label
        )
        self.layout_toolbar_header_layout.addWidget(
            self.layout_lock_button
        )

        self.layout_toolbar_controls_layout = (
            QHBoxLayout()
        )
        self.layout_toolbar_controls_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        self.layout_toolbar_controls_layout.setSpacing(
            8
        )

        self.layout_primary_group = QFrame()
        self.layout_primary_group.setObjectName(
            "layoutToolbarGroup"
        )
        self.layout_primary_group.setProperty(
            "groupRole",
            "layout",
        )

        self.layout_primary_group_layout = (
            QHBoxLayout(
                self.layout_primary_group
            )
        )
        self.layout_primary_group_layout.setContentsMargins(
            8,
            4,
            8,
            4,
        )
        self.layout_primary_group_layout.setSpacing(
            7
        )

        layout_group_label = QLabel(
            "LAYOUT"
        )
        layout_group_label.setObjectName(
            "layoutToolbarGroupLabel"
        )

        self.layout_preset_combo = QComboBox()
        self.layout_preset_combo.setObjectName(
            "layoutPresetCombo"
        )
        self.layout_preset_combo.setMinimumWidth(
            150
        )
        self.layout_preset_combo.setPlaceholderText(
            "Custom"
        )
        self.layout_preset_combo.addItems(
            available_presets()
        )
        self.layout_preset_combo.setToolTip(
            "Choose a dashboard layout preset"
        )
        self.layout_preset_combo.currentTextChanged.connect(
            self.apply_dashboard_preset
        )

        self.layout_profiles_button = QPushButton(
            "Profiles"
        )
        self.layout_profiles_button.setObjectName(
            "layoutMenuButton"
        )
        self.layout_profiles_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.layout_profiles_button.setToolTip(
            "Save, apply, or delete dashboard "
            "layout profiles"
        )

        self.layout_profiles_menu = QMenu(
            self.layout_profiles_button
        )
        self.layout_profiles_menu.aboutToShow.connect(
            self.populate_dashboard_profiles_menu
        )
        self.layout_profiles_button.setMenu(
            self.layout_profiles_menu
        )

        self.layout_undo_button = QPushButton(
            "Undo"
        )
        self.layout_undo_button.setObjectName(
            "layoutControlButton"
        )
        self.layout_undo_button.setProperty(
            "historyRole",
            "undo",
        )
        self.layout_undo_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.layout_undo_button.setToolTip(
            "Nothing to undo"
        )
        self.layout_undo_button.clicked.connect(
            self.undo_dashboard_layout
        )

        self.layout_redo_button = QPushButton(
            "Redo"
        )
        self.layout_redo_button.setObjectName(
            "layoutControlButton"
        )
        self.layout_redo_button.setProperty(
            "historyRole",
            "redo",
        )
        self.layout_redo_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.layout_redo_button.setToolTip(
            "Nothing to redo"
        )
        self.layout_redo_button.clicked.connect(
            self.redo_dashboard_layout
        )

        self.layout_revert_session_button = QPushButton(
            "Revert"
        )
        self.layout_revert_session_button.setObjectName(
            "layoutControlButton"
        )
        self.layout_revert_session_button.setProperty(
            "sessionRole",
            "revert",
        )
        self.layout_revert_session_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.layout_revert_session_button.setToolTip(
            (
                "Edit the layout to begin "
                "a revert session."
            )
        )
        self.layout_revert_session_button.clicked.connect(
            lambda _checked=False: (
                DashboardPage
                .revert_dashboard_layout_session(
                    self
                )
            )
        )

        self.layout_snap_button = QPushButton(
            "Snap: On"
        )
        self.layout_snap_button.setObjectName(
            "layoutControlButton"
        )
        self.layout_snap_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.layout_snap_button.setCheckable(True)
        self.layout_snap_button.setToolTip(
            "Snap cards to a tidy grid while "
            "moving or resizing"
        )
        self.layout_snap_button.toggled.connect(
            self.set_dashboard_snap_enabled
        )
        self.update_dashboard_snap_button()

        self.layout_primary_group_layout.addWidget(
            layout_group_label
        )
        self.layout_primary_group_layout.addWidget(
            self.layout_preset_combo
        )
        self.layout_primary_group_layout.addWidget(
            self.layout_profiles_button
        )

        self.layout_secondary_group = QFrame()
        self.layout_secondary_group.setObjectName(
            "layoutToolbarGroup"
        )
        self.layout_secondary_group.setProperty(
            "groupRole",
            "editing",
        )

        self.layout_secondary_group_layout = (
            QHBoxLayout(
                self.layout_secondary_group
            )
        )
        self.layout_secondary_group_layout.setContentsMargins(
            8,
            4,
            8,
            4,
        )
        self.layout_secondary_group_layout.setSpacing(
            7
        )

        cards_group_label = QLabel(
            "EDITING"
        )
        cards_group_label.setObjectName(
            "layoutToolbarGroupLabel"
        )

        self.layout_add_card_button = QPushButton(
            "Add card"
        )
        self.layout_add_card_button.setObjectName(
            "layoutMenuButton"
        )
        self.layout_add_card_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.layout_add_card_button.setToolTip(
            "Add a card to the dashboard"
        )

        self.layout_add_card_menu = QMenu(
            self.layout_add_card_button
        )

        self.layout_add_queue_action = QAction(
            "Spotify Queue",
            self.layout_add_card_menu,
        )
        self.layout_add_queue_action.setToolTip(
            "Show your Spotify Queue on the dashboard"
        )
        self.layout_add_queue_action.triggered.connect(
            lambda _checked=False:
            DashboardPage.add_queue_card(
                self
            )
        )
        self.layout_add_card_menu.addAction(
            self.layout_add_queue_action
        )

        self.layout_add_link_action = QAction(
            "Link card",
            self.layout_add_card_menu,
        )
        self.layout_add_link_action.setToolTip(
            "Add a safe http:// or https:// shortcut"
        )
        self.layout_add_link_action.triggered.connect(
            self.add_link_card
        )
        self.layout_add_card_menu.addAction(
            self.layout_add_link_action
        )

        self.layout_add_launcher_action = QAction(
            "Launcher card",
            self.layout_add_card_menu,
        )
        self.layout_add_launcher_action.setToolTip(
            "Add a local application, file, "
            "or folder shortcut"
        )
        self.layout_add_launcher_action.triggered.connect(
            self.add_launcher_card
        )
        self.layout_add_card_menu.addAction(
            self.layout_add_launcher_action
        )

        self.layout_add_card_button.setMenu(
            self.layout_add_card_menu
        )

        self.layout_visibility_button = QPushButton(
            "Cards"
        )
        self.layout_visibility_button.setObjectName(
            "layoutMenuButton"
        )
        self.layout_visibility_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.layout_visibility_button.setToolTip(
            "Choose which dashboard cards "
            "are visible"
        )

        self.layout_visibility_menu = QMenu(
            self.layout_visibility_button
        )

        self.layout_visibility_actions = {}

        for card_id in CARD_ORDER:
            self.register_dashboard_visibility_action(
                card_id,
                CARD_SPECS[card_id].title,
            )

        for card in self.custom_cards.values():
            self.register_dashboard_visibility_action(
                card.card_id,
                card.title,
            )

        self.layout_visibility_button.setMenu(
            self.layout_visibility_menu
        )

        self.layout_reset_button = QPushButton(
            "Reset"
        )
        self.layout_reset_button.setObjectName(
            "layoutControlButton"
        )
        self.layout_reset_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.layout_reset_button.setToolTip(
            "Restore the default dashboard layout"
        )
        self.layout_reset_button.clicked.connect(
            self.reset_dashboard_layout
        )

        self.layout_secondary_group_layout.addWidget(
            cards_group_label
        )
        self.layout_secondary_group_layout.addWidget(
            self.layout_undo_button
        )
        self.layout_secondary_group_layout.addWidget(
            self.layout_redo_button
        )
        self.layout_secondary_group_layout.addWidget(
            self.layout_revert_session_button
        )
        self.layout_secondary_group_layout.addWidget(
            self.layout_snap_button
        )
        self.layout_secondary_group_layout.addWidget(
            self.layout_add_card_button
        )
        self.layout_secondary_group_layout.addWidget(
            self.layout_visibility_button
        )
        self.layout_secondary_group_layout.addWidget(
            self.layout_reset_button
        )

        self.layout_toolbar_controls_layout.addWidget(
            self.layout_primary_group
        )
        self.layout_toolbar_controls_layout.addStretch()
        self.layout_toolbar_controls_layout.addWidget(
            self.layout_secondary_group
        )

        self.layout_toolbar_layout.addLayout(
            self.layout_toolbar_header_layout
        )
        self.layout_toolbar_layout.addLayout(
            self.layout_toolbar_controls_layout
        )

        self.configure_dashboard_layout_toolbar_accessibility()
        self.setup_dashboard_history_shortcuts()
        self.update_dashboard_layout_toolbar_responsive_state()
        self.update_dashboard_history_controls()



    def set_dashboard_snap_enabled(
        self,
        enabled: bool,
    ):
        self.dashboard_snap_to_grid = bool(
            enabled
        )

        if not self.dashboard_snap_to_grid:
            self.clear_dashboard_alignment_guides()

        self.dashboard_snap_settings.setValue(
            "dashboard/snap_to_grid",
            self.dashboard_snap_to_grid,
        )

        self.update_dashboard_snap_button()

    def update_dashboard_snap_button(self):
        button = getattr(
            self,
            "layout_snap_button",
            None,
        )

        if button is None:
            return

        blocker = QSignalBlocker(
            button
        )

        button.setChecked(
            self.dashboard_snap_to_grid
        )

        button.setText(
            "Snap: On"
            if self.dashboard_snap_to_grid
            else "Snap: Off"
        )

        button.setToolTip(
            (
                "Cards snap to a 24px grid, "
                "nearby card edges, and centres "
                "while moving or resizing"
            )
            if self.dashboard_snap_to_grid
            else (
                "Cards move and resize freely"
            )
        )

        del blocker

        canvas = getattr(
            self,
            "dashboard_canvas",
            None,
        )

        if (
            canvas is not None
            and hasattr(
                canvas,
                "set_snap_enabled",
            )
        ):
            canvas.set_snap_enabled(
                self.dashboard_snap_to_grid
            )

        accessibility_sync = getattr(
            self,
            "sync_dashboard_layout_accessibility",
            None,
        )

        if callable(accessibility_sync):
            accessibility_sync()


    def snap_dashboard_pixel_value(
        self,
        value: int,
        minimum: int,
        maximum: int,
    ) -> int:
        value = min(
            maximum,
            max(
                minimum,
                int(value),
            ),
        )

        if not self.dashboard_snap_to_grid:
            return value

        grid_size = max(
            1,
            int(
                self.dashboard_snap_grid_size
            ),
        )

        snapped = int(
            round(value / grid_size)
            * grid_size
        )

        return min(
            maximum,
            max(
                minimum,
                snapped,
            ),
        )

    def register_dashboard_visibility_action(
        self,
        card_id: str,
        title: str,
    ):
        existing = self.layout_visibility_actions.get(
            card_id
        )

        if existing is not None:
            existing.setText(title)
            return existing

        action = QAction(
            title,
            self.layout_visibility_menu,
        )
        action.setCheckable(True)
        action.toggled.connect(
            lambda checked,
            current_card_id=card_id:
            self.set_dashboard_card_visibility(
                current_card_id,
                checked,
            )
        )
        self.layout_visibility_menu.addAction(action)
        self.layout_visibility_actions[card_id] = action
        return action

    def build_saved_custom_cards(self):
        for card in self.custom_cards.values():
            self.dashboard_cards[card.card_id] = (
                self.create_custom_card_widget(
                    card
                )
            )


    def create_custom_card_widget(
        self,
        card,
    ):
        if isinstance(
            card,
            LinkCardData,
        ):
            return self.create_link_card_widget(
                card
            )

        if isinstance(
            card,
            LauncherCardData,
        ):
            return self.create_launcher_card_widget(
                card
            )

        raise TypeError(
            "Unsupported custom card object."
        )

    def create_link_card_widget(
        self,
        card: LinkCardData,
    ) -> LinkCardWidget:
        widget = LinkCardWidget(
            card,
            self.dashboard_canvas,
        )
        widget.open_requested.connect(
            self.open_link_card_url
        )
        widget.set_theme(
            self.theme_manager.theme()
        )
        return widget

    def create_launcher_card_widget(
        self,
        card: LauncherCardData,
    ) -> LauncherCardWidget:
        widget = LauncherCardWidget(
            card,
            self.dashboard_canvas,
        )

        widget.launch_requested.connect(
            lambda _target,
            current_card_id=card.card_id:
            self.open_launcher_card_target(
                current_card_id
            )
        )
        widget.set_launch_enabled(True)
        widget.set_theme(
            self.theme_manager.theme()
        )

        return widget


    def default_custom_card_layout(
        self,
        card_id: str,
        existing_cards=None,
    ) -> DashboardCardLayout:
        cards = tuple(
            self.dashboard_layout_state.cards
            if existing_cards is None
            else existing_cards
        )
        custom_count = sum(
            1
            for card in cards
            if is_custom_dashboard_card_id(card.card_id)
        )
        offset = (custom_count % 8) * 180
        highest_layer = max(
            (
                card.z_index
                for card in cards
            ),
            default=0,
        )

        return DashboardCardLayout(
            card_id=card_id,
            x=3600 + offset,
            y=2700 + offset,
            width=2600,
            height=1900,
            z_index=highest_layer + 1,
            visible=True,
        )

    def reconcile_custom_card_layouts(self):
        stored_ids = set(self.custom_cards)
        original_cards = self.dashboard_layout_state.cards
        reconciled = [
            card
            for card in original_cards
            if (
                not is_custom_dashboard_card_id(card.card_id)
                or card.card_id in stored_ids
            )
        ]
        layout_ids = {
            card.card_id
            for card in reconciled
        }

        for card_id in self.custom_cards:
            if card_id in layout_ids:
                continue

            reconciled.append(
                self.default_custom_card_layout(
                    card_id,
                    existing_cards=reconciled,
                )
            )
            layout_ids.add(card_id)

        cards = tuple(reconciled)

        if cards == original_cards:
            return

        updated = replace(
            self.dashboard_layout_state,
            cards=cards,
            preset="Custom",
        )
        validated = validate_layout(updated)

        try:
            validated = self.dashboard_layout_store.save(
                validated
            )
        except OSError as error:
            print(
                "Custom dashboard layout repair could not "
                f"be saved: {error}"
            )

        self.dashboard_layout_state = validated

    def with_current_custom_layout_cards(
        self,
        layout: DashboardLayout,
    ) -> DashboardLayout:
        custom_layouts = tuple(
            card
            for card in self.dashboard_layout_state.cards
            if is_custom_dashboard_card_id(card.card_id)
        )

        if not custom_layouts:
            return layout

        return replace(
            layout,
            cards=layout.cards + custom_layouts,
            preset="Custom",
        )

    def dashboard_profile_layout_for_current_cards(
        self,
        layout: DashboardLayout,
    ) -> DashboardLayout:
        current_custom_layouts = {
            card.card_id: card
            for card in self.dashboard_layout_state.cards
            if is_custom_dashboard_card_id(
                card.card_id
            )
        }

        merged_cards = []
        used_custom_ids = set()

        for card in layout.cards:
            if is_custom_dashboard_card_id(
                card.card_id
            ):
                if card.card_id not in self.custom_cards:
                    continue

                used_custom_ids.add(
                    card.card_id
                )

            merged_cards.append(
                card
            )

        for card_id in self.custom_cards:
            if card_id in used_custom_ids:
                continue

            current_layout = current_custom_layouts.get(
                card_id
            )

            if current_layout is None:
                current_layout = (
                    self.default_custom_card_layout(
                        card_id,
                        existing_cards=merged_cards,
                    )
                )

            merged_cards.append(
                current_layout
            )
            used_custom_ids.add(
                card_id
            )

        return validate_layout(
            replace(
                layout,
                cards=tuple(
                    merged_cards
                ),
            )
        )

    def populate_dashboard_profiles_menu(
        self,
    ):
        self.layout_profiles_menu.clear()

        save_action = self.layout_profiles_menu.addAction(
            "💾  Save current layout..."
        )
        save_action.triggered.connect(
            self.save_current_dashboard_profile
        )

        profiles = self.dashboard_profile_store.load()

        self.layout_profiles_menu.addSeparator()

        apply_menu = self.layout_profiles_menu.addMenu(
            "Apply saved profile"
        )
        delete_menu = self.layout_profiles_menu.addMenu(
            "Delete saved profile"
        )

        if not profiles:
            empty_apply = apply_menu.addAction(
                "No saved profiles"
            )
            empty_apply.setEnabled(False)

            empty_delete = delete_menu.addAction(
                "No saved profiles"
            )
            empty_delete.setEnabled(False)
            return

        for profile in profiles:
            apply_action = apply_menu.addAction(
                profile.name
            )
            apply_action.triggered.connect(
                lambda checked=False,
                name=profile.name:
                self.apply_dashboard_profile(
                    name
                )
            )

            delete_action = delete_menu.addAction(
                profile.name
            )
            delete_action.triggered.connect(
                lambda checked=False,
                name=profile.name:
                self.delete_dashboard_profile(
                    name
                )
            )

    def save_current_dashboard_profile(
        self,
    ):
        if self.dashboard_layout_state.locked:
            self.sync_dashboard_layout_controls()
            return

        name, accepted = QInputDialog.getText(
            self,
            "Save dashboard profile",
            "Profile name:",
        )

        if not accepted:
            return

        try:
            profile_name = validate_profile_name(
                name
            )
        except ValueError as error:
            QMessageBox.warning(
                self,
                "Profile not saved",
                str(error),
            )
            return

        existing_names = {
            profile.name.casefold()
            for profile in self.dashboard_profile_store.load()
        }

        if profile_name.casefold() in existing_names:
            answer = QMessageBox.question(
                self,
                "Replace dashboard profile",
                (
                    f'Replace the saved "{profile_name}" '
                    "dashboard profile?"
                ),
                (
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No
                ),
                QMessageBox.StandardButton.No,
            )

            if answer != QMessageBox.StandardButton.Yes:
                return

        profile_layout = replace(
            self.dashboard_layout_state,
            preset=f"Profile: {profile_name}",
        )

        try:
            self.dashboard_profile_store.upsert(
                DashboardLayoutProfile(
                    name=profile_name,
                    layout=profile_layout,
                )
            )
        except (OSError, TypeError, ValueError) as error:
            QMessageBox.warning(
                self,
                "Profile not saved",
                str(error),
            )
            return

        QMessageBox.information(
            self,
            "Dashboard profile saved",
            f'Saved "{profile_name}".',
        )

    def apply_dashboard_profile(
        self,
        profile_name: str,
    ):
        if self.dashboard_layout_state.locked:
            self.sync_dashboard_layout_controls()
            return

        try:
            profile = self.dashboard_profile_store.get(
                profile_name
            )
            layout = (
                self.dashboard_profile_layout_for_current_cards(
                    profile.layout
                )
            )
        except (KeyError, TypeError, ValueError) as error:
            QMessageBox.warning(
                self,
                "Profile not applied",
                str(error),
            )
            self.sync_dashboard_layout_controls()
            return

        layout = replace(
            layout,
            locked=(
                self.dashboard_layout_state.locked
            ),
            preset=f"Profile: {profile.name}",
        )

        self.apply_dashboard_layout(
            layout,
            persist=True,
            record_history=True,
            history_label=f"profile {profile.name}",
        )

    def delete_dashboard_profile(
        self,
        profile_name: str,
    ):
        if self.dashboard_layout_state.locked:
            self.sync_dashboard_layout_controls()
            return

        try:
            profile_name = validate_profile_name(
                profile_name
            )
        except ValueError as error:
            QMessageBox.warning(
                self,
                "Profile not deleted",
                str(error),
            )
            return

        answer = QMessageBox.question(
            self,
            "Delete dashboard profile",
            (
                f'Delete the saved "{profile_name}" '
                "dashboard profile?"
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self.dashboard_profile_store.delete(
                profile_name
            )
        except (OSError, TypeError, ValueError) as error:
            QMessageBox.warning(
                self,
                "Profile not deleted",
                str(error),
            )

    def add_queue_card(
        self,
    ):
        if self.dashboard_layout_state.locked:
            self.sync_dashboard_layout_controls()
            return

        try:
            queue_layout = (
                self.dashboard_layout_state.card(
                    "queue"
                )
            )
        except KeyError:
            self.sync_dashboard_layout_controls()
            return

        if queue_layout.visible:
            self.sync_dashboard_layout_controls()
            return

        self.set_dashboard_card_visibility(
            "queue",
            True,
        )


    def add_link_card(self):
        if self.dashboard_layout_state.locked:
            self.sync_dashboard_layout_controls()
            return

        dialog = LinkCardDialog(self)

        if not dialog.exec():
            return

        card = dialog.card_data()

        if card is None:
            return

        previous_cards = tuple(
            self.custom_cards.values()
        )

        try:
            saved_cards = self.custom_card_store.upsert(card)
        except (OSError, TypeError, ValueError) as error:
            QMessageBox.warning(
                self,
                "Link card not saved",
                str(error),
            )
            return

        self.custom_cards = {
            item.card_id: item
            for item in saved_cards
        }

        widget = self.create_link_card_widget(card)
        self.dashboard_cards[card.card_id] = widget
        self.create_dashboard_card_handles(
            card.card_id,
            widget,
        )
        self.register_dashboard_visibility_action(
            card.card_id,
            card.title,
        )

        new_layout = replace(
            self.dashboard_layout_state,
            cards=(
                self.dashboard_layout_state.cards
                + (
                    self.default_custom_card_layout(
                        card.card_id
                    ),
                )
            ),
            preset="Custom",
        )

        try:
            self.apply_dashboard_layout(
                new_layout,
                persist=True,
            )
        except (OSError, TypeError, ValueError) as error:
            try:
                self.custom_card_store.save(previous_cards)
            except OSError:
                pass

            self.custom_cards = {
                item.card_id: item
                for item in previous_cards
            }
            self.remove_custom_card_ui(card.card_id)

            QMessageBox.warning(
                self,
                "Link card not added",
                str(error),
            )
            return

        self.sync_dashboard_layout_controls()
        self.schedule_dashboard_geometry_refresh()

    def prune_unused_launcher_card_images(
        self,
        cards=None,
    ):
        card_values = tuple(
            self.custom_cards.values()
            if cards is None
            else cards
        )

        referenced_assets = {
            card.image_asset
            for card in card_values
            if (
                isinstance(
                    card,
                    LauncherCardData,
                )
                and card.image_asset
            )
        }

        try:
            prune_launcher_card_images(
                referenced_assets
            )
        except (
            OSError,
            TypeError,
            ValueError,
        ) as error:
            print(
                "Launcher card image cleanup "
                f"could not finish: {error}"
            )

    def add_launcher_card(self):
        if self.dashboard_layout_state.locked:
            self.sync_dashboard_layout_controls()
            return

        dialog = LauncherCardDialog(self)

        if not dialog.exec():
            return

        card = dialog.card_data()

        if card is None:
            return

        previous_cards = tuple(
            self.custom_cards.values()
        )

        try:
            saved_cards = (
                self.custom_card_store.upsert(
                    card
                )
            )
        except (
            OSError,
            TypeError,
            ValueError,
        ) as error:
            self.prune_unused_launcher_card_images(
                previous_cards
            )

            QMessageBox.warning(
                self,
                "Launcher card not saved",
                str(error),
            )
            return

        self.custom_cards = {
            item.card_id: item
            for item in saved_cards
        }

        widget = (
            self.create_launcher_card_widget(
                card
            )
        )

        self.dashboard_cards[
            card.card_id
        ] = widget

        self.create_dashboard_card_handles(
            card.card_id,
            widget,
        )

        self.register_dashboard_visibility_action(
            card.card_id,
            card.title,
        )

        new_layout = replace(
            self.dashboard_layout_state,
            cards=(
                self.dashboard_layout_state.cards
                + (
                    self.default_custom_card_layout(
                        card.card_id
                    ),
                )
            ),
            preset="Custom",
        )

        try:
            self.apply_dashboard_layout(
                new_layout,
                persist=True,
            )
        except (
            OSError,
            TypeError,
            ValueError,
        ) as error:
            try:
                self.custom_card_store.save(
                    previous_cards
                )
            except OSError:
                pass

            self.custom_cards = {
                item.card_id: item
                for item in previous_cards
            }

            self.remove_custom_card_ui(
                card.card_id
            )
            self.prune_unused_launcher_card_images(
                previous_cards
            )

            QMessageBox.warning(
                self,
                "Launcher card not added",
                str(error),
            )
            return

        self.prune_unused_launcher_card_images()
        self.sync_dashboard_layout_controls()
        self.schedule_dashboard_geometry_refresh()

    def remove_custom_card_ui(self, card_id: str):
        widget = self.dashboard_cards.pop(
            card_id,
            None,
        )
        if widget is not None:
            widget.hide()
            widget.deleteLater()

        move_handle = self.dashboard_drag_handles.pop(
            card_id,
            None,
        )
        if move_handle is not None:
            move_handle.hide()
            move_handle.deleteLater()

        resize_handle = self.dashboard_resize_handles.pop(
            card_id,
            None,
        )
        if resize_handle is not None:
            resize_handle.hide()
            resize_handle.deleteLater()

        action_handle = self.dashboard_action_handles.pop(
            card_id,
            None,
        )
        if action_handle is not None:
            action_handle.hide()
            action_handle.deleteLater()

        delete_handle = self.dashboard_delete_handles.pop(
            card_id,
            None,
        )
        if delete_handle is not None:
            delete_handle.hide()
            delete_handle.deleteLater()

        action = self.layout_visibility_actions.pop(
            card_id,
            None,
        )
        if action is not None:
            self.layout_visibility_menu.removeAction(action)
            action.deleteLater()


    def edit_custom_card(
        self,
        card_id: str,
    ) -> bool:
        card = self.custom_cards.get(
            card_id
        )

        if isinstance(
            card,
            LauncherCardData,
        ):
            return self.edit_custom_launcher_card(
                card_id
            )

        if isinstance(
            card,
            LinkCardData,
        ):
            return self.edit_custom_link_card(
                card_id
            )

        return False

    def edit_custom_link_card(
        self,
        card_id: str,
    ) -> bool:
        if self.dashboard_layout_state.locked:
            self.sync_dashboard_layout_controls()
            return False

        card = self.custom_cards.get(card_id)

        if card is None:
            return False

        dialog = LinkCardDialog(
            self,
            card=card,
        )

        if not dialog.exec():
            return False

        updated_card = dialog.card_data()

        if updated_card is None:
            return False

        return self.save_edited_link_card(
            updated_card
        )

    def edit_custom_launcher_card(
        self,
        card_id: str,
    ) -> bool:
        if self.dashboard_layout_state.locked:
            self.sync_dashboard_layout_controls()
            return False

        card = self.custom_cards.get(
            card_id
        )

        if not isinstance(
            card,
            LauncherCardData,
        ):
            return False

        dialog = LauncherCardDialog(
            self,
            card=card,
        )

        if not dialog.exec():
            return False

        updated_card = dialog.card_data()

        if updated_card is None:
            return False

        return self.save_edited_launcher_card(
            updated_card
        )

    def save_edited_link_card(
        self,
        card: LinkCardData,
    ) -> bool:
        previous_card = self.custom_cards.get(
            card.card_id
        )

        if previous_card is None:
            return False

        widget = self.dashboard_cards.get(
            card.card_id
        )

        if not isinstance(widget, LinkCardWidget):
            return False

        previous_cards = tuple(
            self.custom_cards.values()
        )

        try:
            saved_cards = self.custom_card_store.upsert(
                card
            )
            widget.update_card(card)
        except (OSError, TypeError, ValueError) as error:
            rollback_error = None

            try:
                self.custom_card_store.save(
                    previous_cards
                )
            except (OSError, TypeError, ValueError) as restore_error:
                rollback_error = restore_error

            try:
                widget.update_card(previous_card)
            except (TypeError, ValueError):
                pass

            message = str(error)

            if rollback_error is not None:
                message += (
                    "\n\nThe custom-card rollback also failed: "
                    f"{rollback_error}"
                )

            QMessageBox.warning(
                self,
                "Link card not updated",
                message,
            )
            return False

        self.custom_cards = {
            item.card_id: item
            for item in saved_cards
        }

        visibility_action = (
            self.layout_visibility_actions.get(
                card.card_id
            )
        )

        if visibility_action is not None:
            visibility_action.setText(card.title)

        widget.set_theme(
            self.theme_manager.theme()
        )
        self.schedule_dashboard_geometry_refresh()
        return True

    def save_edited_launcher_card(
        self,
        card: LauncherCardData,
    ) -> bool:
        previous_card = self.custom_cards.get(
            card.card_id
        )

        if not isinstance(
            previous_card,
            LauncherCardData,
        ):
            return False

        widget = self.dashboard_cards.get(
            card.card_id
        )

        if not isinstance(
            widget,
            LauncherCardWidget,
        ):
            return False

        previous_cards = tuple(
            self.custom_cards.values()
        )

        try:
            saved_cards = (
                self.custom_card_store.upsert(
                    card
                )
            )
            widget.update_card(card)
        except (
            OSError,
            TypeError,
            ValueError,
        ) as error:
            rollback_error = None

            try:
                self.custom_card_store.save(
                    previous_cards
                )
            except (
                OSError,
                TypeError,
                ValueError,
            ) as restore_error:
                rollback_error = restore_error

            try:
                widget.update_card(
                    previous_card
                )
            except (
                TypeError,
                ValueError,
            ):
                pass

            message = str(error)

            if rollback_error is not None:
                message += (
                    "\n\nThe custom-card rollback "
                    "also failed: "
                    f"{rollback_error}"
                )

            self.prune_unused_launcher_card_images(
                previous_cards
            )

            QMessageBox.warning(
                self,
                "Launcher card not updated",
                message,
            )
            return False

        self.custom_cards = {
            item.card_id: item
            for item in saved_cards
        }

        visibility_action = (
            self.layout_visibility_actions.get(
                card.card_id
            )
        )

        if visibility_action is not None:
            visibility_action.setText(
                card.title
            )

        self.prune_unused_launcher_card_images()
        widget.set_launch_enabled(True)
        widget.set_theme(
            self.theme_manager.theme()
        )

        self.schedule_dashboard_geometry_refresh()
        return True

    def duplicate_custom_card_layout(
        self,
        source_layout: DashboardCardLayout,
        card_id: str,
    ) -> DashboardCardLayout:
        offset = 360
        maximum_x = max(
            0,
            CANVAS_UNITS - source_layout.width,
        )
        maximum_y = max(
            0,
            CANVAS_UNITS - source_layout.height,
        )

        x = min(
            maximum_x,
            source_layout.x + offset,
        )
        y = min(
            maximum_y,
            source_layout.y + offset,
        )

        if x == source_layout.x and source_layout.x > 0:
            x = max(
                0,
                source_layout.x - offset,
            )

        if y == source_layout.y and source_layout.y > 0:
            y = max(
                0,
                source_layout.y - offset,
            )

        highest_layer = max(
            (
                card.z_index
                for card in self.dashboard_layout_state.cards
            ),
            default=0,
        )

        return replace(
            source_layout,
            card_id=card_id,
            x=x,
            y=y,
            z_index=highest_layer + 1,
            visible=True,
        )

    def duplicate_custom_card(
        self,
        card_id: str,
    ) -> bool:
        card = self.custom_cards.get(
            card_id
        )

        if isinstance(
            card,
            LauncherCardData,
        ):
            return (
                self.duplicate_custom_launcher_card(
                    card_id
                )
            )

        if isinstance(
            card,
            LinkCardData,
        ):
            return (
                self.duplicate_custom_link_card(
                    card_id
                )
            )

        return False

    def duplicate_custom_link_card(
        self,
        card_id: str,
    ) -> bool:
        if self.dashboard_layout_state.locked:
            self.sync_dashboard_layout_controls()
            return False

        source_card = self.custom_cards.get(
            card_id
        )

        if source_card is None:
            return False

        try:
            source_layout = (
                self.dashboard_layout_state.card(
                    card_id
                )
            )
            duplicated_card = duplicate_link_card_data(
                source_card
            )
            duplicated_layout = (
                self.duplicate_custom_card_layout(
                    source_layout,
                    duplicated_card.card_id,
                )
            )
        except (KeyError, TypeError, ValueError) as error:
            QMessageBox.warning(
                self,
                "Link card not duplicated",
                str(error),
            )
            return False

        previous_cards = tuple(
            self.custom_cards.values()
        )
        widget = None

        try:
            saved_cards = self.custom_card_store.upsert(
                duplicated_card
            )

            self.custom_cards = {
                item.card_id: item
                for item in saved_cards
            }

            widget = self.create_link_card_widget(
                duplicated_card
            )
            self.dashboard_cards[
                duplicated_card.card_id
            ] = widget
            self.create_dashboard_card_handles(
                duplicated_card.card_id,
                widget,
            )
            self.register_dashboard_visibility_action(
                duplicated_card.card_id,
                duplicated_card.title,
            )

            new_layout = replace(
                self.dashboard_layout_state,
                cards=(
                    self.dashboard_layout_state.cards
                    + (duplicated_layout,)
                ),
                preset="Custom",
            )

            self.apply_dashboard_layout(
                new_layout,
                persist=True,
            )
        except (OSError, TypeError, ValueError) as error:
            rollback_error = None

            try:
                self.custom_card_store.save(
                    previous_cards
                )
            except (OSError, TypeError, ValueError) as restore_error:
                rollback_error = restore_error

            self.custom_cards = {
                item.card_id: item
                for item in previous_cards
            }

            if widget is not None:
                self.remove_custom_card_ui(
                    duplicated_card.card_id
                )

            message = str(error)

            if rollback_error is not None:
                message += (
                    "\n\nThe custom-card rollback also failed: "
                    f"{rollback_error}"
                )

            QMessageBox.warning(
                self,
                "Link card not duplicated",
                message,
            )
            return False

        self.sync_dashboard_layout_controls()
        self.schedule_dashboard_geometry_refresh()
        return True

    def duplicate_custom_launcher_card(
        self,
        card_id: str,
    ) -> bool:
        if self.dashboard_layout_state.locked:
            self.sync_dashboard_layout_controls()
            return False

        source_card = self.custom_cards.get(
            card_id
        )

        if not isinstance(
            source_card,
            LauncherCardData,
        ):
            return False

        try:
            source_layout = (
                self.dashboard_layout_state.card(
                    card_id
                )
            )
            duplicated_card = (
                duplicate_launcher_card_data(
                    source_card
                )
            )
            duplicated_layout = (
                self.duplicate_custom_card_layout(
                    source_layout,
                    duplicated_card.card_id,
                )
            )
        except (
            KeyError,
            TypeError,
            ValueError,
        ) as error:
            QMessageBox.warning(
                self,
                "Launcher card not duplicated",
                str(error),
            )
            return False

        previous_cards = tuple(
            self.custom_cards.values()
        )
        widget = None

        try:
            saved_cards = (
                self.custom_card_store.upsert(
                    duplicated_card
                )
            )

            self.custom_cards = {
                item.card_id: item
                for item in saved_cards
            }

            widget = (
                self.create_launcher_card_widget(
                    duplicated_card
                )
            )

            self.dashboard_cards[
                duplicated_card.card_id
            ] = widget

            self.create_dashboard_card_handles(
                duplicated_card.card_id,
                widget,
            )

            self.register_dashboard_visibility_action(
                duplicated_card.card_id,
                duplicated_card.title,
            )

            new_layout = replace(
                self.dashboard_layout_state,
                cards=(
                    self.dashboard_layout_state.cards
                    + (duplicated_layout,)
                ),
                preset="Custom",
            )

            self.apply_dashboard_layout(
                new_layout,
                persist=True,
            )

        except (
            OSError,
            TypeError,
            ValueError,
        ) as error:
            rollback_error = None

            try:
                self.custom_card_store.save(
                    previous_cards
                )
            except (
                OSError,
                TypeError,
                ValueError,
            ) as restore_error:
                rollback_error = restore_error

            self.custom_cards = {
                item.card_id: item
                for item in previous_cards
            }

            if widget is not None:
                self.remove_custom_card_ui(
                    duplicated_card.card_id
                )

            message = str(error)

            if rollback_error is not None:
                message += (
                    "\n\nThe custom-card rollback "
                    "also failed: "
                    f"{rollback_error}"
                )

            self.prune_unused_launcher_card_images(
                previous_cards
            )

            QMessageBox.warning(
                self,
                "Launcher card not duplicated",
                message,
            )
            return False

        self.prune_unused_launcher_card_images()
        self.sync_dashboard_layout_controls()
        self.schedule_dashboard_geometry_refresh()
        return True

    def confirm_delete_custom_card(
        self,
        card_id: str,
    ):
        card = self.custom_cards.get(
            card_id
        )

        if card is None:
            return

        if isinstance(
            card,
            LauncherCardData,
        ):
            card_kind = "Launcher"
        elif isinstance(
            card,
            LinkCardData,
        ):
            card_kind = "Link"
        else:
            card_kind = "Custom"

        answer = QMessageBox.question(
            self,
            f"Delete {card_kind} card",
            (
                f'Delete "{card.title}" '
                "from the dashboard?\n\n"
                "This cannot be undone."
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if (
            answer
            != QMessageBox.StandardButton.Yes
        ):
            return

        self.delete_custom_card(
            card_id
        )


    def delete_custom_card(
        self,
        card_id: str,
    ) -> bool:
        if (
            not is_custom_dashboard_card_id(card_id)
            or card_id not in self.custom_cards
        ):
            return False

        previous_cards = tuple(
            self.custom_cards.values()
        )

        new_layout = replace(
            self.dashboard_layout_state,
            cards=tuple(
                card
                for card in self.dashboard_layout_state.cards
                if card.card_id != card_id
            ),
            preset="Custom",
        )

        try:
            validated_layout = validate_layout(
                new_layout
            )
            saved_cards = self.custom_card_store.delete(
                card_id
            )
            saved_layout = self.dashboard_layout_store.save(
                validated_layout
            )
        except (OSError, TypeError, ValueError) as error:
            rollback_error = None

            try:
                self.custom_card_store.save(
                    previous_cards
                )
            except (OSError, TypeError, ValueError) as restore_error:
                rollback_error = restore_error

            message = str(error)

            if rollback_error is not None:
                message += (
                    "\n\nThe custom-card rollback also failed: "
                    f"{rollback_error}"
                )

            QMessageBox.warning(
                self,
                "Custom card not deleted",
                message,
            )
            return False

        self.custom_cards = {
            item.card_id: item
            for item in saved_cards
        }
        self.dashboard_layout_state = saved_layout
        self.clear_dashboard_layout_history()
        self.invalidate_dashboard_layout_session()
        self.prune_unused_launcher_card_images()
        self.remove_custom_card_ui(card_id)
        self.sync_dashboard_layout_controls()
        self.schedule_dashboard_geometry_refresh()
        return True

    def open_launcher_card_target(
        self,
        card_id: str,
    ):
        card = self.custom_cards.get(
            card_id
        )

        if not isinstance(
            card,
            LauncherCardData,
        ):
            QMessageBox.warning(
                self,
                "Launcher target cannot be opened",
                "The Launcher card could not be found.",
            )
            return

        try:
            prepared = prepare_launcher_target(
                card
            )
        except (
            OSError,
            TypeError,
            ValueError,
        ) as error:
            QMessageBox.warning(
                self,
                "Launcher target cannot be opened",
                str(error),
            )
            return

        if (
            prepared
            .requires_script_confirmation
        ):
            answer = QMessageBox.question(
                self,
                "Open script target?",
                (
                    "This Launcher target is a script "
                    "file and may run commands using "
                    "your Windows account permissions."
                    "\n\n"
                    f"Target:\n{prepared.path}"
                    "\n\n"
                    "Open it?"
                ),
                (
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No
                ),
                QMessageBox.StandardButton.No,
            )

            if (
                answer
                != QMessageBox.StandardButton.Yes
            ):
                return

        try:
            open_prepared_launcher_target(
                prepared
            )
        except (
            OSError,
            TypeError,
            ValueError,
        ) as error:
            QMessageBox.warning(
                self,
                "Launcher target could not be opened",
                str(error),
            )

    def open_link_card_url(self, url: str):
        try:
            safe_url = normalize_web_url(url)
        except (TypeError, ValueError) as error:
            QMessageBox.warning(
                self,
                "Link cannot be opened",
                str(error),
            )
            return

        opened = QDesktopServices.openUrl(
            QUrl(safe_url)
        )

        if not opened:
            QMessageBox.warning(
                self,
                "Link could not be opened",
                "Windows could not open this address in "
                "your default browser.",
            )

    def dashboard_layout_session_card_ids(
        self,
        layout=None,
    ) -> frozenset[str]:
        if layout is None:
            layout = getattr(
                self,
                "dashboard_layout_state",
                None,
            )

        if layout is None:
            return frozenset()

        return frozenset(
            card.card_id
            for card in layout.cards
        )

    def begin_dashboard_layout_session(
        self,
        layout=None,
    ) -> bool:
        source_layout = (
            layout
            if layout is not None
            else getattr(
                self,
                "dashboard_layout_state",
                None,
            )
        )

        if source_layout is None:
            self.end_dashboard_layout_session()
            return False

        snapshot = replace(
            validate_layout(
                source_layout
            ),
            locked=False,
        )

        self._dashboard_layout_session_baseline = (
            snapshot
        )
        self._dashboard_layout_session_card_ids = (
            self.dashboard_layout_session_card_ids(
                snapshot
            )
        )
        self._dashboard_layout_session_valid = True

        self.update_dashboard_layout_session_controls()
        return True

    def end_dashboard_layout_session(
        self,
    ):
        self._dashboard_layout_session_baseline = None
        self._dashboard_layout_session_card_ids = (
            frozenset()
        )
        self._dashboard_layout_session_valid = False

        self.update_dashboard_layout_session_controls()

    def invalidate_dashboard_layout_session(
        self,
    ):
        self._dashboard_layout_session_valid = False

        self.update_dashboard_layout_session_controls()

    def dashboard_layout_session_is_safe(
        self,
    ) -> bool:
        baseline = getattr(
            self,
            "_dashboard_layout_session_baseline",
            None,
        )

        if (
            baseline is None
            or not getattr(
                self,
                "_dashboard_layout_session_valid",
                False,
            )
        ):
            return False

        current_layout = getattr(
            self,
            "dashboard_layout_state",
            None,
        )

        if current_layout is None:
            return False

        recorded_ids = getattr(
            self,
            "_dashboard_layout_session_card_ids",
            frozenset(),
        )

        return bool(
            recorded_ids
            == self.dashboard_layout_session_card_ids(
                baseline
            )
            == self.dashboard_layout_session_card_ids(
                current_layout
            )
        )

    def dashboard_layout_session_has_changes(
        self,
    ) -> bool:
        if not self.dashboard_layout_session_is_safe():
            return False

        baseline = (
            self._dashboard_layout_session_baseline
        )

        current_layout = replace(
            validate_layout(
                self.dashboard_layout_state
            ),
            locked=False,
        )

        return current_layout != baseline

    def update_dashboard_layout_session_controls(
        self,
    ):
        button = getattr(
            self,
            "layout_revert_session_button",
            None,
        )

        if button is None:
            return

        layout = getattr(
            self,
            "dashboard_layout_state",
            None,
        )

        locked = bool(
            layout is None
            or layout.locked
        )

        baseline = getattr(
            self,
            "_dashboard_layout_session_baseline",
            None,
        )

        valid = bool(
            getattr(
                self,
                "_dashboard_layout_session_valid",
                False,
            )
        )

        safe = (
            self.dashboard_layout_session_is_safe()
        )

        changed = bool(
            safe
            and self.dashboard_layout_session_has_changes()
        )

        button.setEnabled(
            bool(
                not locked
                and changed
            )
        )

        if locked:
            button.setToolTip(
                (
                    "Edit the layout to begin "
                    "a revert session."
                )
            )

        elif baseline is None:
            button.setToolTip(
                (
                    "No editing-session snapshot "
                    "is available."
                )
            )

        elif not valid or not safe:
            button.setToolTip(
                (
                    "Revert is unavailable after "
                    "adding, duplicating, or "
                    "deleting cards. Finish editing "
                    "and begin a new session."
                )
            )

        elif not changed:
            button.setToolTip(
                (
                    "The layout matches the start "
                    "of this editing session."
                )
            )

        else:
            button.setToolTip(
                (
                    "Restore the layout from when "
                    "editing began. This action can "
                    "be undone."
                )
            )

        accessibility_sync = getattr(
            self,
            "sync_dashboard_layout_accessibility",
            None,
        )

        if callable(accessibility_sync):
            accessibility_sync()

    def revert_dashboard_layout_session(
        self,
    ) -> bool:
        layout = getattr(
            self,
            "dashboard_layout_state",
            None,
        )

        if (
            layout is None
            or layout.locked
        ):
            self.update_dashboard_layout_session_controls()
            return False

        if getattr(
            self,
            "_dashboard_drag_active",
            False,
        ):
            self.cancel_dashboard_live_drag()

        if getattr(
            self,
            "_dashboard_resize_active",
            False,
        ):
            self.cancel_dashboard_live_resize()

        if getattr(
            self,
            "_dashboard_keyboard_active",
            False,
        ):
            self.cancel_dashboard_keyboard_adjustment()

        if (
            not self.dashboard_layout_session_is_safe()
            or not self.dashboard_layout_session_has_changes()
        ):
            self.update_dashboard_layout_session_controls()
            return False

        baseline = (
            self._dashboard_layout_session_baseline
        )

        target_layout = replace(
            validate_layout(
                baseline
            ),
            locked=False,
        )

        try:
            self.apply_dashboard_layout(
                target_layout,
                persist=True,
                sync_controls=False,
                record_history=True,
                history_label="session revert",
            )

        except (
            OSError,
            TypeError,
            ValueError,
        ) as error:
            QMessageBox.warning(
                self,
                "Layout not reverted",
                str(error),
            )

            self.update_dashboard_layout_session_controls()
            return False

        self.sync_dashboard_layout_controls()

        print(
            "Dashboard layout reverted to "
            "the editing-session start."
        )

        return True

    def setup_dashboard_history_shortcuts(
        self,
    ):
        existing = getattr(
            self,
            "dashboard_undo_shortcut",
            None,
        )

        if existing is not None:
            self.update_dashboard_history_shortcut_state()
            return

        self.dashboard_undo_shortcut = QShortcut(
            QKeySequence(
                "Ctrl+Z"
            ),
            self,
        )
        self.dashboard_undo_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        self.dashboard_undo_shortcut.setAutoRepeat(
            False
        )
        self.dashboard_undo_shortcut.activated.connect(
            self.trigger_dashboard_undo_shortcut
        )

        self.dashboard_redo_shortcut = QShortcut(
            QKeySequence(
                "Ctrl+Y"
            ),
            self,
        )
        self.dashboard_redo_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        self.dashboard_redo_shortcut.setAutoRepeat(
            False
        )
        self.dashboard_redo_shortcut.activated.connect(
            self.trigger_dashboard_redo_shortcut
        )

        self.dashboard_alternate_redo_shortcut = (
            QShortcut(
                QKeySequence(
                    "Ctrl+Shift+Z"
                ),
                self,
            )
        )
        self.dashboard_alternate_redo_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        self.dashboard_alternate_redo_shortcut.setAutoRepeat(
            False
        )
        self.dashboard_alternate_redo_shortcut.activated.connect(
            self.trigger_dashboard_redo_shortcut
        )

        application = QApplication.instance()

        if (
            application is not None
            and not getattr(
                self,
                "_dashboard_history_focus_connected",
                False,
            )
        ):
            application.focusChanged.connect(
                self.handle_dashboard_history_focus_changed
            )

            self._dashboard_history_focus_connected = True

        self.update_dashboard_history_shortcut_state()

    def dashboard_history_focus_blocks_shortcuts(
        self,
        focused_widget=None,
    ) -> bool:
        if focused_widget is None:
            focused_widget = QApplication.focusWidget()

        if focused_widget is None:
            return False

        if isinstance(
            focused_widget,
            (
                QLineEdit,
                QTextEdit,
                QPlainTextEdit,
                QAbstractSpinBox,
            ),
        ):
            return True

        if (
            isinstance(
                focused_widget,
                QComboBox,
            )
            and focused_widget.isEditable()
        ):
            return True

        return False

    def update_dashboard_history_shortcut_state(
        self,
        focused_widget=None,
    ):
        layout = getattr(
            self,
            "dashboard_layout_state",
            None,
        )

        locked = bool(
            layout is None
            or layout.locked
        )

        blocked = (
            self.dashboard_history_focus_blocks_shortcuts(
                focused_widget
            )
        )

        undo_available = bool(
            not locked
            and not blocked
            and getattr(
                self,
                "_dashboard_layout_undo_stack",
                [],
            )
        )

        redo_available = bool(
            not locked
            and not blocked
            and getattr(
                self,
                "_dashboard_layout_redo_stack",
                [],
            )
        )

        undo_shortcut = getattr(
            self,
            "dashboard_undo_shortcut",
            None,
        )

        if undo_shortcut is not None:
            undo_shortcut.setEnabled(
                undo_available
            )

        for attribute_name in (
            "dashboard_redo_shortcut",
            "dashboard_alternate_redo_shortcut",
        ):
            redo_shortcut = getattr(
                self,
                attribute_name,
                None,
            )

            if redo_shortcut is not None:
                redo_shortcut.setEnabled(
                    redo_available
                )

    def handle_dashboard_history_focus_changed(
        self,
        _previous_widget,
        focused_widget,
    ):
        self.update_dashboard_history_shortcut_state(
            focused_widget
        )

    def trigger_dashboard_history_shortcut(
        self,
        action: str,
        focused_widget=None,
    ) -> bool:
        if self.dashboard_history_focus_blocks_shortcuts(
            focused_widget
        ):
            return False

        layout = getattr(
            self,
            "dashboard_layout_state",
            None,
        )

        if (
            layout is None
            or layout.locked
        ):
            return False

        normalized = str(
            action
            or ""
        ).strip().casefold()

        if normalized == "undo":
            return bool(
                self.undo_dashboard_layout()
            )

        if normalized == "redo":
            return bool(
                self.redo_dashboard_layout()
            )

        return False

    def trigger_dashboard_undo_shortcut(
        self,
    ) -> bool:
        return self.trigger_dashboard_history_shortcut(
            "undo"
        )

    def trigger_dashboard_redo_shortcut(
        self,
    ) -> bool:
        return self.trigger_dashboard_history_shortcut(
            "redo"
        )

    def clear_dashboard_layout_history(
        self,
    ):
        self._dashboard_layout_undo_stack = []
        self._dashboard_layout_redo_stack = []

        self.update_dashboard_history_controls()

    def record_dashboard_layout_history(
        self,
        previous_layout: DashboardLayout,
        label: str,
    ):
        snapshot = validate_layout(
            previous_layout
        )

        normalized_label = str(
            label
            or "change"
        ).strip()

        if not normalized_label:
            normalized_label = "change"

        undo_stack = getattr(
            self,
            "_dashboard_layout_undo_stack",
            None,
        )

        if not isinstance(
            undo_stack,
            list,
        ):
            undo_stack = []
            self._dashboard_layout_undo_stack = (
                undo_stack
            )

        undo_stack.append(
            (
                normalized_label,
                snapshot,
            )
        )

        if len(undo_stack) > 50:
            del undo_stack[:-50]

        redo_stack = getattr(
            self,
            "_dashboard_layout_redo_stack",
            None,
        )

        if not isinstance(
            redo_stack,
            list,
        ):
            redo_stack = []
            self._dashboard_layout_redo_stack = (
                redo_stack
            )

        redo_stack.clear()

        self.update_dashboard_history_controls()

    def update_dashboard_history_controls(
        self,
    ):
        layout = getattr(
            self,
            "dashboard_layout_state",
            None,
        )

        locked = bool(
            layout is None
            or layout.locked
        )

        undo_stack = getattr(
            self,
            "_dashboard_layout_undo_stack",
            [],
        )

        redo_stack = getattr(
            self,
            "_dashboard_layout_redo_stack",
            [],
        )

        undo_available = bool(
            not locked
            and undo_stack
        )

        redo_available = bool(
            not locked
            and redo_stack
        )

        undo_button = getattr(
            self,
            "layout_undo_button",
            None,
        )

        if undo_button is not None:
            undo_button.setEnabled(
                undo_available
            )

            if undo_stack:
                undo_label = str(
                    undo_stack[-1][0]
                    or "change"
                )

                undo_button.setToolTip(
                    (
                        (
                            f"Undo {undo_label} "
                            "(Ctrl+Z)"
                        )
                        if not locked
                        else (
                            "Edit the layout to "
                            f"undo {undo_label} "
                            "(Ctrl+Z)"
                        )
                    )
                )
            else:
                undo_button.setToolTip(
                    "Nothing to undo (Ctrl+Z)"
                )

        redo_button = getattr(
            self,
            "layout_redo_button",
            None,
        )

        if redo_button is not None:
            redo_button.setEnabled(
                redo_available
            )

            if redo_stack:
                redo_label = str(
                    redo_stack[-1][0]
                    or "change"
                )

                redo_button.setToolTip(
                    (
                        (
                            f"Redo {redo_label} "
                            "(Ctrl+Y / Ctrl+Shift+Z)"
                        )
                        if not locked
                        else (
                            "Edit the layout to "
                            f"redo {redo_label} "
                            "(Ctrl+Y / Ctrl+Shift+Z)"
                        )
                    )
                )
            else:
                redo_button.setToolTip(
                    (
                        "Nothing to redo "
                        "(Ctrl+Y / Ctrl+Shift+Z)"
                    )
                )

        shortcut_sync = getattr(
            self,
            "update_dashboard_history_shortcut_state",
            None,
        )

        if callable(shortcut_sync):
            shortcut_sync()

        session_sync = getattr(
            self,
            "update_dashboard_layout_session_controls",
            None,
        )

        if callable(session_sync):
            session_sync()

        accessibility_sync = getattr(
            self,
            "sync_dashboard_layout_accessibility",
            None,
        )

        if callable(accessibility_sync):
            accessibility_sync()


    def undo_dashboard_layout(
        self,
    ) -> bool:
        if self.dashboard_layout_state.locked:
            self.sync_dashboard_layout_controls()
            return False

        undo_stack = getattr(
            self,
            "_dashboard_layout_undo_stack",
            [],
        )

        if not undo_stack:
            self.update_dashboard_history_controls()
            return False

        if self._dashboard_drag_active:
            self.cancel_dashboard_live_drag()

        if self._dashboard_resize_active:
            self.cancel_dashboard_live_resize()

        if getattr(
            self,
            "_dashboard_keyboard_active",
            False,
        ):
            self.cancel_dashboard_keyboard_adjustment()

        entry = undo_stack.pop()
        label, target_layout = entry

        current_layout = (
            self.dashboard_layout_state
        )

        try:
            restored_layout = replace(
                validate_layout(
                    target_layout
                ),
                locked=current_layout.locked,
            )

            self.apply_dashboard_layout(
                restored_layout,
                persist=True,
                sync_controls=False,
                record_history=False,
            )

        except (
            OSError,
            TypeError,
            ValueError,
        ) as error:
            undo_stack.append(entry)

            print(
                "Dashboard layout undo rejected: "
                f"{error}"
            )

            self.update_dashboard_history_controls()
            return False

        redo_stack = getattr(
            self,
            "_dashboard_layout_redo_stack",
            None,
        )

        if not isinstance(
            redo_stack,
            list,
        ):
            redo_stack = []
            self._dashboard_layout_redo_stack = (
                redo_stack
            )

        redo_stack.append(
            (
                label,
                current_layout,
            )
        )

        if len(redo_stack) > 50:
            del redo_stack[:-50]

        self.sync_dashboard_layout_controls()

        print(
            "Dashboard layout undone: "
            f"{label}."
        )

        return True

    def redo_dashboard_layout(
        self,
    ) -> bool:
        if self.dashboard_layout_state.locked:
            self.sync_dashboard_layout_controls()
            return False

        redo_stack = getattr(
            self,
            "_dashboard_layout_redo_stack",
            [],
        )

        if not redo_stack:
            self.update_dashboard_history_controls()
            return False

        if self._dashboard_drag_active:
            self.cancel_dashboard_live_drag()

        if self._dashboard_resize_active:
            self.cancel_dashboard_live_resize()

        if getattr(
            self,
            "_dashboard_keyboard_active",
            False,
        ):
            self.cancel_dashboard_keyboard_adjustment()

        entry = redo_stack.pop()
        label, target_layout = entry

        current_layout = (
            self.dashboard_layout_state
        )

        try:
            restored_layout = replace(
                validate_layout(
                    target_layout
                ),
                locked=current_layout.locked,
            )

            self.apply_dashboard_layout(
                restored_layout,
                persist=True,
                sync_controls=False,
                record_history=False,
            )

        except (
            OSError,
            TypeError,
            ValueError,
        ) as error:
            redo_stack.append(entry)

            print(
                "Dashboard layout redo rejected: "
                f"{error}"
            )

            self.update_dashboard_history_controls()
            return False

        undo_stack = getattr(
            self,
            "_dashboard_layout_undo_stack",
            None,
        )

        if not isinstance(
            undo_stack,
            list,
        ):
            undo_stack = []
            self._dashboard_layout_undo_stack = (
                undo_stack
            )

        undo_stack.append(
            (
                label,
                current_layout,
            )
        )

        if len(undo_stack) > 50:
            del undo_stack[:-50]

        self.sync_dashboard_layout_controls()

        print(
            "Dashboard layout redone: "
            f"{label}."
        )

        return True

    def apply_dashboard_preset(
        self,
        preset_name: str,
    ):
        name = str(
            preset_name
            or ""
        ).strip()

        if (
            not name
            or self.dashboard_layout_state.locked
        ):
            self.sync_dashboard_layout_controls()
            return

        try:
            layout = preset_layout(
                name
            )
        except KeyError:
            self.sync_dashboard_layout_controls()
            return

        layout = self.with_current_custom_layout_cards(
            layout
        )

        layout = replace(
            layout,
            locked=(
                self.dashboard_layout_state.locked
            ),
        )

        self.apply_dashboard_layout(
            layout,
            persist=True,
            record_history=True,
            history_label=f"preset {name}",
        )

    def toggle_dashboard_layout_lock(self):
        if self._dashboard_drag_active:
            self.cancel_dashboard_live_drag()

        if self._dashboard_resize_active:
            self.cancel_dashboard_live_resize()

        if getattr(
            self,
            "_dashboard_keyboard_active",
            False,
        ):
            self.cancel_dashboard_keyboard_adjustment()

        current_layout = (
            self.dashboard_layout_state
        )

        entering_editing = bool(
            current_layout.locked
        )

        session_baseline = (
            replace(
                validate_layout(
                    current_layout
                ),
                locked=False,
            )
            if entering_editing
            else None
        )

        updated = replace(
            current_layout,
            locked=(
                not current_layout.locked
            ),
        )

        self.apply_dashboard_layout(
            updated,
            persist=True,
        )

        if entering_editing:
            self.begin_dashboard_layout_session(
                session_baseline
            )
        else:
            self.end_dashboard_layout_session()


    def reset_dashboard_layout(self):
        if self.dashboard_layout_state.locked:
            self.sync_dashboard_layout_controls()
            return

        layout = self.with_current_custom_layout_cards(
            preset_layout(
                "Default"
            )
        )

        layout = replace(
            layout,
            locked=(
                self.dashboard_layout_state.locked
            ),
        )

        self.apply_dashboard_layout(
            layout,
            persist=True,
            record_history=True,
            history_label="layout reset",
        )

    def set_dashboard_card_visibility(
        self,
        card_id: str,
        visible: bool,
    ):
        if self.dashboard_layout_state.locked:
            self.sync_dashboard_layout_controls()
            return

        try:
            current_card = (
                self.dashboard_layout_state.card(
                    card_id
                )
            )
        except KeyError:
            self.sync_dashboard_layout_controls()
            return

        visible = bool(
            visible
        )

        if current_card.visible == visible:
            return

        visible_count = sum(
            1
            for card in (
                self.dashboard_layout_state.cards
            )
            if card.visible
        )

        if (
            not visible
            and visible_count <= 1
        ):
            print(
                "Dashboard visibility change rejected: "
                "at least one card must remain visible."
            )
            self.sync_dashboard_layout_controls()
            return

        updated_cards = tuple(
            replace(
                card,
                visible=visible,
            )
            if card.card_id == card_id
            else card
            for card in (
                self.dashboard_layout_state.cards
            )
        )

        updated = replace(
            self.dashboard_layout_state,
            cards=updated_cards,
            preset="Custom",
        )

        try:
            self.apply_dashboard_layout(
                updated,
                persist=True,
                record_history=True,
                history_label="card visibility",
            )
        except ValueError as error:
            print(
                "Dashboard visibility change rejected: "
                f"{error}"
            )
            self.sync_dashboard_layout_controls()
        if (
            card_id == "queue"
            and visible
        ):
            DashboardPage.refresh_spotify_queue(
                self,
                force=True,
            )

    def sync_dashboard_add_queue_action(
        self,
    ):
        action = getattr(
            self,
            "layout_add_queue_action",
            None,
        )

        if action is None:
            return

        layout = getattr(
            self,
            "dashboard_layout_state",
            None,
        )

        if layout is None:
            action.setVisible(
                False
            )
            action.setEnabled(
                False
            )
            return

        try:
            queue_layout = layout.card(
                "queue"
            )
        except KeyError:
            action.setVisible(
                False
            )
            action.setEnabled(
                False
            )
            return

        available = (
            not queue_layout.visible
        )

        action.setVisible(
            available
        )

        action.setEnabled(
            available
            and not layout.locked
        )


    def sync_dashboard_layout_controls(self):
        if not hasattr(
            self,
            "layout_preset_combo",
        ):
            return

        preset_names = available_presets()

        preset_blocker = QSignalBlocker(
            self.layout_preset_combo
        )

        if (
            self.dashboard_layout_state.preset
            in preset_names
        ):
            self.layout_preset_combo.setCurrentText(
                self.dashboard_layout_state.preset
            )
        else:
            self.layout_preset_combo.setCurrentIndex(
                -1
            )

        del preset_blocker

        for (
            card_id,
            action,
        ) in self.layout_visibility_actions.items():
            action_blocker = QSignalBlocker(
                action
            )

            action.setChecked(
                self.dashboard_layout_state.card(
                    card_id
                ).visible
            )

            del action_blocker

        locked = bool(
            self.dashboard_layout_state.locked
        )
        DashboardPage.sync_dashboard_add_queue_action(
            self
        )

        layout_state = (
            "locked"
            if locked
            else "editing"
        )

        self.layout_status_label.setText(
            "LOCKED"
            if locked
            else "EDITING"
        )

        self.layout_toolbar_hint.setText(
            (
                "Your dashboard is protected "
                "from accidental changes."
            )
            if locked
            else (
                "Drag, resize, add, or hide cards. "
                "Finish editing when it feels right."
            )
        )

        self.layout_toolbar.setProperty(
            "layoutState",
            layout_state,
        )
        self.layout_status_label.setProperty(
            "layoutState",
            layout_state,
        )
        self.layout_lock_button.setProperty(
            "layoutState",
            layout_state,
        )

        self.layout_preset_combo.setEnabled(
            not locked
        )
        self.layout_profiles_button.setEnabled(
            not locked
        )
        self.layout_snap_button.setEnabled(
            not locked
        )
        self.update_dashboard_snap_button()

        self.layout_add_card_button.setEnabled(
            not locked
        )
        self.layout_visibility_button.setEnabled(
            not locked
        )
        self.layout_reset_button.setEnabled(
            not locked
        )

        self.layout_lock_button.setToolTip(
            (
                "Enter dashboard layout editing"
                if locked
                else (
                    "Finish editing and protect "
                    "the dashboard layout"
                )
            )
        )

        for widget in (
            self.layout_toolbar,
            self.layout_status_label,
            self.layout_lock_button,
        ):
            style = widget.style()
            style.unpolish(widget)
            style.polish(widget)
            widget.update()

        self.update_dashboard_layout_toolbar_responsive_state()
        self.sync_dashboard_drag_handles()
        self.update_dashboard_history_controls()

        accessibility_sync = getattr(
            self,
            "sync_dashboard_layout_accessibility",
            None,
        )

        if callable(accessibility_sync):
            accessibility_sync()


    def apply_dashboard_layout(
        self,
        layout: DashboardLayout,
        persist: bool = False,
        sync_controls: bool = True,
        record_history: bool = False,
        history_label: str = "change",
    ) -> DashboardLayout:
        previous_layout = getattr(
            self,
            "dashboard_layout_state",
            None,
        )

        validated = validate_layout(
            layout
        )

        previous_card_ids = (
            frozenset(
                card.card_id
                for card in previous_layout.cards
            )
            if previous_layout is not None
            else frozenset()
        )

        validated_card_ids = frozenset(
            card.card_id
            for card in validated.cards
        )

        structural_change = bool(
            previous_layout is not None
            and previous_card_ids
            != validated_card_ids
        )

        if persist:
            validated = (
                self.dashboard_layout_store.save(
                    validated
                )
            )

        if (
            record_history
            and previous_layout is not None
            and validated != previous_layout
        ):
            self.record_dashboard_layout_history(
                previous_layout,
                history_label,
            )

        if structural_change:
            self.clear_dashboard_layout_history()
            self.invalidate_dashboard_layout_session()

        self.dashboard_layout_state = (
            validated
        )

        if sync_controls:
            self.sync_dashboard_layout_controls()

        self.schedule_dashboard_geometry_refresh()

        return validated


    def build_now_playing_card(self):
        self.now_playing_card = QFrame()
        self.now_playing_card.setObjectName(
            "nowPlayingCard"
        )

        outer_layout = QVBoxLayout(
            self.now_playing_card
        )
        outer_layout.setContentsMargins(
            14,
            12,
            14,
            12,
        )
        outer_layout.setSpacing(8)

        heading_row = QHBoxLayout()

        self.section_label = QLabel(
            "🎵  NOW PLAYING"
        )
        self.section_label.setObjectName(
            "sectionLabel"
        )

        source_button = QPushButton()
        source_button.setIcon(
            self.style().standardIcon(
                QStyle.StandardPixmap.SP_ArrowForward
            )
        )
        source_button.setObjectName(
            "cardIconButton"
        )
        source_button.setFixedSize(
            34,
            34,
        )
        source_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        source_button.setToolTip(
            "Open the current media source"
        )
        source_button.clicked.connect(
            self.open_current_source
        )

        heading_row.addWidget(
            self.section_label
        )
        heading_row.addStretch()
        heading_row.addWidget(
            source_button
        )

        outer_layout.addLayout(
            heading_row
        )

        body_layout = QHBoxLayout()
        body_layout.setSpacing(14)

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

        body_layout.addWidget(
            self.artwork,
            alignment=Qt.AlignmentFlag.AlignVCenter,
        )

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

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
            self.song_title
        )
        info_layout.addWidget(
            self.artist
        )
        info_layout.addWidget(
            self.album
        )
        info_layout.addStretch()

        playback_row = QHBoxLayout()
        playback_row.setSpacing(8)
        playback_row.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.playback_previous_button = (
            QPushButton()
        )
        self.playback_previous_button.setIcon(
            self.style().standardIcon(
                QStyle.StandardPixmap.SP_MediaSkipBackward
            )
        )
        self.playback_previous_button.setToolTip(
            "Previous track"
        )
        self.playback_previous_button.setAccessibleName(
            "Previous track"
        )

        self.playback_play_pause_button = (
            QPushButton()
        )
        self.playback_play_pause_button.setIcon(
            self.style().standardIcon(
                QStyle.StandardPixmap.SP_MediaPlay
            )
        )
        self.playback_play_pause_button.setToolTip(
            "Play"
        )
        self.playback_play_pause_button.setAccessibleName(
            "Play"
        )

        self.playback_next_button = (
            QPushButton()
        )
        self.playback_next_button.setIcon(
            self.style().standardIcon(
                QStyle.StandardPixmap.SP_MediaSkipForward
            )
        )
        self.playback_next_button.setToolTip(
            "Next track"
        )
        self.playback_next_button.setAccessibleName(
            "Next track"
        )

        playback_description = (
            "Control the current media session "
            "without bringing another app "
            "to the foreground."
        )

        for playback_button in (
            self.playback_previous_button,
            self.playback_play_pause_button,
            self.playback_next_button,
        ):
            playback_button.setObjectName(
                "cardIconButton"
            )
            playback_button.setFixedSize(
                34,
                34,
            )
            playback_button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )
            playback_button.setFocusPolicy(
                Qt.FocusPolicy.StrongFocus
            )
            playback_button.setAccessibleDescription(
                playback_description
            )
            playback_button.setStatusTip(
                playback_description
            )
            playback_button.setEnabled(
                False
            )

        self.playback_previous_button.clicked.connect(
            self.request_previous_playback
        )
        self.playback_play_pause_button.clicked.connect(
            self.request_toggle_playback
        )
        self.playback_next_button.clicked.connect(
            self.request_next_playback
        )

        playback_row.addStretch()
        self.playback_shuffle_button = QPushButton()
        self.playback_shuffle_button.setObjectName(
            self.playback_previous_button.objectName()
        )
        self.playback_shuffle_button.setFixedSize(
            self.playback_previous_button.size()
        )
        self.playback_shuffle_button.setIconSize(
            self.playback_previous_button.iconSize()
        )
        self.playback_shuffle_button.setCursor(
            self.playback_previous_button.cursor()
        )
        self.playback_shuffle_button.setFocusPolicy(
            self.playback_previous_button.focusPolicy()
        )
        self.playback_shuffle_button.setAccessibleName(
            "Shuffle"
        )
        self.playback_shuffle_button.setAccessibleDescription(
            "Shuffle unavailable"
        )
        self.playback_shuffle_button.setStatusTip(
            "Toggle Spotify shuffle"
        )
        self.playback_shuffle_button.setToolTip(
            "Shuffle unavailable"
        )
        self.playback_shuffle_button.setEnabled(False)
        self.playback_shuffle_button.clicked.connect(
            self.request_shuffle_playback
        )

        self.playback_repeat_button = QPushButton()
        self.playback_repeat_button.setObjectName(
            self.playback_next_button.objectName()
        )
        self.playback_repeat_button.setFixedSize(
            self.playback_next_button.size()
        )
        self.playback_repeat_button.setIconSize(
            self.playback_next_button.iconSize()
        )
        self.playback_repeat_button.setCursor(
            self.playback_next_button.cursor()
        )
        self.playback_repeat_button.setFocusPolicy(
            self.playback_next_button.focusPolicy()
        )
        self.playback_repeat_button.setAccessibleName(
            "Repeat"
        )
        self.playback_repeat_button.setAccessibleDescription(
            "Repeat unavailable"
        )
        self.playback_repeat_button.setStatusTip(
            "Cycle Spotify repeat mode"
        )
        self.playback_repeat_button.setToolTip(
            "Repeat unavailable"
        )
        self.playback_repeat_button.setEnabled(False)
        self.playback_repeat_button.clicked.connect(
            self.request_repeat_playback
        )

        playback_row.addWidget(
            self.playback_shuffle_button
        )
        playback_row.addWidget(
            self.playback_previous_button
        )
        playback_row.addWidget(
            self.playback_play_pause_button
        )
        playback_row.addWidget(
            self.playback_next_button
        )
        playback_row.addWidget(
            self.playback_repeat_button
        )
        playback_row.addStretch()

        info_layout.addLayout(
            playback_row
        )

        self._refresh_playback_transport_icons()

        progress_row = QHBoxLayout()
        progress_row.setSpacing(8)

        self.current_time = QLabel(
            self.song.position
        )
        self.current_time.setObjectName(
            "timeLabel"
        )

        self.progress = PlaybackSeekSlider()
        self.progress.setObjectName(
            "playbackProgress"
        )
        self.progress.setRange(0, 10000)
        self.progress.setValue(0)
        self.progress.setEnabled(False)
        self.progress.setFocusPolicy(
            Qt.FocusPolicy.StrongFocus
        )
        self.progress.setAccessibleName(
            "Playback position"
        )
        self.progress.setAccessibleDescription(
            (
                "Drag or click to seek within "
                "the current track."
            )
        )

        self.progress_visual = PlaybackProgressVisual()
        self.progress_visual.setObjectName(
            "playbackProgressVisual"
        )
        self.progress_visual.setRange(
            0,
            10000,
        )
        self.progress_visual.setValue(
            0
        )
        self.progress_visual.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )

        self.progress.valueChanged.connect(
            self.progress_visual.setValue
        )

        self.progress_stack = QWidget()
        self.progress_stack.setObjectName(
            "playbackProgressStack"
        )

        progress_stack_layout = QGridLayout(
            self.progress_stack
        )
        progress_stack_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        progress_stack_layout.setSpacing(
            0
        )

        progress_stack_layout.addWidget(
            self.progress_visual,
            0,
            0,
            alignment=Qt.AlignmentFlag.AlignVCenter,
        )
        progress_stack_layout.addWidget(
            self.progress,
            0,
            0,
        )

        self.progress.raise_()

        self._playback_scrubbing = False
        self._playback_seek_pending = False
        self._playback_seek_target_seconds = None
        self._playback_seek_origin_seconds = None
        self._playback_seek_target_identity = None

        self._playback_seek_pending_timer = QTimer(
            self
        )
        self._playback_seek_pending_timer.setSingleShot(
            True
        )
        self._playback_seek_pending_timer.setInterval(
            PLAYBACK_SEEK_PENDING_TIMEOUT_MS
        )
        self._playback_seek_pending_timer.timeout.connect(
            self._expire_playback_seek_pending
        )

        self.progress.scrub_started.connect(
            self._begin_playback_scrub
        )
        self.progress.scrub_moved.connect(
            self._preview_playback_scrub
        )
        self.progress.scrub_committed.connect(
            self._commit_playback_scrub
        )

        self.total_time = QLabel(
            self.song.duration
        )
        self.total_time.setObjectName(
            "timeLabel"
        )

        progress_row.addWidget(
            self.current_time
        )
        progress_row.addWidget(
            self.progress_stack,
            stretch=1,
        )
        progress_row.addWidget(
            self.total_time
        )

        info_layout.addLayout(
            progress_row
        )

        lower_row = QHBoxLayout()
        lower_row.setSpacing(8)

        self.now_source = QLabel(
            "●  Waiting for media"
        )
        self.now_source.setObjectName(
            "sourceLine"
        )

        self.equalizer = QLabel(
            "▁▃▅▇▄▆▂▅"
        )
        self.equalizer.setObjectName(
            "equalizer"
        )

        lower_row.addWidget(
            self.now_source
        )
        lower_row.addStretch()
        lower_row.addWidget(
            self.equalizer
        )

        info_layout.addLayout(
            lower_row
        )

        body_layout.addLayout(
            info_layout,
            stretch=1,
        )

        outer_layout.addLayout(
            body_layout,
            stretch=1,
        )

    def _emit_playback_control(
        self,
        action: str,
    ) -> bool:
        song = getattr(
            self,
            "song",
            None,
        )

        play_button = getattr(
            self,
            "playback_play_pause_button",
            None,
        )

        if (
            song is None
            or not str(
                getattr(
                    song,
                    "title",
                    "",
                )
                or ""
            ).strip()
            or play_button is None
            or not play_button.isEnabled()
        ):
            return False

        source_app = str(
            getattr(
                song,
                "source_app",
                "",
            )
            or ""
        )

        playing = bool(
            getattr(
                song,
                "playing",
                False,
            )
        )

        self.playback_control_requested.emit(
            action,
            source_app,
            playing,
        )

        return True

    def request_previous_playback(
        self,
    ) -> bool:
        return self._emit_playback_control(
            "previous"
        )

    def request_toggle_playback(
        self,
    ) -> bool:
        return self._emit_playback_control(
            "toggle_play_pause"
        )

    def request_next_playback(
        self,
    ) -> bool:
        return self._emit_playback_control(
            "next"
        )

    def request_shuffle_playback(self):
        song = getattr(
            self,
            "song",
            None,
        )

        shuffle_active = getattr(
            song,
            "shuffle_active",
            None,
        )

        if not isinstance(
            shuffle_active,
            bool,
        ):
            return

        source_app = str(
            getattr(
                song,
                "source_app",
                "",
            )
            or ""
        )

        self.playback_shuffle_requested.emit(
            not shuffle_active,
            source_app,
        )

    def request_repeat_playback(self):
        song = getattr(
            self,
            "song",
            None,
        )

        repeat_mode = str(
            getattr(
                song,
                "repeat_mode",
                "",
            )
            or ""
        ).strip().casefold()

        desired_mode = {
            "off": "context",
            "context": "track",
            "track": "off",
        }.get(
            repeat_mode
        )

        if desired_mode is None:
            return

        source_app = str(
            getattr(
                song,
                "source_app",
                "",
            )
            or ""
        )

        self.playback_repeat_requested.emit(
            desired_mode,
            source_app,
        )

    def _playback_seek_seconds_for_value(
        self,
        value,
    ) -> float | None:
        song = getattr(
            self,
            "song",
            None,
        )

        if song is None:
            return None

        total_seconds = (
            self.time_to_seconds(
                getattr(
                    song,
                    "duration",
                    "",
                )
            )
        )

        if total_seconds <= 0:
            return None

        progress = getattr(
            self,
            "progress",
            None,
        )

        if progress is None:
            return None

        minimum = int(
            progress.minimum()
        )

        maximum = int(
            progress.maximum()
        )

        span = (
            maximum
            - minimum
        )

        if span <= 0:
            return None

        try:
            checked_value = int(
                value
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

        checked_value = max(
            minimum,
            min(
                maximum,
                checked_value,
            ),
        )

        ratio = (
            (
                checked_value
                - minimum
            )
            / span
        )

        return max(
            0.0,
            min(
                float(
                    total_seconds
                ),
                float(
                    total_seconds
                )
                * ratio,
            ),
        )

    @staticmethod
    def _playback_seek_identity(
        song,
    ) -> tuple[str, ...]:
        return (
            str(
                getattr(
                    song,
                    "title",
                    "",
                )
                or ""
            ),
            str(
                getattr(
                    song,
                    "artist",
                    "",
                )
                or ""
            ),
            str(
                getattr(
                    song,
                    "album",
                    "",
                )
                or ""
            ),
            str(
                getattr(
                    song,
                    "source_app",
                    "",
                )
                or ""
            ),
        )

    def _playback_seek_updates_blocked(
        self,
    ) -> bool:
        return bool(
            getattr(
                self,
                "_playback_scrubbing",
                False,
            )
            or getattr(
                self,
                "_playback_seek_pending",
                False,
            )
        )

    def _clear_playback_seek_pending(
        self,
    ) -> None:
        timer = getattr(
            self,
            "_playback_seek_pending_timer",
            None,
        )

        if (
            timer is not None
            and timer.isActive()
        ):
            timer.stop()

        self._playback_seek_pending = False
        self._playback_seek_target_seconds = None
        self._playback_seek_origin_seconds = None
        self._playback_seek_target_identity = None

    def _begin_playback_seek_pending(
        self,
        seconds: float,
        song,
    ) -> None:
        origin_seconds = float(
            self.time_to_seconds(
                getattr(
                    song,
                    "position",
                    "",
                )
            )
        )

        self._playback_seek_pending = True
        self._playback_seek_target_seconds = float(
            seconds
        )
        self._playback_seek_origin_seconds = (
            origin_seconds
        )
        self._playback_seek_target_identity = (
            self._playback_seek_identity(
                song
            )
        )

        self._playback_seek_pending_timer.start()

    def _expire_playback_seek_pending(
        self,
    ) -> None:
        if not bool(
            getattr(
                self,
                "_playback_seek_pending",
                False,
            )
        ):
            return

        self._clear_playback_seek_pending()

        self.refresh_playback_presentation()

    def _sync_playback_seek_pending(
        self,
        song,
    ) -> bool:
        if not bool(
            getattr(
                self,
                "_playback_seek_pending",
                False,
            )
        ):
            return False

        identity = (
            self._playback_seek_identity(
                song
            )
        )

        if (
            identity
            != getattr(
                self,
                "_playback_seek_target_identity",
                None,
            )
        ):
            self._clear_playback_seek_pending()
            return False

        target = getattr(
            self,
            "_playback_seek_target_seconds",
            None,
        )

        origin = getattr(
            self,
            "_playback_seek_origin_seconds",
            None,
        )

        if (
            target is None
            or origin is None
        ):
            self._clear_playback_seek_pending()
            return False

        current = float(
            self.time_to_seconds(
                getattr(
                    song,
                    "position",
                    "",
                )
            )
        )

        tolerance = (
            PLAYBACK_SEEK_CONFIRM_TOLERANCE_SECONDS
        )

        if target >= origin:
            confirmed = (
                current
                >= (
                    target
                    - tolerance
                )
            )

        else:
            confirmed = (
                current
                <= (
                    target
                    + tolerance
                )
            )

        if confirmed:
            self._clear_playback_seek_pending()
            return False

        return True

    def _begin_playback_scrub(
        self,
    ) -> None:
        progress = getattr(
            self,
            "progress",
            None,
        )

        if (
            progress is None
            or not progress.isEnabled()
        ):
            self._playback_scrubbing = False
            return

        self._clear_playback_seek_pending()

        self._playback_scrubbing = True

        self._preview_playback_scrub(
            progress.value()
        )

    def _preview_playback_scrub(
        self,
        value,
    ) -> None:
        if not bool(
            getattr(
                self,
                "_playback_scrubbing",
                False,
            )
        ):
            return

        seconds = (
            self._playback_seek_seconds_for_value(
                value
            )
        )

        if seconds is None:
            return

        self.current_time.setText(
            format_playback_time(
                seconds
            )
        )

    def _commit_playback_scrub(
        self,
        value,
    ) -> None:
        if not bool(
            getattr(
                self,
                "_playback_scrubbing",
                False,
            )
        ):
            return

        seconds = (
            self._playback_seek_seconds_for_value(
                value
            )
        )

        self._playback_scrubbing = False

        if seconds is None:
            self.refresh_playback_presentation()
            return

        song = getattr(
            self,
            "song",
            None,
        )

        source_app = str(
            getattr(
                song,
                "source_app",
                "",
            )
            or ""
        )

        self._begin_playback_seek_pending(
            float(
                seconds
            ),
            song,
        )

        self.current_time.setText(
            format_playback_time(
                seconds
            )
        )

        self.playback_seek_requested.emit(
            float(
                seconds
            ),
            source_app,
        )

    def _tinted_playback_standard_icon(
        self,
        standard_pixmap,
        *,
        accent_color,
        muted_color,
    ):
        from PyQt6.QtGui import (
            QColor,
            QIcon,
            QPainter,
        )

        source_icon = (
            self.style().standardIcon(
                standard_pixmap
            )
        )

        themed_icon = QIcon()

        for (
            mode,
            color,
        ) in (
            (
                QIcon.Mode.Normal,
                accent_color,
            ),
            (
                QIcon.Mode.Active,
                accent_color,
            ),
            (
                QIcon.Mode.Selected,
                accent_color,
            ),
            (
                QIcon.Mode.Disabled,
                muted_color,
            ),
        ):
            pixmap = source_icon.pixmap(
                16,
                16,
            )

            if pixmap.isNull():
                continue

            painter = QPainter(
                pixmap
            )

            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceIn
            )

            painter.fillRect(
                pixmap.rect(),
                QColor(
                    color
                ),
            )

            painter.end()

            themed_icon.addPixmap(
                pixmap,
                mode,
                QIcon.State.Off,
            )

        return themed_icon

    def _playback_mode_icon(
        self,
        mode,
        *,
        active=False,
        enabled=True,
        theme=None,
    ):
        resolved_theme = (
            theme
            if isinstance(
                theme,
                dict,
            )
            else getattr(
                self,
                "_playback_control_theme",
                {},
            )
        )

        if not isinstance(
            resolved_theme,
            dict,
        ):
            resolved_theme = {}

        if active:
            colour = resolved_theme.get(
                "accent",
                "#ff6fbd",
            )
        elif enabled:
            colour = resolved_theme.get(
                "text",
                "#f2f2f2",
            )
        else:
            colour = resolved_theme.get(
                "muted",
                "#777777",
            )

        icon_colour = QColor(
            str(colour)
        )

        pixmap = QPixmap(
            20,
            20,
        )

        pixmap.fill(
            Qt.GlobalColor.transparent
        )

        painter = QPainter(
            pixmap
        )

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )

        pen = painter.pen()

        pen.setColor(
            icon_colour
        )

        pen.setWidthF(
            2.65
        )

        pen.setCapStyle(
            Qt.PenCapStyle.RoundCap
        )

        pen.setJoinStyle(
            Qt.PenJoinStyle.RoundJoin
        )

        painter.setPen(
            pen
        )

        normalized = str(
            mode
            or ""
        ).strip().casefold()

        if normalized == "shuffle":
            upper_path = QPainterPath()

            upper_path.moveTo(
                2.8,
                5.2,
            )

            upper_path.lineTo(
                5.0,
                5.2,
            )

            upper_path.cubicTo(
                7.7,
                5.2,
                10.2,
                14.8,
                14.5,
                14.8,
            )

            upper_path.lineTo(
                15.1,
                14.8,
            )

            painter.drawPath(
                upper_path
            )

            lower_path = QPainterPath()

            lower_path.moveTo(
                2.8,
                14.8,
            )

            lower_path.lineTo(
                5.0,
                14.8,
            )

            lower_path.cubicTo(
                7.7,
                14.8,
                10.2,
                5.2,
                14.5,
                5.2,
            )

            lower_path.lineTo(
                15.1,
                5.2,
            )

            painter.drawPath(
                lower_path
            )

            top_arrow = QPainterPath()

            top_arrow.moveTo(
                14.2,
                1.9,
            )

            top_arrow.lineTo(
                18.0,
                5.2,
            )

            top_arrow.lineTo(
                14.2,
                8.5,
            )

            top_arrow.closeSubpath()

            painter.fillPath(
                top_arrow,
                icon_colour,
            )

            bottom_arrow = QPainterPath()

            bottom_arrow.moveTo(
                14.2,
                11.5,
            )

            bottom_arrow.lineTo(
                18.0,
                14.8,
            )

            bottom_arrow.lineTo(
                14.2,
                18.1,
            )

            bottom_arrow.closeSubpath()

            painter.fillPath(
                bottom_arrow,
                icon_colour,
            )

        else:
            top_path = QPainterPath()

            top_path.moveTo(
                3.0,
                8.2,
            )

            top_path.cubicTo(
                3.0,
                5.5,
                5.0,
                4.0,
                7.5,
                4.0,
            )

            top_path.lineTo(
                15.1,
                4.0,
            )

            painter.drawPath(
                top_path
            )

            top_arrow = QPainterPath()

            top_arrow.moveTo(
                14.5,
                1.2,
            )

            top_arrow.lineTo(
                18.4,
                4.0,
            )

            top_arrow.lineTo(
                14.5,
                6.8,
            )

            top_arrow.closeSubpath()

            painter.fillPath(
                top_arrow,
                icon_colour,
            )

            bottom_path = QPainterPath()

            bottom_path.moveTo(
                17.0,
                11.8,
            )

            bottom_path.cubicTo(
                17.0,
                14.5,
                15.0,
                16.0,
                12.5,
                16.0,
            )

            bottom_path.lineTo(
                4.9,
                16.0,
            )

            painter.drawPath(
                bottom_path
            )

            bottom_arrow = QPainterPath()

            bottom_arrow.moveTo(
                5.5,
                13.2,
            )

            bottom_arrow.lineTo(
                1.6,
                16.0,
            )

            bottom_arrow.lineTo(
                5.5,
                18.8,
            )

            bottom_arrow.closeSubpath()

            painter.fillPath(
                bottom_arrow,
                icon_colour,
            )

            if normalized == "track":
                text_pen = painter.pen()

                text_pen.setWidthF(
                    1.0
                )

                text_pen.setColor(
                    icon_colour
                )

                painter.setPen(
                    text_pen
                )

                font = painter.font()

                font.setPixelSize(
                    7
                )

                font.setBold(
                    True
                )

                painter.setFont(
                    font
                )

                painter.drawText(
                    8,
                    13,
                    "1",
                )

        painter.end()

        return QIcon(
            pixmap
        )

    def _refresh_playback_mode_icons(
        self,
        theme=None,
    ):
        if isinstance(
            theme,
            dict,
        ):
            self._playback_control_theme = dict(
                theme
            )

        resolved_theme = getattr(
            self,
            "_playback_control_theme",
            {},
        )

        shuffle_button = getattr(
            self,
            "playback_shuffle_button",
            None,
        )

        repeat_button = getattr(
            self,
            "playback_repeat_button",
            None,
        )

        if shuffle_button is not None:
            shuffle_button.setIcon(
                self._playback_mode_icon(
                    "shuffle",
                    active=bool(
                        shuffle_button.property(
                            "playbackModeActive"
                        )
                    ),
                    enabled=(
                        shuffle_button.isEnabled()
                    ),
                    theme=resolved_theme,
                )
            )

        if repeat_button is not None:
            repeat_mode = str(
                repeat_button.property(
                    "playbackRepeatMode"
                )
                or "off"
            ).strip().casefold()

            repeat_button.setIcon(
                self._playback_mode_icon(
                    (
                        "track"
                        if repeat_mode
                        == "track"
                        else "repeat"
                    ),
                    active=(
                        repeat_mode
                        in {
                            "context",
                            "track",
                        }
                    ),
                    enabled=(
                        repeat_button.isEnabled()
                    ),
                    theme=resolved_theme,
                )
            )

    def _refresh_playback_transport_icons(
        self,
        theme=None,
        *,
        playing=None,
    ):
        previous_button = getattr(
            self,
            "playback_previous_button",
            None,
        )

        play_pause_button = getattr(
            self,
            "playback_play_pause_button",
            None,
        )

        next_button = getattr(
            self,
            "playback_next_button",
            None,
        )

        if (
            previous_button is None
            or play_pause_button is None
            or next_button is None
        ):
            return

        if theme is None:
            theme_manager = getattr(
                self,
                "theme_manager",
                None,
            )

            if theme_manager is None:
                return

            theme = dict(
                theme_manager.theme()
            )

        accent_color = str(
            theme.get(
                "accent",
                "#ffffff",
            )
        )

        muted_color = str(
            theme.get(
                "muted",
                accent_color,
            )
        )

        if playing is None:
            song = getattr(
                self,
                "song",
                None,
            )

            playing = bool(
                play_pause_button.isEnabled()
                and song is not None
                and getattr(
                    song,
                    "playing",
                    False,
                )
            )

        previous_button.setText(
            ""
        )

        play_pause_button.setText(
            ""
        )

        next_button.setText(
            ""
        )

        previous_button.setIcon(
            self._tinted_playback_standard_icon(
                QStyle.StandardPixmap.SP_MediaSkipBackward,
                accent_color=accent_color,
                muted_color=muted_color,
            )
        )

        play_pause_button.setIcon(
            self._tinted_playback_standard_icon(
                (
                    QStyle.StandardPixmap.SP_MediaPause
                    if playing
                    else QStyle.StandardPixmap.SP_MediaPlay
                ),
                accent_color=accent_color,
                muted_color=muted_color,
            )
        )

        next_button.setIcon(
            self._tinted_playback_standard_icon(
                QStyle.StandardPixmap.SP_MediaSkipForward,
                accent_color=accent_color,
                muted_color=muted_color,
            )
        )

        self._refresh_playback_mode_icons(
            theme
        )

    def sync_playback_control_state(
        self,
        *,
        available: bool | None = None,
    ) -> None:
        previous_button = getattr(
            self,
            "playback_previous_button",
            None,
        )

        play_pause_button = getattr(
            self,
            "playback_play_pause_button",
            None,
        )

        next_button = getattr(
            self,
            "playback_next_button",
            None,
        )

        if (
            previous_button is None
            or play_pause_button is None
            or next_button is None
        ):
            return

        song = getattr(
            self,
            "song",
            None,
        )

        if available is None:
            available = bool(
                song is not None
                and str(
                    getattr(
                        song,
                        "title",
                        "",
                    )
                    or ""
                ).strip()
            )

        enabled = bool(
            available
        )

        for button in (
            previous_button,
            play_pause_button,
            next_button,
        ):
            button.setEnabled(
                enabled
            )

        playing = bool(
            enabled
            and getattr(
                song,
                "playing",
                False,
            )
        )

        if playing:
            play_pause_button.setToolTip(
                "Pause"
            )
            play_pause_button.setAccessibleName(
                "Pause"
            )

        else:
            play_pause_button.setToolTip(
                "Play"
            )
            play_pause_button.setAccessibleName(
                "Play"
            )
        self._refresh_playback_transport_icons(
            playing=playing
        )

        song = getattr(
            self,
            "song",
            None,
        )

        shuffle_state = (
            getattr(
                song,
                "shuffle_active",
                None,
            )
            if available
            else None
        )

        repeat_mode = (
            str(
                getattr(
                    song,
                    "repeat_mode",
                    "",
                )
                or ""
            ).strip().casefold()
            if available
            else ""
        )

        shuffle_known = isinstance(
            shuffle_state,
            bool,
        )

        repeat_known = (
            repeat_mode
            in {
                "off",
                "context",
                "track",
            }
        )

        self.playback_shuffle_button.setEnabled(
            bool(
                available
                and shuffle_known
            )
        )

        self.playback_repeat_button.setEnabled(
            bool(
                available
                and repeat_known
            )
        )

        self.playback_shuffle_button.setProperty(
            "playbackModeActive",
            (
                bool(shuffle_state)
                if shuffle_known
                else False
            ),
        )

        self.playback_repeat_button.setProperty(
            "playbackModeActive",
            (
                repeat_mode
                in {
                    "context",
                    "track",
                }
            )
            if repeat_known
            else False,
        )

        self.playback_repeat_button.setProperty(
            "playbackRepeatMode",
            (
                repeat_mode
                if repeat_known
                else ""
            ),
        )

        if shuffle_known:
            shuffle_label = (
                "Shuffle on"
                if shuffle_state
                else "Shuffle off"
            )
        else:
            shuffle_label = (
                "Shuffle unavailable"
            )

        if repeat_known:
            repeat_label = {
                "off": "Repeat off",
                "context": (
                    "Repeat context"
                ),
                "track": "Repeat track",
            }[repeat_mode]
        else:
            repeat_label = (
                "Repeat unavailable"
            )

        self.playback_shuffle_button.setToolTip(
            shuffle_label
        )

        self.playback_shuffle_button.setAccessibleDescription(
            shuffle_label
        )

        self.playback_repeat_button.setToolTip(
            repeat_label
        )

        self.playback_repeat_button.setAccessibleDescription(
            repeat_label
        )

        self._refresh_playback_mode_icons()

    def build_discord_preview_card(self):
        self.preview_card = DiscordProfilePreview(
            self
        )
        self.preview_card.setObjectName(
            "previewCard"
        )
        self.preview_card.set_compact(True)

        self.preview_card.set_profile(
            display_name="Your Discord profile",
            username="",
            status="Preview",
        )

        self.discord_profile_preview = (
            self.preview_card
        )

        self._discord_preview_mode = "music"
        self._discord_presence_payload = {}
        self._discord_presence_elapsed_started = None

        self.discord_presence_preview_timer = QTimer(
            self
        )
        self.discord_presence_preview_timer.setInterval(
            1000
        )
        self.discord_presence_preview_timer.timeout.connect(
            self.refresh_discord_presence_preview_elapsed
        )

        # Preserve the established Dashboard
        # presentation attributes. Existing media
        # update paths can feed the richer widget
        # without owning its layout.
        self.preview_mode = (
            self.preview_card.activity_source_badge
        )
        self.preview_app = (
            self.preview_card.activity_application
        )
        self.preview_artwork = (
            self.preview_card.activity_artwork
        )
        self.preview_title = (
            self.preview_card.activity_title
        )
        self.preview_state = (
            self.preview_card.activity_artist
        )
        self.preview_album = (
            self.preview_card.activity_album
        )
        self.preview_time = (
            self.preview_card.activity_time
        )

        self.preview_card.open_discord_button.setIcon(
            self.style().standardIcon(
                QStyle.StandardPixmap.SP_ArrowForward
            )
        )
        self.preview_card.open_discord_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.preview_card.open_discord_requested.connect(
            self.open_discord
        )

    def set_discord_profile_identity(
        self,
        identity,
    ):
        preview = getattr(
            self,
            "discord_profile_preview",
            None,
        )

        if preview is None:
            return

        source = (
            identity
            if isinstance(identity, dict)
            else {}
        )

        display_name = str(
            source.get(
                "display_name"
            )
            or source.get(
                "username"
            )
            or "Your Discord profile"
        ).strip()

        username = str(
            source.get(
                "username"
            )
            or ""
        ).strip()

        user_id = str(
            source.get(
                "user_id"
            )
            or ""
        ).strip()

        avatar_hash = str(
            source.get(
                "avatar_hash"
            )
            or ""
        ).strip()

        identity_key = (
            user_id,
            username,
            display_name,
            avatar_hash,
        )

        if identity_key == getattr(
            self,
            "_discord_profile_identity_key",
            None,
        ):
            return

        self._discord_profile_identity_key = (
            identity_key
        )

        username_label = (
            f"@{username}"
            if username
            else ""
        )

        self._discord_profile_identity_values = {
            "display_name": display_name,
            "username": username_label,
        }

        # Render the identity immediately with the
        # normal initial fallback. The asynchronous
        # avatar replaces it when available.
        preview.set_profile(
            display_name=display_name,
            username=username_label,
            status="",
        )

        self._discord_profile_avatar_key = ""

        loader = getattr(
            self,
            "discord_avatar_loader",
            None,
        )

        if (
            loader is not None
            and user_id
        ):
            self._discord_profile_avatar_key = (
                loader.request_avatar(
                    user_id,
                    avatar_hash,
                )
            )

    def apply_discord_profile_avatar(
        self,
        avatar_key,
        pixmap,
    ):
        if (
            not avatar_key
            or avatar_key != getattr(
                self,
                "_discord_profile_avatar_key",
                "",
            )
        ):
            return

        if (
            pixmap is None
            or pixmap.isNull()
        ):
            return

        preview = getattr(
            self,
            "discord_profile_preview",
            None,
        )

        values = getattr(
            self,
            "_discord_profile_identity_values",
            {},
        )

        if (
            preview is None
            or not isinstance(values, dict)
        ):
            return

        display_name = str(
            values.get(
                "display_name"
            )
            or "Discord profile"
        ).strip()

        username = str(
            values.get(
                "username"
            )
            or ""
        ).strip()

        preview.set_profile(
            display_name=display_name,
            username=username,
            status="",
            avatar=pixmap,
        )

    def _discord_music_preview_active(
        self,
    ) -> bool:
        return (
            str(
                getattr(
                    self,
                    "_discord_preview_mode",
                    "music",
                )
                or "music"
            ).strip().lower()
            == "music"
        )

    @pyqtSlot(dict)
    def set_discord_presence_mode(
        self,
        payload,
    ):
        source = (
            dict(payload)
            if isinstance(payload, dict)
            else {}
        )

        mode = str(
            source.get(
                "mode"
            )
            or "music"
        ).strip().lower()

        if not mode:
            mode = "music"

        self._discord_preview_mode = mode
        self._discord_presence_payload = source

        timer = getattr(
            self,
            "discord_presence_preview_timer",
            None,
        )

        if timer is not None:
            timer.stop()

        self._discord_presence_elapsed_started = None

        if mode == "music":
            # A custom Presence mode can replace
            # only the Discord-preview artwork while
            # the normal song-artwork signature still
            # says the current track is already painted.
            # Force one presentation refresh when
            # returning to Music.
            self._last_artwork_signature = None

            song = getattr(
                self,
                "song",
                None,
            )

            if (
                song is not None
                and str(
                    getattr(
                        song,
                        "title",
                        "",
                    )
                    or ""
                ).strip()
            ):
                self.apply_song(
                    song
                )
            else:
                self.show_nothing_playing()

            return

        if mode == "disabled":
            self._render_discord_presence_payload()
            return

        if bool(
            source.get(
                "show_elapsed"
            )
        ):
            self._discord_presence_elapsed_started = (
                time.monotonic()
            )

        self._render_discord_presence_payload()

    def _render_discord_presence_payload(
        self,
    ):
        if self._discord_music_preview_active():
            return

        timer = getattr(
            self,
            "discord_presence_preview_timer",
            None,
        )

        source = getattr(
            self,
            "_discord_presence_payload",
            {},
        )

        if not isinstance(source, dict):
            source = {}

        mode = str(
            source.get(
                "mode"
            )
            or getattr(
                self,
                "_discord_preview_mode",
                "custom",
            )
            or "custom"
        ).strip().lower()

        mode_name = str(
            MODE_NAMES.get(
                mode,
                mode.replace(
                    "_",
                    " ",
                ).title(),
            )
            or mode
            or "Presence"
        ).strip()

        mode_badge = (
            "OFF"
            if mode == "disabled"
            else mode_name.upper()
        )

        title = str(
            source.get(
                "title"
            )
            or (
                "Rich Presence disabled"
                if mode == "disabled"
                else "Custom presence"
            )
        ).strip()

        message = str(
            source.get(
                "message"
            )
            or (
                "Nothing is being published"
                if mode == "disabled"
                else ""
            )
        ).strip()

        self.preview_mode.setText(
            mode_badge
        )

        self.preview_title.setText(
            title
        )

        self.preview_state.setText(
            message
        )
        self.preview_state.setHidden(
            not bool(message)
        )

        self.preview_album.setText("")
        self.preview_album.setHidden(True)

        preview = getattr(
            self,
            "discord_profile_preview",
            None,
        )

        if preview is not None:
            preview.activity_progress.setValue(
                0
            )
            preview.activity_progress.setHidden(
                True
            )

        image_bytes = source.get(
            "image_bytes"
        )

        if isinstance(
            image_bytes,
            bytearray,
        ):
            image_bytes = bytes(
                image_bytes
            )

        pixmap = QPixmap()

        image_loaded = bool(
            isinstance(
                image_bytes,
                bytes,
            )
            and image_bytes
            and pixmap.loadFromData(
                image_bytes
            )
            and not pixmap.isNull()
        )

        self.preview_artwork.clear()

        if image_loaded:
            width = max(
                1,
                self.preview_artwork.width(),
            )
            height = max(
                1,
                self.preview_artwork.height(),
            )

            self.preview_artwork.setPixmap(
                pixmap.scaled(
                    width,
                    height,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            fallback = (
                "OFF"
                if mode == "disabled"
                else mode_name[:5]
            )

            self.preview_artwork.setText(
                fallback
                or "Mode"
            )

        show_elapsed = bool(
            source.get(
                "show_elapsed"
            )
        )

        if (
            show_elapsed
            and mode != "disabled"
        ):
            if (
                self._discord_presence_elapsed_started
                is None
            ):
                self._discord_presence_elapsed_started = (
                    time.monotonic()
                )

            self.refresh_discord_presence_preview_elapsed()

            if timer is not None:
                timer.start()
        else:
            self.preview_time.setText("")
            self.preview_time.setHidden(True)

            if timer is not None:
                timer.stop()

    def refresh_discord_presence_preview_elapsed(
        self,
    ):
        if self._discord_music_preview_active():
            return

        source = getattr(
            self,
            "_discord_presence_payload",
            {},
        )

        if (
            not isinstance(source, dict)
            or not bool(
                source.get(
                    "show_elapsed"
                )
            )
        ):
            return

        started = getattr(
            self,
            "_discord_presence_elapsed_started",
            None,
        )

        if started is None:
            return

        elapsed = max(
            0.0,
            time.monotonic()
            - float(started),
        )

        self.preview_time.setText(
            format_playback_time(
                elapsed
            )
        )
        self.preview_time.setHidden(False)

    def _restore_non_music_discord_preview(
        self,
    ):
        if not self._discord_music_preview_active():
            self._render_discord_presence_payload()

    def open_discord(self):
        try:
            os.startfile(
                "discord://-/channels/@me"
            )
            return

        except Exception:
            pass

        local_app_data = os.getenv(
            "LOCALAPPDATA",
            "",
        )

        discord_versions = [
            (
                "Discord",
                "Discord.exe",
            ),
            (
                "DiscordPTB",
                "DiscordPTB.exe",
            ),
            (
                "DiscordCanary",
                "DiscordCanary.exe",
            ),
        ]

        for folder, executable in discord_versions:
            updater = os.path.join(
                local_app_data,
                folder,
                "Update.exe",
            )

            if not os.path.exists(
                updater
            ):
                continue

            try:
                creation_flags = getattr(
                    subprocess,
                    "CREATE_NO_WINDOW",
                    0,
                )

                subprocess.Popen(
                    [
                        updater,
                        "--processStart",
                        executable,
                    ],
                    creationflags=creation_flags,
                )
                return

            except Exception:
                continue

        QDesktopServices.openUrl(
            QUrl(
                "https://discord.com/app"
            )
        )

    def open_current_source(self):
        source = str(
            getattr(
                self.song,
                "source_app",
                "",
            )
            or ""
        ).lower()

        if "spotify" in source:
            QDesktopServices.openUrl(
                QUrl("spotify:")
            )
            return

        if any(
            browser in source
            for browser in (
                "chrome",
                "msedge",
                "firefox",
                "brave",
                "opera",
                "vivaldi",
            )
        ):
            QDesktopServices.openUrl(
                QUrl("https://soundcloud.com")
            )
            return

        self.navigate_requested.emit(2)

    def build_recent_card(self):
        self.recent_card = QFrame()
        self.recent_card.setObjectName(
            "recentCard"
        )

        layout = QVBoxLayout(
            self.recent_card
        )
        layout.setContentsMargins(
            16,
            14,
            16,
            14,
        )
        layout.setSpacing(8)

        heading_row = QHBoxLayout()

        heading = QLabel(
            "RECENTLY PLAYED"
        )
        heading.setObjectName(
            "sectionLabel"
        )

        view_all = QPushButton(
            "View all"
        )
        view_all.setObjectName(
            "textButton"
        )
        view_all.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        view_all.clicked.connect(
            lambda:
            self.navigate_requested.emit(2)
        )

        heading_row.addWidget(heading)
        heading_row.addStretch()
        heading_row.addWidget(view_all)

        layout.addLayout(heading_row)

        self.recent_empty = QLabel(
            (
                "Your recent listening "
                "history will appear here."
            )
        )
        self.recent_empty.setObjectName(
            "emptyRecent"
        )
        self.recent_empty.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.recent_empty.setWordWrap(True)

        layout.addWidget(
            self.recent_empty,
            stretch=1,
        )

        self.recent_rows = []

        for _ in range(self._recent_track_fetch_limit):
            row_card = QFrame()
            row_card.setObjectName(
                "recentRow"
            )
            row_card.setFixedHeight(
                48
            )
            row_card.hide()

            row_layout = QHBoxLayout(
                row_card
            )
            row_layout.setContentsMargins(
                10,
                7,
                10,
                7,
            )
            row_layout.setSpacing(10)

            icon = QLabel("♪")
            icon.setObjectName(
                "recentIcon"
            )
            icon.setFixedSize(34, 34)
            icon.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            text_layout = QVBoxLayout()
            text_layout.setSpacing(0)

            title = QLabel("")
            title.setObjectName(
                "recentTitle"
            )

            artist = QLabel("")
            artist.setObjectName(
                "recentArtist"
            )

            text_layout.addWidget(title)
            text_layout.addWidget(artist)

            source = QLabel("")
            source.setObjectName(
                "recentSource"
            )
            source.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            played = QLabel("")
            played.setObjectName(
                "recentTime"
            )
            played.setAlignment(
                Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignVCenter
            )

            row_layout.addWidget(icon)
            row_layout.addLayout(
                text_layout,
                stretch=1,
            )
            row_layout.addWidget(source)
            row_layout.addWidget(played)

            layout.addWidget(row_card)

            self.recent_rows.append(
                {
                    "card": row_card,
                    "icon": icon,
                    "title": title,
                    "artist": artist,
                    "source": source,
                    "time": played,
                }
            )

    def build_quick_access_card(self):
        self.quick_access_card = QFrame()
        self.quick_access_card.setObjectName(
            "quickAccessCard"
        )

        layout = QVBoxLayout(
            self.quick_access_card
        )
        layout.setContentsMargins(
            14,
            12,
            14,
            12,
        )
        layout.setSpacing(8)

        heading = QLabel(
            "ϟ  QUICK ACCESS"
        )
        heading.setObjectName(
            "sectionLabel"
        )

        layout.addWidget(
            heading
        )

        self.quick_access_grid = QGridLayout()
        self.quick_access_grid.setHorizontalSpacing(
            8
        )
        self.quick_access_grid.setVerticalSpacing(
            8
        )

        self.quick_access_buttons = []

        layout.addLayout(
            self.quick_access_grid,
            stretch=1,
        )

        self.refresh_quick_access_buttons(
            force=True
        )

    def _make_quick_access_button(
        self,
        *,
        icon: str,
        title: str,
        detail: str,
        callback,
    ) -> dict:
        button = QPushButton()
        button.setObjectName(
            "quickButton"
        )
        button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        button.setMinimumHeight(0)
        button.setToolTip(
            f"{title}: {detail}"
        )
        button.clicked.connect(callback)

        return {
            "button": button,
            "icon": icon,
            "title": title,
            "detail": detail,
        }

    def refresh_quick_access_buttons(
        self,
        force: bool = False,
    ):
        if not hasattr(
            self,
            "quick_access_grid",
        ):
            return

        while self.quick_access_grid.count():
            item = self.quick_access_grid.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.setParent(None)

        for item in getattr(
            self,
            "quick_access_buttons",
            [],
        ):
            button = item.get(
                "button"
            )

            if button is not None:
                button.deleteLater()

        self.quick_access_buttons = []

        page_buttons = [
            (
                chr(0x2659),
                "AFK",
                "Set AFK presence",
                1,
            ),
            (
                chr(0x270E),
                "Custom",
                "Create a presence",
                1,
            ),
            (
                chr(0x2605),
                "Presets",
                "Manage presence modes",
                1,
            ),
            (
                chr(0x2699),
                "Settings",
                "Configure application",
                3,
            ),
        ]

        for (
            icon,
            title,
            detail,
            page_index,
        ) in page_buttons:
            self.quick_access_buttons.append(
                self._make_quick_access_button(
                    icon=icon,
                    title=title,
                    detail=detail,
                    callback=(
                        lambda checked=False,
                        index=page_index:
                        self.navigate_requested.emit(
                            index
                        )
                    ),
                )
            )

        for preset in self.presence_preset_store.pinned():
            mode_name = MODE_NAMES.get(
                preset.mode,
                preset.mode.title(),
            )

            self.quick_access_buttons.append(
                self._make_quick_access_button(
                    icon=chr(0x2605),
                    title=preset.name,
                    detail=f"Apply {mode_name}",
                    callback=(
                        lambda checked=False,
                        preset_id=preset.preset_id:
                        self.apply_presence_preset_requested.emit(
                            preset_id
                        )
                    ),
                )
            )

        self._quick_access_layout_mode = None

        self.update_quick_access_layout(
            force=force,
        )

    def recent_track_capacity(self) -> int:
        if not hasattr(
            self,
            "recent_rows",
        ):
            return 0

        card_height = max(
            0,
            self.recent_card.height(),
        )

        header_and_margins = 55
        row_height = 48
        row_spacing = 8

        available_height = max(
            0,
            (
                card_height
                - header_and_margins
            ),
        )

        capacity = (
            (
                available_height
                + row_spacing
            )
            // (
                row_height
                + row_spacing
            )
        )

        return max(
            1,
            min(
                len(
                    self.recent_rows
                ),
                capacity,
            ),
        )

    def update_quick_access_layout(
        self,
        force: bool = False,
    ):
        if (
            not hasattr(
                self,
                "quick_access_grid",
            )
            or not hasattr(
                self,
                "quick_access_buttons",
            )
        ):
            return

        card_width = max(
            1,
            self.quick_access_card.width(),
        )

        card_height = max(
            1,
            self.quick_access_card.height(),
        )

        if card_width < 330:
            columns = 1
        elif card_width >= 720:
            columns = 4
        else:
            columns = 2

        button_count = len(
            self.quick_access_buttons
        )

        rows = max(
            1,
            (
                button_count
                + columns
                - 1
            )
            // columns,
        )

        horizontal_spacing = 8
        vertical_spacing = 8
        horizontal_margins = 28
        vertical_overhead = 60

        button_width = max(
            1,
            (
                card_width
                - horizontal_margins
                - (
                    horizontal_spacing
                    * (
                        columns
                        - 1
                    )
                )
            )
            // columns,
        )

        button_height = max(
            1,
            (
                card_height
                - vertical_overhead
                - (
                    vertical_spacing
                    * (
                        rows
                        - 1
                    )
                )
            )
            // rows,
        )

        show_details = (
            button_width >= 145
            and button_height >= 66
        )

        layout_mode = (
            columns,
            rows,
            show_details,
        )

        if (
            not force
            and layout_mode
            == self._quick_access_layout_mode
        ):
            return

        while self.quick_access_grid.count():
            self.quick_access_grid.takeAt(
                0
            )

        for index in range(4):
            self.quick_access_grid.setColumnStretch(
                index,
                0,
            )
            self.quick_access_grid.setRowStretch(
                index,
                0,
            )

        for column in range(
            columns
        ):
            self.quick_access_grid.setColumnStretch(
                column,
                1,
            )

        for row in range(
            rows
        ):
            self.quick_access_grid.setRowStretch(
                row,
                1,
            )

        for index, item in enumerate(
            self.quick_access_buttons
        ):
            row = index // columns
            column = index % columns

            text = (
                f"{item['icon']}  {item['title']}"
            )

            if show_details:
                text += (
                    "\n"
                    + item["detail"]
                )

            button = item[
                "button"
            ]

            button.setText(
                text
            )

            button.setProperty(
                "compactQuickAccess",
                not show_details,
            )

            self._refresh_dashboard_widget_style(
                button
            )

            self.quick_access_grid.addWidget(
                button,
                row,
                column,
            )

        self._quick_access_layout_mode = (
            layout_mode
        )

    def update_responsive_dashboard_cards(
        self,
        card_id: str | None = None,
    ):
        if (
            card_id is None
            or card_id == "recently_played"
        ):
            if hasattr(
                self,
                "recent_rows",
            ):
                self.populate_recent_tracks(
                    self._recent_tracks
                )

        if (
            card_id is None
            or card_id == "quick_access"
        ):
            self.update_quick_access_layout()

    def set_spotify_queue_runtime(
        self,
        runtime,
    ) -> None:
        loader = getattr(
            runtime,
            "load_queue",
            None,
        )

        if not callable(
            loader
        ):
            raise TypeError(
                (
                    "runtime must expose a callable "
                    "load_queue() method"
                )
            )

        existing = getattr(
            self,
            "spotify_queue_runtime",
            None,
        )

        if existing is runtime:
            return

        self.spotify_queue_runtime = (
            runtime
        )

        queue_ready = getattr(
            runtime,
            "queue_ready",
            None,
        )

        connect_ready = getattr(
            queue_ready,
            "connect",
            None,
        )

        if callable(
            connect_ready
        ):
            connect_ready(
                lambda result:
                DashboardPage.show_spotify_queue_result(
                    self,
                    result,
                )
            )

        failed = getattr(
            runtime,
            "failed",
            None,
        )

        connect_failed = getattr(
            failed,
            "connect",
            None,
        )

        if callable(
            connect_failed
        ):
            connect_failed(
                lambda error_code, message:
                DashboardPage.show_spotify_queue_runtime_failure(
                    self,
                    error_code,
                    message,
                )
            )

        busy_changed = getattr(
            runtime,
            "busy_changed",
            None,
        )

        connect_busy = getattr(
            busy_changed,
            "connect",
            None,
        )

        if callable(
            connect_busy
        ):
            connect_busy(
                lambda busy:
                DashboardPage.set_spotify_queue_busy(
                    self,
                    busy,
                )
            )




    def _spotify_queue_card_visible(
        self,
    ) -> bool:
        layout = getattr(
            self,
            "dashboard_layout_state",
            None,
        )

        if layout is None:
            return False

        try:
            queue_layout = layout.card(
                "queue"
            )

        except (
            AttributeError,
            KeyError,
        ):
            return False

        return bool(
            queue_layout.visible
        )

    def _spotify_queue_item_detail(
        self,
        item,
    ) -> str:
        creator = str(
            getattr(
                item,
                "creator",
                "",
            )
            or ""
        ).strip()

        collection = str(
            getattr(
                item,
                "collection",
                "",
            )
            or ""
        ).strip()

        if (
            creator
            and collection
            and creator.casefold()
            != collection.casefold()
        ):
            return (
                f"{creator} - {collection}"
            )

        if creator:
            return creator

        if collection:
            return collection

        if bool(
            getattr(
                item,
                "is_local",
                False,
            )
        ):
            return "Local file"

        return "Spotify"

    def _spotify_queue_item_duration(
        self,
        item,
    ) -> str:
        duration_ms = getattr(
            item,
            "duration_ms",
            None,
        )

        if (
            isinstance(
                duration_ms,
                bool,
            )
            or not isinstance(
                duration_ms,
                int,
            )
            or duration_ms <= 0
        ):
            return ""

        return format_playback_time(
            duration_ms / 1000.0
        )

    def _set_spotify_queue_row(
        self,
        row,
        item,
        *,
        marker: str,
        badge: str,
    ) -> None:
        row["icon"].setText(
            marker
        )

        row["title"].setText(
            str(
                getattr(
                    item,
                    "name",
                    "",
                )
                or "Unknown item"
            )
        )

        row["artist"].setText(
            DashboardPage
            ._spotify_queue_item_detail(
                self,
                item,
            )
        )

        row["source"].setText(
            badge
        )

        row["source"].setVisible(
            bool(badge)
        )

        row["time"].setText(
            DashboardPage
            ._spotify_queue_item_duration(
                self,
                item,
            )
        )

        row["card"].setVisible(
            True
        )

    def _show_spotify_queue_message(
        self,
        message: str,
        *,
        status_text: str | None = None,
    ) -> None:
        placeholder = getattr(
            self,
            "queue_placeholder",
            None,
        )

        if placeholder is not None:
            placeholder.setText(
                str(
                    message
                    or (
                        "Spotify Queue is "
                        "unavailable."
                    )
                )
            )
            placeholder.setVisible(
                True
            )

        current_row = getattr(
            self,
            "queue_current_row",
            None,
        )

        if current_row is not None:
            current_row[
                "card"
            ].setVisible(
                False
            )

        up_next = getattr(
            self,
            "queue_up_next_label",
            None,
        )

        if up_next is not None:
            up_next.setVisible(
                False
            )

        for row in getattr(
            self,
            "queue_rows",
            (),
        ):
            row[
                "card"
            ].setVisible(
                False
            )

        more = getattr(
            self,
            "queue_more",
            None,
        )

        if more is not None:
            more.setVisible(
                False
            )

        status = getattr(
            self,
            "queue_status",
            None,
        )

        if status is not None:
            status.setText(
                str(
                    status_text
                    or message
                    or ""
                )
            )

    def set_spotify_queue_busy(
        self,
        busy,
    ) -> None:
        busy = bool(
            busy
        )

        button = getattr(
            self,
            "queue_refresh_button",
            None,
        )

        if button is not None:
            button.setEnabled(
                not busy
            )

        if not busy:
            return

        status = getattr(
            self,
            "queue_status",
            None,
        )

        if status is None:
            return

        if bool(
            getattr(
                self,
                "_spotify_queue_has_result",
                False,
            )
        ):
            status.setText(
                "Refreshing Spotify Queue..."
            )

        else:
            status.setText(
                "Loading Spotify Queue..."
            )

    def refresh_spotify_queue(
        self,
        force: bool = False,
    ) -> bool:
        if not DashboardPage._spotify_queue_card_visible(
            self
        ):
            return False

        runtime = getattr(
            self,
            "spotify_queue_runtime",
            None,
        )

        if runtime is None:
            if force:
                DashboardPage._show_spotify_queue_message(
                    self,
                    "Spotify Queue is unavailable.",
                )

            return False

        if bool(
            getattr(
                runtime,
                "busy",
                False,
            )
        ):
            return False

        now = time.monotonic()

        next_refresh = float(
            getattr(
                self,
                "_spotify_queue_next_refresh_at",
                0.0,
            )
            or 0.0
        )

        if (
            not force
            and now < next_refresh
        ):
            return False

        self._spotify_queue_next_refresh_at = (
            now + 15.0
        )

        if bool(
            getattr(
                self,
                "_spotify_queue_has_result",
                False,
            )
        ):
            status = getattr(
                self,
                "queue_status",
                None,
            )

            if status is not None:
                status.setText(
                    "Refreshing Spotify Queue..."
                )

        else:
            DashboardPage._show_spotify_queue_message(
                self,
                "Loading Spotify Queue...",
            )

        loader = getattr(
            runtime,
            "load_queue",
            None,
        )

        if not callable(
            loader
        ):
            DashboardPage._show_spotify_queue_message(
                self,
                "Spotify Queue is unavailable.",
            )
            return False

        try:
            loader()

        except Exception as error:
            error_code = str(
                getattr(
                    error,
                    "error_code",
                    "",
                )
                or ""
            ).strip()

            if error_code in {
                "busy",
                "shutting_down",
            }:
                return False

            DashboardPage.show_spotify_queue_runtime_failure(
                self,
                error_code,
                str(
                    error
                    or ""
                ),
            )
            return False

        return True

    def show_spotify_queue_runtime_failure(
        self,
        error_code,
        message,
    ) -> None:
        del error_code

        self._spotify_queue_has_result = (
            True
        )

        self._spotify_queue_next_refresh_at = (
            time.monotonic()
            + 15.0
        )

        DashboardPage._show_spotify_queue_message(
            self,
            (
                str(
                    message
                    or ""
                ).strip()
                or (
                    "Spotify Queue could not "
                    "be loaded."
                )
            ),
            status_text="Queue unavailable",
        )

    def show_spotify_queue_result(
        self,
        result,
    ) -> None:
        if not isinstance(
            result,
            SpotifyQueueServiceResult,
        ):
            DashboardPage.show_spotify_queue_runtime_failure(
                self,
                "invalid_result",
                (
                    "Spotify Queue returned "
                    "an invalid result."
                ),
            )
            return

        self._spotify_queue_has_result = (
            True
        )

        if (
            result.retry_after_seconds
            is not None
        ):
            self._spotify_queue_next_refresh_at = max(
                float(
                    getattr(
                        self,
                        "_spotify_queue_next_refresh_at",
                        0.0,
                    )
                    or 0.0
                ),
                (
                    time.monotonic()
                    + float(
                        result.retry_after_seconds
                    )
                ),
            )

        if (
            result.status
            is SpotifyQueueServiceStatus.READY
        ):
            snapshot = result.queue

            if snapshot is None:
                DashboardPage.show_spotify_queue_runtime_failure(
                    self,
                    "invalid_result",
                    (
                        "Spotify Queue returned "
                        "an invalid result."
                    ),
                )
                return

            DashboardPage.populate_spotify_queue(
                self,
                snapshot,
            )
            return

        message = str(
            result.message
            or ""
        ).strip()

        if (
            result.status
            is SpotifyQueueServiceStatus
            .DISCONNECTED
        ):
            DashboardPage._show_spotify_queue_message(
                self,
                (
                    message
                    or (
                        "Connect Spotify to view "
                        "the Queue."
                    )
                ),
                status_text="Spotify disconnected",
            )
            return

        if (
            result.status
            is SpotifyQueueServiceStatus
            .REAUTHORIZATION_REQUIRED
        ):
            DashboardPage._show_spotify_queue_message(
                self,
                (
                    message
                    or (
                        "Reconnect Spotify to "
                        "view the Queue."
                    )
                ),
                status_text="Reconnect Spotify",
            )
            return

        if (
            result.status
            is SpotifyQueueServiceStatus.ERROR
        ):
            if (
                result.retry_after_seconds
                is not None
                and result.retry_after_seconds > 0
            ):
                retry_text = (
                    " Try again in "
                    f"{result.retry_after_seconds}s."
                )

            else:
                retry_text = ""

            DashboardPage._show_spotify_queue_message(
                self,
                (
                    message
                    or (
                        "Spotify Queue could not "
                        "be loaded."
                    )
                )
                + retry_text,
                status_text="Queue unavailable",
            )
            return

        DashboardPage.show_spotify_queue_runtime_failure(
            self,
            "invalid_status",
            (
                "Spotify Queue returned "
                "an invalid status."
            ),
        )

    def populate_spotify_queue(
        self,
        snapshot,
    ) -> None:
        current = getattr(
            snapshot,
            "currently_playing",
            None,
        )

        items = tuple(
            getattr(
                snapshot,
                "items",
                (),
            )
            or ()
        )

        partial_reason = str(
            getattr(
                snapshot,
                "partial_reason",
                "",
            )
            or ""
        ).strip()

        shuffle_local_partial = (
            partial_reason
            == QUEUE_PARTIAL_REASON_SHUFFLE_LOCAL_ORDER
        )

        self._spotify_queue_has_result = (
            True
        )

        current_row = getattr(
            self,
            "queue_current_row",
            None,
        )

        if (
            current is not None
            and current_row is not None
        ):
            badges = [
                "NOW",
            ]

            if bool(
                getattr(
                    current,
                    "is_local",
                    False,
                )
            ):
                badges.append(
                    "LOCAL"
                )

            elif (
                str(
                    getattr(
                        current,
                        "item_type",
                        "",
                    )
                )
                == "episode"
            ):
                badges.append(
                    "EPISODE"
                )

            DashboardPage._set_spotify_queue_row(
                self,
                current_row,
                current,
                marker="♪",
                badge=" / ".join(
                    badges
                ),
            )

        elif current_row is not None:
            current_row[
                "card"
            ].setVisible(
                False
            )

        capacity = int(
            getattr(
                self,
                "_spotify_queue_row_limit",
                3,
            )
            or 3
        )

        visible_items = items[
            :capacity
        ]

        for index, row in enumerate(
            getattr(
                self,
                "queue_rows",
                (),
            )
        ):
            if index >= len(
                visible_items
            ):
                row[
                    "card"
                ].setVisible(
                    False
                )
                continue

            item = visible_items[
                index
            ]

            if bool(
                getattr(
                    item,
                    "is_local",
                    False,
                )
            ):
                badge = "LOCAL"

            elif (
                str(
                    getattr(
                        item,
                        "item_type",
                        "",
                    )
                )
                == "episode"
            ):
                badge = "EPISODE"

            else:
                badge = ""

            DashboardPage._set_spotify_queue_row(
                self,
                row,
                item,
                marker=(
                    "♪"
                    if shuffle_local_partial
                    else str(
                        index + 1
                    )
                ),
                badge=badge,
            )

        placeholder = getattr(
            self,
            "queue_placeholder",
            None,
        )

        up_next = getattr(
            self,
            "queue_up_next_label",
            None,
        )

        more = getattr(
            self,
            "queue_more",
            None,
        )

        if up_next is not None:
            up_next.setText(
                (
                    "SPOTIFY-VISIBLE QUEUE"
                    if shuffle_local_partial
                    else "UP NEXT"
                )
            )

        if items:
            if placeholder is not None:
                placeholder.setVisible(
                    False
                )

            if up_next is not None:
                up_next.setVisible(
                    True
                )

        else:
            if up_next is not None:
                up_next.setVisible(
                    False
                )

            if placeholder is not None:
                if shuffle_local_partial:
                    placeholder.setText(
                        (
                            "Spotify does not expose "
                            "shuffled local-file "
                            "positions."
                        )
                    )

                else:
                    placeholder.setText(
                        (
                            "Nothing else is queued."
                            if current is not None
                            else (
                                "Spotify Queue is "
                                "empty."
                            )
                        )
                    )

                placeholder.setVisible(
                    True
                )

        remaining = max(
            0,
            len(items)
            - capacity,
        )

        if more is not None:
            if remaining:
                if shuffle_local_partial:
                    more.setText(
                        (
                            "+"
                            f"{remaining} more "
                            "Spotify-visible"
                        )
                    )

                else:
                    more.setText(
                        (
                            "+"
                            f"{remaining} more in Queue"
                        )
                    )

                more.setVisible(
                    True
                )

            else:
                more.setVisible(
                    False
                )

        status = getattr(
            self,
            "queue_status",
            None,
        )

        if status is not None:
            count = len(items)

            if shuffle_local_partial:
                status.setText(
                    (
                        "Shuffle on | "
                        "local-file order hidden"
                    )
                )

            elif count:
                status.setText(
                    (
                        f"{count} item"
                        + (
                            ""
                            if count == 1
                            else "s"
                        )
                        + " up next"
                    )
                )

            elif current is not None:
                status.setText(
                    "Nothing else queued"
                )

            else:
                status.setText(
                    "Queue is empty"
                )

    def build_queue_card(
        self,
    ):
        self.queue_card = QFrame()
        self.queue_card.setObjectName(
            "queueCard"
        )

        layout = QVBoxLayout(
            self.queue_card
        )
        layout.setContentsMargins(
            14,
            12,
            14,
            12,
        )
        layout.setSpacing(
            6
        )

        heading_row = QHBoxLayout()

        heading = QLabel(
            "SPOTIFY QUEUE"
        )
        heading.setObjectName(
            "sectionLabel"
        )

        self.queue_refresh_button = QPushButton(
            "Refresh"
        )
        self.queue_refresh_button.setObjectName(
            "textButton"
        )
        self.queue_refresh_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.queue_refresh_button.setToolTip(
            "Refresh Spotify Queue"
        )
        self.queue_refresh_button.clicked.connect(
            lambda _checked=False:
            DashboardPage.refresh_spotify_queue(
                self,
                force=True,
            )
        )

        heading_row.addWidget(
            heading
        )
        heading_row.addStretch()
        heading_row.addWidget(
            self.queue_refresh_button
        )

        layout.addLayout(
            heading_row
        )

        self.queue_status = QLabel(
            "Queue content will appear here."
        )
        self.queue_status.setObjectName(
            "recentArtist"
        )

        layout.addWidget(
            self.queue_status
        )

        self.queue_placeholder = QLabel(
            "Queue content will appear here."
        )
        self.queue_placeholder.setObjectName(
            "queuePlaceholder"
        )
        self.queue_placeholder.setWordWrap(
            True
        )
        self.queue_placeholder.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        layout.addWidget(
            self.queue_placeholder,
            1,
        )

        def make_queue_row(
            marker,
        ):
            row_card = QFrame()
            row_card.setObjectName(
                "recentRow"
            )
            row_card.setFixedHeight(
                42
            )
            row_card.hide()

            row_layout = QHBoxLayout(
                row_card
            )
            row_layout.setContentsMargins(
                10,
                5,
                10,
                5,
            )
            row_layout.setSpacing(
                10
            )

            icon = QLabel(
                str(
                    marker
                )
            )
            icon.setObjectName(
                "recentIcon"
            )
            icon.setFixedSize(
                34,
                30,
            )
            icon.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            text_layout = QVBoxLayout()
            text_layout.setSpacing(
                0
            )

            title = QLabel("")
            title.setObjectName(
                "recentTitle"
            )

            artist = QLabel("")
            artist.setObjectName(
                "recentArtist"
            )

            text_layout.addWidget(
                title
            )
            text_layout.addWidget(
                artist
            )

            source = QLabel("")
            source.setObjectName(
                "recentSource"
            )
            source.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            duration = QLabel("")
            duration.setObjectName(
                "recentTime"
            )
            duration.setAlignment(
                Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignVCenter
            )

            row_layout.addWidget(
                icon
            )
            row_layout.addLayout(
                text_layout,
                stretch=1,
            )
            row_layout.addWidget(
                source
            )
            row_layout.addWidget(
                duration
            )

            layout.addWidget(
                row_card
            )

            return {
                "card": row_card,
                "icon": icon,
                "title": title,
                "artist": artist,
                "source": source,
                "time": duration,
            }

        self.queue_current_row = (
            make_queue_row("♪")
        )

        self.queue_up_next_label = QLabel(
            "UP NEXT"
        )
        self.queue_up_next_label.setObjectName(
            "recentSource"
        )
        self.queue_up_next_label.hide()

        layout.addWidget(
            self.queue_up_next_label
        )

        self._spotify_queue_row_limit = 3

        self.queue_rows = [
            make_queue_row(
                index + 1
            )
            for index in range(
                self._spotify_queue_row_limit
            )
        ]

        self.queue_more = QLabel("")
        self.queue_more.setObjectName(
            "recentArtist"
        )
        self.queue_more.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )
        self.queue_more.hide()

        layout.addWidget(
            self.queue_more
        )

        self._spotify_queue_has_result = (
            False
        )

        self._spotify_queue_next_refresh_at = (
            0.0
        )

        self.queue_card.setMinimumHeight(
            270
        )




    def build_library_status_card(self):
        self.library_status_card = QFrame()
        self.library_status_card.setObjectName(
            "libraryStatusCard"
        )

        layout = QVBoxLayout(
            self.library_status_card
        )
        layout.setContentsMargins(
            14,
            12,
            14,
            12,
        )
        layout.setSpacing(8)

        heading = QLabel(
            "▥  LIBRARY STATUS"
        )
        heading.setObjectName(
            "sectionLabel"
        )

        layout.addWidget(
            heading
        )

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        (
            tracks_tile,
            self.library_track_count,
            self.library_track_detail,
        ) = self.make_stat_tile(
            "Total Tracks",
            "0",
            "Saved in Library",
        )

        (
            plays_tile,
            self.library_play_count,
            self.library_play_detail,
        ) = self.make_stat_tile(
            "Total Plays",
            "0",
            "Listening events",
        )

        (
            sources_tile,
            self.library_source_count,
            self.library_source_detail,
        ) = self.make_stat_tile(
            "Sources",
            "0",
            "None enabled",
        )

        (
            latest_tile,
            self.library_latest_track,
            self.library_latest_artist,
        ) = self.make_stat_tile(
            "Last Added",
            "Waiting",
            "",
        )

        grid.addWidget(
            tracks_tile,
            0,
            0,
        )
        grid.addWidget(
            plays_tile,
            0,
            1,
        )
        grid.addWidget(
            sources_tile,
            1,
            0,
        )
        grid.addWidget(
            latest_tile,
            1,
            1,
        )

        layout.addLayout(
            grid,
            stretch=1,
        )

        open_library = QPushButton(
            "▱  Open Library  →"
        )
        open_library.setObjectName(
            "libraryOpenButton"
        )
        open_library.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        open_library.clicked.connect(
            lambda:
            self.navigate_requested.emit(2)
        )

        layout.addWidget(
            open_library
        )

    @staticmethod
    def make_stat_tile(
        title: str,
        value: str,
        detail: str,
    ):
        tile = QFrame()
        tile.setObjectName(
            "statTile"
        )

        layout = QVBoxLayout(
            tile
        )
        layout.setContentsMargins(
            10,
            8,
            10,
            8,
        )
        layout.setSpacing(2)

        title_label = QLabel(
            title
        )
        title_label.setObjectName(
            "statTitle"
        )

        value_label = QLabel(
            value
        )
        value_label.setObjectName(
            "statValue"
        )
        value_label.setWordWrap(
            True
        )

        detail_label = QLabel(
            detail
        )
        detail_label.setObjectName(
            "statDetail"
        )
        detail_label.setWordWrap(
            True
        )

        layout.addWidget(
            title_label
        )
        layout.addWidget(
            value_label
        )
        layout.addWidget(
            detail_label
        )
        layout.addStretch()

        return (
            tile,
            value_label,
            detail_label,
        )

    def make_status_card(
        self,
        icon_text: str,
        title: str,
        value: str,
        detail: str,
        button_text: str = "",
        button_page: int | None = None,
        button_section: str = "",
    ):
        card = QFrame()
        card.setObjectName(
            "statusStripCard"
        )
        card.setMinimumHeight(
            68
        )

        layout = QHBoxLayout(card)
        layout.setContentsMargins(
            13,
            8,
            13,
            8,
        )
        layout.setSpacing(10)

        icon = QLabel(icon_text)
        icon.setObjectName(
            "statusIcon"
        )
        icon.setFixedWidth(40)
        icon.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)

        title_label = QLabel(title)
        title_label.setObjectName(
            "statusStripTitle"
        )

        value_label = QLabel(value)
        value_label.setObjectName(
            "statusValue"
        )

        detail_label = QLabel(detail)
        detail_label.setObjectName(
            "statusDetail"
        )

        text_layout.addWidget(
            title_label
        )
        text_layout.addWidget(
            value_label
        )
        text_layout.addWidget(
            detail_label
        )

        layout.addWidget(icon)
        layout.addLayout(
            text_layout,
            stretch=1,
        )

        if button_text:
            button = QPushButton(
                button_text
            )
            button.setObjectName(
                "statusConfigure"
            )
            button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

            if button_section:
                button.clicked.connect(
                    lambda checked=False,
                    section=button_section:
                    self.settings_section_requested.emit(
                        section
                    )
                )

            elif button_page is not None:
                button.clicked.connect(
                    lambda checked=False,
                    page=button_page:
                    self.navigate_requested.emit(
                        page
                    )
                )

            layout.addWidget(button)

        return (
            card,
            value_label,
            detail_label,
        )

    @pyqtSlot(dict)
    def apply_theme(self, theme: dict):
        discord_preview = getattr(
            self,
            "discord_profile_preview",
            None,
        )

        if discord_preview is not None:
            discord_preview.set_compact(
                bool(
                    theme.get(
                        "compact",
                        True,
                    )
                )
            )
            discord_preview.apply_theme(
                theme
            )
        compact = theme.get(
            "compact",
            True,
        )

        self._artwork_size = (
            140 if compact else 156
        )
        self._preview_artwork_size = (
            62 if compact else 72
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

        playback_progress_height = (
            14 if compact else 16
        )

        self.progress.setFixedHeight(
            playback_progress_height
        )
        self.progress_visual.setFixedHeight(
            4
        )
        self.progress_stack.setFixedHeight(
            playback_progress_height
        )

        card_glass = colour_with_alpha(
            theme["card"],
            0.66,
        )
        card_alt_glass = colour_with_alpha(
            theme["card_alt"],
            0.72,
        )
        page_background = "transparent"

        self.dashboard_canvas.set_editor_theme(
            theme["accent"],
            theme["border"],
        )

        self.setStyleSheet(
            f"""
            QWidget#dashboardRoot {{
                background: {page_background};
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

            QFrame#dashboardLayoutToolbar {{
                background: {card_glass};
                border: 1px solid {theme["border"]};
                border-radius: 12px;
            }}

            QFrame#dashboardLayoutToolbar[layoutState="editing"] {{
                background: {colour_with_alpha(theme["card"], 0.78)};
                border: 1px solid {theme["accent"]};
            }}

            QLabel#layoutToolbarTitle {{
                color: {theme["accent"]};
                font-size: 9px;
                font-weight: 750;
                letter-spacing: 1.2px;
            }}

            QLabel#layoutToolbarHint {{
                color: {theme["muted"]};
                font-size: 9px;
            }}

            QFrame#layoutToolbarGroup {{
                background: {card_alt_glass};
                border: 1px solid {theme["border"]};
                border-radius: 8px;
            }}

            QLabel#layoutToolbarGroupLabel {{
                color: {theme["muted"]};
                font-size: 7px;
                font-weight: 750;
                letter-spacing: 1px;
                padding-right: 2px;
            }}

            QLabel#layoutToolbarStatus {{
                color: {theme["muted"]};
                background: {card_alt_glass};
                border: 1px solid {theme["border"]};
                border-radius: 7px;
                padding: 4px 9px;
                font-size: 8px;
                font-weight: 750;
                letter-spacing: 0.6px;
            }}

            QLabel#layoutToolbarStatus[layoutState="editing"] {{
                color: {theme["background"]};
                background: {theme["accent"]};
                border-color: {theme["accent"]};
            }}

            QPushButton#layoutLockButton[layoutState="editing"] {{
                color: {theme["background"]};
                background: {theme["accent"]};
                border-color: {theme["accent"]};
            }}

            QLabel#dashboardDragHandle,
            QLabel#dashboardResizeHandle {{
                color: {theme["muted"]};
                background: {colour_with_alpha(theme["background"], 0.82)};
                border: 1px solid {colour_with_alpha(theme["accent"], 0.56)};
                border-radius: 7px;
                font-size: 7px;
                font-weight: 750;
                letter-spacing: 0.8px;
            }}

            QLabel#dashboardDragHandle:hover,
            QLabel#dashboardResizeHandle:hover {{
                color: {theme["background"]};
                background: {theme["accent"]};
                border-color: {theme["accent"]};
            }}

            QLabel#dashboardDragHandle:focus,
            QLabel#dashboardResizeHandle:focus {{
                color: {theme["background"]};
                background: {theme["accent"]};
                border: 2px solid {theme["accent"]};
            }}

            QPushButton#dashboardCustomActionHandle,
            QPushButton#dashboardDeleteHandle {{
                color: {theme["muted"]};
                background: {colour_with_alpha(theme["background"], 0.82)};
                border: 1px solid {colour_with_alpha(theme["accent"], 0.56)};
                border-radius: 7px;
                padding: 0px;
                font-size: 9px;
                font-weight: 800;
            }}

            QPushButton#dashboardCustomActionHandle:hover,
            QPushButton#dashboardDeleteHandle:hover {{
                color: {theme["background"]};
                background: {theme["accent"]};
                border-color: {theme["accent"]};
            }}

            QPushButton#dashboardCustomActionHandle::menu-indicator {{
                image: none;
                width: 0px;
            }}

            QFrame#dashboardCanvas {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 14px;
            }}

            QFrame#dashboardCanvas[editing="true"] {{
                background: {colour_with_alpha(theme["card_alt"], 0.18)};
                border: 1px dashed {colour_with_alpha(theme["accent"], 0.62)};
                border-radius: 14px;
            }}

            QFrame#dashboardEditorOutline {{
                background: transparent;
                border: 2px solid {theme["accent"]};
                border-radius: 13px;
            }}

            QFrame#dashboardEditorOutline[editorMode="resize"] {{
                border: 2px dashed {theme["accent"]};
            }}

            QComboBox#layoutPresetCombo,
            QPushButton#layoutControlButton,
            QPushButton#layoutMenuButton,
            QPushButton#layoutLockButton {{
                color: {theme["text"]};
                background: {card_alt_glass};
                border: 1px solid {theme["border"]};
                border-radius: 7px;
                padding: 5px 9px;
                font-size: 9px;
                font-weight: 650;
            }}

            QComboBox#layoutPresetCombo:hover,
            QPushButton#layoutControlButton:hover,
            QPushButton#layoutMenuButton:hover,
            QPushButton#layoutLockButton:hover {{
                border: 1px solid {theme["accent"]};
            }}

            QComboBox#layoutPresetCombo:focus,
            QPushButton#layoutControlButton:focus,
            QPushButton#layoutMenuButton:focus,
            QPushButton#layoutLockButton:focus {{
                border: 2px solid {theme["accent"]};
            }}

            QComboBox#layoutPresetCombo:disabled,
            QPushButton#layoutControlButton:disabled,
            QPushButton#layoutMenuButton:disabled {{
                color: {theme["muted"]};
                background: {theme["background"]};
            }}

            QComboBox#layoutPresetCombo {{
                padding-right: 28px;
            }}

            QComboBox#layoutPresetCombo::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border: none;
                background: transparent;
            }}

            QComboBox#layoutPresetCombo::down-arrow {{
                width: 8px;
                height: 8px;
            }}

            QPushButton#layoutMenuButton {{
                padding-right: 18px;
            }}

            QPushButton#layoutMenuButton::menu-indicator {{
                image: none;
                width: 0px;
                height: 0px;
            }}

            QComboBox#layoutPresetCombo QAbstractItemView {{
                color: {theme["text"]};
                background: {card_glass};
                border: 1px solid {theme["border"]};
                selection-background-color: {theme["accent"]};
            }}

            QMenu {{
                color: {theme["text"]};
                background: {card_glass};
                border: 1px solid {theme["border"]};
                padding: 4px;
            }}

            QMenu::item {{
                padding: 6px 20px 6px 8px;
                border-radius: 5px;
            }}

            QMenu::item:selected {{
                background: {theme["accent"]};
            }}

            QPushButton#cardIconButton {{
                color: {theme["text"]};
                background: {card_alt_glass};
                border: 1px solid {theme["border"]};
                border-radius: 8px;
                font-size: 14px;
                font-weight: 700;
            }}

            QPushButton#cardIconButton:hover {{
                border: 1px solid {theme["accent"]};
            }}

            QLabel#sourceLine {{
                color: {theme["text"]};
                font-size: 10px;
                font-weight: 650;
            }}

            QLabel#equalizer {{
                color: {theme["accent"]};
                font-size: 14px;
                letter-spacing: 1px;
            }}

            QFrame#statusStripCard {{
                background: {card_glass};
                border: 1px solid {theme["border"]};
                border-radius: 10px;
            }}

            QLabel#statusIcon {{
                color: {theme["accent"]};
                font-size: 24px;
            }}

            QLabel#statusStripTitle {{
                color: {theme["accent"]};
                font-size: 8px;
                font-weight: 750;
            }}

            QLabel#statusDetail {{
                color: {theme["muted"]};
                font-size: 8px;
            }}

            QPushButton#statusConfigure {{
                color: {theme["text"]};
                background: {card_alt_glass};
                border: 1px solid {theme["border"]};
                border-radius: 8px;
                padding: 7px 9px;
                font-size: 8px;
                font-weight: 700;
            }}

            QPushButton#statusConfigure:hover {{
                border: 1px solid {theme["accent"]};
            }}

            QFrame#dashboardFooter {{
                background: transparent;
                border-top: 1px solid {theme["border"]};
            }}

            QLabel#footerText {{
                color: {theme["muted"]};
                font-size: 8px;
            }}

            QFrame#connectionCard {{
                background: {card_alt_glass};
                border: 1px solid {theme["border"]};
                border-radius: 10px;
            }}

            QLabel#connectionDot {{
                color: #31d158;
                font-size: 12px;
            }}

            QLabel#connectionStatus {{
                color: {theme["text"]};
                font-size: 10px;
                font-weight: 700;
            }}

            QLabel#connectionDetail {{
                color: {theme["muted"]};
                font-size: 9px;
            }}

            QPushButton#headerSettingsButton {{
                color: {theme["text"]};
                background: {theme["accent"]};
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: 700;
            }}

            QPushButton#headerSettingsButton:hover {{
                border: 1px solid {theme["text"]};
            }}

            QFrame#discordActivityPanel {{
                background: {card_alt_glass};
                border: 1px solid {theme["border"]};
                border-radius: 10px;
            }}

            QLabel#appBadge {{
                color: {theme["text"]};
                background: {theme["accent"]};
                border-radius: 4px;
                padding: 2px 4px;
                font-size: 7px;
                font-weight: 750;
            }}

            QLabel#activityBadge {{
                color: {theme["text"]};
                background: {card_alt_glass};
                border: 1px solid {theme["border"]};
                border-radius: 9px;
                padding: 5px 10px;
                font-size: 10px;
                font-weight: 700;
            }}

            QFrame#nowPlayingCard,
            QFrame#previewCard {{
                background: {card_glass};
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
                background: {card_alt_glass};
                border: 1px solid {theme["border"]};
                border-radius: 7px;
                padding: 3px 7px;
                font-size: 9px;
                font-weight: 700;
            }}

            QWidget#playbackProgressStack {{
                background: transparent;
                border: none;
            }}

            QFrame#playbackProgressVisual {{
                background: {theme["background"]};
                border: none;
                border-radius: 2px;
            }}

            QFrame#playbackProgressPlayed {{
                background: {theme["accent"]};
                border: none;
                border-radius: 2px;
            }}

            QFrame#playbackProgressRemaining {{
                background: transparent;
                border: none;
            }}


            QFrame#statusPill {{
                background: {card_alt_glass};
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

            QFrame#recentCard,
            QFrame#quickAccessCard,
            QFrame#libraryStatusCard,
            QFrame#queueCard {{
                background: {card_glass};
                border: 1px solid {theme["border"]};
                border-radius: 14px;
            }}

            QFrame#recentRow,
            QFrame#statTile {{
                background: {card_alt_glass};
                border: 1px solid {theme["border"]};
                border-radius: 9px;
            }}

            QLabel#recentIcon {{
                color: {theme["accent"]};
                background: {theme["background"]};
                border: 1px solid {theme["border"]};
                border-radius: 8px;
                font-size: 15px;
                font-weight: 700;
            }}

            QLabel#recentTitle {{
                color: {theme["text"]};
                font-size: 10px;
                font-weight: 700;
            }}

            QLabel#recentArtist,
            QLabel#recentTime,
            QLabel#emptyRecent,
            QLabel#statTitle,
            QLabel#statDetail {{
                color: {theme["muted"]};
                font-size: 9px;
            }}

            QLabel#recentSource {{
                color: {theme["accent"]};
                background: {theme["background"]};
                border: 1px solid {theme["border"]};
                border-radius: 6px;
                padding: 3px 6px;
                font-size: 8px;
                font-weight: 700;
            }}

            QLabel#statValue {{
                color: {theme["text"]};
                font-size: 15px;
                font-weight: 750;
            }}

            QPushButton#quickButton {{
                color: {theme["text"]};
                background: {card_alt_glass};
                border: 1px solid {theme["border"]};
                border-radius: 9px;
                padding: 8px 10px;
                text-align: left;
                font-size: 10px;
                font-weight: 650;
            }}

            QPushButton#quickButton:hover {{
                border: 1px solid {theme["accent"]};
                background: {theme["background"]};
            }}

            QPushButton#quickButton[compactQuickAccess="true"] {{
                padding: 6px;
                text-align: center;
            }}

            QPushButton#libraryOpenButton {{
                color: {theme["text"]};
                background: {card_alt_glass};
                border: 1px solid {theme["border"]};
                border-radius: 8px;
                padding: 7px 10px;
                text-align: left;
                font-size: 9px;
                font-weight: 700;
            }}

            QPushButton#libraryOpenButton:hover {{
                border: 1px solid {theme["accent"]};
            }}

            QPushButton#textButton {{
                color: {theme["accent"]};
                background: transparent;
                border: none;
                padding: 3px 5px;
                font-size: 9px;
                font-weight: 700;
            }}

            QPushButton#textButton:hover {{
                color: {theme["text"]};
            }}

            QFrame#nowPlayingCard[dashboardEditing="true"],
            QFrame#previewCard[dashboardEditing="true"],
            QFrame#recentCard[dashboardEditing="true"],
            QFrame#quickAccessCard[dashboardEditing="true"],
            QFrame#libraryStatusCard[dashboardEditing="true"],
            QFrame#queueCard[dashboardEditing="true"],
            QFrame#statusStripCard[dashboardEditing="true"] {{
                border: 1px solid {colour_with_alpha(theme["accent"], 0.34)};
            }}

            QWidget[dashboardEditing="true"] {{
                border-color: {colour_with_alpha(theme["accent"], 0.34)};
            }}
            """
        )

        for card in self.dashboard_cards.values():
            if isinstance(
                card,
                (
                    LinkCardWidget,
                    LauncherCardWidget,
                ),
            ):
                card.set_theme(theme)

        self.schedule_dashboard_geometry_refresh()

        if getattr(
            self.song,
            "artwork_bytes",
            None,
        ):
            self._last_artwork_signature = None
            self.update_artwork(self.song)
        self._refresh_playback_transport_icons(
            theme
        )

    @pyqtSlot(dict)
    def apply_branding(self, branding: dict):
        title = (
            branding.get("title", "")
            or "03:37am Presence"
        )

        self._branding_title = title

        self.preview_app.setText(
            title
        )

    def start_equalizer_animation(self):
        source_app = str(
            getattr(
                self.song,
                "source_app",
                "",
            )
            or ""
        ).casefold()

        if "spotify" not in source_app:
            self.stop_equalizer_animation()
            return

        spectrum_service = getattr(
            self,
            "spotify_audio_spectrum_service",
            None,
        )

        if spectrum_service is None:
            self.equalizer.clear()
            self.equalizer.setVisible(
                False
            )
            return

        self.equalizer.setVisible(
            True
        )

        spectrum_service.start()

        if not self.equalizer_timer.isActive():
            self.equalizer_timer.start()

        self.advance_equalizer()

    def stop_equalizer_animation(self):
        self.equalizer_timer.stop()

        spectrum_service = getattr(
            self,
            "spotify_audio_spectrum_service",
            None,
        )

        if spectrum_service is not None:
            spectrum_service.stop(
                timeout_seconds=0.5
            )

        self.equalizer.clear()
        self.equalizer.setVisible(
            False
        )

    def advance_equalizer(self):
        spectrum_service = getattr(
            self,
            "spotify_audio_spectrum_service",
            None,
        )

        if spectrum_service is None:
            return

        try:
            equalizer_text = (
                spectrum_levels_to_text(
                    spectrum_service.latest_levels
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            equalizer_text = (
                "▁" * 8
            )

        self.equalizer.setText(
            equalizer_text
        )

    @pyqtSlot(object)
    def apply_song(self, song):
        if song is None or not song.title:
            self.playback_presentation_clock.clear()
            self.show_nothing_playing()
            return

        self._last_worker_error = ""

        self.restore_cached_song_artwork(
            song
        )

        self.song = song

        self._sync_playback_seek_pending(
            song
        )

        self.progress.setEnabled(
            self.time_to_seconds(
                song.duration
            )
            > 0
        )

        self.sync_playback_control_state(
            available=True
        )

        self.playback_presentation_clock.observe(
            position_seconds=float(
                self.time_to_seconds(
                    song.position
                )
            ),
            duration_seconds=float(
                self.time_to_seconds(
                    song.duration
                )
            ),
            playing=bool(
                song.playing
            ),
            identity=(
                str(
                    song.title
                    or ""
                ),
                str(
                    song.artist
                    or ""
                ),
                str(
                    song.album
                    or ""
                ),
                str(
                    getattr(
                        song,
                        "source_app",
                        "",
                    )
                    or ""
                ),
            ),
        )

        self.cache_song_artwork(song)

        self.song_title.setText(song.title)
        self.artist.setText(song.artist)
        self.album.setText(song.album)

        if not DashboardPage._playback_seek_updates_blocked(self):
            self.current_time.setText(
                song.position
            )

        self.total_time.setText(
            song.duration
        )

        preview_artist = (
            song.artist or "Unknown artist"
        )
        preview_album = str(
            song.album or ""
        ).strip()
        preview_title_key = str(
            song.title or ""
        ).strip().casefold()

        if (
            preview_album
            and preview_album.casefold()
            == preview_title_key
        ):
            preview_album = ""

        self.preview_title.setText(
            song.title
        )
        self.preview_state.setText(
            preview_artist
        )
        self.preview_state.setHidden(False)
        self.preview_album.setText(
            preview_album
        )
        self.preview_album.setHidden(
            not bool(preview_album)
        )

        source_name = self._display_source(
            getattr(
                song,
                "source_app",
                "",
            )
        )

        self.preview_mode.setText(
            source_name.upper()
        )

        if song.playing:
            self.music_status.setText(
                f"{source_name} • Playing"
            )
            self.music_status_detail.setText(
                f"Listening on {source_name}"
            )
            self.activity_badge.setText(
                "PLAYING"
            )
            self.now_source.setText(
                f"●  Playing on {source_name}"
            )
            self.start_equalizer_animation()
            self.preview_time.setText(
                f"{song.position} / {song.duration}"
            )
            self.preview_time.setHidden(False)
        else:
            self.music_status.setText(
                f"{source_name} • Paused"
            )
            self.music_status_detail.setText(
                f"Paused on {source_name}"
            )
            self.activity_badge.setText(
                "PAUSED"
            )
            self.now_source.setText(
                f"Ⅱ  Paused on {source_name}"
            )
            self.stop_equalizer_animation()
            self.preview_time.setText(
                "Paused"
            )
            self.preview_time.setHidden(False)

        self.update_artwork(song)
        self.update_progress(song)
        self.refresh_playback_presentation()
        self._restore_non_music_discord_preview()

        QTimer.singleShot(
            300,
            self.refresh_dashboard_data,
        )

    def refresh_dashboard_data(self):
        tracks = (
            self.history_store.list_tracks(
                limit=(
                    self._recent_track_fetch_limit
                )
            )
        )

        self._recent_tracks = list(
            tracks
        )

        self.populate_recent_tracks(
            self._recent_tracks
        )

        self.library_track_count.setText(
            str(
                self.history_store.count_tracks()
            )
        )

        self.library_play_count.setText(
            str(
                self.history_store.total_plays()
            )
        )

        source_preferences = (
            self.source_preferences_store.load()
        )

        enabled_sources = []

        if source_preferences.spotify_enabled:
            enabled_sources.append(
                "Spotify"
            )

        if source_preferences.browser_enabled:
            enabled_sources.append(
                "Browsers"
            )

        self.library_source_count.setText(
            str(
                len(enabled_sources)
            )
        )

        self.library_source_detail.setText(
            ", ".join(enabled_sources)
            or "None enabled"
        )

        if tracks:
            self.library_latest_track.setText(
                tracks[0].title
            )
            self.library_latest_artist.setText(
                tracks[0].artist
            )
        else:
            self.library_latest_track.setText(
                "Waiting"
            )
            self.library_latest_artist.setText(
                ""
            )

        preferences = (
            self.afk_preferences_store.load()
        )

        if not preferences.enabled:
            self.afk_status.setText(
                "Inactive"
            )
            self.afk_status_detail.setText(
                "Auto AFK is disabled"
            )
        else:
            try:
                active = (
                    WindowsIdleMonitor.is_idle(
                        preferences.timeout_minutes
                        * 60
                    )
                )
            except Exception:
                active = False

            if active:
                self.afk_status.setText(
                    "Active"
                )
            else:
                self.afk_status.setText(
                    "Inactive"
                )

            self.afk_status_detail.setText(
                (
                    "AFK after "
                    f"{preferences.timeout_minutes} "
                    "minute"
                    + (
                        ""
                        if preferences.timeout_minutes == 1
                        else "s"
                    )
                )
            )

        connection_text = (
            self.discord_status.text().strip()
            or "Waiting"
        )

        self.header_connection_status.setText(
            f"Status: {connection_text}"
        )

        if connection_text == "Connected":
            detail = "Discord Connected"
        elif connection_text == "Waiting for Discord":
            detail = "Waiting for Discord"
        else:
            detail = "Discord unavailable"

        self.header_connection_detail.setText(
            detail
        )

        if connection_text == "Connected":
            strip_detail = (
                "Ready to update rich presence"
            )
        elif connection_text == "Waiting for Discord":
            strip_detail = (
                "Open Discord to connect"
            )
        else:
            strip_detail = (
                "Discord is not connected"
            )

        self.discord_status_detail.setText(
            strip_detail
        )
        DashboardPage.refresh_spotify_queue(
            self
        )

    @staticmethod
    def _artwork_cache_directory() -> Path:
        local_app_data = os.getenv(
            "LOCALAPPDATA",
            "",
        ).strip()

        if local_app_data:
            directory = (
                Path(local_app_data)
                / "0337am Presence"
                / "artwork_cache"
            )
        else:
            directory = (
                Path.home()
                / ".0337am-presence"
                / "artwork_cache"
            )

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        return directory

    @staticmethod
    def _artwork_identity(
        title,
        artist,
        album,
        source_app,
    ) -> str:
        identity = "|".join(
            [
                str(title or "").strip().lower(),
                str(artist or "").strip().lower(),
                str(album or "").strip().lower(),
                str(source_app or "").strip().lower(),
            ]
        )

        return hashlib.sha256(
            identity.encode("utf-8")
        ).hexdigest()

    def restore_cached_song_artwork(
        self,
        song,
    ) -> bool:
        """
        Restore the current track's artwork from the
        persistent Dashboard cache when Windows media
        temporarily supplies no thumbnail.

        The cache key contains the complete track
        identity, preventing another song's artwork
        from being applied.
        """
        if (
            song is None
            or not getattr(
                song,
                "title",
                "",
            )
            or getattr(
                song,
                "artwork_bytes",
                None,
            )
        ):
            return False

        cache_key = self._artwork_identity(
            getattr(song, "title", ""),
            getattr(song, "artist", ""),
            getattr(song, "album", ""),
            getattr(song, "source_app", ""),
        )

        cache_path = (
            self._artwork_cache_directory()
            / f"{cache_key}.img"
        )

        try:
            artwork_bytes = cache_path.read_bytes()

        except OSError:
            return False

        if not artwork_bytes:
            return False

        song.artwork_bytes = bytes(
            artwork_bytes
        )

        self._last_artwork_signature = None

        return True

    def cache_song_artwork(
        self,
        song,
    ):
        artwork_bytes = getattr(
            song,
            "artwork_bytes",
            None,
        )

        if not artwork_bytes:
            return

        candidate_artwork = bytes(
            artwork_bytes
        )

        cache_key = self._artwork_identity(
            getattr(song, "title", ""),
            getattr(song, "artist", ""),
            getattr(song, "album", ""),
            getattr(song, "source_app", ""),
        )

        cache_path = (
            self._artwork_cache_directory()
            / f"{cache_key}.img"
        )

        if cache_path.exists():
            try:
                existing_size = int(
                    cache_path.stat().st_size
                )

            except OSError:
                existing_size = 0

            if not should_upgrade_artwork(
                existing_size,
                len(
                    candidate_artwork
                ),
            ):
                return

        try:
            cache_path.write_bytes(
                candidate_artwork
            )

        except OSError:
            pass

    def set_recent_artwork(
        self,
        label: QLabel,
        track: HistoryTrack,
    ):
        cache_key = self._artwork_identity(
            track.title,
            track.artist,
            track.album,
            track.source_app,
        )

        cache_path = (
            self._artwork_cache_directory()
            / f"{cache_key}.img"
        )

        if not cache_path.exists():
            label.clear()
            label.setText("♪")
            return

        try:
            artwork_bytes = (
                cache_path.read_bytes()
            )

        except OSError:
            artwork_bytes = b""

        pixmap = QPixmap()

        if (
            not artwork_bytes
            or not pixmap.loadFromData(
                artwork_bytes
            )
            or pixmap.isNull()
        ):
            label.clear()
            label.setText("♪")
            return

        label.clear()
        label.setText("")

        label.setPixmap(
            pixmap.scaled(
                label.width(),
                label.height(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def populate_recent_tracks(
        self,
        tracks: list[HistoryTrack],
    ):
        track_list = list(
            tracks
            or []
        )

        capacity = (
            self.recent_track_capacity()
        )

        self._recent_visible_capacity = (
            capacity
        )

        visible_tracks = track_list[
            :capacity
        ]

        self.recent_empty.setVisible(
            not bool(
                track_list
            )
        )

        for index, row in enumerate(
            self.recent_rows
        ):
            if index >= len(
                visible_tracks
            ):
                row["card"].setVisible(
                    False
                )
                continue

            track = visible_tracks[
                index
            ]

            row["title"].setText(
                track.title
            )
            row["artist"].setText(
                track.artist
            )

            self.set_recent_artwork(
                row["icon"],
                track,
            )

            row["source"].setText(
                self._display_source(
                    track.source_app
                )
            )
            row["time"].setText(
                self._friendly_time(
                    track.last_played
                )
            )
            row["card"].setVisible(
                True
            )

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
            self._restore_non_music_discord_preview()
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
            self._restore_non_music_discord_preview()
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

        self._restore_non_music_discord_preview()

    def refresh_playback_presentation(
        self,
    ):
        if DashboardPage._playback_seek_updates_blocked(self):
            return

        clock = getattr(
            self,
            "playback_presentation_clock",
            None,
        )

        if clock is None:
            return

        try:
            state = clock.current()

        except Exception:
            return

        if state is None:
            return

        current_text = (
            format_playback_time(
                state.position_seconds
            )
        )

        self.current_time.setText(
            current_text
        )

        song = getattr(
            self,
            "song",
            None,
        )

        if (
            state.playing
            and song is not None
            and self._discord_music_preview_active()
        ):
            self.preview_time.setText(
                (
                    f"{current_text} / "
                    f"{song.duration}"
                )
            )
            self.preview_time.setHidden(False)

        total = (
            state.duration_seconds
        )

        if total <= 0.0:
            self.progress.setValue(
                0
            )
            return

        progress_value = int(
            round(
                (
                    state.position_seconds
                    / total
                )
                * 10000
            )
        )

        progress_value = max(
            0,
            min(
                10000,
                progress_value,
            ),
        )

        self.progress.setValue(
            progress_value
        )

        discord_preview = getattr(
            self,
            "discord_profile_preview",
            None,
        )

        if (
            discord_preview is not None
            and self._discord_music_preview_active()
        ):
            preview_progress = max(
                0,
                min(
                    100,
                    int(
                        round(
                            progress_value / 100
                        )
                    ),
                ),
            )
            discord_preview.activity_progress.setValue(
                preview_progress
            )
            discord_preview.activity_progress.setHidden(
                False
            )

    def update_progress(self, song: Song):
        if DashboardPage._playback_seek_updates_blocked(self):
            return

        current = self.time_to_seconds(
            song.position
        )
        total = self.time_to_seconds(
            song.duration
        )

        if total <= 0:
            self.progress.setValue(0)
            return

        progress_value = int(
            round(
                (current / total) * 10000
            )
        )

        progress_value = max(
            0,
            min(
                10000,
                progress_value,
            ),
        )

        self.progress.setValue(
            progress_value
        )

    def show_nothing_playing(self):
        self._playback_scrubbing = False
        self._clear_playback_seek_pending()

        self.progress.setEnabled(
            False
        )

        self.sync_playback_control_state(
            available=False
        )
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

        self.stop_equalizer_animation()

        self.preview_title.setText(
            "Nothing playing"
        )
        self.preview_state.setText(
            "Waiting for Spotify"
        )
        self.preview_state.setHidden(False)
        self.preview_album.setText("")
        self.preview_album.setHidden(True)
        self.preview_time.setText(
            "Waiting"
        )
        self.preview_time.setHidden(False)

        discord_preview = getattr(
            self,
            "discord_profile_preview",
            None,
        )

        if discord_preview is not None:
            discord_preview.activity_progress.setValue(
                0
            )
            discord_preview.activity_progress.setHidden(
                True
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

        self._restore_non_music_discord_preview()

        self._last_artwork_signature = None

    @pyqtSlot(str)
    def show_worker_error(self, message):
        self._last_worker_error = str(
            message
            or "Unknown media error"
        )

        print("Media worker error:")
        print(message)

        self.stop_equalizer_animation()

        self.music_status.setText(
            "Error"
        )
        self.activity_badge.setText(
            "Error"
        )
        self.preview_time.setText(
            "Media error"
        )

        self._restore_non_music_discord_preview()

    def stop_media_worker(self):
        equalizer_timer = getattr(
            self,
            "equalizer_timer",
            None,
        )

        if equalizer_timer is not None:
            equalizer_timer.stop()

        dashboard_timer = getattr(
            self,
            "dashboard_timer",
            None,
        )

        if dashboard_timer is not None:
            dashboard_timer.stop()

        playback_presentation_timer = getattr(
            self,
            "playback_presentation_timer",
            None,
        )

        if playback_presentation_timer is not None:
            playback_presentation_timer.stop()

        discord_presence_preview_timer = getattr(
            self,
            "discord_presence_preview_timer",
            None,
        )

        if discord_presence_preview_timer is not None:
            discord_presence_preview_timer.stop()

        spectrum_service = getattr(
            self,
            "spotify_audio_spectrum_service",
            None,
        )

        if spectrum_service is not None:
            spectrum_service.shutdown(
                timeout_seconds=2.0
            )

        avatar_loader = getattr(
            self,
            "discord_avatar_loader",
            None,
        )

        if avatar_loader is not None:
            avatar_loader.shutdown()

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
    def _display_source(
        source_app: str,
    ) -> str:
        source = str(
            source_app or ""
        ).strip()

        lowered = source.lower()

        markers = [
            ("spotify", "Spotify"),
            ("googlechrome", "Chrome"),
            ("chrome", "Chrome"),
            ("msedge", "Edge"),
            ("firefox", "Firefox"),
            ("brave", "Brave"),
            ("opera", "Opera"),
            ("vivaldi", "Vivaldi"),
            ("soundcloud", "SoundCloud"),
        ]

        for marker, label in markers:
            if marker in lowered:
                return label

        if not source:
            return "Unknown"

        cleaned = (
            source
            .replace(".exe", "")
            .replace("_", " ")
            .strip()
        )

        return (
            cleaned[:18]
            or "Unknown"
        )

    @staticmethod
    def _friendly_time(
        value: str,
    ) -> str:
        try:
            played = datetime.strptime(
                value,
                "%Y-%m-%d %H:%M:%S",
            )

        except (
            TypeError,
            ValueError,
        ):
            return ""

        seconds = max(
            0,
            int(
                (
                    datetime.now()
                    - played
                ).total_seconds()
            ),
        )

        if seconds < 60:
            return "Just now"

        minutes = seconds // 60

        if minutes < 60:
            return f"{minutes}m ago"

        hours = minutes // 60

        if hours < 24:
            return f"{hours}h ago"

        days = hours // 24

        if days < 7:
            return f"{days}d ago"

        return played.strftime(
            "%d %b"
        )

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
