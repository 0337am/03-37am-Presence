from __future__ import annotations

import inspect
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QLineEdit,
    QSpinBox,
    QWidget,
)

from src.discord.presence_modes import (
    PresenceMode,
)
from src.ui.presence_page import (
    PartySpinBox,
    PresencePage,
)


UI_PATH = (
    Path(__file__).resolve().parents[2]
    / "src/ui/presence_page.py"
)


def ensure_app():
    app = QApplication.instance()

    if app is None:
        app = QApplication(
            sys.argv
        )

    return app


class PartyEditorProxy:
    _load_party_editor = (
        PresencePage._load_party_editor
    )
    _update_party_editor_state = (
        PresencePage._update_party_editor_state
    )
    _on_party_current_changed = (
        PresencePage._on_party_current_changed
    )
    _on_party_maximum_changed = (
        PresencePage._on_party_maximum_changed
    )
    current_editor_presence_mode = (
        PresencePage.current_editor_presence_mode
    )

    def __init__(
        self,
        mode="custom",
    ):
        self._app = ensure_app()

        self._mode = mode

        self.party_editor = QWidget()

        self.show_party_box = QCheckBox(
            "Show on Discord"
        )

        self.party_current_spin = QSpinBox()
        self.party_current_spin.setRange(
            1,
            9999,
        )
        self.party_current_spin.setValue(
            1
        )

        self.party_maximum_spin = QSpinBox()
        self.party_maximum_spin.setRange(
            1,
            9999,
        )
        self.party_maximum_spin.setValue(
            2
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

        self.title_input = QLineEdit()
        self.message_input = QLineEdit()
        self.elapsed_box = QCheckBox()
        self.show_link_buttons_box = QCheckBox()

        self.image_path = ""
        self.loop_count_box = None

    @property
    def current_mode(self):
        return self._mode

    def _editor_presence_buttons(self):
        return ()


class PresenceStudioPartyUiTests(
    unittest.TestCase
):
    def test_custom_editor_collects_party_numbers(self):
        proxy = PartyEditorProxy(
            "custom"
        )

        proxy.show_party_box.setChecked(
            True
        )
        proxy.party_current_spin.setValue(
            4
        )
        proxy.party_maximum_spin.setValue(
            10
        )

        mode = (
            proxy.current_editor_presence_mode()
        )

        self.assertTrue(
            mode.show_party
        )

        self.assertEqual(
            mode.normalized_party_size(),
            (4, 10),
        )

    def test_non_custom_mode_cannot_enable_party(self):
        proxy = PartyEditorProxy(
            "working"
        )

        proxy.show_party_box.setChecked(
            True
        )

        mode = (
            proxy.current_editor_presence_mode()
        )

        self.assertFalse(
            mode.show_party
        )

        self.assertIsNone(
            mode.discord_party_size()
        )

    def test_hidden_party_restores_saved_numbers(self):
        proxy = PartyEditorProxy(
            "custom"
        )

        proxy._load_party_editor(
            PresenceMode(
                mode="custom",
                show_party=False,
                party_current=6,
                party_maximum=12,
            )
        )

        self.assertFalse(
            proxy.show_party_box.isChecked()
        )

        self.assertEqual(
            proxy.party_current_spin.value(),
            6,
        )

        self.assertEqual(
            proxy.party_maximum_spin.value(),
            12,
        )

        self.assertFalse(
            proxy.party_current_spin.isEnabled()
        )

        self.assertFalse(
            proxy.party_maximum_spin.isEnabled()
        )

    def test_enabled_party_restores_numbers(self):
        proxy = PartyEditorProxy(
            "custom"
        )

        proxy._load_party_editor(
            PresenceMode(
                mode="custom",
                show_party=True,
                party_current=2,
                party_maximum=5,
            )
        )

        self.assertTrue(
            proxy.show_party_box.isChecked()
        )

        self.assertTrue(
            proxy.party_current_spin.isEnabled()
        )

        self.assertTrue(
            proxy.party_maximum_spin.isEnabled()
        )

        self.assertEqual(
            (
                proxy.party_current_spin.value(),
                proxy.party_maximum_spin.value(),
            ),
            (2, 5),
        )

    def test_party_editor_hidden_outside_custom(self):
        proxy = PartyEditorProxy(
            "working"
        )

        proxy.show_party_box.setChecked(
            True
        )

        proxy.party_editor.show()
        proxy._app.processEvents()

        self.assertFalse(
            proxy.party_editor.isHidden()
        )

        proxy._update_party_editor_state()

        self.assertTrue(
            proxy.party_editor.isHidden()
        )

        self.assertFalse(
            proxy.show_party_box.isEnabled()
        )

    def test_current_above_maximum_raises_maximum(self):
        proxy = PartyEditorProxy(
            "custom"
        )

        proxy.party_maximum_spin.setValue(
            4
        )

        proxy.party_current_spin.setValue(
            8
        )

        self.assertEqual(
            proxy.party_maximum_spin.value(),
            8,
        )

    def test_maximum_below_current_lowers_current(self):
        proxy = PartyEditorProxy(
            "custom"
        )

        proxy.party_maximum_spin.setValue(
            10
        )

        proxy.party_current_spin.setValue(
            8
        )

        proxy.party_maximum_spin.setValue(
            3
        )

        self.assertEqual(
            proxy.party_current_spin.value(),
            3,
        )

    def test_party_spinbox_uses_app_owned_chevrons(self):
        self.assertTrue(
            issubclass(
                PartySpinBox,
                QSpinBox,
            )
        )

        paint_source = inspect.getsource(
            PartySpinBox.paintEvent
        )

        for marker in (
            "SC_SpinBoxUp",
            "SC_SpinBoxDown",
            "QPainter(",
            "_draw_chevron(",
        ):
            self.assertIn(
                marker,
                paint_source,
            )

        chevron_source = inspect.getsource(
            PartySpinBox._draw_chevron
        )

        self.assertIn(
            "painter.drawLine(",
            chevron_source,
        )

    def test_source_contains_custom_only_party_ui(self):
        source = UI_PATH.read_text(
            encoding="utf-8-sig"
        )

        for marker in (
            '"PARTY / GROUP"',
            'self.current_mode == "custom"',
            '"presence/custom/show_party"',
            '"presence/custom/party_current"',
            '"presence/custom/party_maximum"',
            'QSpinBox#presencePartySpin::up-button {',
            'QSpinBox#presencePartySpin::down-button {',
        ):
            self.assertIn(
                marker,
                source,
            )

        self.assertIn(
            """QSpinBox#presencePartySpin::up-arrow,
            QSpinBox#presencePartySpin::down-arrow {{
                width: 0px;
                height: 0px;
            }}""",
            source,
        )


if __name__ == "__main__":
    unittest.main()
