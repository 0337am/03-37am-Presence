from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import (
    Qt,
    QUrl,
)
from PyQt6.QtGui import (
    QDesktopServices,
)
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


CLOUDINARY_DASHBOARD_URL = (
    "https://console.cloudinary.com/"
)

CLOUDINARY_UPLOAD_PRESETS_URL = (
    "https://console.cloudinary.com/"
    "settings/upload/presets"
)

CLOUDINARY_UPLOAD_PRESETS_DOCS_URL = (
    "https://cloudinary.com/"
    "documentation/upload_presets"
)


UrlOpener = Callable[
    [QUrl],
    bool,
]


def cloudinary_setup_checklist() -> str:
    return """03:37am Presence Cloudinary setup

1. Create or sign in to a Cloudinary account.

2. In the Cloudinary Dashboard, copy the Cloud name
   shown for the selected Product Environment.

3. Open Settings > Upload > Upload Presets.

4. Add a dedicated upload preset and set its
   signing mode to Unsigned.

5. In 03:37am Presence, enter the Cloud name and
   unsigned preset name.

6. Enable personal artwork hosting.

7. Click Test connection.

8. After the test succeeds, click
   Save artwork hosting.

Security:
- Never enter an API key.
- Never enter an API secret.
- Never enter a password or access token.
- 03:37am Presence only needs the Cloud name and
  dedicated unsigned upload preset.
"""


class CloudinarySetupGuide(QDialog):
    def __init__(
        self,
        parent=None,
        *,
        url_opener: UrlOpener | None = None,
    ):
        super().__init__(parent)

        self._url_opener = (
            url_opener
            or QDesktopServices.openUrl
        )

        self.setWindowTitle(
            "Cloudinary Setup Guide"
        )

        self.setModal(
            True
        )

        self.setMinimumSize(
            650,
            560,
        )

        self.resize(
            700,
            620,
        )

        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            18,
            18,
            18,
            18,
        )
        outer.setSpacing(
            12
        )

        title = QLabel(
            "Cloudinary Setup Guide"
        )
        title.setObjectName(
            "pageTitle"
        )

        description = QLabel(
            (
                "Cloudinary is optional. It gives "
                "03:37am Presence a public image URL "
                "for locally sourced cover artwork so "
                "Discord can display it."
            )
        )
        description.setObjectName(
            "cardDescription"
        )
        description.setWordWrap(
            True
        )

        outer.addWidget(
            title
        )
        outer.addWidget(
            description
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(
            True
        )
        scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        content = QWidget()
        content_layout = QVBoxLayout(
            content
        )
        content_layout.setContentsMargins(
            0,
            0,
            6,
            0,
        )
        content_layout.setSpacing(
            10
        )

        for number, (
            heading,
            body,
        ) in enumerate(
            self.guide_steps(),
            start=1,
        ):
            step = QFrame()
            step.setObjectName(
                "cloudinaryGuideStep"
            )

            step_layout = QVBoxLayout(
                step
            )
            step_layout.setContentsMargins(
                14,
                12,
                14,
                12,
            )
            step_layout.setSpacing(
                5
            )

            step_title = QLabel(
                f"{number}. {heading}"
            )
            step_title.setObjectName(
                "fieldLabel"
            )

            step_body = QLabel(
                body
            )
            step_body.setObjectName(
                "helpText"
            )
            step_body.setWordWrap(
                True
            )
            step_body.setTextInteractionFlags(
                Qt.TextInteractionFlag
                .TextSelectableByMouse
            )

            step_layout.addWidget(
                step_title
            )
            step_layout.addWidget(
                step_body
            )

            content_layout.addWidget(
                step
            )

        security = QFrame()
        security.setObjectName(
            "cloudinarySecurityNotice"
        )

        security_layout = QVBoxLayout(
            security
        )
        security_layout.setContentsMargins(
            14,
            12,
            14,
            12,
        )
        security_layout.setSpacing(
            5
        )

        security_title = QLabel(
            "Security rule"
        )
        security_title.setObjectName(
            "fieldLabel"
        )

        security_body = QLabel(
            (
                "Only enter the Cloud name and the "
                "name of a dedicated unsigned upload "
                "preset. Never enter an API key, API "
                "secret, password, access token, or "
                "Cloudinary credential URL."
            )
        )
        security_body.setObjectName(
            "helpText"
        )
        security_body.setWordWrap(
            True
        )
        security_body.setTextInteractionFlags(
            Qt.TextInteractionFlag
            .TextSelectableByMouse
        )

        security_layout.addWidget(
            security_title
        )
        security_layout.addWidget(
            security_body
        )

        content_layout.addWidget(
            security
        )
        content_layout.addStretch()

        scroll.setWidget(
            content
        )

        outer.addWidget(
            scroll,
            stretch=1,
        )

        self.status_label = QLabel("")
        self.status_label.setObjectName(
            "helpText"
        )
        self.status_label.setWordWrap(
            True
        )

        outer.addWidget(
            self.status_label
        )

        link_row = QHBoxLayout()
        link_row.setSpacing(
            8
        )

        dashboard_button = QPushButton(
            "Open Cloudinary Dashboard"
        )
        dashboard_button.setObjectName(
            "secondaryButton"
        )
        dashboard_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        dashboard_button.clicked.connect(
            self.open_dashboard
        )

        presets_button = QPushButton(
            "Open Upload Presets"
        )
        presets_button.setObjectName(
            "secondaryButton"
        )
        presets_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        presets_button.clicked.connect(
            self.open_upload_presets
        )

        documentation_button = QPushButton(
            "Open Cloudinary documentation"
        )
        documentation_button.setObjectName(
            "secondaryButton"
        )
        documentation_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        documentation_button.clicked.connect(
            self.open_documentation
        )

        link_row.addWidget(
            dashboard_button
        )
        link_row.addWidget(
            presets_button
        )
        link_row.addWidget(
            documentation_button
        )
        link_row.addStretch()

        outer.addLayout(
            link_row
        )

        action_row = QHBoxLayout()
        action_row.setSpacing(
            8
        )

        copy_button = QPushButton(
            "Copy setup checklist"
        )
        copy_button.setObjectName(
            "secondaryButton"
        )
        copy_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        copy_button.clicked.connect(
            self.copy_checklist
        )

        close_button = QPushButton(
            "Close"
        )
        close_button.setObjectName(
            "secondaryButton"
        )
        close_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        close_button.clicked.connect(
            self.accept
        )

        action_row.addWidget(
            copy_button
        )
        action_row.addStretch()
        action_row.addWidget(
            close_button
        )

        outer.addLayout(
            action_row
        )

    @staticmethod
    def guide_steps() -> tuple[
        tuple[str, str],
        ...,
    ]:
        return (
            (
                "Create or sign in",
                (
                    "Open the Cloudinary Console and "
                    "create an account or sign in. "
                    "Cloudinary is optional, and the "
                    "rest of the app continues to work "
                    "without it."
                ),
            ),
            (
                "Copy the Cloud name",
                (
                    "On the Cloudinary Dashboard, find "
                    "the Cloud name for the selected "
                    "Product Environment. Copy only the "
                    "Cloud name, not the API key or API "
                    "secret."
                ),
            ),
            (
                "Open Upload Presets",
                (
                    "In Cloudinary, open Settings, then "
                    "Upload, then Upload Presets. Create "
                    "a new preset dedicated to "
                    "03:37am Presence."
                ),
            ),
            (
                "Choose Unsigned",
                (
                    "Set the preset signing mode to "
                    "Unsigned and save it. Copy the "
                    "preset name exactly as Cloudinary "
                    "shows it."
                ),
            ),
            (
                "Test and save",
                (
                    "Return to the Artwork Hosting card, "
                    "enter the Cloud name and unsigned "
                    "preset, enable personal artwork "
                    "hosting, then click Test connection. "
                    "After the test succeeds, click "
                    "Save artwork hosting."
                ),
            ),
        )

    def _open_url(
        self,
        url: str,
        label: str,
    ) -> bool:
        opened = bool(
            self._url_opener(
                QUrl(url)
            )
        )

        if opened:
            self.status_label.setText(
                f"Opened {label}."
            )
        else:
            self.status_label.setText(
                f"{label} could not be opened."
            )

        return opened

    def open_dashboard(self) -> bool:
        return self._open_url(
            CLOUDINARY_DASHBOARD_URL,
            "the Cloudinary Dashboard",
        )

    def open_upload_presets(self) -> bool:
        return self._open_url(
            CLOUDINARY_UPLOAD_PRESETS_URL,
            "Cloudinary Upload Presets",
        )

    def open_documentation(self) -> bool:
        return self._open_url(
            CLOUDINARY_UPLOAD_PRESETS_DOCS_URL,
            "the Cloudinary documentation",
        )

    def copy_checklist(self) -> bool:
        clipboard = (
            QApplication.clipboard()
        )

        if clipboard is None:
            self.status_label.setText(
                "The clipboard is unavailable."
            )
            return False

        clipboard.setText(
            cloudinary_setup_checklist()
        )

        self.status_label.setText(
            "Cloudinary setup checklist copied."
        )

        return True
