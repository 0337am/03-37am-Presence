from __future__ import annotations

from PyQt6.QtCore import QSize, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.ui.custom_cards import (
    LinkCardData,
    MAX_BUTTON_LABEL_LENGTH,
    MAX_DESCRIPTION_LENGTH,
    MAX_ICON_LENGTH,
    MAX_TITLE_LENGTH,
    MAX_URL_LENGTH,
    create_link_card,
    normalize_web_url,
)
from src.ui.link_card_icons import (
    WebsiteIconFetchWorker,
    cached_favicon_path,
    domain_initial,
    remove_cached_favicon,
    save_favicon_bytes,
)


class LinkCardDialog(QDialog):
    def __init__(
        self,
        parent=None,
        card: LinkCardData | None = None,
    ):
        super().__init__(parent)

        self._editing_card = card
        self._result_card = None
        self._icon_thread = None
        self._icon_worker = None
        self._icon_fetch_url = ""
        self._icon_fetching = False

        self.setWindowTitle(
            "Edit Link card"
            if card is not None
            else "Add Link card"
        )
        self.setModal(True)
        self.setMinimumWidth(430)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        intro = QLabel(
            "Create a safe web shortcut for your dashboard. "
            "Only http:// and https:// addresses are allowed."
        )
        intro.setWordWrap(True)
        intro.setObjectName("linkCardDialogIntro")
        root.addWidget(intro)

        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(9)

        self.url_edit = QLineEdit()
        self.url_edit.setMaxLength(MAX_URL_LENGTH)
        self.url_edit.setPlaceholderText("https://example.com")
        self.url_edit.setClearButtonEnabled(True)

        self.title_edit = QLineEdit()
        self.title_edit.setMaxLength(MAX_TITLE_LENGTH)
        self.title_edit.setPlaceholderText(
            "Optional, uses the website domain when blank"
        )
        self.title_edit.setClearButtonEnabled(True)

        self.icon_edit = QLineEdit()
        self.icon_edit.setMaxLength(MAX_ICON_LENGTH)
        self.icon_edit.setPlaceholderText("🔗")
        self.icon_edit.setClearButtonEnabled(True)

        self.website_icon_preview = QLabel("↗")
        self.website_icon_preview.setObjectName(
            "linkCardWebsiteIconPreview"
        )
        self.website_icon_preview.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.website_icon_preview.setFixedSize(46, 46)
        self.website_icon_preview.setFrameShape(
            QFrame.Shape.StyledPanel
        )

        self.fetch_icon_button = QPushButton(
            "Fetch from website"
        )
        self.fetch_icon_button.setObjectName(
            "linkCardFetchIconButton"
        )
        self.fetch_icon_button.setToolTip(
            "Contacts the website homepage once and saves "
            "its public tab icon locally."
        )

        self.remove_icon_button = QPushButton(
            "Remove cached icon"
        )
        self.remove_icon_button.setObjectName(
            "linkCardRemoveIconButton"
        )
        self.remove_icon_button.setToolTip(
            "Removes the locally cached icon for this website."
        )

        icon_buttons = QHBoxLayout()
        icon_buttons.setContentsMargins(0, 0, 0, 0)
        icon_buttons.setSpacing(7)
        icon_buttons.addWidget(self.fetch_icon_button)
        icon_buttons.addWidget(self.remove_icon_button)

        self.website_icon_status = QLabel(
            "Used automatically when Icon or emoji is blank."
        )
        self.website_icon_status.setObjectName(
            "linkCardWebsiteIconStatus"
        )
        self.website_icon_status.setWordWrap(True)

        icon_details = QVBoxLayout()
        icon_details.setContentsMargins(0, 0, 0, 0)
        icon_details.setSpacing(5)
        icon_details.addLayout(icon_buttons)
        icon_details.addWidget(self.website_icon_status)

        self.website_icon_controls = QWidget()
        website_icon_layout = QHBoxLayout(
            self.website_icon_controls
        )
        website_icon_layout.setContentsMargins(0, 0, 0, 0)
        website_icon_layout.setSpacing(9)
        website_icon_layout.addWidget(
            self.website_icon_preview
        )
        website_icon_layout.addLayout(
            icon_details,
            stretch=1,
        )

        self.description_edit = QPlainTextEdit()
        self.description_edit.setPlaceholderText(
            "Optional description shown on larger cards"
        )
        self.description_edit.setMaximumHeight(96)

        self.button_label_edit = QLineEdit()
        self.button_label_edit.setMaxLength(
            MAX_BUTTON_LABEL_LENGTH
        )
        self.button_label_edit.setPlaceholderText("Open")
        self.button_label_edit.setClearButtonEnabled(True)

        self.accent_edit = QLineEdit()
        self.accent_edit.setMaxLength(7)
        self.accent_edit.setPlaceholderText(
            "Optional #RRGGBB"
        )
        self.accent_edit.setClearButtonEnabled(True)

        form.addRow("Destination URL", self.url_edit)
        form.addRow("Title", self.title_edit)
        form.addRow("Icon or emoji", self.icon_edit)
        form.addRow(
            "Website icon",
            self.website_icon_controls,
        )
        form.addRow("Description", self.description_edit)
        form.addRow("Button label", self.button_label_edit)
        form.addRow("Accent colour", self.accent_edit)
        root.addLayout(form)

        self.error_label = QLabel("")
        self.error_label.setObjectName("linkCardDialogError")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        root.addWidget(self.error_label)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        ok_button = self.buttons.button(
            QDialogButtonBox.StandardButton.Ok
        )
        ok_button.setText(
            "Save changes"
            if card is not None
            else "Add card"
        )
        self.buttons.accepted.connect(
            self._validate_and_accept
        )
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)

        if card is not None:
            self.url_edit.setText(card.url)
            self.title_edit.setText(card.title)
            self.icon_edit.setText(card.icon)
            self.description_edit.setPlainText(
                card.description
            )
            self.button_label_edit.setText(
                card.button_label
            )
            self.accent_edit.setText(card.accent)
        else:
            self.button_label_edit.setText("Open")

        self.url_edit.textChanged.connect(
            self._website_icon_url_changed
        )
        self.fetch_icon_button.clicked.connect(
            self._fetch_website_icon
        )
        self.remove_icon_button.clicked.connect(
            self._remove_cached_website_icon
        )
        self._refresh_website_icon_preview()
        self.url_edit.setFocus()

    def _website_icon_url_changed(self):
        if not self._icon_fetching:
            self.website_icon_status.setText(
                "Used automatically when Icon or emoji is blank."
            )
        self._refresh_website_icon_preview()

    def _refresh_website_icon_preview(self):
        try:
            normalized_url = normalize_web_url(
                self.url_edit.text()
            )
        except (TypeError, ValueError):
            normalized_url = ""

        path = (
            cached_favicon_path(normalized_url)
            if normalized_url
            else None
        )

        if path is not None:
            pixmap = QPixmap(str(path))

            if not pixmap.isNull():
                self.website_icon_preview.setText("")
                self.website_icon_preview.setPixmap(
                    pixmap.scaled(
                        34,
                        34,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                self.website_icon_preview.setPixmap(QPixmap())
                self.website_icon_preview.setText(
                    domain_initial(normalized_url)
                )
        else:
            self.website_icon_preview.setPixmap(QPixmap())
            self.website_icon_preview.setText(
                domain_initial(normalized_url)
                if normalized_url
                else "↗"
            )

        self.fetch_icon_button.setEnabled(
            bool(normalized_url)
            and not self._icon_fetching
        )
        self.remove_icon_button.setEnabled(
            path is not None
            and not self._icon_fetching
        )

    def _set_icon_fetching(self, fetching: bool):
        self._icon_fetching = bool(fetching)
        self.url_edit.setEnabled(not fetching)
        self.buttons.setEnabled(not fetching)
        self.fetch_icon_button.setEnabled(not fetching)
        self.remove_icon_button.setEnabled(not fetching)

        if not fetching:
            self._refresh_website_icon_preview()

    def _fetch_website_icon(self):
        if self._icon_fetching:
            return

        try:
            self._icon_fetch_url = normalize_web_url(
                self.url_edit.text()
            )
        except (TypeError, ValueError) as error:
            self.website_icon_status.setText(str(error))
            return

        self.website_icon_preview.setPixmap(QPixmap())
        self.website_icon_preview.setText("…")
        self.website_icon_status.setText(
            "Contacting the website homepage and checking its public icon…"
        )
        self._set_icon_fetching(True)

        thread = QThread()
        worker = WebsiteIconFetchWorker(
            self._icon_fetch_url
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.icon_ready.connect(
            self._website_icon_downloaded
        )
        worker.failed.connect(
            self._website_icon_failed
        )
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(
            self._website_icon_fetch_finished
        )
        self._icon_thread = thread
        self._icon_worker = worker
        thread.start()

    def _website_icon_downloaded(self, icon_bytes: bytes):
        try:
            save_favicon_bytes(
                self._icon_fetch_url,
                icon_bytes,
            )
        except (OSError, TypeError, ValueError) as error:
            self.website_icon_status.setText(
                f"Website icon could not be saved: {error}"
            )
            return

        self.website_icon_status.setText(
            "Website icon saved. It will be used when Icon or emoji is blank."
        )
        self._refresh_website_icon_preview()

    def _website_icon_failed(self, message: str):
        self.website_icon_status.setText(
            message or "No usable website icon was found."
        )

    def _website_icon_fetch_finished(self):
        self._icon_worker = None
        self._icon_thread = None
        self._set_icon_fetching(False)

    def _remove_cached_website_icon(self):
        try:
            normalized_url = normalize_web_url(
                self.url_edit.text()
            )
            removed = remove_cached_favicon(
                normalized_url
            )
        except (OSError, TypeError, ValueError) as error:
            self.website_icon_status.setText(str(error))
            return

        self.website_icon_status.setText(
            "Cached website icon removed."
            if removed
            else "No cached website icon was found."
        )
        self._refresh_website_icon_preview()

    def reject(self):
        if self._icon_fetching:
            self.website_icon_status.setText(
                "Please wait for the website icon check to finish."
            )
            return

        super().reject()

    def closeEvent(self, event):
        if self._icon_fetching:
            event.ignore()
            self.website_icon_status.setText(
                "Please wait for the website icon check to finish."
            )
            return

        super().closeEvent(event)

    def validated_card(self) -> LinkCardData:
        description = self.description_edit.toPlainText().strip()

        if len(description) > MAX_DESCRIPTION_LENGTH:
            raise ValueError("Description is too long.")

        return create_link_card(
            card_id=(
                self._editing_card.card_id
                if self._editing_card is not None
                else None
            ),
            url=self.url_edit.text(),
            title=self.title_edit.text(),
            icon=self.icon_edit.text(),
            description=description,
            button_label=self.button_label_edit.text(),
            accent=self.accent_edit.text(),
        )

    def card_data(self) -> LinkCardData | None:
        return self._result_card

    def _validate_and_accept(self):
        try:
            self._result_card = self.validated_card()
        except (TypeError, ValueError) as error:
            self.error_label.setText(str(error))
            self.error_label.show()
            return

        self.error_label.hide()
        self.accept()


class LinkCardWidget(QFrame):
    open_requested = pyqtSignal(str)

    def __init__(
        self,
        card: LinkCardData,
        parent=None,
    ):
        super().__init__(parent)

        self._card = card
        self._responsive_state = "large"
        self._theme = {}

        self.setObjectName("linkCard")
        self.setMinimumSize(1, 1)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(13, 12, 13, 12)
        self.root_layout.setSpacing(7)

        self.header_widget = QWidget(self)
        self.header_widget.setObjectName(
            "linkCardHeader"
        )
        header = QHBoxLayout(self.header_widget)
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        self.icon_label = QLabel("")
        self.icon_label.setObjectName("linkCardIcon")
        self.icon_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.icon_label.setFixedSize(34, 34)

        self.title_label = QLabel("")
        self.title_label.setObjectName("linkCardTitle")
        self.title_label.setWordWrap(True)
        self.title_label.setMinimumSize(0, 0)

        header.addWidget(self.icon_label)
        header.addWidget(self.title_label, stretch=1)

        self.domain_label = QLabel("")
        self.domain_label.setObjectName("linkCardDomain")
        self.domain_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.description_label = QLabel("")
        self.description_label.setObjectName(
            "linkCardDescription"
        )
        self.description_label.setWordWrap(True)
        self.description_label.setAlignment(
            Qt.AlignmentFlag.AlignTop
            | Qt.AlignmentFlag.AlignLeft
        )
        self.description_label.setMinimumSize(0, 0)

        self.open_button = QPushButton("")
        self.open_button.setObjectName("linkCardOpenButton")
        self.open_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.open_button.setMinimumSize(0, 0)
        self.open_button.clicked.connect(
            lambda checked=False:
            self.open_requested.emit(self._card.url)
        )

        self.root_layout.addWidget(self.header_widget)
        self.root_layout.addWidget(self.domain_label)
        self.root_layout.addWidget(
            self.description_label,
            stretch=1,
        )
        self.root_layout.addWidget(self.open_button)

        self.update_card(card)

    @property
    def card_data(self) -> LinkCardData:
        return self._card

    @property
    def responsive_state(self) -> str:
        return self._responsive_state

    def update_card(self, card: LinkCardData):
        if not isinstance(card, LinkCardData):
            raise TypeError("Expected LinkCardData.")

        self._card = card
        self._update_header_icon()
        self.title_label.setText(card.title)
        self.title_label.setToolTip(card.title)
        self.domain_label.setText(card.domain)
        self.domain_label.setToolTip(card.url)
        self.description_label.setText(card.description)
        self.description_label.setToolTip(
            card.description
        )
        self.setToolTip(card.url)

        self._apply_responsive_state()

        if self._theme:
            self.set_theme(self._theme)

    def _favicon_path(self):
        if self._card.icon:
            return None

        return cached_favicon_path(
            self._card.url
        )

    def _text_icon(self) -> str:
        return self._card.icon or domain_initial(
            self._card.url
        )

    def _update_header_icon(self):
        path = self._favicon_path()

        if path is not None:
            pixmap = QPixmap(str(path))

            if not pixmap.isNull():
                self.icon_label.setText("")
                self.icon_label.setPixmap(
                    pixmap.scaled(
                        22,
                        22,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                return

        self.icon_label.setPixmap(QPixmap())
        self.icon_label.setText(self._text_icon())

    def refresh_website_icon(self):
        self._update_header_icon()
        self._apply_responsive_state()

    def set_theme(self, theme: dict):
        self._theme = dict(theme or {})

        background = self._theme.get("card", "#18181d")
        alternate = self._theme.get(
            "card_alt",
            "#222229",
        )
        border = self._theme.get("border", "#34343e")
        text = self._theme.get("text", "#f5f5f7")
        muted = self._theme.get("muted", "#a0a0ad")
        accent = self._card.accent or self._theme.get(
            "accent",
            "#a970ff",
        )

        self.setStyleSheet(
            f"""
            QFrame#linkCard {{
                background: {background};
                border: 1px solid {accent};
                border-radius: 14px;
            }}

            QWidget#linkCardHeader {{
                background: transparent;
                border: none;
            }}

            QLabel#linkCardIcon {{
                color: {accent};
                background: {alternate};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 4px;
                font-size: 17px;
                font-weight: 700;
            }}

            QLabel#linkCardTitle {{
                color: {text};
                background: transparent;
                border: none;
                font-size: 13px;
                font-weight: 750;
            }}

            QLabel#linkCardDomain {{
                color: {accent};
                background: transparent;
                border: none;
                font-size: 9px;
                font-weight: 650;
            }}

            QLabel#linkCardDescription {{
                color: {muted};
                background: transparent;
                border: none;
                font-size: 10px;
            }}

            QPushButton#linkCardOpenButton {{
                color: {text};
                background: {alternate};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 7px 10px;
                font-size: 10px;
                font-weight: 700;
            }}

            QPushButton#linkCardOpenButton:hover {{
                border: 1px solid {accent};
            }}
            """
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_responsive_state()

    def _apply_responsive_state(self):
        width = max(1, self.width())
        height = max(1, self.height())

        if width < 135 or height < 88:
            state = "tiny"
        elif width < 220 or height < 125:
            state = "small"
        elif width < 300 or height < 180:
            state = "medium"
        else:
            state = "large"

        self._responsive_state = state
        favicon_path = self._favicon_path()
        text_icon = self._text_icon()

        if state == "tiny":
            self.root_layout.setContentsMargins(6, 6, 6, 6)
            self.root_layout.setSpacing(0)
            self.header_widget.hide()
            self.domain_label.hide()
            self.description_label.hide()

            if favicon_path is not None:
                website_icon = QIcon(str(favicon_path))
            else:
                website_icon = QIcon()

            if not website_icon.isNull():
                icon_edge = max(
                    18,
                    min(
                        64,
                        min(width, height) - 24,
                    ),
                )
                self.open_button.setText("")
                self.open_button.setIcon(website_icon)
                self.open_button.setIconSize(
                    QSize(icon_edge, icon_edge)
                )
            else:
                self.open_button.setIcon(QIcon())
                self.open_button.setText(text_icon)

            self.open_button.setToolTip(
                f"Open {self._card.title}"
            )
            self.open_button.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding,
            )
            return

        self.root_layout.setContentsMargins(13, 12, 13, 12)
        self.root_layout.setSpacing(7)
        self.header_widget.show()
        self.title_label.show()
        self._update_header_icon()
        self.open_button.setIcon(QIcon())
        self.open_button.setIconSize(QSize())
        self.open_button.setText(
            self._card.button_label or "Open"
        )
        self.open_button.setToolTip(self._card.url)
        self.open_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        if state == "small":
            self.icon_label.hide()
            self.domain_label.hide()
            self.description_label.hide()
            return

        self.icon_label.show()
        self.domain_label.show()

        if state == "medium":
            self.description_label.hide()
        else:
            self.description_label.setVisible(
                bool(self._card.description)
            )
