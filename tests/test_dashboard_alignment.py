from __future__ import annotations

import unittest

from src.ui.dashboard_alignment import (
    AlignmentRect,
    snap_moving_rect,
    snap_resizing_rect,
)


class DashboardAlignmentTests(
    unittest.TestCase
):
    def test_move_snaps_matching_card_edges(
        self,
    ):
        result = snap_moving_rect(
            requested_x=203,
            requested_y=80,
            width=100,
            height=70,
            canvas_width=800,
            canvas_height=600,
            other_rectangles=(
                AlignmentRect(
                    200,
                    250,
                    180,
                    120,
                ),
            ),
        )

        self.assertEqual(
            result.rect.x,
            200,
        )
        self.assertTrue(
            result.snapped_x
        )
        self.assertEqual(
            result.guides[0].position,
            200,
        )
        self.assertEqual(
            result.guides[0].source,
            "card",
        )

    def test_move_snaps_adjacent_edges(
        self,
    ):
        result = snap_moving_rect(
            requested_x=97,
            requested_y=80,
            width=100,
            height=70,
            canvas_width=800,
            canvas_height=600,
            other_rectangles=(
                AlignmentRect(
                    200,
                    250,
                    180,
                    120,
                ),
            ),
        )

        self.assertEqual(
            result.rect.x,
            100,
        )
        self.assertEqual(
            result.guides[0].kind,
            "adjacent edge",
        )
        self.assertEqual(
            result.guides[0].position,
            200,
        )

    def test_move_snaps_card_centres(
        self,
    ):
        result = snap_moving_rect(
            requested_x=157,
            requested_y=80,
            width=80,
            height=70,
            canvas_width=800,
            canvas_height=600,
            other_rectangles=(
                AlignmentRect(
                    100,
                    250,
                    200,
                    120,
                ),
            ),
        )

        self.assertEqual(
            result.rect.x,
            160,
        )
        self.assertEqual(
            result.guides[0].kind,
            "centre",
        )
        self.assertEqual(
            result.guides[0].position,
            200,
        )

    def test_move_snaps_canvas_edge_and_centre(
        self,
    ):
        result = snap_moving_rect(
            requested_x=198,
            requested_y=3,
            width=100,
            height=70,
            canvas_width=500,
            canvas_height=400,
        )

        self.assertEqual(
            result.rect.x,
            200,
        )
        self.assertEqual(
            result.rect.y,
            0,
        )
        self.assertTrue(
            result.snapped_x
        )
        self.assertTrue(
            result.snapped_y
        )

        self.assertEqual(
            {
                (
                    guide.orientation,
                    guide.position,
                )
                for guide in result.guides
            },
            {
                (
                    "vertical",
                    250,
                ),
                (
                    "horizontal",
                    0,
                ),
            },
        )

    def test_card_alignment_precedes_canvas(
        self,
    ):
        result = snap_moving_rect(
            requested_x=5,
            requested_y=90,
            width=80,
            height=60,
            canvas_width=500,
            canvas_height=400,
            other_rectangles=(
                AlignmentRect(
                    10,
                    220,
                    120,
                    80,
                ),
            ),
            threshold=5,
        )

        self.assertEqual(
            result.rect.x,
            10,
        )
        self.assertEqual(
            result.guides[0].source,
            "card",
        )

    def test_move_outside_threshold_stays_free(
        self,
    ):
        result = snap_moving_rect(
            requested_x=30,
            requested_y=90,
            width=80,
            height=60,
            canvas_width=500,
            canvas_height=400,
            other_rectangles=(
                AlignmentRect(
                    50,
                    220,
                    120,
                    80,
                ),
            ),
            threshold=5,
        )

        self.assertEqual(
            result.rect.x,
            30,
        )
        self.assertFalse(
            result.snapped_x
        )
        self.assertEqual(
            result.guides,
            (),
        )

    def test_move_clamps_to_canvas_bounds(
        self,
    ):
        result = snap_moving_rect(
            requested_x=-100,
            requested_y=999,
            width=120,
            height=90,
            canvas_width=500,
            canvas_height=400,
            threshold=0,
        )

        self.assertEqual(
            result.rect.x,
            0,
        )
        self.assertEqual(
            result.rect.y,
            310,
        )

    def test_resize_snaps_to_card_edges(
        self,
    ):
        result = snap_resizing_rect(
            x=50,
            y=40,
            requested_width=147,
            requested_height=137,
            minimum_width=80,
            minimum_height=70,
            canvas_width=800,
            canvas_height=600,
            other_rectangles=(
                AlignmentRect(
                    200,
                    180,
                    180,
                    120,
                ),
            ),
        )

        self.assertEqual(
            result.rect.width,
            150,
        )
        self.assertEqual(
            result.rect.height,
            140,
        )

        self.assertEqual(
            {
                (
                    guide.orientation,
                    guide.position,
                )
                for guide in result.guides
            },
            {
                (
                    "vertical",
                    200,
                ),
                (
                    "horizontal",
                    180,
                ),
            },
        )

    def test_resize_snaps_to_canvas_edges(
        self,
    ):
        result = snap_resizing_rect(
            x=100,
            y=50,
            requested_width=397,
            requested_height=348,
            minimum_width=80,
            minimum_height=70,
            canvas_width=500,
            canvas_height=400,
        )

        self.assertEqual(
            result.rect.width,
            400,
        )
        self.assertEqual(
            result.rect.height,
            350,
        )
        self.assertTrue(
            result.snapped_x
        )
        self.assertTrue(
            result.snapped_y
        )

    def test_resize_respects_minimum_without_snap(
        self,
    ):
        result = snap_resizing_rect(
            x=100,
            y=80,
            requested_width=10,
            requested_height=20,
            minimum_width=180,
            minimum_height=90,
            canvas_width=500,
            canvas_height=400,
            threshold=0,
        )

        self.assertEqual(
            result.rect.width,
            180,
        )
        self.assertEqual(
            result.rect.height,
            90,
        )
        self.assertFalse(
            result.snapped_x
        )
        self.assertFalse(
            result.snapped_y
        )
        self.assertEqual(
            result.guides,
            (),
        )


if __name__ == "__main__":
    unittest.main()
