from dataclasses import replace
from datetime import datetime
import hashlib
from pathlib import Path
import os
import subprocess

from PyQt6.QtCore import (
    Qt,
    QEvent,
    QPoint,
    QUrl,
    QThread,
    QTimer,
    QSignalBlocker,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import (
    QAction,
    QDesktopServices,
    QPixmap,
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
    QSizePolicy,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from src.library.history_store import (
    HistoryStore,
    HistoryTrack,
)
from src.music.manager import MusicManager
from src.music.song import Song
from src.music.source_preferences import (
    SourcePreferencesStore,
)
from src.system.afk_preferences import (
    AfkPreferencesStore,
)
from src.system.idle_monitor import (
    WindowsIdleMonitor,
)
from src.ui.custom_cards import (
    CustomCardStore,
    LinkCardData,
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
from src.ui.dashboard_profiles import (
    DashboardLayoutProfile,
    DashboardLayoutProfileStore,
    validate_profile_name,
)
from src.ui.link_cards import (
    LinkCardDialog,
    LinkCardWidget,
)
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
    # ANIMATED_EQUALIZER
    # FINAL_GUIDE_DETAILS
    # HEADER_PREVIEW_POLISH
    # V2_DASHBOARD_PATCH
    # V2_THREE_COLUMN_POLISH
    navigate_requested = pyqtSignal(int)
    settings_section_requested = pyqtSignal(str)

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

        self.dashboard_layout_store = (
            DashboardLayoutStore()
        )

        self.dashboard_profile_store = (
            DashboardLayoutProfileStore()
        )

        self.dashboard_layout_state = (
            self.dashboard_layout_store.load()
        )

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

        self._dashboard_editor_outline = None

        self._recent_track_fetch_limit = 24
        self._recent_tracks = []
        self._recent_visible_capacity = 0
        self._quick_access_layout_mode = None

        self.build_ui()

        self._equalizer_frames = [
            "▁▃▆█▄▂▇▅",
            "▃▇▄▁▆█▂▅",
            "▆▂█▄▁▅▇▃",
            "█▄▁▇▃▆▂▅",
            "▄▆▃█▂▁▇▅",
            "▂▅▇▃█▄▁▆",
            "▇▁▄▆▂█▅▃",
            "▃█▅▂▇▁▄▆",
        ]

        self._equalizer_index = 0

        self.equalizer_timer = QTimer(
            self
        )
        self.equalizer_timer.setInterval(
            140
        )
        self.equalizer_timer.timeout.connect(
            self.advance_equalizer
        )

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

        self.dashboard_canvas = QFrame()
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

        move_handle = QLabel(
            "MOVE",
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
            38,
            18,
        )
        move_handle.setToolTip(
            "Drag this card anywhere on the dashboard"
        )
        move_handle.setAttribute(
            Qt.WidgetAttribute.WA_Hover,
            True,
        )
        move_handle.installEventFilter(
            self
        )

        resize_handle = QLabel(
            "↘",
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
            18,
            18,
        )
        resize_handle.setToolTip(
            "Drag to resize this dashboard card"
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
                "⋯",
                self.dashboard_canvas,
            )
            action_handle.setObjectName(
                "dashboardCustomActionHandle"
            )
            action_handle.setCursor(
                Qt.CursorShape.PointingHandCursor
            )
            action_handle.setFixedSize(
                26,
                18,
            )
            action_handle.setToolTip(
                "Edit or duplicate this custom card"
            )

            action_menu = QMenu(action_handle)

            edit_action = QAction(
                "✎  Edit Link card",
                action_menu,
            )
            edit_action.triggered.connect(
                lambda checked=False, current_card_id=card_id:
                self.edit_custom_link_card(
                    current_card_id
                )
            )
            action_menu.addAction(edit_action)

            duplicate_action = QAction(
                "⧉  Duplicate Link card",
                action_menu,
            )
            duplicate_action.triggered.connect(
                lambda checked=False, current_card_id=card_id:
                self.duplicate_custom_link_card(
                    current_card_id
                )
            )
            action_menu.addAction(duplicate_action)

            action_handle.setMenu(action_menu)

            delete_handle = QPushButton(
                "×",
                self.dashboard_canvas,
            )
            delete_handle.setObjectName(
                "dashboardDeleteHandle"
            )
            delete_handle.setCursor(
                Qt.CursorShape.PointingHandCursor
            )
            delete_handle.setFixedSize(
                18,
                18,
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

        if not move_handles:
            return

        locked = (
            self.dashboard_layout_state.locked
        )

        if hasattr(
            self,
            "dashboard_canvas",
        ):
            self.dashboard_canvas.setProperty(
                "editing",
                not locked,
            )

            self._refresh_dashboard_widget_style(
                self.dashboard_canvas
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

            move_handle.setCursor(
                (
                    Qt.CursorShape.OpenHandCursor
                    if editable
                    else Qt.CursorShape.ArrowCursor
                )
            )

            if resize_handle is not None:
                resize_handle.setVisible(
                    editable
                    and dashboard_card_spec(
                        card_id
                    ).resizable
                )

                resize_handle.setCursor(
                    (
                        Qt.CursorShape.SizeFDiagCursor
                        if editable
                        else Qt.CursorShape.ArrowCursor
                    )
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
                - (
                    move_handle.height()
                    // 2
                )
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
                    - (
                        action_handle.width()
                        // 2
                    )
                )

                action_y = (
                    card.y()
                    - (
                        action_handle.height()
                        // 2
                    )
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
                    - (
                        delete_handle.width()
                        // 2
                    )
                )

                delete_y = (
                    card.y()
                    - (
                        delete_handle.height()
                        // 2
                    )
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
                    - (
                        resize_handle.width()
                        // 2
                    )
                )

                resize_y = (
                    card.y()
                    + card.height()
                    - (
                        resize_handle.height()
                        // 2
                    )
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

        if (
            card in responsive_cards
            or isinstance(card, LinkCardWidget)
        ):
            hint_width = 0
            hint_height = 0
        else:
            hint = card.minimumSizeHint()
            hint_width = hint.width()
            hint_height = hint.height()

        if isinstance(card, LinkCardWidget):
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

        event_type = event.type()

        if (
            event_type
            == QEvent.Type.MouseButtonPress
            and event.button()
            == Qt.MouseButton.LeftButton
        ):
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

        self.schedule_dashboard_geometry_refresh()

    def build_dashboard_layout_toolbar(self):
        self.layout_toolbar = QFrame()
        self.layout_toolbar.setObjectName(
            "dashboardLayoutToolbar"
        )

        toolbar_layout = QHBoxLayout(
            self.layout_toolbar
        )
        toolbar_layout.setContentsMargins(
            10,
            6,
            10,
            6,
        )
        toolbar_layout.setSpacing(8)

        toolbar_title = QLabel(
            "DASHBOARD LAYOUT"
        )
        toolbar_title.setObjectName(
            "layoutToolbarTitle"
        )

        self.layout_status_label = QLabel(
            "Locked"
        )
        self.layout_status_label.setObjectName(
            "layoutToolbarStatus"
        )

        self.layout_preset_combo = QComboBox()
        self.layout_preset_combo.setObjectName(
            "layoutPresetCombo"
        )
        self.layout_preset_combo.setMinimumWidth(
            145
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
            "Profiles  ▾"
        )
        self.layout_profiles_button.setObjectName(
            "layoutMenuButton"
        )
        self.layout_profiles_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.layout_profiles_button.setToolTip(
            "Save, apply, or delete dashboard layout profiles"
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

        self.layout_add_card_button = QPushButton(
            "Add card  ▾"
        )
        self.layout_add_card_button.setObjectName(
            "layoutMenuButton"
        )
        self.layout_add_card_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.layout_add_card_button.setToolTip(
            "Add a custom card to the dashboard"
        )

        self.layout_add_card_menu = QMenu(
            self.layout_add_card_button
        )
        self.layout_add_link_action = QAction(
            "🔗  Link card",
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
        self.layout_add_card_button.setMenu(
            self.layout_add_card_menu
        )

        self.layout_visibility_button = QPushButton(
            "Cards  \u25be"
        )
        self.layout_visibility_button.setObjectName(
            "layoutMenuButton"
        )
        self.layout_visibility_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.layout_visibility_button.setToolTip(
            "Choose which dashboard cards are visible"
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

        self.layout_lock_button = QPushButton(
            "Unlock layout"
        )
        self.layout_lock_button.setObjectName(
            "layoutLockButton"
        )
        self.layout_lock_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.layout_lock_button.clicked.connect(
            self.toggle_dashboard_layout_lock
        )

        toolbar_layout.addWidget(
            toolbar_title
        )
        toolbar_layout.addWidget(
            self.layout_status_label
        )
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(
            self.layout_preset_combo
        )
        toolbar_layout.addWidget(
            self.layout_profiles_button
        )
        toolbar_layout.addWidget(
            self.layout_add_card_button
        )
        toolbar_layout.addWidget(
            self.layout_visibility_button
        )
        toolbar_layout.addWidget(
            self.layout_reset_button
        )
        toolbar_layout.addWidget(
            self.layout_lock_button
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
                self.create_link_card_widget(card)
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

    def confirm_delete_custom_card(
        self,
        card_id: str,
    ):
        card = self.custom_cards.get(card_id)

        if card is None:
            return

        answer = QMessageBox.question(
            self,
            "Delete Link card",
            (
                f'Delete "{card.title}" from the dashboard?\n\n'
                "This cannot be undone."
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        self.delete_custom_card(card_id)

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
                "Link card not deleted",
                message,
            )
            return False

        self.custom_cards = {
            item.card_id: item
            for item in saved_cards
        }
        self.dashboard_layout_state = saved_layout
        self.remove_custom_card_ui(card_id)
        self.sync_dashboard_layout_controls()
        self.schedule_dashboard_geometry_refresh()
        return True

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
        )

    def toggle_dashboard_layout_lock(self):
        if self._dashboard_drag_active:
            self.cancel_dashboard_live_drag()

        if self._dashboard_resize_active:
            self.cancel_dashboard_live_resize()

        updated = replace(
            self.dashboard_layout_state,
            locked=(
                not self.dashboard_layout_state.locked
            ),
        )

        self.apply_dashboard_layout(
            updated,
            persist=True,
        )

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
            )
        except ValueError as error:
            print(
                "Dashboard visibility change rejected: "
                f"{error}"
            )
            self.sync_dashboard_layout_controls()

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

        locked = (
            self.dashboard_layout_state.locked
        )

        self.layout_status_label.setText(
            "Locked"
            if locked
            else "Editing"
        )

        self.layout_preset_combo.setEnabled(
            not locked
        )
        self.layout_profiles_button.setEnabled(
            not locked
        )
        self.layout_add_card_button.setEnabled(
            not locked
        )
        self.layout_visibility_button.setEnabled(
            not locked
        )
        self.layout_reset_button.setEnabled(
            not locked
        )

        self.layout_lock_button.setText(
            "Unlock layout"
            if locked
            else "Lock layout"
        )

        self.layout_lock_button.setToolTip(
            (
                "Enable dashboard layout editing"
                if locked
                else "Prevent accidental layout changes"
            )
        )

        self.sync_dashboard_drag_handles()

    def apply_dashboard_layout(
        self,
        layout: DashboardLayout,
        persist: bool = False,
        sync_controls: bool = True,
    ) -> DashboardLayout:
        validated = validate_layout(
            layout
        )

        if persist:
            validated = (
                self.dashboard_layout_store.save(
                    validated
                )
            )

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

        progress_row = QHBoxLayout()
        progress_row.setSpacing(8)

        self.current_time = QLabel(
            self.song.position
        )
        self.current_time.setObjectName(
            "timeLabel"
        )

        self.progress = QProgressBar()
        self.progress.setObjectName(
            "playbackProgress"
        )
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)

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
            self.progress,
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
            12,
            14,
            12,
        )
        preview_layout.setSpacing(8)

        preview_top = QHBoxLayout()
        preview_top.setSpacing(8)

        preview_heading = QLabel(
            "🎮  DISCORD PREVIEW"
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

        activity_panel = QFrame()
        activity_panel.setObjectName(
            "discordActivityPanel"
        )

        panel_layout = QVBoxLayout(
            activity_panel
        )
        panel_layout.setContentsMargins(
            12,
            9,
            12,
            9,
        )
        panel_layout.setSpacing(7)

        app_row = QHBoxLayout()
        app_row.setSpacing(6)

        self.preview_app = QLabel(
            "03:37am Presence"
        )
        self.preview_app.setObjectName(
            "previewApp"
        )

        app_badge = QLabel("APP")
        app_badge.setObjectName(
            "appBadge"
        )

        app_row.addWidget(
            self.preview_app
        )
        app_row.addWidget(
            app_badge
        )
        app_row.addStretch()

        panel_layout.addLayout(
            app_row
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

        panel_layout.addLayout(
            activity_row
        )

        preview_layout.addWidget(
            activity_panel,
            stretch=1,
        )

        open_discord = QPushButton(
            "Open in Discord"
        )
        open_discord.setIcon(
            self.style().standardIcon(
                QStyle.StandardPixmap.SP_ArrowForward
            )
        )
        open_discord.setObjectName(
            "libraryOpenButton"
        )
        open_discord.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        open_discord.clicked.connect(
            self.open_discord
        )

        preview_layout.addWidget(
            open_discord
        )

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

        button_definitions = [
            (
                "♙",
                "AFK",
                "Set AFK presence",
                1,
            ),
            (
                "✎",
                "Custom",
                "Create a presence",
                1,
            ),
            (
                "★",
                "Presets",
                "Manage presence modes",
                1,
            ),
            (
                "⚙",
                "Settings",
                "Configure application",
                3,
            ),
        ]

        self.quick_access_buttons = []

        for (
            icon,
            title,
            detail,
            page_index,
        ) in button_definitions:
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

            button.clicked.connect(
                lambda checked=False,
                index=page_index:
                self.navigate_requested.emit(
                    index
                )
            )

            self.quick_access_buttons.append(
                {
                    "button": button,
                    "icon": icon,
                    "title": title,
                    "detail": detail,
                }
            )

        layout.addLayout(
            self.quick_access_grid,
            stretch=1,
        )

        self.update_quick_access_layout(
            force=True
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

            QFrame#dashboardLayoutToolbar {{
                background: {theme["card"]};
                border: 1px solid {theme["border"]};
                border-radius: 10px;
            }}

            QLabel#layoutToolbarTitle {{
                color: {theme["accent"]};
                font-size: 8px;
                font-weight: 750;
                letter-spacing: 1px;
            }}

            QLabel#layoutToolbarStatus {{
                color: {theme["muted"]};
                background: {theme["card_alt"]};
                border: 1px solid {theme["border"]};
                border-radius: 6px;
                padding: 3px 7px;
                font-size: 8px;
                font-weight: 700;
            }}

            QLabel#dashboardDragHandle {{
                color: {theme["text"]};
                background: {theme["card_alt"]};
                border: 1px solid {theme["accent"]};
                border-radius: 6px;
                font-size: 6px;
                font-weight: 750;
                letter-spacing: 1px;
            }}

            QLabel#dashboardDragHandle:hover {{
                color: {theme["background"]};
                background: {theme["accent"]};
            }}

            QLabel#dashboardResizeHandle {{
                color: {theme["background"]};
                background: {theme["accent"]};
                border: 1px solid {theme["card"]};
                border-radius: 6px;
                font-size: 11px;
                font-weight: 750;
            }}

            QLabel#dashboardResizeHandle:hover {{
                color: {theme["text"]};
                border: 1px solid {theme["text"]};
            }}

            QPushButton#dashboardCustomActionHandle,
            QPushButton#dashboardDeleteHandle {{
                color: {theme["text"]};
                background: {theme["card_alt"]};
                border: 1px solid {theme["accent"]};
                border-radius: 6px;
                padding: 0px;
                font-size: 12px;
                font-weight: 800;
            }}

            QPushButton#dashboardCustomActionHandle:hover,
            QPushButton#dashboardDeleteHandle:hover {{
                color: {theme["background"]};
                background: {theme["accent"]};
            }}

            QPushButton#dashboardCustomActionHandle::menu-indicator {{
                image: none;
                width: 0px;
            }}

            QFrame#dashboardCanvas {{
                background: transparent;
                border: none;
            }}

            QFrame#dashboardCanvas[editing="true"] {{
                background: transparent;
                border: none;
            }}

            QFrame#dashboardEditorOutline {{
                background: transparent;
                border: 1px solid {theme["accent"]};
                border-radius: 13px;
            }}

            QFrame#dashboardEditorOutline[editorMode="resize"] {{
                border: 1px dashed {theme["accent"]};
            }}

            QComboBox#layoutPresetCombo,
            QPushButton#layoutControlButton,
            QPushButton#layoutMenuButton,
            QPushButton#layoutLockButton {{
                color: {theme["text"]};
                background: {theme["card_alt"]};
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
                background: {theme["card"]};
                border: 1px solid {theme["border"]};
                selection-background-color: {theme["accent"]};
            }}

            QMenu {{
                color: {theme["text"]};
                background: {theme["card"]};
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
                background: {theme["card_alt"]};
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
                background: {theme["card"]};
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
                background: {theme["card_alt"]};
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
                background: {theme["card_alt"]};
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
                background: {theme["card_alt"]};
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

            QFrame#recentCard,
            QFrame#quickAccessCard,
            QFrame#libraryStatusCard {{
                background: {theme["card"]};
                border: 1px solid {theme["border"]};
                border-radius: 14px;
            }}

            QFrame#recentRow,
            QFrame#statTile {{
                background: {theme["card_alt"]};
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
                background: {theme["card_alt"]};
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
                background: {theme["card_alt"]};
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
            """
        )

        for card in self.dashboard_cards.values():
            if isinstance(card, LinkCardWidget):
                card.set_theme(theme)

        self.schedule_dashboard_geometry_refresh()

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
            title
        )

    def start_equalizer_animation(self):
        self.equalizer.setVisible(
            True
        )

        if not self.equalizer_timer.isActive():
            self.equalizer_timer.start()

        self.advance_equalizer()

    def stop_equalizer_animation(self):
        self.equalizer_timer.stop()
        self.equalizer.clear()
        self.equalizer.setVisible(
            False
        )

    def advance_equalizer(self):
        if not self._equalizer_frames:
            return

        self.equalizer.setText(
            self._equalizer_frames[
                self._equalizer_index
            ]
        )

        self._equalizer_index = (
            self._equalizer_index + 1
        ) % len(
            self._equalizer_frames
        )

    @pyqtSlot(object)
    def apply_song(self, song):
        if song is None or not song.title:
            self.show_nothing_playing()
            return

        self._last_worker_error = ""

        self.song = song
        self.cache_song_artwork(song)

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

        self.update_artwork(song)
        self.update_progress(song)

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
            return

        try:
            cache_path.write_bytes(
                bytes(artwork_bytes)
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

        self.stop_equalizer_animation()

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