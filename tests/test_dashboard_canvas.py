from __future__ import annotations

from dataclasses import replace
import inspect
import os
import unittest

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QPushButton,
    QWidget,
)

from src.ui.dashboard import (
    DashboardCanvas,
    DashboardPage,
)
from src.ui.dashboard_layout import (
    available_presets,
    preset_layout,
)


class _CanvasStateStub(QWidget):
    update_dashboard_canvas_editor_state = (
        DashboardPage
        .update_dashboard_canvas_editor_state
    )

    _refresh_dashboard_widget_style = staticmethod(
        DashboardPage
        ._refresh_dashboard_widget_style
    )

    def __init__(self):
        super().__init__()

        self.dashboard_layout_state = replace(
            preset_layout(
                available_presets()[0]
            ),
            locked=True,
        )

        self.dashboard_snap_grid_size = 24
        self.dashboard_snap_to_grid = True

        self.dashboard_canvas = (
            DashboardCanvas(self)
        )

        self.dashboard_cards = {
            "first": QFrame(
                self.dashboard_canvas
            ),
            "second": QFrame(
                self.dashboard_canvas
            ),
        }


class _HandlePositionStub(QWidget):
    position_dashboard_drag_handles = (
        DashboardPage
        .position_dashboard_drag_handles
    )

    def __init__(self):
        super().__init__()

        self.dashboard_canvas = QFrame(self)
        self.dashboard_canvas.resize(
            500,
            400,
        )

        self.card = QFrame(
            self.dashboard_canvas
        )
        self.card.setGeometry(
            100,
            80,
            240,
            180,
        )

        self.move_handle = QLabel(
            "DRAG",
            self.dashboard_canvas,
        )
        self.move_handle.setFixedSize(
            44,
            20,
        )

        self.resize_handle = QLabel(
            "SIZE",
            self.dashboard_canvas,
        )
        self.resize_handle.setFixedSize(
            34,
            20,
        )

        self.action_handle = QPushButton(
            "...",
            self.dashboard_canvas,
        )
        self.action_handle.setFixedSize(
            30,
            20,
        )

        self.delete_handle = QPushButton(
            "X",
            self.dashboard_canvas,
        )
        self.delete_handle.setFixedSize(
            20,
            20,
        )

        self.dashboard_cards = {
            "card": self.card,
        }

        self.dashboard_drag_handles = {
            "card": self.move_handle,
        }

        self.dashboard_resize_handles = {
            "card": self.resize_handle,
        }

        self.dashboard_action_handles = {
            "card": self.action_handle,
        }

        self.dashboard_delete_handles = {
            "card": self.delete_handle,
        }

    def update_dashboard_editor_outline(self):
        return None


class DashboardCanvasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def test_canvas_configuration_is_exposed(self):
        canvas = DashboardCanvas()

        canvas.set_editor_theme(
            "#ff44aa",
            "#332244",
        )
        canvas.set_grid_spacing(31)
        canvas.set_snap_enabled(False)

        self.assertEqual(
            canvas.property(
                "editorAccent"
            ),
            "#ff44aa",
        )
        self.assertEqual(
            canvas.property(
                "editorBorder"
            ),
            "#332244",
        )
        self.assertEqual(
            canvas.property(
                "gridSpacing"
            ),
            31,
        )
        self.assertFalse(
            canvas.property(
                "snapEnabled"
            )
        )

        canvas.close()

    def test_canvas_tracks_locked_and_editing_state(
        self,
    ):
        widget = _CanvasStateStub()

        widget.update_dashboard_canvas_editor_state()

        self.assertFalse(
            widget.dashboard_canvas.property(
                "editing"
            )
        )

        for card in (
            widget.dashboard_cards.values()
        ):
            self.assertFalse(
                card.property(
                    "dashboardEditing"
                )
            )

        widget.dashboard_layout_state = replace(
            widget.dashboard_layout_state,
            locked=False,
        )

        widget.update_dashboard_canvas_editor_state()

        self.assertTrue(
            widget.dashboard_canvas.property(
                "editing"
            )
        )

        for card in (
            widget.dashboard_cards.values()
        ):
            self.assertTrue(
                card.property(
                    "dashboardEditing"
                )
            )

        widget.close()

    def test_grid_respects_snap_setting(self):
        widget = _CanvasStateStub()

        widget.dashboard_layout_state = replace(
            widget.dashboard_layout_state,
            locked=False,
        )

        widget.dashboard_snap_to_grid = False
        widget.update_dashboard_canvas_editor_state()

        self.assertTrue(
            widget.dashboard_canvas.property(
                "editing"
            )
        )
        self.assertFalse(
            widget.dashboard_canvas.property(
                "snapEnabled"
            )
        )
        self.assertEqual(
            widget.dashboard_canvas.property(
                "gridSpacing"
            ),
            24,
        )

        widget.close()

    def test_canvas_renders_and_handles_are_ascii_safe(
        self,
    ):
        canvas = DashboardCanvas()
        canvas.resize(
            360,
            220,
        )
        canvas.setProperty(
            "editing",
            True,
        )
        canvas.set_snap_enabled(
            True
        )
        canvas.set_editor_theme(
            "#ff44aa",
            "#332244",
        )

        pixmap = QPixmap(
            canvas.size()
        )
        pixmap.fill(
            Qt.GlobalColor.transparent
        )

        canvas.render(
            pixmap
        )

        self.assertFalse(
            pixmap.isNull()
        )

        source = inspect.getsource(
            DashboardPage
            .create_dashboard_card_handles
        )

        for label in (
            '"DRAG"',
            '"SIZE"',
            '"..."',
            '"X"',
        ):
            self.assertIn(
                label,
                source,
            )

        for code_point in (
            0x2198,
            0x22EF,
            0x00D7,
        ):
            self.assertNotIn(
                chr(code_point),
                source,
            )

        self.assertNotIn(
            '"MOVE"',
            source,
        )

        canvas.close()


    def test_editor_handles_remain_inside_cards(
        self,
    ):
        widget = _HandlePositionStub()

        widget.position_dashboard_drag_handles()

        card_geometry = (
            widget.card.geometry()
        )

        for handle in (
            widget.move_handle,
            widget.resize_handle,
            widget.action_handle,
            widget.delete_handle,
        ):
            self.assertTrue(
                card_geometry.contains(
                    handle.geometry()
                ),
                (
                    f"{handle.text()} escaped "
                    "the card boundary"
                ),
            )

        self.assertEqual(
            widget.move_handle.y(),
            widget.card.y() + 6,
        )
        self.assertEqual(
            widget.action_handle.x(),
            widget.card.x() + 6,
        )
        self.assertEqual(
            widget.delete_handle.y(),
            widget.card.y() + 6,
        )
        self.assertEqual(
            widget.resize_handle.x(),
            (
                widget.card.x()
                + widget.card.width()
                - widget.resize_handle.width()
                - 6
            ),
        )
        self.assertEqual(
            widget.resize_handle.y(),
            (
                widget.card.y()
                + widget.card.height()
                - widget.resize_handle.height()
                - 6
            ),
        )

        widget.close()

if __name__ == "__main__":
    unittest.main()
