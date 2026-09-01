from pathlib import Path
import unittest

from tests.repo_paths import REPO_ROOT


STAGE_PATH = (
    REPO_ROOT
    / "src"
    / "system"
    / "startup_native_stage.py"
)


class StartupNativeStageRuntimeHideTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.source = STAGE_PATH.read_text(
            encoding="utf-8",
        )

        hide_start = cls.source.index(
            "    def staged_hide(self):"
        )

        hide_end = cls.source.index(
            "    def staged_show(self):",
            hide_start,
        )

        cls.hide_block = cls.source[
            hide_start:hide_end
        ]

        show_start = hide_end

        show_end = cls.source.index(
            "    window_class.show = staged_show",
            show_start,
        )

        cls.show_block = cls.source[
            show_start:show_end
        ]

    def test_runtime_hide_suppression_requires_active_stage(
        self,
    ):
        self.assertIn(
            '_state["staging"]',
            self.hide_block,
        )

        self.assertIn(
            "_0337_stage_prepared",
            self.hide_block,
        )

        self.assertIn(
            "_0337_stage_complete",
            self.hide_block,
        )

        self.assertIn(
            "return _original_hide(",
            self.hide_block,
        )

    def test_final_handoff_recovers_recreated_main_hwnd(
        self,
    ):
        for marker in (
            "captured_main_hwnd = int(",
            "current_main_hwnd = int(",
            "self.winId()",
            "desired_main_rect = (",
            '_state["main"] = (',
            '_state["desired"][',
            "_move_targets_onscreen()",
        ):
            self.assertIn(
                marker,
                self.show_block,
            )

        recovery = self.show_block.index(
            "captured_main_hwnd = int("
        )

        move = self.show_block.index(
            "_move_targets_onscreen()"
        )

        self.assertLess(
            recovery,
            move,
        )


if __name__ == "__main__":
    unittest.main()
