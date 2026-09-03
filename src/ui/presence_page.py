from dataclasses import replace
from pathlib import Path

from PyQt6.QtCore import (
    QPoint,
    Qt,
    QUrl,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import (
    QDesktopServices,
    QPainter,
    QPalette,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QScrollArea,
    QSpinBox,
    QStyle,
    QStyleOptionSpinBox,
)

from src.discord.presence_modes import (
    DEFAULT_PARTY_CURRENT,
    DEFAULT_PARTY_MAXIMUM,
    MAX_PARTY_SIZE,
    MODE_NAMES,
    PRESENCE_IMAGE_DIRECTORY,
    PresenceMode,
    remove_mode_image,
    save_mode_image,
)

from src.discord.presence_link_buttons import (
    MAX_PRESENCE_LINK_LABEL_LENGTH,
    MAX_PRESENCE_LINK_URL_LENGTH,
    PresenceLinkButton,
    PresenceLinkButtonError,
)
from src.discord.presence_presets import (
    PresencePresetError,
    PresencePresetStore,
)
from src.ui.theme import ThemeManager


ARTWORK_MAX_BYTES = 10 * 1024 * 1024
ARTWORK_SUPPORTED_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
}


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


from src.ui.presence_library import PresenceLibraryPanel


class PartySpinBox(QSpinBox):
    """Presence Studio spin box with app-owned chevrons."""

    @staticmethod
    def _draw_chevron(
        painter: QPainter,
        rect,
        *,
        points_up: bool,
    ):
        if (
            not rect.isValid()
            or rect.width() <= 0
            or rect.height() <= 0
        ):
            return

        center = rect.center()

        x = center.x()
        y = center.y()

        if points_up:
            left = QPoint(
                x - 3,
                y + 1,
            )
            middle = QPoint(
                x,
                y - 2,
            )
            right = QPoint(
                x + 3,
                y + 1,
            )

        else:
            left = QPoint(
                x - 3,
                y - 1,
            )
            middle = QPoint(
                x,
                y + 2,
            )
            right = QPoint(
                x + 3,
                y - 1,
            )

        painter.drawLine(
            left,
            middle,
        )
        painter.drawLine(
            middle,
            right,
        )

    def paintEvent(
        self,
        event,
    ):
        super().paintEvent(
            event
        )

        option = QStyleOptionSpinBox()
        self.initStyleOption(
            option
        )

        style = self.style()

        up_rect = style.subControlRect(
            QStyle.ComplexControl.CC_SpinBox,
            option,
            QStyle.SubControl.SC_SpinBoxUp,
            self,
        )

        down_rect = style.subControlRect(
            QStyle.ComplexControl.CC_SpinBox,
            option,
            QStyle.SubControl.SC_SpinBoxDown,
            self,
        )

        chevron_color = (
            Qt.GlobalColor.white
            if self.isEnabled()
            else self.palette().color(
                QPalette.ColorRole.Mid
            ).lighter(125)
        )

        painter = QPainter(
            self
        )
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )

        pen = QPen(
            chevron_color
        )
        pen.setWidthF(
            1.45
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

        self._draw_chevron(
            painter,
            up_rect,
            points_up=True,
        )

        self._draw_chevron(
            painter,
            down_rect,
            points_up=False,
        )

        painter.end()

class PresencePage(QWidget):
    presets_changed = pyqtSignal()

    def __init__(
        self,
        controller,
        theme_manager=None,
        *,
        discord_application_store=None,
    ):
        super().__init__()

        self.setObjectName("presenceRoot")

        self.controller = controller

        self.discord_application_store = (
            discord_application_store
        )

        self._application_store_available = False
        self._loading_application_box = False

        self.theme_manager = (
            theme_manager
            or ThemeManager(self)
        )

        self.preset_store = PresencePresetStore()
        self._loading_preset_box = False

        self.image_path = ""
        self._editor_image_size = 108
        self._preview_image_size = 62

        self.build_ui()
        self.connect_signals()

        self.theme_manager.theme_changed.connect(
            self.apply_theme
        )

        self.apply_theme(
            self.theme_manager.theme()
        )

        self.load_active_mode()

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

        heading_group = QVBoxLayout()
        heading_group.setSpacing(1)

        self.page_title = QLabel("Presence")
        self.page_title.setObjectName(
            "presenceTitle"
        )

        self.page_subtitle = QLabel(
            "Choose and preview your Discord activity"
        )
        self.page_subtitle.setObjectName(
            "presenceSubtitle"
        )

        heading_group.addWidget(
            self.page_title
        )
        heading_group.addWidget(
            self.page_subtitle
        )

        self.active_badge = QLabel(
            "MUSIC"
        )
        self.active_badge.setObjectName(
            "activeBadge"
        )
        self.active_badge.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        header.addLayout(heading_group)
        header.addStretch()
        header.addWidget(
            self.active_badge,
            alignment=Qt.AlignmentFlag.AlignVCenter,
        )

        self.root_layout.addLayout(header)

        self.mode_card = QFrame()
        self.mode_card.setObjectName(
            "presenceCard"
        )

        mode_layout = QVBoxLayout(
            self.mode_card
        )
        mode_layout.setContentsMargins(
            16,
            14,
            16,
            14,
        )
        mode_layout.setSpacing(7)

        mode_header = QHBoxLayout()
        mode_header.setSpacing(10)

        mode_label = QLabel(
            "Presence mode"
        )
        mode_label.setObjectName(
            "fieldTitle"
        )

        self.mode_box = QComboBox()
        self.mode_box.setObjectName(
            "modeBox"
        )
        self.mode_box.setMinimumWidth(190)

        for mode, display_name in MODE_NAMES.items():
            self.mode_box.addItem(
                display_name,
                mode,
            )

        mode_header.addWidget(mode_label)
        mode_header.addStretch()
        mode_header.addWidget(
            self.mode_box
        )

        self.mode_help = QLabel("")
        self.mode_help.setObjectName(
            "modeHelp"
        )
        self.mode_help.setWordWrap(True)

        mode_layout.addLayout(mode_header)
        mode_layout.addWidget(
            self.mode_help
        )

        self.root_layout.addWidget(
            self.mode_card
        )

        self.presets_card = QFrame()
        self.presets_card.setObjectName(
            "presenceCard"
        )

        presets_layout = QVBoxLayout(
            self.presets_card
        )
        presets_layout.setContentsMargins(
            16,
            14,
            16,
            14,
        )
        presets_layout.setSpacing(8)

        presets_header = QHBoxLayout()
        presets_header.setSpacing(10)

        presets_label = QLabel(
            "Presence presets"
        )
        presets_label.setObjectName(
            "fieldTitle"
        )

        self.preset_box = QComboBox()
        self.preset_box.setObjectName(
            "presetBox"
        )
        self.preset_box.setMinimumWidth(220)

        presets_header.addWidget(
            presets_label
        )
        presets_header.addStretch()
        presets_header.addWidget(
            self.preset_box
        )

        presets_buttons = QHBoxLayout()
        presets_buttons.setSpacing(7)

        self.apply_preset_button = QPushButton(
            "Apply preset"
        )
        self.save_preset_button = QPushButton(
            "Save current"
        )
        self.update_preset_button = QPushButton(
            "Update"
        )
        self.duplicate_preset_button = QPushButton(
            "Duplicate"
        )
        self.rename_preset_button = QPushButton(
            "Rename"
        )
        self.pin_preset_button = QPushButton(
            "Pin"
        )
        self.delete_preset_button = QPushButton(
            "Delete"
        )

        for button in (
            self.apply_preset_button,
            self.save_preset_button,
            self.update_preset_button,
            self.duplicate_preset_button,
            self.rename_preset_button,
            self.pin_preset_button,
            self.delete_preset_button,
        ):
            button.setObjectName(
                "secondaryButton"
            )
            button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )
            presets_buttons.addWidget(
                button
            )

        self.preset_help = QLabel(
            "Save a full presence setup and apply it again later."
        )
        self.preset_help.setObjectName(
            "presetHelp"
        )
        self.preset_help.setWordWrap(True)

        presets_layout.addLayout(
            presets_header
        )
        presets_layout.addLayout(
            presets_buttons
        )
        presets_layout.addWidget(
            self.preset_help
        )

        self.root_layout.addWidget(
            self.presets_card
        )

        self.content_row = QHBoxLayout()
        self.content_row.setSpacing(12)

        self.editor_card = QFrame()
        self.editor_card.setObjectName(
            "presenceCard"
        )

        self.editor_card.setMinimumHeight(
            180
        )

        self.editor_layout = QVBoxLayout(
            self.editor_card
        )
        self.editor_layout.setContentsMargins(
            16,
            15,
            16,
            15,
        )
        self.editor_layout.setSpacing(10)

        editor_heading = QLabel(
            "Activity details"
        )
        editor_heading.setObjectName(
            "cardHeading"
        )

        title_label = QLabel("Title")
        title_label.setObjectName(
            "fieldTitle"
        )

        self.title_input = QLineEdit()
        self.title_input.setObjectName(
            "presenceInput"
        )
        self.title_input.setPlaceholderText(
            "Away right now"
        )
        self.title_input.setMaxLength(128)
        self.title_input.setMinimumHeight(
            34
        )

        message_label = QLabel("Message")
        message_label.setObjectName(
            "fieldTitle"
        )

        self.message_input = QLineEdit()
        self.message_input.setObjectName(
            "presenceInput"
        )
        self.message_input.setPlaceholderText(
            "Replies not guaranteed"
        )
        self.message_input.setMaxLength(128)
        self.message_input.setMinimumHeight(
            34
        )

        self.elapsed_box = QCheckBox(
            "Show elapsed time"
        )
        self.elapsed_box.setObjectName(
            "elapsedBox"
        )
        self.elapsed_box.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.party_editor = QWidget()
        self.party_editor.setObjectName(
            "presencePartyEditor"
        )

        party_layout = QVBoxLayout(
            self.party_editor
        )
        party_layout.setContentsMargins(
            0,
            4,
            0,
            0,
        )
        party_layout.setSpacing(8)

        party_header = QHBoxLayout()
        party_header.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        party_header.setSpacing(8)

        party_heading = QLabel(
            "PARTY / GROUP"
        )
        party_heading.setObjectName(
            "presenceStudioSectionTitle"
        )

        self.show_party_box = QCheckBox(
            "Show on Discord"
        )
        self.show_party_box.setObjectName(
            "partyBox"
        )
        self.show_party_box.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.show_party_box.setToolTip(
            "Show Discord's native party size "
            "indicator for this Custom Presence."
        )

        party_header.addWidget(
            party_heading
        )
        party_header.addStretch()
        party_header.addWidget(
            self.show_party_box
        )

        self.party_help = QLabel(
            "Choose the current and maximum group size. "
            "Turning this off keeps the saved numbers."
        )
        self.party_help.setObjectName(
            "modeHelp"
        )
        self.party_help.setWordWrap(True)

        party_members_row = QHBoxLayout()
        party_members_row.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        party_members_row.setSpacing(10)

        current_members_layout = QVBoxLayout()
        current_members_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        current_members_layout.setSpacing(5)

        current_members_label = QLabel(
            "Current members"
        )
        current_members_label.setObjectName(
            "fieldTitle"
        )

        self.party_current_spin = PartySpinBox()
        self.party_current_spin.setObjectName(
            "presencePartySpin"
        )
        self.party_current_spin.setRange(
            1,
            MAX_PARTY_SIZE,
        )
        self.party_current_spin.setValue(
            DEFAULT_PARTY_CURRENT
        )
        self.party_current_spin.setMinimumHeight(
            34
        )
        self.party_current_spin.setToolTip(
            "Current number of members in the party."
        )

        current_members_layout.addWidget(
            current_members_label
        )
        current_members_layout.addWidget(
            self.party_current_spin
        )

        maximum_members_layout = QVBoxLayout()
        maximum_members_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        maximum_members_layout.setSpacing(5)

        maximum_members_label = QLabel(
            "Maximum members"
        )
        maximum_members_label.setObjectName(
            "fieldTitle"
        )

        self.party_maximum_spin = PartySpinBox()
        self.party_maximum_spin.setObjectName(
            "presencePartySpin"
        )
        self.party_maximum_spin.setRange(
            1,
            MAX_PARTY_SIZE,
        )
        self.party_maximum_spin.setValue(
            DEFAULT_PARTY_MAXIMUM
        )
        self.party_maximum_spin.setMinimumHeight(
            34
        )
        self.party_maximum_spin.setToolTip(
            "Maximum number of members in the party."
        )

        maximum_members_layout.addWidget(
            maximum_members_label
        )
        maximum_members_layout.addWidget(
            self.party_maximum_spin
        )

        party_members_row.addLayout(
            current_members_layout,
            1,
        )
        party_members_row.addLayout(
            maximum_members_layout,
            1,
        )

        party_layout.addLayout(
            party_header
        )
        party_layout.addWidget(
            self.party_help
        )
        party_layout.addLayout(
            party_members_row
        )

        self.show_party_box.toggled.connect(
            self._update_party_editor_state
        )
        self.party_current_spin.valueChanged.connect(
            self._on_party_current_changed
        )
        self.party_maximum_spin.valueChanged.connect(
            self._on_party_maximum_changed
        )

        self.link_buttons_editor = QFrame()
        self.link_buttons_editor.setObjectName(
            "presenceStudioLinkButtonsCard"
        )

        self.link_buttons_editor.setMinimumHeight(
            286
        )

        self.link_buttons_editor.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )

        link_buttons_layout = QVBoxLayout(
            self.link_buttons_editor
        )

        link_buttons_layout.setContentsMargins(
            14,
            12,
            14,
            14,
        )

        link_buttons_layout.setSpacing(
            9
        )

        link_header = QHBoxLayout()
        link_header.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        link_header.setSpacing(
            8
        )

        link_heading = QLabel(
            "LINK BUTTONS"
        )

        link_heading.setObjectName(
            "presenceStudioSectionTitle"
        )

        self.show_link_buttons_box = QCheckBox(
            "Show on Discord"
        )

        self.show_link_buttons_box.setObjectName(
            "elapsedBox"
        )

        self.show_link_buttons_box.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.show_link_buttons_box.setToolTip(
            "Controls whether the saved link "
            "buttons are published to Discord."
        )

        link_header.addWidget(
            link_heading
        )

        link_header.addStretch()

        link_header.addWidget(
            self.show_link_buttons_box
        )

        self.link_buttons_help = QLabel(
            "Add up to two links to this Presence. "
            "Turning visibility off keeps the saved links. "
            "Discord hides your own Rich Presence buttons "
            "from you, but other users can see them."
        )

        self.link_buttons_help.setObjectName(
            "modeHelp"
        )

        self.link_buttons_help.setWordWrap(
            True
        )

        self.link_buttons_status = QLabel(
            "No buttons configured"
        )

        self.link_buttons_status.setObjectName(
            "presenceStudioLinkButtonsStatus"
        )

        self.link_buttons_status.setWordWrap(
            True
        )

        self.link_button_label_inputs = []
        self.link_button_url_inputs = []

        link_buttons_layout.addLayout(
            link_header
        )

        link_buttons_layout.addWidget(
            self.link_buttons_help
        )

        link_buttons_layout.addWidget(
            self.link_buttons_status
        )

        for button_number in (
            1,
            2,
        ):
            slot = QFrame()
            slot.setObjectName(
                "presenceStudioLinkButtonSlot"
            )

            slot.setMinimumHeight(
                88
            )

            slot_layout = QVBoxLayout(
                slot
            )

            slot_layout.setContentsMargins(
                10,
                8,
                10,
                10,
            )

            slot_layout.setSpacing(
                5
            )

            button_heading = QLabel(
                f"Button {button_number}"
            )

            button_heading.setObjectName(
                "fieldTitle"
            )

            label_input = QLineEdit()
            label_input.setObjectName(
                "presenceInput"
            )

            label_input.setPlaceholderText(
                "Button label"
            )

            label_input.setMaxLength(
                MAX_PRESENCE_LINK_LABEL_LENGTH
            )

            label_input.setMinimumHeight(
                34
            )

            label_input.setClearButtonEnabled(
                True
            )

            label_input.setToolTip(
                "Discord button label, up to "
                "32 characters."
            )

            url_input = QLineEdit()
            url_input.setObjectName(
                "presenceInput"
            )

            url_input.setPlaceholderText(
                "https://example.com"
            )

            url_input.setMaxLength(
                MAX_PRESENCE_LINK_URL_LENGTH
            )

            url_input.setMinimumHeight(
                34
            )

            url_input.setClearButtonEnabled(
                True
            )

            url_input.setToolTip(
                "HTTP or HTTPS link for this "
                "Discord Presence button."
            )

            self.link_button_label_inputs.append(
                label_input
            )

            self.link_button_url_inputs.append(
                url_input
            )

            slot_layout.addWidget(
                button_heading
            )

            slot_layout.addWidget(
                label_input
            )

            slot_layout.addWidget(
                url_input
            )

            link_buttons_layout.addWidget(
                slot
            )

        self.editor_layout.addWidget(
            editor_heading
        )
        self.editor_layout.addWidget(
            title_label
        )
        self.editor_layout.addWidget(
            self.title_input
        )
        self.editor_layout.addWidget(
            message_label
        )
        self.editor_layout.addWidget(
            self.message_input
        )
        self.editor_layout.addWidget(
            self.elapsed_box
        )
        self.editor_layout.addWidget(
            self.party_editor
        )

        self.editor_layout.addStretch()

        self.image_card = QFrame()
        self.image_card.setObjectName(
            "presenceCard"
        )

        self.image_card.setMinimumHeight(
            180
        )

        image_layout = QVBoxLayout(
            self.image_card
        )
        image_layout.setContentsMargins(
            14,
            14,
            14,
            14,
        )
        image_layout.setSpacing(8)

        image_heading = QLabel(
            "Artwork manager"
        )
        image_heading.setObjectName(
            "cardHeading"
        )

        self.image_preview = QLabel(
            "No image selected"
        )
        self.image_preview.setObjectName(
            "imagePreview"
        )
        self.image_preview.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.image_preview.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )

        self.image_name = QLabel("")
        self.image_name.setObjectName(
            "imageName"
        )
        self.image_name.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.image_name.setWordWrap(True)

        self.image_details = QLabel(
            "Choose an image to preview it here."
        )
        self.image_details.setObjectName(
            "imageDetails"
        )
        self.image_details.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.image_details.setWordWrap(True)

        artwork_hover_label = QLabel(
            "Artwork hover text"
        )
        artwork_hover_label.setObjectName(
            "fieldTitle"
        )

        self.artwork_hover_input = QLineEdit()
        self.artwork_hover_input.setObjectName(
            "presenceInput"
        )
        self.artwork_hover_input.setPlaceholderText(
            "Leave blank for no hover text"
        )
        self.artwork_hover_input.setMaxLength(
            128
        )
        self.artwork_hover_input.setToolTip(
            "Optional text shown when hovering "
            "this Presence artwork on Discord. "
            "Leave blank to show no hover text."
        )

        image_buttons = QHBoxLayout()
        image_buttons.setSpacing(7)

        self.choose_image_button = QPushButton(
            "Choose"
        )
        self.choose_image_button.setObjectName(
            "secondaryButton"
        )
        self.choose_image_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.open_image_button = QPushButton(
            "Open image"
        )
        self.open_image_button.setObjectName(
            "secondaryButton"
        )
        self.open_image_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.open_artwork_folder_button = QPushButton(
            "Open folder"
        )
        self.open_artwork_folder_button.setObjectName(
            "secondaryButton"
        )
        self.open_artwork_folder_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.remove_image_button = QPushButton(
            "Remove"
        )
        self.remove_image_button.setObjectName(
            "secondaryButton"
        )
        self.remove_image_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        image_buttons.addWidget(
            self.choose_image_button
        )
        image_buttons.addWidget(
            self.open_image_button
        )
        image_buttons.addWidget(
            self.open_artwork_folder_button
        )
        image_buttons.addWidget(
            self.remove_image_button
        )

        image_layout.addWidget(
            image_heading
        )
        image_layout.addWidget(
            self.image_preview,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        image_layout.addWidget(
            self.image_name
        )
        image_layout.addWidget(
            self.image_details
        )
        image_layout.addWidget(
            artwork_hover_label
        )
        image_layout.addWidget(
            self.artwork_hover_input
        )
        image_layout.addLayout(
            image_buttons
        )

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

        preview_header = QHBoxLayout()
        preview_header.setSpacing(8)

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
        self.preview_mode.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        preview_header.addWidget(
            preview_heading
        )
        preview_header.addStretch()
        preview_header.addWidget(
            self.preview_mode
        )

        self.preview_app = QLabel(
            "03:37am Presence"
        )
        self.preview_app.setObjectName(
            "previewApp"
        )

        activity_row = QHBoxLayout()
        activity_row.setSpacing(10)

        self.preview_image = QLabel(
            "Image"
        )
        self.preview_image.setObjectName(
            "previewImage"
        )
        self.preview_image.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.preview_image.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )

        preview_text = QVBoxLayout()
        preview_text.setSpacing(2)

        self.preview_title = QLabel(
            "Waiting for activity"
        )
        self.preview_title.setObjectName(
            "previewTitle"
        )
        self.preview_title.setWordWrap(True)

        self.preview_message = QLabel(
            "Select a presence mode"
        )
        self.preview_message.setObjectName(
            "previewMessage"
        )
        self.preview_message.setWordWrap(True)

        self.preview_timer = QLabel("")
        self.preview_timer.setObjectName(
            "previewTimer"
        )

        preview_text.addWidget(
            self.preview_title
        )
        preview_text.addWidget(
            self.preview_message
        )
        preview_text.addStretch()
        preview_text.addWidget(
            self.preview_timer
        )

        activity_row.addWidget(
            self.preview_image,
            alignment=Qt.AlignmentFlag.AlignTop,
        )
        activity_row.addLayout(
            preview_text,
            stretch=1,
        )

        preview_layout.addLayout(
            preview_header
        )
        preview_layout.addWidget(
            self.preview_app
        )
        preview_layout.addLayout(
            activity_row
        )

        self.preview_link_buttons = []

        preview_link_buttons_row = QHBoxLayout()

        preview_link_buttons_row.setSpacing(
            6
        )

        for _ in range(2):
            preview_link_button = QLabel(
                ""
            )

            preview_link_button.setObjectName(
                "previewLinkButton"
            )

            preview_link_button.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            preview_link_button.setMinimumHeight(
                30
            )

            preview_link_button.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )

            preview_link_button.setHidden(
                True
            )

            preview_link_button.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                True,
            )

            self.preview_link_buttons.append(
                preview_link_button
            )

            preview_link_buttons_row.addWidget(
                preview_link_button,
                stretch=1,
            )

        preview_layout.addLayout(
            preview_link_buttons_row
        )

        preview_layout.addStretch()

        right_column = QVBoxLayout()
        right_column.setSpacing(12)
        right_column.addWidget(
            self.image_card
        )
        right_column.addWidget(
            self.preview_card,
            stretch=1,
        )

        self.content_row.addWidget(
            self.editor_card,
            stretch=3,
        )
        self.content_row.addLayout(
            right_column,
            stretch=2,
        )

        self.root_layout.addLayout(
            self.content_row
        )

        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        self.status_label = QLabel("")
        self.status_label.setObjectName(
            "presenceStatus"
        )
        self.status_label.setWordWrap(True)

        self.reset_custom_button = QPushButton(
            "Reset Custom"
        )
        self.reset_custom_button.setObjectName(
            "secondaryButton"
        )
        self.reset_custom_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.reset_custom_button.setToolTip(
            "Clear saved Custom presence text, timer, and image."
        )

        self.music_mode_button = QPushButton(
            "Back to Music"
        )
        self.music_mode_button.setObjectName(
            "secondaryButton"
        )
        self.music_mode_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.music_mode_button.setToolTip(
            "Switch back to Music presence."
        )

        self.apply_secondary_button = QPushButton(
            "Apply as Secondary"
        )
        self.apply_secondary_button.setObjectName(
            "secondaryButton"
        )
        self.apply_secondary_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.apply_secondary_button.setToolTip(
            "Publish the current editor values as an independent Secondary Presence while Music remains primary."
        )

        self.clear_secondary_button = QPushButton(
            "Clear Secondary"
        )
        self.clear_secondary_button.setObjectName(
            "secondaryButton"
        )
        self.clear_secondary_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.clear_secondary_button.setToolTip(
            "Clear only the Secondary Presence without stopping the primary Music Presence."
        )

        self.apply_button = QPushButton(
            "Apply to Discord"
        )
        self.apply_button.setObjectName(
            "applyButton"
        )
        self.apply_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        bottom_layout.addWidget(
            self.status_label,
            stretch=1,
        )
        bottom_layout.addWidget(
            self.reset_custom_button
        )
        bottom_layout.addWidget(
            self.music_mode_button
        )
        bottom_layout.addWidget(
            self.apply_button
        )

        self.root_layout.addLayout(
            bottom_layout
        )
        self.root_layout.addStretch()

        self._install_presence_studio_shell()

    def _install_presence_studio_shell(
        self,
    ):
        self.page_title.setText(
            "Presence Studio"
        )

        self.page_subtitle.setText(
            "Create, collect, preview, and switch your Discord presence."
        )

        # The original mode and preset controls stay alive
        # underneath the Studio as compatibility engines.
        self.mode_card.setVisible(
            False
        )

        self.presets_card.setVisible(
            False
        )

        self.presence_library = PresenceLibraryPanel(
            self
        )

        self.presence_library.setMinimumWidth(
            410
        )

        self.presence_library.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        content_index = -1

        for index in range(
            self.root_layout.count()
        ):
            item = self.root_layout.itemAt(
                index
            )

            if (
                item is not None
                and item.layout()
                is self.content_row
            ):
                content_index = index
                break

        if content_index < 0:
            raise RuntimeError(
                "Presence Studio could not locate "
                "the legacy content workspace."
            )

        self.root_layout.takeAt(
            content_index
        )

        bottom_layout = None
        bottom_index = -1

        for index in range(
            self.root_layout.count()
        ):
            item = self.root_layout.itemAt(
                index
            )

            layout = (
                item.layout()
                if item is not None
                else None
            )

            if (
                layout is not None
                and layout.indexOf(
                    self.apply_button
                )
                >= 0
            ):
                bottom_layout = layout
                bottom_index = index
                break

        if (
            bottom_layout is None
            or bottom_index < 0
        ):
            raise RuntimeError(
                "Presence Studio could not locate "
                "the legacy action row."
            )

        self.root_layout.takeAt(
            bottom_index
        )

        while self.root_layout.count():
            last_index = (
                self.root_layout.count()
                - 1
            )

            last_item = (
                self.root_layout.itemAt(
                    last_index
                )
            )

            if (
                last_item is None
                or last_item.spacerItem()
                is None
            ):
                break

            self.root_layout.takeAt(
                last_index
            )

        def drain_layout(
            layout,
        ):
            while layout.count():
                item = layout.takeAt(
                    0
                )

                child_layout = (
                    item.layout()
                )

                if child_layout is not None:
                    drain_layout(
                        child_layout
                    )

        drain_layout(
            self.content_row
        )

        drain_layout(
            bottom_layout
        )

        self.studio_workspace = QFrame(
            self
        )

        self.studio_workspace.setObjectName(
            "presenceStudioWorkspace"
        )

        self.studio_workspace.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        workspace_layout = QVBoxLayout(
            self.studio_workspace
        )

        workspace_layout.setContentsMargins(
            14,
            14,
            14,
            14,
        )

        workspace_layout.setSpacing(
            10
        )

        workspace_header = QHBoxLayout()

        workspace_header.setSpacing(
            8
        )

        heading_group = QVBoxLayout()

        heading_group.setSpacing(
            2
        )

        self.studio_workspace_heading = QLabel(
            "CURRENT PRESENCE"
        )

        self.studio_workspace_heading.setObjectName(
            "presenceStudioSectionTitle"
        )

        self.studio_workspace_subtitle = QLabel(
            "Preview, edit, and publish without leaving the Studio."
        )

        self.studio_workspace_subtitle.setObjectName(
            "presenceStudioSubtitle"
        )

        self.studio_workspace_subtitle.setWordWrap(
            True
        )

        heading_group.addWidget(
            self.studio_workspace_heading
        )

        heading_group.addWidget(
            self.studio_workspace_subtitle
        )

        application_row = QHBoxLayout()
        application_row.setContentsMargins(
            0,
            7,
            0,
            0,
        )
        application_row.setSpacing(
            9
        )

        self.application_label = QLabel(
            "Discord Application"
        )
        self.application_label.setObjectName(
            "fieldTitle"
        )

        self.application_box = QComboBox()
        self.application_box.setObjectName(
            "applicationBox"
        )
        self.application_box.setMinimumWidth(
            230
        )
        self.application_box.setMaximumWidth(
            330
        )
        self.application_box.setToolTip(
            "Choose which Discord Application Library "
            "entry this Presence uses."
        )

        application_row.addWidget(
            self.application_label
        )
        application_row.addStretch()
        application_row.addWidget(
            self.application_box
        )

        heading_group.addLayout(
            application_row
        )

        self.refresh_application_box(
            ""
        )

        workspace_header.addLayout(
            heading_group
        )

        workspace_header.addStretch()

        self.studio_mode_badge = QLabel(
            "MUSIC"
        )

        self.studio_mode_badge.setObjectName(
            "presenceStudioModeBadge"
        )

        self.studio_mode_badge.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        workspace_header.addWidget(
            self.studio_mode_badge,
            alignment=Qt.AlignmentFlag.AlignTop,
        )

        workspace_layout.addLayout(
            workspace_header
        )

        self.studio_mode_rail = QFrame(
            self.studio_workspace
        )

        self.studio_mode_rail.setObjectName(
            "presenceStudioModeRail"
        )

        mode_rail_layout = QHBoxLayout(
            self.studio_mode_rail
        )

        mode_rail_layout.setContentsMargins(
            6,
            6,
            6,
            6,
        )

        mode_rail_layout.setSpacing(
            5
        )

        self.studio_mode_buttons = {}

        for mode, display_name in MODE_NAMES.items():
            button = QPushButton(
                (
                    "Off"
                    if mode == "disabled"
                    else display_name
                )
            )

            button.setObjectName(
                "presenceStudioModeButton"
            )

            button.setCheckable(
                True
            )

            button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

            button.setProperty(
                "modeKey",
                mode,
            )

            button.clicked.connect(
                lambda checked=False, key=mode:
                self.select_studio_mode(
                    key
                )
            )

            self.studio_mode_buttons[
                mode
            ] = button

            mode_rail_layout.addWidget(
                button,
                stretch=1,
            )

        workspace_layout.addWidget(
            self.studio_mode_rail
        )

        # Reuse the original explanatory label so there is
        # still one source of truth for mode descriptions.
        self.studio_mode_help = (
            self.mode_help
        )

        workspace_layout.addWidget(
            self.studio_mode_help
        )

        self.preview_card.setMinimumHeight(
            206
        )

        self.preview_card.setMaximumHeight(
            271
        )

        self.preview_card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        workspace_layout.addWidget(
            self.preview_card
        )

        self.studio_context_card = QFrame(
            self.studio_workspace
        )

        self.studio_context_card.setObjectName(
            "presenceStudioContext"
        )

        context_layout = QVBoxLayout(
            self.studio_context_card
        )

        context_layout.setContentsMargins(
            14,
            14,
            14,
            14,
        )

        context_layout.setSpacing(
            5
        )

        self.studio_context_title = QLabel(
            "AUTOMATIC MUSIC PRESENCE"
        )

        self.studio_context_title.setObjectName(
            "presenceStudioContextTitle"
        )

        self.studio_context_text = QLabel(
            "Your music presence follows the active media session automatically."
        )

        self.studio_context_text.setObjectName(
            "presenceStudioContextText"
        )

        self.studio_context_text.setWordWrap(
            True
        )

        context_layout.addWidget(
            self.studio_context_title
        )

        context_layout.addWidget(
            self.studio_context_text
        )
        self.loop_count_box = QCheckBox(
            "Show song loop count on Discord"
        )
        self.loop_count_box.setObjectName(
            "loopCountBox"
        )
        self.loop_count_box.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.loop_count_box.setToolTip(
            "Show how many times the current song has "
            "genuinely replayed in Discord Music Presence."
        )

        context_layout.addWidget(
            self.loop_count_box
        )

        self.loop_count_box.toggled.connect(
            self.update_preview
        )
        self.loop_count_box.toggled.connect(
            self.apply_music_loop_count_setting
        )


        context_layout.addStretch()

        workspace_layout.addWidget(
            self.studio_context_card,
            stretch=1,
        )

        self.studio_editor_container = QFrame(
            self.studio_workspace
        )

        self.studio_editor_container.setObjectName(
            "presenceStudioEditorContainer"
        )

        self.studio_editor_container.setMinimumHeight(
            180
        )

        editor_container_layout = QHBoxLayout(
            self.studio_editor_container
        )

        editor_container_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        editor_container_layout.setSpacing(
            10
        )

        editor_container_layout.addWidget(
            self.editor_card,
            stretch=3,
        )

        editor_container_layout.addWidget(
            self.image_card,
            stretch=2,
        )

        workspace_layout.addWidget(
            self.studio_editor_container,
            stretch=1,
        )

        self.studio_action_bar = QFrame(
            self.studio_workspace
        )

        self.studio_action_bar.setObjectName(
            "presenceStudioActionBar"
        )

        self.studio_action_bar.setMinimumHeight(
            52
        )

        action_layout = QHBoxLayout(
            self.studio_action_bar
        )

        action_layout.setContentsMargins(
            8,
            8,
            8,
            8,
        )

        action_layout.setSpacing(
            8
        )

        self.library_save_button = QPushButton(
            "Save to Library"
        )

        self.library_save_button.setObjectName(
            "secondaryButton"
        )

        self.library_save_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        action_layout.addWidget(
            self.status_label,
            stretch=1,
        )

        action_layout.addWidget(
            self.reset_custom_button
        )

        action_layout.addWidget(
            self.music_mode_button
        )

        action_layout.addWidget(
            self.library_save_button
        )

        action_layout.addWidget(
            self.apply_secondary_button
        )

        action_layout.addWidget(
            self.clear_secondary_button
        )

        action_layout.addWidget(
            self.apply_button
        )

        workspace_layout.addWidget(
            self.studio_action_bar
        )

        self.studio_row = QHBoxLayout()

        self.studio_row.setSpacing(
            14
        )

        self.studio_row.addWidget(
            self.presence_library,
            stretch=5,
        )

        self.studio_workspace_scroll = QScrollArea(
            self
        )

        self.studio_workspace_scroll.setObjectName(
            "presenceStudioWorkspaceScroll"
        )

        self.studio_workspace_scroll.setWidgetResizable(
            True
        )

        self.studio_workspace_scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        self.studio_workspace_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.studio_workspace_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self.studio_workspace_scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self.studio_workspace_scroll.setWidget(
            self.studio_workspace
        )

        self.studio_row.addWidget(
            self.studio_workspace_scroll,
            stretch=6,
        )

        self.root_layout.insertLayout(
            content_index,
            self.studio_row,
            1,
        )

        self.presence_library.preset_selected.connect(
            self.open_library_preset
        )

        self.presence_library.preset_apply_requested.connect(
            self.apply_library_preset
        )

        self.presence_library.preset_action_requested.connect(
            self.handle_library_preset_action
        )

        self.presence_library.create_requested.connect(
            self.start_new_library_presence
        )

        self.library_save_button.clicked.connect(
            self.save_current_as_preset
        )

        self._install_link_buttons_studio_card()
        self._refresh_studio_mode_controls()

    def _refresh_studio_mode_controls(
        self,
    ):
        mode = self.current_mode

        mode_buttons = getattr(
            self,
            "studio_mode_buttons",
            {},
        )

        for mode_key, button in mode_buttons.items():
            button.setChecked(
                mode_key == mode
            )

        badge = getattr(
            self,
            "studio_mode_badge",
            None,
        )

        if badge is not None:
            mode_name = MODE_NAMES.get(
                mode,
                str(mode).title(),
            )

            if mode == "disabled":
                mode_name = "Off"

            badge.setText(
                mode_name.upper()
            )

    def select_studio_mode(
        self,
        mode,
    ):
        mode = str(
            mode
            or ""
        ).strip().lower()

        index = self.mode_box.findData(
            mode
        )

        if index < 0:
            return

        self.mode_box.setCurrentIndex(
            index
        )

        self.update_editor_state()
        self.update_image_preview()
        self.update_preview()

    def _install_link_buttons_studio_card(
        self,
    ):
        link_card = getattr(
            self,
            "link_buttons_editor",
            None,
        )

        workspace = getattr(
            self,
            "studio_workspace",
            None,
        )

        action_bar = getattr(
            self,
            "studio_action_bar",
            None,
        )

        if (
            link_card is None
            or workspace is None
            or action_bar is None
        ):
            return

        workspace_layout = workspace.layout()

        if workspace_layout is None:
            return

        old_layout = getattr(
            self,
            "editor_layout",
            None,
        )

        if old_layout is not None:
            old_layout.removeWidget(
                link_card
            )

        current_index = workspace_layout.indexOf(
            link_card
        )

        if current_index >= 0:
            workspace_layout.removeWidget(
                link_card
            )

        link_card.setParent(
            workspace
        )

        action_index = workspace_layout.indexOf(
            action_bar
        )

        if action_index < 0:
            workspace_layout.addWidget(
                link_card
            )

        else:
            workspace_layout.insertWidget(
                action_index,
                link_card,
            )

    def _apply_presence_studio_scroll_theme(
        self,
        theme,
    ):
        scroll = getattr(
            self,
            "studio_workspace_scroll",
            None,
        )

        if scroll is None:
            return

        background = theme.get(
            "background",
            "#160d12",
        )

        card_alt = theme.get(
            "card_alt",
            "#351d2a",
        )

        border = theme.get(
            "border",
            "#5a3346",
        )

        accent = theme.get(
            "accent",
            "#ff6ea9",
        )

        scroll.setStyleSheet(
            f"""
            QScrollArea#presenceStudioWorkspaceScroll {{
                background: transparent;
                border: none;
            }}

            QScrollArea#presenceStudioWorkspaceScroll > QWidget > QWidget {{
                background: transparent;
            }}

            QScrollBar:vertical {{
                background: {background};
                width: 10px;
                margin: 2px 0 2px 0;
                border: 1px solid {border};
                border-radius: 5px;
            }}

            QScrollBar::handle:vertical {{
                background: {card_alt};
                min-height: 32px;
                border: 1px solid {border};
                border-radius: 4px;
            }}

            QScrollBar::handle:vertical:hover {{
                background: {accent};
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

    def _apply_presence_studio_theme(
        self,
        theme,
    ):
        workspace = getattr(
            self,
            "studio_workspace",
            None,
        )

        if workspace is None:
            return

        self._apply_presence_studio_scroll_theme(
            theme
        )

        text = theme.get(
            "text",
            "#ffffff",
        )

        muted = theme.get(
            "muted",
            "#b9aeb8",
        )

        accent = theme.get(
            "accent",
            "#ff6ea9",
        )

        card = theme.get(
            "card",
            "#2a1721",
        )

        card_alt = theme.get(
            "card_alt",
            "#351d2a",
        )

        background = theme.get(
            "background",
            "#160d12",
        )

        border = theme.get(
            "border",
            "#5a3346",
        )

        workspace.setStyleSheet(
            f"""
            QFrame#presenceStudioWorkspace {{
                background: {card};
                border: 1px solid {border};
                border-radius: 16px;
            }}

            QLabel#presenceStudioSectionTitle {{
                color: {accent};
                font-size: 10px;
                font-weight: 800;
                letter-spacing: 1.1px;
            }}

            QLabel#presenceStudioSubtitle,
            QLabel#modeHelp,
            QLabel#presenceStudioContextText {{
                color: {muted};
                font-size: 10px;
            }}

            QLabel#presenceStudioModeBadge {{
                color: {accent};
                background: {background};
                border: 1px solid {border};
                border-radius: 7px;
                padding: 4px 8px;
                font-size: 8px;
                font-weight: 800;
            }}

            QFrame#presenceStudioModeRail {{
                background: {background};
                border: 1px solid {border};
                border-radius: 10px;
            }}

            QPushButton#presenceStudioModeButton {{
                color: {muted};
                background: transparent;
                border: 1px solid transparent;
                border-radius: 7px;
                padding: 7px 6px;
                font-size: 9px;
                font-weight: 700;
            }}

            QPushButton#presenceStudioModeButton:hover {{
                color: {text};
                border-color: {border};
                background: {card_alt};
            }}

            QPushButton#presenceStudioModeButton:checked {{
                color: {background};
                background: {accent};
                border-color: {accent};
            }}

            QFrame#presenceStudioContext {{
                background: {card_alt};
                border: 1px dashed {border};
                border-radius: 12px;
            }}

            QLabel#presenceStudioContextTitle {{
                color: {text};
                font-size: 12px;
                font-weight: 750;
            }}

            QFrame#presenceStudioEditorContainer {{
                background: transparent;
                border: none;
            }}

            QFrame#presenceStudioLinkButtonsCard {{
                background: {card_alt};
                border: 1px solid {border};
                border-radius: 12px;
            }}

            QLabel#presenceStudioLinkButtonsStatus {{
                color: {accent};
                font-size: 10px;
                font-weight: 650;
            }}

            QFrame#presenceStudioLinkButtonSlot {{
                background: {background};
                border: 1px solid {border};
                border-radius: 10px;
            }}

            QFrame#presenceStudioActionBar {{
                background: {card_alt};
                border: 1px solid {border};
                border-radius: 11px;
            }}
            """
        )

    def refresh_presence_library(
        self,
        selected_id="",
    ):
        library = getattr(
            self,
            "presence_library",
            None,
        )

        if library is None:
            return

        selection = str(
            selected_id
            or self.selected_preset_id()
            or ""
        ).strip()

        library.set_presets(
            self.preset_store.load(),
            selected_id=selection,
        )

    def _select_library_preset_in_engine(
        self,
        preset_id,
    ) -> bool:
        preset_id = str(
            preset_id
            or ""
        ).strip()

        index = self.preset_box.findData(
            preset_id
        )

        if index < 0:
            return False

        self.preset_box.blockSignals(
            True
        )

        self.preset_box.setCurrentIndex(
            index
        )

        self.preset_box.blockSignals(
            False
        )

        self.update_preset_buttons()

        library = getattr(
            self,
            "presence_library",
            None,
        )

        if library is not None:
            library.set_selected_id(
                preset_id
            )

        return True

    def open_library_preset(
        self,
        preset_id,
    ):
        if not self._select_library_preset_in_engine(
            preset_id
        ):
            self.refresh_presence_library()
            return

        preset = self.selected_preset()

        if preset is None:
            return

        presence_mode = preset.to_presence_mode()

        self._sync_application_box_from_mode(
            presence_mode
        )

        index = self.mode_box.findData(
            presence_mode.mode
        )

        if index >= 0:
            self.mode_box.blockSignals(
                True
            )

            self.mode_box.setCurrentIndex(
                index
            )

            self.mode_box.blockSignals(
                False
            )

        self.title_input.blockSignals(
            True
        )

        self.message_input.blockSignals(
            True
        )

        self.elapsed_box.blockSignals(
            True
        )
        _loop_count_box = getattr(
            self,
            "loop_count_box",
            None,
        )
        if _loop_count_box is not None:
            _loop_count_box.blockSignals(
                True
            )

        self.title_input.setText(
            presence_mode.title
        )

        self.message_input.setText(
            presence_mode.message
        )

        self.elapsed_box.setChecked(
            presence_mode.show_elapsed
        )
        _loop_count_box = getattr(
            self,
            "loop_count_box",
            None,
        )
        if _loop_count_box is not None:
            _loop_count_box.setChecked(
                presence_mode.show_loop_count
            )

        self.title_input.blockSignals(
            False
        )

        self.message_input.blockSignals(
            False
        )

        self.elapsed_box.blockSignals(
            False
        )
        _loop_count_box = getattr(
            self,
            "loop_count_box",
            None,
        )
        if _loop_count_box is not None:
            _loop_count_box.blockSignals(
                False
            )

        self._load_artwork_hover_editor(
            presence_mode
        )

        self._load_link_button_editor(
            presence_mode
        )
        self._load_party_editor(
            presence_mode
        )

        self.image_path = (
            presence_mode.image_path
        )

        self.update_editor_state()
        self.update_image_preview()
        self.update_preview()

        self.status_label.setText(
            f"Opened from Library: {preset.name}"
        )

    def apply_library_preset(
        self,
        preset_id,
    ):
        if not self._select_library_preset_in_engine(
            preset_id
        ):
            self.refresh_presence_library()
            return

        self.apply_selected_preset()

        self.refresh_presence_library(
            preset_id
        )

    def handle_library_preset_action(
        self,
        preset_id,
        action,
    ):
        preset_id = str(
            preset_id
            or ""
        ).strip()

        action = str(
            action
            or ""
        ).strip().lower()

        if not preset_id:
            return

        if action == "edit":
            self.open_library_preset(
                preset_id
            )
            return

        if not self._select_library_preset_in_engine(
            preset_id
        ):
            self.refresh_presence_library()
            return

        if action == "rename":
            self.rename_selected_preset()

        elif action == "duplicate":
            self.duplicate_selected_preset()

        elif action == "pin":
            self.toggle_selected_preset_pin()

        elif action == "delete":
            self.delete_selected_preset()

    def start_new_library_presence(
        self,
    ):
        no_preset_index = (
            self.preset_box.findData(
                ""
            )
        )

        if no_preset_index >= 0:
            self.preset_box.blockSignals(
                True
            )

            self.preset_box.setCurrentIndex(
                no_preset_index
            )

            self.preset_box.blockSignals(
                False
            )

        custom_index = (
            self.mode_box.findData(
                "custom"
            )
        )

        if custom_index >= 0:
            self.mode_box.blockSignals(
                True
            )

            self.mode_box.setCurrentIndex(
                custom_index
            )

            self.mode_box.blockSignals(
                False
            )

        self.title_input.blockSignals(
            True
        )

        self.message_input.blockSignals(
            True
        )

        self.elapsed_box.blockSignals(
            True
        )
        _loop_count_box = getattr(
            self,
            "loop_count_box",
            None,
        )
        if _loop_count_box is not None:
            _loop_count_box.blockSignals(
                True
            )

        self.title_input.clear()
        self.message_input.clear()
        self.artwork_hover_input.clear()

        self.elapsed_box.setChecked(
            False
        )
        _loop_count_box = getattr(
            self,
            "loop_count_box",
            None,
        )
        if _loop_count_box is not None:
            _loop_count_box.setChecked(
                False
            )

        self._load_party_editor(
            PresenceMode(
                mode="custom"
            )
        )

        self.title_input.blockSignals(
            False
        )

        self.message_input.blockSignals(
            False
        )

        self.elapsed_box.blockSignals(
            False
        )
        _loop_count_box = getattr(
            self,
            "loop_count_box",
            None,
        )
        if _loop_count_box is not None:
            _loop_count_box.blockSignals(
                False
            )

        self._clear_link_button_editor()

        self.image_path = ""

        self.update_preset_buttons()
        self.update_editor_state()
        self.update_image_preview()
        self.update_preview()

        library = getattr(
            self,
            "presence_library",
            None,
        )

        if library is not None:
            library.set_selected_id(
                ""
            )

        self.status_label.setText(
            "New Presence draft ready. "
            "Edit it, then choose Save to Library."
        )

    def connect_signals(self):
        self.mode_box.currentIndexChanged.connect(
            self.on_mode_changed
        )

        self.preset_box.currentIndexChanged.connect(
            self.on_preset_changed
        )
        self.apply_preset_button.clicked.connect(
            self.apply_selected_preset
        )
        self.save_preset_button.clicked.connect(
            self.save_current_as_preset
        )
        self.update_preset_button.clicked.connect(
            self.update_selected_preset
        )
        self.duplicate_preset_button.clicked.connect(
            self.duplicate_selected_preset
        )
        self.rename_preset_button.clicked.connect(
            self.rename_selected_preset
        )
        self.pin_preset_button.clicked.connect(
            self.toggle_selected_preset_pin
        )
        self.delete_preset_button.clicked.connect(
            self.delete_selected_preset
        )

        self.title_input.textChanged.connect(
            self.update_preview
        )
        self.message_input.textChanged.connect(
            self.update_preview
        )
        self.artwork_hover_input.textChanged.connect(
            self.update_preview
        )
        self.elapsed_box.toggled.connect(
            self.update_preview
        )

        self.show_link_buttons_box.toggled.connect(
            self.update_preview
        )

        for link_input in (
            self.link_button_label_inputs
            + self.link_button_url_inputs
        ):
            link_input.textChanged.connect(
                self.update_preview
            )

        self.choose_image_button.clicked.connect(
            self.choose_image
        )
        self.open_image_button.clicked.connect(
            self.open_selected_image
        )
        self.open_artwork_folder_button.clicked.connect(
            self.open_artwork_folder
        )
        self.remove_image_button.clicked.connect(
            self.remove_image
        )
        self.reset_custom_button.clicked.connect(
            self.reset_custom_presence
        )
        self.music_mode_button.clicked.connect(
            self.switch_to_music_presence
        )
        self.apply_secondary_button.clicked.connect(
            self.apply_secondary_presence
        )

        self.clear_secondary_button.clicked.connect(
            self.clear_secondary_presence
        )

        self.apply_button.clicked.connect(
            self.apply_presence
        )

        self.application_box.currentIndexChanged.connect(
            self._on_application_changed
        )

        self.controller.secondary_mode_changed.connect(
            self._refresh_secondary_controls
        )

        self.theme_manager.branding_changed.connect(
            self.apply_branding
        )

        self.apply_branding(
            self.theme_manager.branding()
        )

    def refresh_preset_box(
        self,
        select_id: str = "",
    ):
        previous_id = (
            select_id
            or self.selected_preset_id()
        )

        presets = self.preset_store.load()
        presets = sorted(
            presets,
            key=lambda preset: (
                not preset.pinned,
                preset.name.lower(),
            ),
        )

        self._loading_preset_box = True
        self.preset_box.blockSignals(True)
        self.preset_box.clear()
        self.preset_box.addItem(
            "No preset selected",
            "",
        )

        for preset in presets:
            prefix = "? " if preset.pinned else ""
            self.preset_box.addItem(
                f"{prefix}{preset.name}",
                preset.preset_id,
            )

        index = self.preset_box.findData(
            previous_id
        )

        if index < 0:
            index = 0

        self.preset_box.setCurrentIndex(
            index
        )
        self.preset_box.blockSignals(False)
        self._loading_preset_box = False

        self.update_preset_buttons()

        self.refresh_presence_library(
            self.selected_preset_id()
        )

    def selected_preset_id(self) -> str:
        if not hasattr(
            self,
            "preset_box",
        ):
            return ""

        return str(
            self.preset_box.currentData()
            or ""
        )

    def selected_preset(self):
        preset_id = self.selected_preset_id()

        if not preset_id:
            return None

        return self.preset_store.get(
            preset_id
        )

    def _editor_presence_buttons(
        self,
    ) -> tuple[PresenceLinkButton, ...]:
        buttons = []

        for index, (
            label_input,
            url_input,
        ) in enumerate(
            zip(
                self.link_button_label_inputs,
                self.link_button_url_inputs,
            ),
            start=1,
        ):
            label = (
                label_input.text().strip()
            )
            url = (
                url_input.text().strip()
            )

            if not label and not url:
                continue

            if not label or not url:
                raise PresenceLinkButtonError(
                    f"Button {index} needs both "
                    "a label and a URL."
                )

            try:
                button = PresenceLinkButton(
                    label=label,
                    url=url,
                ).normalized()

            except PresenceLinkButtonError as error:
                raise PresenceLinkButtonError(
                    f"Button {index}: {error}"
                ) from error

            buttons.append(
                button
            )

        return tuple(
            buttons
        )

    def _load_link_button_editor(
        self,
        presence_mode: PresenceMode,
    ):
        controls = [
            self.show_link_buttons_box,
            *self.link_button_label_inputs,
            *self.link_button_url_inputs,
        ]

        for control in controls:
            control.blockSignals(
                True
            )

        try:
            self.show_link_buttons_box.setChecked(
                bool(
                    presence_mode.show_buttons
                )
            )

            for input_widget in (
                self.link_button_label_inputs
                + self.link_button_url_inputs
            ):
                input_widget.clear()

            buttons = (
                presence_mode.normalized_buttons()
            )

            for index, button in enumerate(
                buttons[:2]
            ):
                self.link_button_label_inputs[
                    index
                ].setText(
                    button.label
                )

                self.link_button_url_inputs[
                    index
                ].setText(
                    button.url
                )

        finally:
            for control in controls:
                control.blockSignals(
                    False
                )

    def _clear_link_button_editor(
        self,
    ):
        controls = [
            self.show_link_buttons_box,
            *self.link_button_label_inputs,
            *self.link_button_url_inputs,
        ]

        for control in controls:
            control.blockSignals(
                True
            )

        try:
            self.show_link_buttons_box.setChecked(
                False
            )

            for input_widget in (
                self.link_button_label_inputs
                + self.link_button_url_inputs
            ):
                input_widget.clear()

        finally:
            for control in controls:
                control.blockSignals(
                    False
                )

    def apply_music_loop_count_setting(
        self,
        checked: bool,
    ):
        if self.current_mode != "music":
            return

        self.controller.set_music_loop_count_enabled(
            bool(checked)
        )

    def _load_party_editor(
        self,
        presence_mode: PresenceMode,
    ):
        party_box = getattr(
            self,
            "show_party_box",
            None,
        )
        current_spin = getattr(
            self,
            "party_current_spin",
            None,
        )
        maximum_spin = getattr(
            self,
            "party_maximum_spin",
            None,
        )

        if (
            party_box is None
            or current_spin is None
            or maximum_spin is None
        ):
            return

        current, maximum = (
            presence_mode.normalized_party_size()
        )

        party_box.blockSignals(True)
        current_spin.blockSignals(True)
        maximum_spin.blockSignals(True)

        party_box.setChecked(
            presence_mode.party_enabled()
        )
        current_spin.setValue(
            current
        )
        maximum_spin.setValue(
            maximum
        )

        party_box.blockSignals(False)
        current_spin.blockSignals(False)
        maximum_spin.blockSignals(False)

        self._update_party_editor_state()

    def _update_party_editor_state(
        self,
        *_,
    ):
        party_editor = getattr(
            self,
            "party_editor",
            None,
        )
        party_box = getattr(
            self,
            "show_party_box",
            None,
        )
        current_spin = getattr(
            self,
            "party_current_spin",
            None,
        )
        maximum_spin = getattr(
            self,
            "party_maximum_spin",
            None,
        )

        if (
            party_editor is None
            or party_box is None
            or current_spin is None
            or maximum_spin is None
        ):
            return

        custom_mode = (
            self.current_mode == "custom"
        )

        numbers_enabled = bool(
            custom_mode
            and party_box.isChecked()
        )

        party_editor.setVisible(
            custom_mode
        )
        party_box.setEnabled(
            custom_mode
        )
        current_spin.setEnabled(
            numbers_enabled
        )
        maximum_spin.setEnabled(
            numbers_enabled
        )

    def _on_party_current_changed(
        self,
        value: int,
    ):
        maximum_spin = getattr(
            self,
            "party_maximum_spin",
            None,
        )

        if maximum_spin is None:
            return

        if maximum_spin.value() < int(value):
            maximum_spin.setValue(
                int(value)
            )

    def _on_party_maximum_changed(
        self,
        value: int,
    ):
        current_spin = getattr(
            self,
            "party_current_spin",
            None,
        )

        if current_spin is None:
            return

        if current_spin.value() > int(value):
            current_spin.setValue(
                int(value)
            )

    def _load_artwork_hover_editor(
        self,
        presence_mode,
    ):
        hover_input = getattr(
            self,
            "artwork_hover_input",
            None,
        )

        if hover_input is None:
            return

        hover_input.blockSignals(
            True
        )

        try:
            hover_input.setText(
                str(
                    getattr(
                        presence_mode,
                        "artwork_hover_text",
                        "",
                    )
                    or ""
                )
            )

        finally:
            hover_input.blockSignals(
                False
            )

    def current_editor_presence_mode(
        self,
    ) -> PresenceMode:
        mode = self.current_mode

        if mode == "disabled":
            show_buttons = False
            buttons = ()

        else:
            show_buttons = (
                self.show_link_buttons_box.isChecked()
            )

            buttons = (
                self._editor_presence_buttons()
            )

        loop_count_box = getattr(
            self,
            "loop_count_box",
            None,
        )

        show_loop_count = bool(
            mode == "music"
            and loop_count_box is not None
            and loop_count_box.isChecked()
        )

        party_box = getattr(
            self,
            "show_party_box",
            None,
        )
        party_current_spin = getattr(
            self,
            "party_current_spin",
            None,
        )
        party_maximum_spin = getattr(
            self,
            "party_maximum_spin",
            None,
        )

        show_party = bool(
            mode == "custom"
            and party_box is not None
            and party_box.isChecked()
        )

        party_current = (
            party_current_spin.value()
            if party_current_spin is not None
            else DEFAULT_PARTY_CURRENT
        )

        party_maximum = (
            party_maximum_spin.value()
            if party_maximum_spin is not None
            else DEFAULT_PARTY_MAXIMUM
        )

        current_application_entry_id = getattr(
            self,
            "current_application_entry_id",
            None,
        )

        application_entry_id = None

        if callable(
            current_application_entry_id
        ):
            try:
                application_entry_id = (
                    current_application_entry_id()
                )

            except Exception:
                application_entry_id = None

        artwork_hover_text = ""

        artwork_hover_input = getattr(
            self,
            "artwork_hover_input",
            None,
        )

        if artwork_hover_input is not None:
            hover_text_getter = getattr(
                artwork_hover_input,
                "text",
                None,
            )

            if callable(
                hover_text_getter
            ):
                try:
                    artwork_hover_text = str(
                        hover_text_getter()
                        or ""
                    ).strip()

                except Exception:
                    artwork_hover_text = ""

        if (
            mode == "music"
            or mode == "disabled"
        ):
            artwork_hover_text = ""

        return PresenceMode(
            mode=mode,
            application_entry_id=application_entry_id,
            title=self.title_input.text().strip(),
            message=self.message_input.text().strip(),
            image_path=self.image_path,
            artwork_hover_text=(
                artwork_hover_text
            ),
            show_elapsed=(
                self.elapsed_box.isChecked()
            ),
            show_buttons=show_buttons,
            buttons=buttons,
            show_loop_count=show_loop_count,
            show_party=show_party,
            party_current=party_current,
            party_maximum=party_maximum,
        )

    def on_preset_changed(self, *_):
        if self._loading_preset_box:
            return

        self.update_preset_buttons()

    def update_preset_buttons(self):
        preset = self.selected_preset()
        has_preset = preset is not None

        for button in (
            self.apply_preset_button,
            self.update_preset_button,
            self.duplicate_preset_button,
            self.rename_preset_button,
            self.pin_preset_button,
            self.delete_preset_button,
        ):
            button.setEnabled(
                has_preset
            )

        self.save_preset_button.setEnabled(
            True
        )

        if preset is None:
            self.pin_preset_button.setText(
                "Pin"
            )
            preset_count = max(
                self.preset_box.count() - 1,
                0,
            )
            if preset_count:
                self.preset_help.setText(
                    "Choose a saved preset or save the current setup."
                )
            else:
                self.preset_help.setText(
                    "No presets yet. Use Save current to create one."
                )
            return

        self.pin_preset_button.setText(
            "Unpin" if preset.pinned else "Pin"
        )
        self.preset_help.setText(
            f"Selected: {preset.name} ({MODE_NAMES.get(preset.mode, preset.mode)})"
        )

    def save_current_as_preset(self):
        mode_name = MODE_NAMES.get(
            self.current_mode,
            self.current_mode.title(),
        )
        default_name = (
            self.title_input.text().strip()
            or mode_name
        )

        name, accepted = QInputDialog.getText(
            self,
            "Save presence preset",
            "Preset name:",
            text=default_name,
        )

        if not accepted:
            return

        name = name.strip()

        if not name:
            self.status_label.setText(
                "Preset name cannot be empty."
            )
            return

        try:
            presence_mode = (
                self.current_editor_presence_mode()
            )
            preset = self.preset_store.create(
                name=name,
                presence_mode=presence_mode,
            )

            copied_image_path = (
                self.preset_store.copy_image_for_preset(
                    presence_mode.image_path,
                    preset.preset_id,
                )
            )

            if copied_image_path:
                preset = self.preset_store.upsert(
                    replace(
                        preset,
                        image_path=copied_image_path,
                    )
                )

            self.refresh_preset_box(
                preset.preset_id
            )
            self.presets_changed.emit()
            self.status_label.setText(
                f"Preset saved: {preset.name}"
            )

        except (
            PresencePresetError,
            PresenceLinkButtonError,
        ) as error:
            self.status_label.setText(
                str(error)
            )

    def apply_selected_preset(self):
        preset = self.selected_preset()

        if preset is None:
            return

        presence_mode = preset.to_presence_mode()

        self._sync_application_box_from_mode(
            presence_mode
        )

        index = self.mode_box.findData(
            presence_mode.mode
        )

        if index >= 0:
            self.mode_box.blockSignals(True)
            self.mode_box.setCurrentIndex(
                index
            )
            self.mode_box.blockSignals(False)

        self.title_input.blockSignals(True)
        self.message_input.blockSignals(True)
        self.elapsed_box.blockSignals(True)
        _loop_count_box = getattr(
            self,
            "loop_count_box",
            None,
        )
        if _loop_count_box is not None:
            _loop_count_box.blockSignals(True)

        self.title_input.setText(
            presence_mode.title
        )
        self.message_input.setText(
            presence_mode.message
        )
        self.elapsed_box.setChecked(
            presence_mode.show_elapsed
        )
        _loop_count_box = getattr(
            self,
            "loop_count_box",
            None,
        )
        if _loop_count_box is not None:
            _loop_count_box.setChecked(
                presence_mode.show_loop_count
            )

        self.title_input.blockSignals(False)
        self.message_input.blockSignals(False)
        self.elapsed_box.blockSignals(False)
        _loop_count_box = getattr(
            self,
            "loop_count_box",
            None,
        )
        if _loop_count_box is not None:
            _loop_count_box.blockSignals(False)

        self._load_artwork_hover_editor(
            presence_mode
        )

        self._load_link_button_editor(
            presence_mode
        )
        self._load_party_editor(
            presence_mode
        )

        self.image_path = presence_mode.image_path

        self.update_editor_state()
        self.update_image_preview()
        self.update_preview()

        self.controller.apply_mode(
            presence_mode
        )

        self.status_label.setText(
            f"Preset applied: {preset.name}"
        )

    def update_selected_preset(self):
        preset = self.selected_preset()

        if preset is None:
            return

        answer = QMessageBox.question(
            self,
            "Update presence preset",
            f"Replace '{preset.name}' with the current editor values?",
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            presence_mode = (
                self.current_editor_presence_mode()
            )
            copied_image_path = (
                self.preset_store.copy_image_for_preset(
                    presence_mode.image_path,
                    preset.preset_id,
                )
            )

            if copied_image_path:
                presence_mode.image_path = copied_image_path

            updated = self.preset_store.update_from_mode(
                preset.preset_id,
                name=preset.name,
                presence_mode=presence_mode,
                pinned=preset.pinned,
            )

            self.refresh_preset_box(
                updated.preset_id
            )
            self.presets_changed.emit()
            self.status_label.setText(
                f"Preset updated: {updated.name}"
            )

        except (
            PresencePresetError,
            PresenceLinkButtonError,
        ) as error:
            self.status_label.setText(
                str(error)
            )

    def rename_selected_preset(self):
        preset = self.selected_preset()

        if preset is None:
            return

        name, accepted = QInputDialog.getText(
            self,
            "Rename presence preset",
            "Preset name:",
            text=preset.name,
        )

        if not accepted:
            return

        name = name.strip()

        if not name:
            self.status_label.setText(
                "Preset name cannot be empty."
            )
            return

        try:
            updated = self.preset_store.upsert(
                replace(
                    preset,
                    name=name,
                )
            )
            self.refresh_preset_box(
                updated.preset_id
            )
            self.presets_changed.emit()
            self.status_label.setText(
                f"Preset renamed: {updated.name}"
            )

        except PresencePresetError as error:
            self.status_label.setText(
                str(error)
            )

    def duplicate_selected_preset(self):
        preset = self.selected_preset()

        if preset is None:
            return

        try:
            duplicate = self.preset_store.duplicate(
                preset.preset_id
            )
            self.refresh_preset_box(
                duplicate.preset_id
            )
            self.presets_changed.emit()
            self.status_label.setText(
                f"Preset duplicated: {duplicate.name}"
            )

        except PresencePresetError as error:
            self.status_label.setText(
                str(error)
            )

    def toggle_selected_preset_pin(self):
        preset = self.selected_preset()

        if preset is None:
            return

        try:
            updated = self.preset_store.set_pinned(
                preset.preset_id,
                not preset.pinned,
            )
            self.refresh_preset_box(
                updated.preset_id
            )
            self.presets_changed.emit()
            state = (
                "Pinned"
                if updated.pinned
                else "Unpinned"
            )
            self.status_label.setText(
                f"{state}: {updated.name}"
            )

        except PresencePresetError as error:
            self.status_label.setText(
                str(error)
            )

    def delete_selected_preset(self):
        preset = self.selected_preset()

        if preset is None:
            return

        answer = QMessageBox.question(
            self,
            "Delete presence preset",
            f"Delete '{preset.name}'?",
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        if self.preset_store.delete(
            preset.preset_id
        ):
            self.refresh_preset_box()
            self.presets_changed.emit()
            self.status_label.setText(
                f"Preset deleted: {preset.name}"
            )

    @pyqtSlot(dict)
    def apply_theme(self, theme: dict):
        library = getattr(
            self,
            "presence_library",
            None,
        )

        if library is not None:
            library.apply_theme(
                theme
            )

        self._apply_presence_studio_theme(
            theme
        )

        compact = theme.get(
            "compact",
            True,
        )

        self._editor_image_size = (
            100 if compact else 120
        )

        self._preview_image_size = (
            56 if compact else 68
        )

        margin = 18 if compact else 24
        spacing = 10 if compact else 14
        title_size = 23 if compact else 27
        input_padding = 8 if compact else 10

        self.root_layout.setContentsMargins(
            margin,
            margin,
            margin,
            margin,
        )

        self.root_layout.setSpacing(
            spacing
        )

        self.image_preview.setFixedSize(
            self._editor_image_size,
            self._editor_image_size,
        )

        self.preview_image.setFixedSize(
            self._preview_image_size,
            self._preview_image_size,
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

        self.setStyleSheet(
            f"""
            QWidget#presenceRoot {{
                background: {page_background};
            }}

            QLabel#presenceTitle {{
                color: {theme["text"]};
                font-size: {title_size}px;
                font-weight: 700;
            }}

            QLabel#presenceSubtitle {{
                color: {theme["muted"]};
                font-size: 11px;
            }}

            QLabel#activeBadge {{
                color: {theme["accent"]};
                background: {card_alt_glass};
                border: 1px solid {theme["border"]};
                border-radius: 9px;
                padding: 5px 10px;
                font-size: 10px;
                font-weight: 700;
            }}

            QFrame#presenceCard,
            QFrame#previewCard {{
                background: {card_glass};
                border: 1px solid {theme["border"]};
                border-radius: 14px;
            }}

            QLabel#cardHeading {{
                color: {theme["accent"]};
                font-size: 11px;
                font-weight: 700;
            }}

            QLabel#fieldTitle {{
                color: {theme["text"]};
                font-size: 11px;
                font-weight: 650;
            }}

            QLabel#modeHelp,
            QLabel#presetHelp,
            QLabel#imageName,
            QLabel#imageDetails,
            QLabel#presenceStatus {{
                color: {theme["muted"]};
                font-size: 10px;
            }}

            QLabel#imagePreview,
            QLabel#previewImage {{
                color: {theme["muted"]};
                background: {theme["background"]};
                border: 1px solid {theme["border"]};
                border-radius: 10px;
            }}

            QComboBox#modeBox,
            QComboBox#presetBox,
            QComboBox#applicationBox,
            QLineEdit#presenceInput {{
                color: {theme["text"]};
                background: {card_alt_glass};
                border: 1px solid {theme["border"]};
                border-radius: 9px;
                padding: {input_padding}px 10px;
                selection-background-color: {theme["accent"]};
            }}

            QComboBox#modeBox,
            QComboBox#presetBox,
            QComboBox#applicationBox {{
                font-size: 9pt;
            }}

            QLineEdit#presenceInput {{
                font-size: 11px;
            }}

            QComboBox#modeBox:hover,
            QComboBox#modeBox:focus,
            QComboBox#presetBox:hover,
            QComboBox#presetBox:focus,
            QComboBox#applicationBox:hover,
            QComboBox#applicationBox:focus,
            QLineEdit#presenceInput:hover,
            QLineEdit#presenceInput:focus {{
                border: 1px solid {theme["accent"]};
            }}

            QComboBox#modeBox::drop-down,
            QComboBox#presetBox::drop-down,
            QComboBox#applicationBox::drop-down {{
                border: none;
                width: 22px;
            }}

            QComboBox QAbstractItemView {{
                color: {theme["text"]};
                background: {card_glass};
                border: 1px solid {theme["border"]};
                selection-color: {theme["text"]};
                selection-background-color: {theme["accent"]};
                outline: none;
            }}

            QCheckBox#elapsedBox,
            QCheckBox#loopCountBox,
            QCheckBox#partyBox {{
                color: {theme["text"]};
                spacing: 8px;
                font-size: 11px;
                padding-top: 3px;
            }}

            QCheckBox#elapsedBox::indicator,
            QCheckBox#loopCountBox::indicator,
            QCheckBox#partyBox::indicator {{
                width: 16px;
                height: 16px;
                background: {theme["background"]};
                border: 1px solid {theme["border"]};
                border-radius: 4px;
            }}

            QCheckBox#elapsedBox::indicator:hover,
            QCheckBox#loopCountBox::indicator:hover,
            QCheckBox#partyBox::indicator:hover {{
                border: 1px solid {theme["accent"]};
            }}

            QCheckBox#elapsedBox::indicator:checked,
            QCheckBox#loopCountBox::indicator:checked,
            QCheckBox#partyBox::indicator:checked {{
                background: {theme["accent"]};
                border: 1px solid {theme["accent"]};
            }}

            QSpinBox#presencePartySpin {{
                color: {theme["text"]};
                background: {card_alt_glass};
                border: 1px solid {theme["border"]};
                border-radius: 9px;
                padding: {input_padding}px 27px {input_padding}px 8px;
                font-size: 11px;
                selection-background-color: {theme["accent"]};
            }}

            QSpinBox#presencePartySpin:hover,
            QSpinBox#presencePartySpin:focus {{
                border: 1px solid {theme["accent"]};
            }}

            QSpinBox#presencePartySpin:disabled {{
                color: {theme["muted"]};
                background: {theme["background"]};
                border-color: {theme["border"]};
            }}

            QSpinBox#presencePartySpin::up-button {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid {theme["border"]};
                border-bottom: 1px solid {theme["border"]};
                border-top-right-radius: 8px;
                background: rgba(255, 255, 255, 0.03);
            }}

            QSpinBox#presencePartySpin::down-button {{
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 20px;
                border-left: 1px solid {theme["border"]};
                border-bottom-right-radius: 8px;
                background: rgba(255, 255, 255, 0.03);
            }}

            QSpinBox#presencePartySpin::up-button:hover,
            QSpinBox#presencePartySpin::down-button:hover {{
                background: rgba(255, 255, 255, 0.07);
            }}

            QSpinBox#presencePartySpin::up-button:pressed,
            QSpinBox#presencePartySpin::down-button:pressed {{
                background: rgba(255, 255, 255, 0.10);
            }}

            QSpinBox#presencePartySpin::up-arrow,
            QSpinBox#presencePartySpin::down-arrow {{
                width: 0px;
                height: 0px;
            }}

            QPushButton#secondaryButton {{
                color: {theme["text"]};
                background: {card_alt_glass};
                border: 1px solid {theme["border"]};
                border-radius: 8px;
                padding: 7px 10px;
                font-size: 10px;
                font-weight: 650;
            }}

            QPushButton#secondaryButton:hover {{
                border: 1px solid {theme["accent"]};
            }}

            QPushButton#secondaryButton:pressed {{
                background: {theme["background"]};
            }}

            QPushButton#applyButton {{
                color: {theme["background"]};
                background: {theme["accent"]};
                border: 1px solid {theme["accent"]};
                border-radius: 9px;
                padding: 9px 17px;
                font-size: 11px;
                font-weight: 700;
            }}

            QPushButton#applyButton:hover {{
                color: {theme["text"]};
            }}

            QPushButton#applyButton:pressed {{
                padding-top: 10px;
                padding-bottom: 8px;
            }}

            QPushButton:disabled,
            QLineEdit:disabled {{
                color: {theme["muted"]};
                background: {theme["background"]};
                border-color: {theme["border"]};
            }}

            QCheckBox:disabled {{
                color: {theme["muted"]};
            }}

            QLabel#previewHeading {{
                color: {theme["accent"]};
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 1px;
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

            QLabel#previewApp {{
                color: {theme["text"]};
                font-size: 11px;
                font-weight: 650;
            }}

            QLabel#previewTitle {{
                color: {theme["text"]};
                font-size: 12px;
                font-weight: 700;
            }}

            QLabel#previewLinkButton {{
                color: {theme["text"]};
                background: {theme["card_alt"]};
                border: 1px solid {theme["border"]};
                border-radius: 7px;
                padding: 5px 9px;
                font-size: 10px;
                font-weight: 650;
            }}

            QLabel#previewMessage,
            QLabel#previewTimer {{
                color: {theme["muted"]};
                font-size: 10px;
            }}
            """
        )

        self.update_image_preview()

    @property
    def current_mode(self) -> str:
        return str(
            self.mode_box.currentData()
            or "music"
        )

    def load_active_mode(self):
        active_mode = self.controller.active_mode

        index = self.mode_box.findData(
            active_mode
        )

        if index < 0:
            index = 0

        self.mode_box.blockSignals(True)
        self.mode_box.setCurrentIndex(index)
        self.mode_box.blockSignals(False)

        self.load_mode(active_mode)
        self.update_editor_state()
        self.update_preview()
        self.refresh_preset_box()

    def on_mode_changed(self, *_):
        self.load_mode(
            self.current_mode
        )
        self.update_editor_state()
        self.update_preview()

        self.status_label.setText(
            "Press Apply to update Discord."
        )

    def load_mode(self, mode: str):
        presence_mode = (
            self.controller.load_mode(mode)
        )

        self._sync_application_box_from_mode(
            presence_mode
        )

        self.title_input.blockSignals(True)
        self.message_input.blockSignals(True)
        self.elapsed_box.blockSignals(True)
        _loop_count_box = getattr(
            self,
            "loop_count_box",
            None,
        )
        if _loop_count_box is not None:
            _loop_count_box.blockSignals(True)

        self.title_input.setText(
            presence_mode.title
        )
        self.message_input.setText(
            presence_mode.message
        )
        self.elapsed_box.setChecked(
            presence_mode.show_elapsed
        )
        _loop_count_box = getattr(
            self,
            "loop_count_box",
            None,
        )
        if _loop_count_box is not None:
            _loop_count_box.setChecked(
                presence_mode.show_loop_count
            )

        self.title_input.blockSignals(False)
        self.message_input.blockSignals(False)
        self.elapsed_box.blockSignals(False)
        _loop_count_box = getattr(
            self,
            "loop_count_box",
            None,
        )
        if _loop_count_box is not None:
            _loop_count_box.blockSignals(False)

        self._load_artwork_hover_editor(
            presence_mode
        )

        self._load_link_button_editor(
            presence_mode
        )
        self._load_party_editor(
            presence_mode
        )

        self.image_path = (
            presence_mode.image_path
        )

        self.update_image_preview()

    def update_editor_state(self):
        mode = self.current_mode

        editable = mode not in {
            "music",
            "disabled",
        }

        buttons_available = (
            mode != "disabled"
        )

        if mode == "disabled":
            workspace_minimum_height = 520

        elif mode == "music":
            workspace_minimum_height = 760

        else:
            workspace_minimum_height = 900

        self.studio_workspace.setMinimumHeight(
            workspace_minimum_height
        )

        self.editor_card.setVisible(
            editable
        )

        self.image_card.setVisible(
            editable
        )

        self.title_input.setEnabled(
            editable
        )

        self.message_input.setEnabled(
            editable
        )

        self.elapsed_box.setEnabled(
            editable
        )

        self.artwork_hover_input.setEnabled(
            editable
        )

        self.show_link_buttons_box.setEnabled(
            buttons_available
        )

        self.link_buttons_editor.setEnabled(
            buttons_available
        )

        self.link_buttons_editor.setVisible(
            buttons_available
        )

        self._update_party_editor_state()

        has_image = bool(
            self.image_path
            and Path(
                self.image_path
            ).is_file()
        )

        self.choose_image_button.setEnabled(
            editable
        )

        self.open_image_button.setEnabled(
            editable
            and has_image
        )

        self.open_artwork_folder_button.setEnabled(
            editable
        )

        self.remove_image_button.setEnabled(
            editable
            and has_image
        )

        mode_name = self.mode_box.currentText()

        self.active_badge.setText(
            mode_name.upper()
        )

        self.preview_mode.setText(
            (
                "OFF"
                if mode == "disabled"
                else mode_name.upper()
            )
        )

        if mode == "music":
            self.mode_help.setText(
                "Music follows the active Spotify or Windows media session automatically. Optional Link Buttons remain fixed for the Music Presence."
            )

        elif mode == "disabled":
            self.mode_help.setText(
                "Discord Rich Presence will be cleared."
            )

        elif mode == "custom":
            self.mode_help.setText(
                "Edit the title, message, artwork, timer, optional party information, and link buttons before publishing."
            )

        else:
            self.mode_help.setText(
                "Edit the title, message, artwork, timer, and optional link buttons before publishing."
            )

        editor_container = getattr(
            self,
            "studio_editor_container",
            None,
        )

        context_card = getattr(
            self,
            "studio_context_card",
            None,
        )

        if editor_container is not None:
            editor_container.setVisible(
                editable
            )

        if context_card is not None:
            context_card.setVisible(
                not editable
            )

        loop_count_box = getattr(
            self,
            "loop_count_box",
            None,
        )

        if loop_count_box is not None:
            loop_count_box.setVisible(
                mode == "music"
            )
            loop_count_box.setEnabled(
                mode == "music"
            )

        context_title = getattr(
            self,
            "studio_context_title",
            None,
        )

        context_text = getattr(
            self,
            "studio_context_text",
            None,
        )

        if (
            context_title is not None
            and context_text is not None
        ):
            if mode == "music":
                context_title.setText(
                    "AUTOMATIC MUSIC PRESENCE"
                )

                context_text.setText(
                    "Track title, artist, artwork, and playback timing follow your active media session automatically. Optional Link Buttons can be configured below without interacting with Spotify."
                )

            elif mode == "disabled":
                context_title.setText(
                    "RICH PRESENCE IS OFF"
                )

                context_text.setText(
                    "Nothing will be published to Discord until another Presence mode is applied."
                )

        reset_button = getattr(
            self,
            "reset_custom_button",
            None,
        )

        if reset_button is not None:
            reset_button.setVisible(
                mode == "custom"
            )

        music_button = getattr(
            self,
            "music_mode_button",
            None,
        )

        if music_button is not None:
            music_button.setVisible(
                mode != "music"
            )

        save_button = getattr(
            self,
            "library_save_button",
            None,
        )

        if save_button is not None:
            save_button.setVisible(
                mode != "disabled"
            )

        self._refresh_secondary_controls()

        self._refresh_studio_mode_controls()

    @pyqtSlot(dict)
    def apply_branding(self, branding: dict):
        title = (
            branding.get("title", "")
            or "03:37am Presence"
        )

        self.preview_app.setText(title)

    def _update_link_button_preview(
        self,
    ):
        mode = self.current_mode

        completed_labels = []
        has_saved_data = False

        for (
            label_input,
            url_input,
        ) in zip(
            self.link_button_label_inputs,
            self.link_button_url_inputs,
        ):
            label = (
                label_input.text().strip()
            )

            url = (
                url_input.text().strip()
            )

            if label or url:
                has_saved_data = True

            if label and url:
                completed_labels.append(
                    label
                )

        show_buttons = (
            mode != "disabled"
            and self.show_link_buttons_box.isChecked()
        )

        visible_labels = (
            completed_labels[:2]
            if show_buttons
            else []
        )

        for index, preview_button in enumerate(
            self.preview_link_buttons
        ):
            if index < len(
                visible_labels
            ):
                preview_button.setText(
                    visible_labels[index]
                )

                preview_button.setHidden(
                    False
                )

            else:
                preview_button.clear()

                preview_button.setHidden(
                    True
                )

        if mode == "disabled":
            status = (
                "Unavailable while Rich Presence is off"
            )

        elif not show_buttons:
            if has_saved_data:
                status = (
                    "Hidden on Discord - links saved"
                )
            else:
                status = (
                    "Hidden on Discord"
                )

        elif completed_labels:
            status = (
                "Visible to others on Discord"
            )

        else:
            status = (
                "No buttons configured"
            )

        self.link_buttons_status.setText(
            status
        )

    def update_preview(self, *_):
        mode = self.current_mode

        mode_name = self.mode_box.currentText()

        self.preview_mode.setText(
            (
                "OFF"
                if mode == "disabled"
                else mode_name.upper()
            )
        )

        self._update_link_button_preview()

        if mode == "music":
            self.preview_title.setText(
                "Current music activity"
            )

            self.preview_message.setText(
                "Track details update automatically"
            )

            self.preview_timer.setText(
                "Playback timer"
            )

            # Music does not use a user-selected custom image.
            # Always clear stale custom/invalid presentation state.
            self.preview_image.clear()

            self.preview_image.setText(
                "MUSIC"
            )

            return

        if mode == "disabled":
            self.preview_title.setText(
                "Rich Presence disabled"
            )

            self.preview_message.setText(
                "Nothing will be displayed on Discord"
            )

            self.preview_timer.setText(
                ""
            )

            self.preview_image.clear()

            self.preview_image.setText(
                "OFF"
            )

            return

        title = (
            self.title_input.text().strip()
            or mode_name
        )

        message = (
            self.message_input.text().strip()
            or "No message"
        )

        self.preview_title.setText(
            title
        )

        self.preview_message.setText(
            message
        )

        if self.elapsed_box.isChecked():
            self.preview_timer.setText(
                "00:00 elapsed"
            )
        else:
            self.preview_timer.setText(
                ""
            )

        image_path = str(
            self.image_path
            or ""
        ).strip()

        if (
            not image_path
            or not Path(
                image_path
            ).is_file()
        ):
            self.preview_image.clear()

            self.preview_image.setText(
                (
                    mode_name[:5]
                    or "MODE"
                )
            )

    def reset_custom_presence(self):
        answer = QMessageBox.question(
            self,
            "Reset Custom presence",
            "Clear the saved Custom presence title, message, timer, image, party information, and buttons?",
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        store = getattr(
            self.controller,
            "store",
            None,
        )

        if store is None:
            self.status_label.setText(
                "Local presence settings were not available."
            )
            return

        old_image_path = str(
            store.value(
                "presence/custom/image_path",
                "",
            )
            or ""
        )

        remove_mode_image(
            old_image_path
        )

        if PRESENCE_IMAGE_DIRECTORY.exists():
            for candidate in PRESENCE_IMAGE_DIRECTORY.glob(
                "custom.*"
            ):
                try:
                    candidate.unlink()
                except OSError:
                    pass

        for key in (
            "presence/custom/title",
            "presence/custom/message",
            "presence/custom/image_path",
            "presence/custom/artwork_hover_text",
            "presence/custom/show_elapsed",
            "presence/custom/show_party",
            "presence/custom/party_current",
            "presence/custom/party_maximum",
            "presence/custom/show_buttons",
            "presence/custom/buttons",
        ):
            store.remove(key)

        store.sync()

        self.controller.apply_mode(
            self.controller.load_mode(
                "music"
            )
        )
        self.load_active_mode()
        self.status_label.setText(
            "Custom presence reset. Music presence is active."
        )

    def switch_to_music_presence(self):
        self.controller.apply_mode(
            self.controller.load_mode(
                "music"
            )
        )
        self.load_active_mode()
        self.status_label.setText(
            "Music presence enabled."
        )

    def _format_file_size(
        self,
        byte_count: int,
    ) -> str:
        size = float(byte_count)

        for unit in (
            "B",
            "KB",
            "MB",
            "GB",
        ):
            if size < 1024 or unit == "GB":
                if unit == "B":
                    return f"{int(size)} {unit}"

                return f"{size:.1f} {unit}"

            size /= 1024

        return f"{byte_count} B"

    def open_selected_image(self):
        path = Path(self.image_path)

        if not path.exists():
            self.status_label.setText(
                "No artwork image is selected."
            )
            return

        opened = QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(path))
        )

        if opened:
            self.status_label.setText(
                "Artwork image opened."
            )
        else:
            self.status_label.setText(
                "The artwork image could not be opened."
            )

    def open_artwork_folder(self):
        PRESENCE_IMAGE_DIRECTORY.mkdir(
            parents=True,
            exist_ok=True,
        )

        opened = QDesktopServices.openUrl(
            QUrl.fromLocalFile(
                str(PRESENCE_IMAGE_DIRECTORY)
            )
        )

        if opened:
            self.status_label.setText(
                "Artwork folder opened."
            )
        else:
            self.status_label.setText(
                "The artwork folder could not be opened."
            )

    def validate_artwork_source(
        self,
        source_path: str,
    ) -> tuple[bool, str]:
        path = Path(source_path)

        if not path.is_file():
            return (
                False,
                "The selected artwork file could not be found.",
            )

        if path.suffix.lower() not in ARTWORK_SUPPORTED_SUFFIXES:
            return (
                False,
                "Artwork must be PNG, JPG, JPEG, or WEBP.",
            )

        try:
            byte_count = path.stat().st_size
        except OSError:
            return (
                False,
                "The selected artwork file could not be read.",
            )

        if byte_count > ARTWORK_MAX_BYTES:
            return (
                False,
                "Artwork must be 10 MB or smaller. "
                f"Selected: {self._format_file_size(byte_count)}.",
            )

        pixmap = QPixmap(
            str(path)
        )

        if pixmap.isNull():
            return (
                False,
                "The selected artwork image could not be loaded.",
            )

        return (
            True,
            "",
        )

    def choose_image(self):
        source_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Rich Presence image",
            "",
            "Images (*.png *.jpg *.jpeg *.webp)",
        )

        if not source_path:
            return

        valid, validation_message = self.validate_artwork_source(
            source_path
        )

        if not valid:
            self.status_label.setText(
                validation_message
            )
            return

        source_pixmap = QPixmap(
            source_path
        )

        saved_path = save_mode_image(
            source_path,
            self.current_mode,
        )

        if not saved_path:
            self.status_label.setText(
                "The image could not be saved."
            )
            return

        self.image_path = saved_path

        self.update_image_preview()
        self.update_preview()

        if (
            source_pixmap.width()
            and source_pixmap.height()
            and source_pixmap.width() != source_pixmap.height()
        ):
            self.status_label.setText(
                "Image selected. Square artwork works best on Discord. Press Apply to update Discord."
            )
        else:
            self.status_label.setText(
                "Image selected. Press Apply to update Discord."
            )

    def remove_image(self):
        remove_mode_image(
            self.image_path
        )

        self.image_path = ""

        self.update_image_preview()
        self.update_preview()

        self.status_label.setText(
            "Image removed. Press Apply to update Discord."
        )

    def update_image_preview(self):
        path = Path(self.image_path)

        if (
            not self.image_path
            or not path.is_file()
        ):
            self.image_preview.clear()
            self.image_preview.setText(
                "No image selected"
            )

            self.image_name.setText("")
            self.image_details.setText(
                "PNG, JPG, JPEG, or WEBP ? max 10 MB ? square works best for Discord."
            )
            self.open_image_button.setEnabled(False)
            self.remove_image_button.setEnabled(False)

            self.preview_image.clear()

            if self.current_mode == "music":
                self.preview_image.setText(
                    "Music"
                )

            elif self.current_mode == "disabled":
                self.preview_image.setText(
                    "Off"
                )

            else:
                mode_name = (
                    self.mode_box.currentText()
                    or "Mode"
                )

                self.preview_image.setText(
                    mode_name[:5]
                )

            return

        pixmap = QPixmap(str(path))

        if pixmap.isNull():
            self.image_preview.clear()
            self.image_preview.setText(
                "Image could not be loaded"
            )

            self.preview_image.clear()
            self.preview_image.setText(
                "Invalid"
            )

            self.image_name.setText(
                path.name
            )
            self.image_details.setText(
                "This image could not be loaded."
            )
            self.open_image_button.setEnabled(False)
            self.remove_image_button.setEnabled(True)
            return

        editor_pixmap = pixmap.scaled(
            self._editor_image_size,
            self._editor_image_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        preview_pixmap = pixmap.scaled(
            self._preview_image_size,
            self._preview_image_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.image_preview.setText("")
        self.image_preview.setPixmap(
            editor_pixmap
        )

        self.preview_image.setText("")
        self.preview_image.setPixmap(
            preview_pixmap
        )

        file_size = self._format_file_size(
            path.stat().st_size
        )
        self.image_name.setText(
            path.name
        )
        self.image_details.setText(
            f"{pixmap.width()} ? {pixmap.height()} px ? {file_size}"
        )

        editable = self.current_mode not in {
            "music",
            "disabled",
        }
        self.open_image_button.setEnabled(editable)
        self.remove_image_button.setEnabled(editable)

    def current_application_entry_id(
        self,
    ) -> str | None:
        box = getattr(
            self,
            "application_box",
            None,
        )

        if box is not None:
            try:
                value = box.currentData()

            except Exception:
                value = None

            entry_id = (
                str(
                    value or ""
                )
                .replace(
                    "\x00",
                    "",
                )
                .strip()
            )

            if entry_id:
                return entry_id

        controller = getattr(
            self,
            "controller",
            None,
        )

        load_mode = getattr(
            controller,
            "load_mode",
            None,
        )

        if not callable(
            load_mode
        ):
            return None

        try:
            stored_mode = load_mode(
                self.current_mode
            )

            return (
                stored_mode
                .normalized_application_entry_id()
            )

        except Exception:
            return None


    def refresh_application_box(
        self,
        preferred_entry_id=None,
    ):
        box = getattr(
            self,
            "application_box",
            None,
        )

        if box is None:
            return

        if preferred_entry_id is None:
            preferred_entry_id = (
                self.current_application_entry_id()
            )

        preferred = (
            str(
                preferred_entry_id or ""
            )
            .replace(
                "\x00",
                "",
            )
            .strip()
        )

        store = getattr(
            self,
            "discord_application_store",
            None,
        )

        list_entries = getattr(
            store,
            "list_entries",
            None,
        )

        entries = []
        store_available = False

        if callable(
            list_entries
        ):
            try:
                entries = list(
                    list_entries()
                )

                store_available = True

            except Exception:
                entries = []
                store_available = False

        normalized_entries = []

        for entry in entries:
            entry_id = (
                str(
                    getattr(
                        entry,
                        "entry_id",
                        "",
                    )
                    or ""
                )
                .replace(
                    "\x00",
                    "",
                )
                .strip()
            )

            if not entry_id:
                continue

            name = (
                str(
                    getattr(
                        entry,
                        "name",
                        "",
                    )
                    or ""
                )
                .replace(
                    "\x00",
                    "",
                )
                .strip()
            )

            normalized_entries.append(
                (
                    entry_id,
                    (
                        name
                        or "Unnamed Discord Application"
                    ),
                )
            )

        self._application_store_available = bool(
            store_available
            and normalized_entries
        )

        self._loading_application_box = True

        box.blockSignals(
            True
        )

        try:
            box.clear()

            for (
                entry_id,
                name,
            ) in normalized_entries:
                box.addItem(
                    name,
                    entry_id,
                )

            if (
                preferred
                and box.findData(
                    preferred
                )
                < 0
            ):
                box.addItem(
                    (
                        "Unavailable application "
                        "(saved reference)"
                    ),
                    preferred,
                )

                unavailable_index = (
                    box.count() - 1
                )

                box.setItemData(
                    unavailable_index,
                    (
                        "This saved Discord Application "
                        "is no longer present in the "
                        "Application Library. Its stable "
                        "reference is being preserved."
                    ),
                    Qt.ItemDataRole.ToolTipRole,
                )

            if preferred:
                selected_index = (
                    box.findData(
                        preferred
                    )
                )

            else:
                selected_index = (
                    0
                    if box.count()
                    else -1
                )

            if selected_index >= 0:
                box.setCurrentIndex(
                    selected_index
                )

            if box.count() == 0:
                box.addItem(
                    (
                        "Application Library "
                        "unavailable"
                    ),
                    None,
                )

                box.setCurrentIndex(
                    0
                )

            box.setEnabled(
                bool(
                    self._application_store_available
                    and getattr(
                        self,
                        "current_mode",
                        "",
                    )
                    != "disabled"
                )
            )

        finally:
            box.blockSignals(
                False
            )

            self._loading_application_box = False


    def _sync_application_box_from_mode(
        self,
        presence_mode,
    ):
        try:
            entry_id = (
                presence_mode
                .normalized_application_entry_id()
            )

        except Exception:
            entry_id = None

        self.refresh_application_box(
            entry_id
            or ""
        )


    def _on_application_changed(
        self,
        *_,
    ):
        if getattr(
            self,
            "_loading_application_box",
            False,
        ):
            return

        status_label = getattr(
            self,
            "status_label",
            None,
        )

        set_text = getattr(
            status_label,
            "setText",
            None,
        )

        if callable(
            set_text
        ):
            set_text(
                "Discord Application changed. "
                "Press Apply to update Discord."
            )

    def _secondary_editor_application_entry_id(
        self,
    ) -> str | None:
        current_application_entry_id = getattr(
            self,
            "current_application_entry_id",
            None,
        )

        if callable(
            current_application_entry_id
        ):
            try:
                selected_entry_id = (
                    current_application_entry_id()
                )

            except Exception:
                selected_entry_id = None

            if selected_entry_id:
                return selected_entry_id

        selected_preset = getattr(
            self,
            "selected_preset",
            None,
        )

        if callable(
            selected_preset
        ):
            try:
                preset = selected_preset()

            except Exception:
                preset = None

            if preset is not None:
                try:
                    preset_mode = (
                        preset.to_presence_mode()
                    )

                    if (
                        preset_mode.normalized_mode()
                        == self.current_mode
                    ):
                        return (
                            preset_mode
                            .normalized_application_entry_id()
                        )

                except Exception:
                    pass

        controller = getattr(
            self,
            "controller",
            None,
        )

        load_mode = getattr(
            controller,
            "load_mode",
            None,
        )

        if not callable(
            load_mode
        ):
            return None

        try:
            stored_mode = load_mode(
                self.current_mode
            )

            return (
                stored_mode
                .normalized_application_entry_id()
            )

        except Exception:
            return None

    def _refresh_secondary_controls(
        self,
        *_,
    ):
        apply_button = getattr(
            self,
            "apply_secondary_button",
            None,
        )

        clear_button = getattr(
            self,
            "clear_secondary_button",
            None,
        )

        controller = getattr(
            self,
            "controller",
            None,
        )

        current_mode = getattr(
            self,
            "current_mode",
            None,
        )

        editable_secondary = (
            current_mode
            not in {
                "music",
                "disabled",
            }
        )

        primary_mode = getattr(
            controller,
            "active_mode",
            None,
        )

        primary_is_music = (
            primary_mode == "music"
        )

        secondary_active = (
            getattr(
                controller,
                "secondary_presence_mode",
                None,
            )
            is not None
        )

        if apply_button is not None:
            apply_button.setVisible(
                editable_secondary
            )

            apply_button.setEnabled(
                editable_secondary
                and primary_is_music
            )

        if clear_button is not None:
            clear_button.setVisible(
                secondary_active
            )

            clear_button.setEnabled(
                secondary_active
            )

    def apply_secondary_presence(
        self,
    ):
        if self.current_mode in {
            "music",
            "disabled",
        }:
            self.status_label.setText(
                "Music and Disabled cannot be used as a Secondary Presence."
            )

            self._refresh_secondary_controls()
            return

        if (
            getattr(
                self.controller,
                "active_mode",
                None,
            )
            != "music"
        ):
            self.status_label.setText(
                "Secondary Presence is available while Music is the active primary Presence."
            )

            self._refresh_secondary_controls()
            return

        try:
            presence_mode = (
                self.current_editor_presence_mode()
            )

        except PresenceLinkButtonError as error:
            self.status_label.setText(
                str(error)
            )

            self._refresh_secondary_controls()
            return

        presence_mode.application_entry_id = (
            self
            ._secondary_editor_application_entry_id()
        )

        try:
            published = bool(
                self.controller.apply_secondary_mode(
                    presence_mode
                )
            )

        except Exception:
            published = False

        if published:
            mode_name = (
                self.mode_box.currentText()
            )

            self.status_label.setText(
                f"{mode_name} applied as Secondary Presence."
            )

        else:
            self.status_label.setText(
                "Secondary Presence could not be published. Check that its Discord Application exists and is not already used by Music."
            )

        self._refresh_secondary_controls()

    def clear_secondary_presence(
        self,
    ):
        try:
            cleared = bool(
                self.controller.clear_secondary_mode()
            )

        except Exception:
            cleared = False

        if cleared:
            self.status_label.setText(
                "Secondary Presence cleared."
            )

        else:
            self.status_label.setText(
                "Secondary Presence could not be cleared."
            )

        self._refresh_secondary_controls()

    def apply_presence(self):
        try:
            presence_mode = (
                self.current_editor_presence_mode()
            )

        except PresenceLinkButtonError as error:
            self.status_label.setText(
                str(error)
            )
            return

        self.controller.apply_mode(
            presence_mode
        )

        mode_name = self.mode_box.currentText()

        self.active_badge.setText(
            mode_name.upper()
        )

        if self.current_mode == "music":
            self.status_label.setText(
                "Music presence enabled."
            )

        elif self.current_mode == "disabled":
            self.status_label.setText(
                "Discord Rich Presence disabled."
            )

        else:
            self.status_label.setText(
                f"{mode_name} presence applied."
            )

        self.update_preview()
