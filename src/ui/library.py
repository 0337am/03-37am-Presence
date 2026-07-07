from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class LibraryPage(QWidget):
    def __init__(self):
        super().__init__()

        self._last_track_key = None

        self.build_ui()

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 30, 30, 30)
        root.setSpacing(18)

        header_layout = QHBoxLayout()

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        title = QLabel("Library")
        title.setObjectName("libraryTitle")

        subtitle = QLabel("Songs played during this session")
        subtitle.setObjectName("librarySubtitle")

        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)

        clear_button = QPushButton("Clear history")
        clear_button.setObjectName("clearButton")
        clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_button.clicked.connect(self.clear_history)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        header_layout.addWidget(clear_button)

        root.addLayout(header_layout)

        card = QFrame()
        card.setObjectName("libraryCard")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)

        self.table = QTableWidget(0, 5)
        self.table.setObjectName("historyTable")
        self.table.setHorizontalHeaderLabels(
            [
                "Song",
                "Artist",
                "Album",
                "Status",
                "Last played",
            ]
        )

        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        card_layout.addWidget(self.table)
        root.addWidget(card)

        self.setStyleSheet(
            """
            QLabel#libraryTitle {
                color: #fff0f7;
                font-size: 28px;
                font-weight: bold;
            }

            QLabel#librarySubtitle {
                color: #b96f94;
                font-size: 13px;
            }

            QPushButton#clearButton {
                color: #ffeaf4;
                background: #521b3d;
                border: 1px solid #ff79b9;
                border-radius: 10px;
                padding: 9px 16px;
                font-weight: 600;
            }

            QPushButton#clearButton:hover {
                background: #6d234e;
            }

            QFrame#libraryCard {
                background: #26101f;
                border: 1px solid #57213f;
                border-radius: 18px;
            }

            QTableWidget#historyTable {
                color: #f8dce9;
                background: transparent;
                alternate-background-color: #301329;
                border: none;
                selection-background-color: #6d234e;
                selection-color: white;
                font-size: 13px;
            }

            QTableWidget#historyTable::item {
                padding: 10px;
                border-bottom: 1px solid #492039;
            }

            QHeaderView::section {
                color: #ff9dca;
                background: #351328;
                border: none;
                border-bottom: 1px solid #6a284d;
                padding: 10px;
                font-weight: bold;
            }

            QScrollBar:vertical {
                background: #1a0915;
                width: 11px;
                border-radius: 5px;
            }

            QScrollBar::handle:vertical {
                background: #6d234e;
                border-radius: 5px;
                min-height: 28px;
            }

            QScrollBar::handle:vertical:hover {
                background: #ff6caf;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
            }
            """
        )

    def add_song(self, song):
        if song is None:
            return

        title = str(getattr(song, "title", "") or "").strip()
        artist = str(getattr(song, "artist", "") or "").strip()
        album = str(getattr(song, "album", "") or "").strip()

        if not title or title.lower() in {"unknown title", "nothing playing"}:
            return

        track_key = (
            title.lower(),
            artist.lower(),
            album.lower(),
        )

        status = "Playing" if getattr(song, "playing", False) else "Paused"
        played_time = datetime.now().strftime("%H:%M:%S")

        if track_key == self._last_track_key and self.table.rowCount() > 0:
            self.table.item(0, 3).setText(status)
            self.table.item(0, 4).setText(played_time)
            return

        self._last_track_key = track_key

        self.table.insertRow(0)

        values = [
            title,
            artist or "Unknown artist",
            album or "No album",
            status,
            played_time,
        ]

        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignVCenter
                | Qt.AlignmentFlag.AlignLeft
            )
            self.table.setItem(0, column, item)

        while self.table.rowCount() > 100:
            self.table.removeRow(self.table.rowCount() - 1)

    def clear_history(self):
        self.table.setRowCount(0)
        self._last_track_key = None