from __future__ import annotations

import inspect
import unittest
from types import SimpleNamespace

from src.ui.dashboard import DashboardPage


class _FakeLayout:
    def __init__(
        self,
    ):
        self.invalidate_calls = 0
        self.activate_calls = 0

    def invalidate(
        self,
    ):
        self.invalidate_calls += 1

    def activate(
        self,
    ):
        self.activate_calls += 1
        return True


class _FakeCard:
    def __init__(
        self,
        *,
        width=500,
        height=300,
        layout=None,
    ):
        self._width = int(width)
        self._height = int(height)
        self._layout = layout

    def width(
        self,
    ):
        return self._width

    def height(
        self,
    ):
        return self._height

    def layout(
        self,
    ):
        return self._layout


class _FakeButton:
    def __init__(
        self,
    ):
        self.update_geometry_calls = 0
        self.fixed_heights = []

    def updateGeometry(
        self,
    ):
        self.update_geometry_calls += 1

    def setFixedHeight(
        self,
        height,
    ):
        self.fixed_heights.append(
            int(height)
        )


class DashboardQuickAccessResizeTests(
    unittest.TestCase
):
    def test_geometry_helper_invalidates_outer_and_grid_layouts(
        self,
    ):
        outer_layout = _FakeLayout()
        grid_layout = _FakeLayout()

        dashboard = SimpleNamespace(
            quick_access_card=_FakeCard(
                layout=outer_layout
            ),
            quick_access_grid=grid_layout,
            quick_access_buttons=[],
        )

        DashboardPage._activate_quick_access_layout_geometry(
            dashboard
        )

        self.assertEqual(
            outer_layout.invalidate_calls,
            1,
        )

        self.assertEqual(
            outer_layout.activate_calls,
            1,
        )

        self.assertEqual(
            grid_layout.invalidate_calls,
            1,
        )

        self.assertEqual(
            grid_layout.activate_calls,
            1,
        )

    def test_geometry_helper_refreshes_every_button_hint(
        self,
    ):
        buttons = [
            _FakeButton(),
            _FakeButton(),
            _FakeButton(),
        ]

        dashboard = SimpleNamespace(
            quick_access_card=_FakeCard(
                layout=_FakeLayout()
            ),
            quick_access_grid=_FakeLayout(),
            quick_access_buttons=[
                {
                    "button": button
                }
                for button in buttons
            ],
        )

        DashboardPage._activate_quick_access_layout_geometry(
            dashboard
        )

        self.assertEqual(
            [
                button.update_geometry_calls
                for button in buttons
            ],
            [
                1,
                1,
                1,
            ],
        )

    def test_same_logical_mode_still_reactivates_geometry(
        self,
    ):
        outer_layout = _FakeLayout()
        grid_layout = _FakeLayout()

        buttons = [
            _FakeButton()
            for _ in range(4)
        ]

        dashboard = SimpleNamespace(
            quick_access_card=_FakeCard(
                width=500,
                height=300,
                layout=outer_layout,
            ),
            quick_access_grid=grid_layout,
            quick_access_buttons=[
                {
                    "button": button,
                    "title": "Test",
                    "detail": "Detail",
                }
                for button in buttons
            ],
            _quick_access_layout_mode=(
                2,
                2,
                2,
                True,
            ),
        )

        dashboard._activate_quick_access_layout_geometry = (
            DashboardPage
            ._activate_quick_access_layout_geometry
            .__get__(dashboard)
        )

        dashboard._apply_quick_access_button_height = (
            DashboardPage
            ._apply_quick_access_button_height
            .__get__(dashboard)
        )

        DashboardPage.update_quick_access_layout(
            dashboard
        )

        self.assertEqual(
            outer_layout.activate_calls,
            1,
        )

        self.assertEqual(
            grid_layout.activate_calls,
            1,
        )

        self.assertEqual(
            [
                button.update_geometry_calls
                for button in buttons
            ],
            [
                1,
                1,
                1,
                1,
            ],
        )

    def test_same_mode_branch_is_not_an_inert_return(
        self,
    ):
        source = inspect.getsource(
            DashboardPage.update_quick_access_layout
        )

        expected = (
            "layout_mode\n"
            "            == self._quick_access_layout_mode\n"
            "        ):\n"
            "            self._activate_quick_access_layout_geometry()\n"
            "            return"
        )

        self.assertIn(
            expected,
            source,
        )

    def test_structural_reflow_finishes_with_geometry_activation(
        self,
    ):
        source = inspect.getsource(
            DashboardPage.update_quick_access_layout
        )

        assignment = (
            "self._quick_access_layout_mode = (\n"
            "            layout_mode\n"
            "        )"
        )

        activation = (
            "self._activate_quick_access_layout_geometry()"
        )

        assignment_index = source.rfind(
            assignment
        )

        activation_index = source.rfind(
            activation
        )

        self.assertGreaterEqual(
            assignment_index,
            0,
        )

        self.assertGreater(
            activation_index,
            assignment_index,
        )

    def test_dashboard_resize_pipeline_reaches_responsive_cards(
        self,
    ):
        resize_source = inspect.getsource(
            DashboardPage.resizeEvent
        )

        geometry_source = inspect.getsource(
            DashboardPage.apply_dashboard_layout_geometry
        )

        self.assertIn(
            "self.schedule_dashboard_geometry_refresh()",
            resize_source,
        )

        self.assertIn(
            "self.update_responsive_dashboard_cards()",
            geometry_source,
        )



    def test_responsive_height_is_applied_to_every_button(
        self,
    ):
        buttons = [
            _FakeButton(),
            _FakeButton(),
            _FakeButton(),
        ]

        dashboard = SimpleNamespace(
            quick_access_buttons=[
                {
                    "button": button
                }
                for button in buttons
            ]
        )

        DashboardPage._apply_quick_access_button_height(
            dashboard,
            57,
        )

        self.assertEqual(
            [
                button.fixed_heights
                for button in buttons
            ],
            [
                [57],
                [57],
                [57],
            ],
        )

    def test_two_column_single_tail_fills_complete_row(
        self,
    ):
        self.assertEqual(
            DashboardPage._quick_access_grid_slot(
                index=8,
                button_count=9,
                columns=2,
            ),
            (
                4,
                0,
                2,
                2,
            ),
        )

    def test_four_column_two_item_tail_splits_full_row_evenly(
        self,
    ):
        first = (
            DashboardPage
            ._quick_access_grid_slot(
                index=8,
                button_count=10,
                columns=4,
            )
        )

        second = (
            DashboardPage
            ._quick_access_grid_slot(
                index=9,
                button_count=10,
                columns=4,
            )
        )

        self.assertEqual(
            first,
            (
                2,
                0,
                4,
                8,
            ),
        )

        self.assertEqual(
            second,
            (
                2,
                4,
                4,
                8,
            ),
        )

    def test_four_column_three_item_tail_splits_full_row_evenly(
        self,
    ):
        slots = [
            DashboardPage._quick_access_grid_slot(
                index=index,
                button_count=11,
                columns=4,
            )
            for index in (
                8,
                9,
                10,
            )
        ]

        self.assertEqual(
            slots,
            [
                (
                    2,
                    0,
                    4,
                    12,
                ),
                (
                    2,
                    4,
                    4,
                    12,
                ),
                (
                    2,
                    8,
                    4,
                    12,
                ),
            ],
        )

    def test_update_layout_applies_height_before_cached_return(
        self,
    ):
        source = inspect.getsource(
            DashboardPage.update_quick_access_layout
        )

        height_index = source.find(
            "self._apply_quick_access_button_height("
        )

        cache_index = source.find(
            "not force"
        )

        self.assertGreaterEqual(
            height_index,
            0,
        )

        self.assertGreater(
            cache_index,
            height_index,
        )


if __name__ == "__main__":
    unittest.main()
