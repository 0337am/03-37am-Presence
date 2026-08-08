from __future__ import annotations

from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


ACTION_GET_STARTED = (
    "get_started"
)

ACTION_MEDIA_SOURCES = (
    "media_sources"
)

ACTION_DISCORD_PRESENCE = (
    "discord_presence"
)

ACTION_MEDIA_HOTKEYS = (
    "media_hotkeys"
)

WELCOME_ACTIONS = (
    ACTION_GET_STARTED,
    ACTION_MEDIA_SOURCES,
    ACTION_DISCORD_PRESENCE,
    ACTION_MEDIA_HOTKEYS,
)


FALLBACK_THEME = {
    "background": "#0b1020",
    "card": "#182139",
    "card_alt": "#202b49",
    "accent": "#6ea8ff",
    "text": "#f5f7ff",
    "muted": "#9ba9c5",
    "border": "#2d3b60",
}


class WelcomeDialog(
    QDialog
):
    """
    Small first-launch introduction.

    This widget deliberately owns no persistence and makes no
    changes to application settings. It only emits an action
    requested by the user.

    Startup wiring decides whether an action completes
    onboarding and where the main window should navigate.
    """

    action_requested = pyqtSignal(
        str
    )

    def __init__(
        self,
        *,
        theme: dict | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(
            parent
        )

        self._theme = dict(
            FALLBACK_THEME
        )

        if theme:
            self._theme.update(
                {
                    key: value
                    for key, value
                    in theme.items()
                    if key
                    in FALLBACK_THEME
                }
            )

        self.action_buttons = {}

        self.setObjectName(
            "welcomeDialog"
        )

        self.setWindowTitle(
            "Welcome to 03:37am Presence"
        )

        self.setModal(
            False
        )

        self.setMinimumSize(
            700,
            610,
        )

        self.resize(
            760,
            650,
        )

        self.setWindowFlag(
            Qt.WindowType.WindowContextHelpButtonHint,
            False,
        )

        self.build_ui()
        self.apply_theme(
            self._theme
        )

    def build_ui(
        self,
    ) -> None:
        root = QVBoxLayout(
            self
        )

        root.setContentsMargins(
            28,
            26,
            28,
            24,
        )

        root.setSpacing(
            16
        )

        eyebrow = QLabel(
            "FIRST LAUNCH"
        )

        eyebrow.setObjectName(
            "welcomeEyebrow"
        )

        eyebrow.setAccessibleName(
            "First launch"
        )

        root.addWidget(
            eyebrow
        )

        title = QLabel(
            "Welcome to 03:37am Presence"
        )

        title.setObjectName(
            "welcomeTitle"
        )

        title.setWordWrap(
            True
        )

        title.setAccessibleName(
            "Welcome to 03:37am Presence"
        )

        root.addWidget(
            title
        )

        subtitle = QLabel(
            "Bring your music activity into Discord, "
            "keep a local listening history, and add "
            "optional global playback controls."
        )

        subtitle.setObjectName(
            "welcomeSubtitle"
        )

        subtitle.setWordWrap(
            True
        )

        subtitle.setAccessibleName(
            "Welcome description"
        )

        root.addWidget(
            subtitle
        )

        privacy_note = QLabel(
            "Nothing here enables extra features behind "
            "your back. Browser sources, Windows startup "
            "and global hotkeys stay optional."
        )

        privacy_note.setObjectName(
            "welcomePrivacyNote"
        )

        privacy_note.setWordWrap(
            True
        )

        privacy_note.setAccessibleName(
            "Optional features notice"
        )

        root.addWidget(
            privacy_note
        )

        root.addSpacing(
            4
        )

        self.music_card = (
            self._make_setup_card(
                badge="01",
                title="Music sources",
                description=(
                    "Start with Spotify and Windows media. "
                    "Additional browser-source support can "
                    "be enabled later from Settings."
                ),
                button_text="Set up music",
                action=(
                    ACTION_MEDIA_SOURCES
                ),
                accessible_name=(
                    "Open music source settings"
                ),
            )
        )

        root.addWidget(
            self.music_card
        )

        self.discord_card = (
            self._make_setup_card(
                badge="02",
                title="Discord presence",
                description=(
                    "Open Discord and Presence can publish "
                    "your current music activity. Presence "
                    "modes and custom presets stay under "
                    "your control."
                ),
                button_text="Open Presence",
                action=(
                    ACTION_DISCORD_PRESENCE
                ),
                accessible_name=(
                    "Open Discord Presence page"
                ),
            )
        )

        root.addWidget(
            self.discord_card
        )

        self.hotkey_card = (
            self._make_setup_card(
                badge="03",
                title="Global media controls",
                description=(
                    "Create optional shortcuts for "
                    "play/pause, previous, next, shuffle, "
                    "repeat and seeking. Hotkeys are "
                    "disabled until you enable them."
                ),
                button_text="Set up hotkeys",
                action=(
                    ACTION_MEDIA_HOTKEYS
                ),
                accessible_name=(
                    "Open global media hotkey settings"
                ),
            )
        )

        root.addWidget(
            self.hotkey_card
        )

        root.addStretch(
            1
        )

        footer = QHBoxLayout()

        footer.setSpacing(
            10
        )

        reminder = QLabel(
            "Not ready yet? You can leave this for "
            "another launch."
        )

        reminder.setObjectName(
            "welcomeReminder"
        )

        reminder.setWordWrap(
            True
        )

        footer.addWidget(
            reminder,
            1,
        )

        self.not_now_button = (
            QPushButton(
                "Not now"
            )
        )

        self.not_now_button.setObjectName(
            "secondaryButton"
        )

        self.not_now_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.not_now_button.setAccessibleName(
            "Not now"
        )

        self.not_now_button.setToolTip(
            "Close the welcome screen without "
            "completing first-run setup."
        )

        self.not_now_button.clicked.connect(
            self.reject
        )

        footer.addWidget(
            self.not_now_button
        )

        self.get_started_button = (
            QPushButton(
                "Get started"
            )
        )

        self.get_started_button.setObjectName(
            "primaryButton"
        )

        self.get_started_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.get_started_button.setAccessibleName(
            "Get started"
        )

        self.get_started_button.setToolTip(
            "Finish the welcome experience "
            "and open the Dashboard."
        )

        self.get_started_button.clicked.connect(
            lambda _checked=False:
            self.request_action(
                ACTION_GET_STARTED
            )
        )

        self.get_started_button.setDefault(
            True
        )

        footer.addWidget(
            self.get_started_button
        )

        root.addLayout(
            footer
        )

    def _make_setup_card(
        self,
        *,
        badge: str,
        title: str,
        description: str,
        button_text: str,
        action: str,
        accessible_name: str,
    ) -> QFrame:
        card = QFrame()

        card.setObjectName(
            "welcomeSetupCard"
        )

        card.setAccessibleName(
            title
        )

        layout = QHBoxLayout(
            card
        )

        layout.setContentsMargins(
            16,
            14,
            14,
            14,
        )

        layout.setSpacing(
            14
        )

        badge_label = QLabel(
            badge
        )

        badge_label.setObjectName(
            "welcomeStepBadge"
        )

        badge_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        badge_label.setFixedSize(
            38,
            38,
        )

        badge_label.setAccessibleName(
            f"Step {badge}"
        )

        layout.addWidget(
            badge_label,
            0,
            Qt.AlignmentFlag.AlignTop,
        )

        text_column = QVBoxLayout()

        text_column.setSpacing(
            4
        )

        title_label = QLabel(
            title
        )

        title_label.setObjectName(
            "welcomeCardTitle"
        )

        text_column.addWidget(
            title_label
        )

        description_label = QLabel(
            description
        )

        description_label.setObjectName(
            "welcomeCardDescription"
        )

        description_label.setWordWrap(
            True
        )

        text_column.addWidget(
            description_label
        )

        layout.addLayout(
            text_column,
            1,
        )

        button = QPushButton(
            button_text
        )

        button.setObjectName(
            "welcomeActionButton"
        )

        button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        button.setAccessibleName(
            accessible_name
        )

        button.setMinimumWidth(
            132
        )

        button.clicked.connect(
            lambda _checked=False, target=action:
            self.request_action(
                target
            )
        )

        self.action_buttons[
            action
        ] = button

        layout.addWidget(
            button,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )

        return card

    def request_action(
        self,
        action: str,
    ) -> None:
        action = str(
            action
            or ""
        ).strip()

        if action not in WELCOME_ACTIONS:
            raise ValueError(
                "Unsupported welcome action."
            )

        self.action_requested.emit(
            action
        )

    def apply_theme(
        self,
        theme: dict,
    ) -> None:
        merged = dict(
            FALLBACK_THEME
        )

        if theme:
            merged.update(
                {
                    key: value
                    for key, value
                    in theme.items()
                    if key
                    in FALLBACK_THEME
                }
            )

        self._theme = merged

        self.setStyleSheet(
            f"""
            QDialog#welcomeDialog {{
                background: {merged["background"]};
            }}

            QLabel#welcomeEyebrow {{
                color: {merged["accent"]};
                font-size: 10px;
                font-weight: 800;
                letter-spacing: 2px;
            }}

            QLabel#welcomeTitle {{
                color: {merged["text"]};
                font-size: 27px;
                font-weight: 800;
            }}

            QLabel#welcomeSubtitle {{
                color: {merged["muted"]};
                font-size: 12px;
            }}

            QLabel#welcomePrivacyNote {{
                color: {merged["text"]};
                background: {merged["card"]};
                border: 1px solid {merged["border"]};
                border-radius: 10px;
                padding: 10px 12px;
                font-size: 10px;
            }}

            QFrame#welcomeSetupCard {{
                background: {merged["card"]};
                border: 1px solid {merged["border"]};
                border-radius: 12px;
            }}

            QFrame#welcomeSetupCard:hover {{
                border: 1px solid {merged["accent"]};
            }}

            QLabel#welcomeStepBadge {{
                color: {merged["accent"]};
                background: {merged["card_alt"]};
                border: 1px solid {merged["border"]};
                border-radius: 9px;
                font-size: 10px;
                font-weight: 800;
            }}

            QLabel#welcomeCardTitle {{
                color: {merged["text"]};
                font-size: 13px;
                font-weight: 750;
            }}

            QLabel#welcomeCardDescription {{
                color: {merged["muted"]};
                font-size: 10px;
            }}

            QLabel#welcomeReminder {{
                color: {merged["muted"]};
                font-size: 9px;
            }}

            QPushButton#welcomeActionButton,
            QPushButton#secondaryButton {{
                color: {merged["text"]};
                background: {merged["card_alt"]};
                border: 1px solid {merged["border"]};
                border-radius: 9px;
                padding: 8px 12px;
                font-size: 10px;
                font-weight: 700;
            }}

            QPushButton#welcomeActionButton:hover,
            QPushButton#secondaryButton:hover {{
                border: 1px solid {merged["accent"]};
            }}

            QPushButton#welcomeActionButton:pressed,
            QPushButton#secondaryButton:pressed {{
                background: {merged["card"]};
            }}

            QPushButton#primaryButton {{
                color: {merged["background"]};
                background: {merged["accent"]};
                border: 1px solid {merged["accent"]};
                border-radius: 9px;
                padding: 8px 14px;
                font-size: 10px;
                font-weight: 800;
            }}

            QPushButton#primaryButton:hover {{
                border: 1px solid {merged["text"]};
            }}

            QPushButton#primaryButton:pressed {{
                background: {merged["card_alt"]};
                color: {merged["text"]};
            }}
            """
        )
