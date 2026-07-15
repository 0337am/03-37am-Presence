from __future__ import annotations

import os
import unittest

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtCore import (
    QPoint,
    Qt,
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QWidget,
)

from src.ui.dashboard import (
    DashboardCanvas,
    DashboardPage,
)
from src.ui.dashboard_alignment import (
    AlignmentGuide,
    AlignmentRect,
)


class _AlignmentIntegrationStub(
    QWidget
):
    dashboard_alignment_rectangles = (
        DashboardPage
        .dashboard_alignment_rectangles
    )
    set_dashboard_alignment_guides = (
        DashboardPage
        .set_dashboard_alignment_guides
    )
    clear_dashboard_alignment_guides = (
        DashboardPage
        .clear_dashboard_alignment_guides
    )
    update_dashboard_live_drag = (
        DashboardPage
        .update_dashboard_live_drag
    )
    update_dashboard_live_resize = (
        DashboardPage
        .update_dashboard_live_resize
    )
    snap_dashboard_pixel_value = (
        DashboardPage
        .snap_dashboard_pixel_value
    )

    def __init__(self):
        super().__init__()

        self.resize(
            700,
            500,
        )

        self.dashboard_canvas = (
            DashboardCanvas(self)
        )
        self.dashboard_canvas.setGeometry(
            0,
            0,
            600,
            400,
        )
        self.dashboard_canvas.setProperty(
            "editing",
            True,
        )
        self.dashboard_canvas.set_grid_spacing(
            24
        )
        self.dashboard_canvas.set_snap_enabled(
            True
        )

        self.active_card = QFrame(
            self.dashboard_canvas
        )
        self.active_card.setGeometry(
            100,
            80,
            100,
            80,
        )

        self.other_card = QFrame(
            self.dashboard_canvas
        )
        self.other_card.setGeometry(
            250,
            200,
            120,
            90,
        )

        self.hidden_card = QFrame(
            self.dashboard_canvas
        )
        self.hidden_card.setGeometry(
            420,
            100,
            100,
            80,
        )
        self.hidden_card.hide()

        self.dashboard_cards = {
            "active": self.active_card,
            "other": self.other_card,
            "hidden": self.hidden_card,
        }

        self.dashboard_snap_grid_size = 24
        self.dashboard_snap_to_grid = True

        self._dashboard_drag_active = True
        self._dashboard_drag_card_id = (
            "active"
        )
        self._dashboard_drag_offset = (
            QPoint()
        )

        self._dashboard_resize_active = True
        self._dashboard_resize_card_id = (
            "active"
        )
        self._dashboard_resize_origin = (
            QPoint()
        )
        self._dashboard_resize_original_geometry = (
            self.active_card.geometry()
        )

    def position_dashboard_drag_handles(
        self,
    ):
        return None

    def update_responsive_dashboard_cards(
        self,
        *_,
    ):
        return None

    def dashboard_minimum_card_size(
        self,
        _,
    ):
        return (
            60,
            50,
        )


class DashboardAlignmentIntegrationTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def build_widget(self):
        return _AlignmentIntegrationStub()

    def drag_to(
        self,
        widget,
        x,
        y,
    ):
        global_position = (
            widget.dashboard_canvas
            .mapToGlobal(
                QPoint(
                    x,
                    y,
                )
            )
        )

        return (
            widget
            .update_dashboard_live_drag(
                global_position
            )
        )

    def test_canvas_stores_clears_and_renders_guides(
        self,
    ):
        canvas = DashboardCanvas()
        canvas.resize(
            500,
            320,
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

        canvas.set_alignment_guides(
            (
                AlignmentGuide(
                    orientation="vertical",
                    position=250,
                    source="canvas",
                    kind="centre",
                ),
                AlignmentGuide(
                    orientation="horizontal",
                    position=160,
                    source="canvas",
                    kind="centre",
                ),
            )
        )

        self.assertEqual(
            canvas.property(
                "alignmentGuideCount"
            ),
            2,
        )
        self.assertTrue(
            canvas.property(
                "hasAlignmentGuides"
            )
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

        canvas.clear_alignment_guides()

        self.assertEqual(
            canvas.property(
                "alignmentGuideCount"
            ),
            0,
        )
        self.assertFalse(
            canvas.property(
                "hasAlignmentGuides"
            )
        )

        canvas.close()

    def test_other_rectangles_exclude_active_and_hidden(
        self,
    ):
        widget = self.build_widget()

        rectangles = (
            widget
            .dashboard_alignment_rectangles(
                "active"
            )
        )

        self.assertEqual(
            rectangles,
            (
                AlignmentRect(
                    x=250,
                    y=200,
                    width=120,
                    height=90,
                ),
            ),
        )

        widget.close()

    def test_live_drag_prefers_card_alignment(
        self,
    ):
        widget = self.build_widget()

        self.assertTrue(
            self.drag_to(
                widget,
                247,
                80,
            )
        )

        self.assertEqual(
            widget.active_card.x(),
            250,
        )

        guides = tuple(
            widget.dashboard_canvas
            ._alignment_guides
        )

        self.assertTrue(
            any(
                guide.orientation
                == "vertical"
                and guide.position == 250
                and guide.source == "card"
                for guide in guides
            )
        )

        widget.close()

    def test_live_drag_uses_grid_without_alignment(
        self,
    ):
        widget = self.build_widget()

        self.assertTrue(
            self.drag_to(
                widget,
                37,
                37,
            )
        )

        self.assertEqual(
            widget.active_card.x(),
            48,
        )
        self.assertEqual(
            widget.active_card.y(),
            48,
        )
        self.assertEqual(
            widget.dashboard_canvas
            .property(
                "alignmentGuideCount"
            ),
            0,
        )

        widget.close()

    def test_live_drag_is_free_when_snap_disabled(
        self,
    ):
        widget = self.build_widget()

        widget.dashboard_snap_to_grid = False
        widget.dashboard_canvas.set_snap_enabled(
            False
        )

        self.assertTrue(
            self.drag_to(
                widget,
                37,
                37,
            )
        )

        self.assertEqual(
            widget.active_card.x(),
            37,
        )
        self.assertEqual(
            widget.active_card.y(),
            37,
        )
        self.assertEqual(
            widget.dashboard_canvas
            .property(
                "alignmentGuideCount"
            ),
            0,
        )

        widget.close()

    def test_live_resize_snaps_to_card_edge(
        self,
    ):
        widget = self.build_widget()

        self.assertTrue(
            widget.update_dashboard_live_resize(
                QPoint(
                    47,
                    0,
                )
            )
        )

        self.assertEqual(
            widget.active_card.width(),
            150,
        )

        guides = tuple(
            widget.dashboard_canvas
            ._alignment_guides
        )

        self.assertTrue(
            any(
                guide.orientation
                == "vertical"
                and guide.position == 250
                and guide.source == "card"
                for guide in guides
            )
        )

        widget.close()


if __name__ == "__main__":
    unittest.main()
