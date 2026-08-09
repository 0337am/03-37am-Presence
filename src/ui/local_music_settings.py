from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import (
    Qt,
    pyqtSlot,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from src.media.local_music_index import (
    LocalMusicScanResult,
)
from src.media.qt_local_music_runtime import (
    LocalMusicQtRuntimeError,
)
from src.system.local_music_preferences import (
    LocalMusicPreferences,
)


class LocalMusicSettingsCard(
    QFrame
):
    def __init__(
        self,
        preference_store,
        scan_runtime,
        *,
        theme_manager=None,
        parent=None,
    ) -> None:
        super().__init__(
            parent
        )

        for method_name in (
            "load",
            "add_folder",
            "remove_folder",
            "set_scan_on_startup",
        ):
            method = getattr(
                preference_store,
                method_name,
                None,
            )

            if not callable(
                method
            ):
                raise TypeError(
                    (
                        "preference_store must "
                        "provide "
                        + method_name
                    )
                )

        start_scan = getattr(
            scan_runtime,
            "start_scan",
            None,
        )

        clear_latest = getattr(
            scan_runtime,
            "clear_latest_result",
            None,
        )

        if not callable(
            start_scan
        ):
            raise TypeError(
                (
                    "scan_runtime must "
                    "provide start_scan"
                )
            )

        if not callable(
            clear_latest
        ):
            raise TypeError(
                (
                    "scan_runtime must provide "
                    "clear_latest_result"
                )
            )

        self.preference_store = (
            preference_store
        )

        self.scan_runtime = (
            scan_runtime
        )

        self.theme_manager = (
            theme_manager
        )

        self._preferences = (
            LocalMusicPreferences()
        )

        self._busy = bool(
            getattr(
                scan_runtime,
                "busy",
                False,
            )
        )

        self.setObjectName(
            "settingsCard"
        )

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            18,
            18,
            18,
            18,
        )

        layout.setSpacing(
            10
        )

        title = QLabel(
            "Local Music"
        )

        title.setObjectName(
            "cardTitle"
        )

        description = QLabel(
            (
                "Choose folders that contain "
                "local music. 03:37am Presence "
                "only scans folders you add here."
            )
        )

        description.setObjectName(
            "cardDescription"
        )

        description.setWordWrap(
            True
        )

        privacy = QLabel(
            (
                "Folder paths stay on this device "
                "and are not included in portable "
                "Settings backups."
            )
        )

        privacy.setObjectName(
            "helpText"
        )

        privacy.setWordWrap(
            True
        )

        self.startup_scan_box = QCheckBox(
            "Scan Local Music on startup"
        )

        self.startup_scan_box.setObjectName(
            "localMusicStartupScanCheck"
        )

        self.startup_scan_box.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.startup_scan_box.toggled.connect(
            self._save_scan_on_startup_preference
        )

        self.folder_summary = QLabel()

        self.folder_summary.setObjectName(
            "fieldLabel"
        )

        self.folder_list = QListWidget()

        self.folder_list.setObjectName(
            "localMusicFolderList"
        )

        self.folder_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )

        self.folder_list.setMinimumHeight(
            105
        )

        self.folder_list.setMaximumHeight(
            180
        )

        self.folder_list.itemSelectionChanged.connect(
            self._sync_controls
        )

        button_row = QHBoxLayout()

        button_row.setSpacing(
            8
        )

        self.add_button = QPushButton(
            "Add Folder"
        )

        self.add_button.setObjectName(
            "secondaryButton"
        )

        self.add_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.add_button.clicked.connect(
            self.add_folder
        )

        self.remove_button = QPushButton(
            "Remove"
        )

        self.remove_button.setObjectName(
            "secondaryButton"
        )

        self.remove_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.remove_button.clicked.connect(
            self.remove_selected_folder
        )

        self.rescan_button = QPushButton(
            "Rescan"
        )

        self.rescan_button.setObjectName(
            "secondaryButton"
        )

        self.rescan_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.rescan_button.clicked.connect(
            self.rescan
        )

        button_row.addWidget(
            self.add_button
        )

        button_row.addWidget(
            self.remove_button
        )

        button_row.addWidget(
            self.rescan_button
        )

        button_row.addStretch()

        self.status_label = QLabel(
            (
                "No Local Music scan has "
                "been run yet."
            )
        )

        self.status_label.setObjectName(
            "status"
        )

        self.status_label.setWordWrap(
            True
        )

        layout.addWidget(
            title
        )

        layout.addWidget(
            description
        )

        layout.addWidget(
            privacy
        )

        layout.addWidget(
            self.startup_scan_box
        )

        layout.addWidget(
            self.folder_summary
        )

        layout.addWidget(
            self.folder_list
        )

        layout.addLayout(
            button_row
        )

        layout.addWidget(
            self.status_label
        )

        self._connect_runtime()

        self._connect_theme()

        self.refresh_from_store()

    def _connect_runtime(
        self,
    ) -> None:
        for signal_name, slot in (
            (
                "busy_changed",
                self._handle_busy,
            ),
            (
                "result_ready",
                self._handle_result,
            ),
            (
                "failed",
                self._handle_failure,
            ),
            (
                "scan_cancelled",
                self._handle_cancelled,
            ),
        ):
            signal = getattr(
                self.scan_runtime,
                signal_name,
                None,
            )

            connect = getattr(
                signal,
                "connect",
                None,
            )

            if not callable(
                connect
            ):
                raise TypeError(
                    (
                        "scan_runtime is missing "
                        + signal_name
                        + " signal"
                    )
                )

            connect(
                slot
            )

    def _connect_theme(
        self,
    ) -> None:
        manager = (
            self.theme_manager
        )

        if manager is None:
            return

        theme_method = getattr(
            manager,
            "theme",
            None,
        )

        if callable(
            theme_method
        ):
            try:
                self.apply_theme(
                    theme_method()
                )
            except Exception:
                pass

        signal = getattr(
            manager,
            "theme_changed",
            None,
        )

        connect = getattr(
            signal,
            "connect",
            None,
        )

        if callable(
            connect
        ):
            connect(
                self.apply_theme
            )

    @pyqtSlot(
        object
    )
    def apply_theme(
        self,
        theme,
    ) -> None:
        if not isinstance(
            theme,
            dict,
        ):
            return

        text = str(
            theme.get(
                "text",
                "#f5f5f5",
            )
        )

        muted = str(
            theme.get(
                "muted",
                "#9a9a9a",
            )
        )

        background = str(
            theme.get(
                "card_alt",
                theme.get(
                    "background",
                    "#151515",
                ),
            )
        )

        border = str(
            theme.get(
                "border",
                "#333333",
            )
        )

        accent = str(
            theme.get(
                "accent",
                "#ff477e",
            )
        )

        self.folder_list.setStyleSheet(
            f"""
            QListWidget#localMusicFolderList {{
                color: {text};
                background: {background};
                border: 1px solid {border};
                border-radius: 9px;
                padding: 5px;
            }}

            QListWidget#localMusicFolderList::item {{
                padding: 7px;
                border-radius: 6px;
            }}

            QListWidget#localMusicFolderList::item:selected {{
                color: {text};
                background: {accent};
            }}

            QListWidget#localMusicFolderList::item:disabled {{
                color: {muted};
            }}
            """
        )

    def _set_status(
        self,
        message: str,
    ) -> None:
        self.status_label.setText(
            str(
                message
            )
        )

    def _invalidate_index(
        self,
    ) -> None:
        try:
            self.scan_runtime.clear_latest_result()

        except Exception:
            pass

    def refresh_from_store(
        self,
    ) -> bool:
        try:
            preferences = (
                self.preference_store.load()
            )

        except Exception:
            self._set_status(
                (
                    "Local Music folders "
                    "could not be loaded."
                )
            )

            return False

        if not isinstance(
            preferences,
            LocalMusicPreferences,
        ):
            self._set_status(
                (
                    "Local Music folders "
                    "could not be loaded."
                )
            )

            return False

        self._preferences = (
            preferences
        )

        self.startup_scan_box.blockSignals(
            True
        )

        self.startup_scan_box.setChecked(
            preferences.scan_on_startup
        )

        self.startup_scan_box.blockSignals(
            False
        )

        selected_path = ""

        selected = (
            self.folder_list.currentItem()
        )

        if selected is not None:
            selected_path = str(
                selected.data(
                    Qt.ItemDataRole.UserRole
                )
                or ""
            )

        self.folder_list.clear()

        selected_row = -1

        for index, folder in enumerate(
            preferences.folders
        ):
            item = QListWidgetItem(
                folder
            )

            item.setData(
                Qt.ItemDataRole.UserRole,
                folder,
            )

            item.setToolTip(
                folder
            )

            self.folder_list.addItem(
                item
            )

            if folder == selected_path:
                selected_row = index

        if selected_row >= 0:
            self.folder_list.setCurrentRow(
                selected_row
            )

        count = len(
            preferences.folders
        )

        suffix = (
            "folder"
            if count == 1
            else "folders"
        )

        self.folder_summary.setText(
            f"{count} {suffix} configured"
        )

        self._sync_controls()

        return True

    def _sync_controls(
        self,
    ) -> None:
        has_selection = (
            self.folder_list.currentItem()
            is not None
        )

        has_folders = bool(
            self._preferences.folders
        )

        self.add_button.setEnabled(
            not self._busy
        )

        self.remove_button.setEnabled(
            (
                not self._busy
                and has_selection
            )
        )

        self.rescan_button.setEnabled(
            (
                not self._busy
                and has_folders
            )
        )

        self.folder_list.setEnabled(
            not self._busy
        )

        self.startup_scan_box.setEnabled(
            not self._busy
        )

    def add_folder(
        self,
    ) -> bool:
        if self._busy:
            return False

        selected = (
            QFileDialog.getExistingDirectory(
                self,
                "Add Local Music Folder",
                "",
            )
        )

        if not selected:
            return False

        try:
            self.preference_store.add_folder(
                selected
            )

        except Exception:
            self._set_status(
                (
                    "That Local Music folder "
                    "could not be added."
                )
            )

            return False

        self._invalidate_index()

        self.refresh_from_store()

        for row in range(
            self.folder_list.count()
        ):
            item = (
                self.folder_list.item(
                    row
                )
            )

            if (
                item.data(
                    Qt.ItemDataRole.UserRole
                )
                == selected
            ):
                self.folder_list.setCurrentRow(
                    row
                )

                break

        self._set_status(
            (
                "Folder added. Choose Rescan "
                "to update the Local Music index."
            )
        )

        return True

    def remove_selected_folder(
        self,
    ) -> bool:
        if self._busy:
            return False

        item = (
            self.folder_list.currentItem()
        )

        if item is None:
            return False

        folder = str(
            item.data(
                Qt.ItemDataRole.UserRole
            )
            or ""
        )

        if not folder:
            return False

        try:
            self.preference_store.remove_folder(
                folder
            )

        except Exception:
            self._set_status(
                (
                    "That Local Music folder "
                    "could not be removed."
                )
            )

            return False

        self._invalidate_index()

        self.refresh_from_store()

        self._set_status(
            (
                "Folder removed. Choose Rescan "
                "to update the Local Music index."
            )
        )

        return True

    @staticmethod
    def _folder_available(
        folder: str,
    ) -> bool:
        try:
            return Path(
                folder
            ).is_dir()

        except OSError:
            return False

    def _save_scan_on_startup_preference(
        self,
        enabled: bool,
    ) -> None:
        try:
            preferences = (
                self.preference_store
                .set_scan_on_startup(
                    bool(
                        enabled
                    )
                )
            )

        except Exception:
            self.startup_scan_box.blockSignals(
                True
            )

            self.startup_scan_box.setChecked(
                self._preferences.scan_on_startup
            )

            self.startup_scan_box.blockSignals(
                False
            )

            self._set_status(
                (
                    "Startup scan preference "
                    "could not be saved."
                )
            )

            return

        if isinstance(
            preferences,
            LocalMusicPreferences,
        ):
            self._preferences = (
                preferences
            )

        else:
            self.refresh_from_store()

        self._sync_controls()

        self._set_status(
            (
                "Automatic Local Music scanning "
                + (
                    "enabled."
                    if bool(
                        enabled
                    )
                    else "disabled."
                )
            )
        )

    def scan_on_startup(
        self,
    ) -> bool:
        if self._busy:
            return False

        if (
            getattr(
                self.scan_runtime,
                "latest_result",
                None,
            )
            is not None
        ):
            return False

        if not self.refresh_from_store():
            return False

        if not self._preferences.scan_on_startup:
            return False

        if not self._preferences.folders:
            return False

        return self.rescan()

    def rescan(
        self,
    ) -> bool:
        if self._busy:
            return False

        if not self.refresh_from_store():
            return False

        configured = (
            self._preferences.folders
        )

        if not configured:
            self._set_status(
                (
                    "Add a Local Music folder "
                    "before scanning."
                )
            )

            return False

        available = tuple(
            folder
            for folder
            in configured
            if self._folder_available(
                folder
            )
        )

        unavailable_count = (
            len(
                configured
            )
            - len(
                available
            )
        )

        if not available:
            self._set_status(
                (
                    "None of the configured "
                    "Local Music folders are "
                    "currently available."
                )
            )

            return False

        available_count = len(
            available
        )

        folder_word = (
            "folder"
            if available_count == 1
            else "folders"
        )

        status = (
            "Scanning "
            + str(
                available_count
            )
            + " "
            + folder_word
            + "..."
        )

        if unavailable_count:
            status += (
                " "
                + str(
                    unavailable_count
                )
                + " configured "
                + (
                    "folder is"
                    if unavailable_count == 1
                    else "folders are"
                )
                + " unavailable."
            )

        self._set_status(
            status
        )

        try:
            self.scan_runtime.start_scan(
                available
            )

        except LocalMusicQtRuntimeError as error:
            self._set_status(
                error.message
            )

            return False

        except Exception:
            self._set_status(
                (
                    "Local Music scanning "
                    "could not be started."
                )
            )

            return False

        return True

    @pyqtSlot(
        bool
    )
    def _handle_busy(
        self,
        busy: bool,
    ) -> None:
        self._busy = bool(
            busy
        )

        self._sync_controls()

    @pyqtSlot(
        object
    )
    def _handle_result(
        self,
        result,
    ) -> None:
        if not isinstance(
            result,
            LocalMusicScanResult,
        ):
            self._set_status(
                (
                    "Local Music returned "
                    "an invalid scan result."
                )
            )

            return

        count = (
            result.indexed_files
        )

        track_word = (
            "track"
            if count == 1
            else "tracks"
        )

        message = (
            str(
                count
            )
            + " "
            + track_word
            + " indexed."
        )

        if result.skipped_files:
            message += (
                " "
                + str(
                    result.skipped_files
                )
                + " files skipped."
            )

        if result.limit_reached:
            message += (
                " The scan safety limit "
                "was reached."
            )

        self._set_status(
            message
        )

    @pyqtSlot(
        str,
        str,
    )
    def _handle_failure(
        self,
        _error_code: str,
        message: str,
    ) -> None:
        safe_message = str(
            message
            or (
                "Local Music scanning "
                "could not be completed."
            )
        ).strip()

        self._set_status(
            safe_message
        )

    @pyqtSlot()
    def _handle_cancelled(
        self,
    ) -> None:
        self._set_status(
            "Local Music scan cancelled."
        )
