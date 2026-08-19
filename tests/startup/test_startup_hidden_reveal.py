from pathlib import Path
import unittest
from tests.repo_paths import REPO_ROOT


PROJECT_ROOT = (
    REPO_ROOT
)

MAIN_PATH = (
    PROJECT_ROOT
    / "main.py"
)

STAGE_PATH = (
    PROJECT_ROOT
    / "src"
    / "system"
    / "startup_native_stage.py"
)

WIDGETS_PATH = (
    PROJECT_ROOT
    / "src"
    / "ui"
    / "spotify_playlist_widgets.py"
)


class StartupHiddenRevealTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.main_source = (
            MAIN_PATH.read_text(
                encoding="utf-8-sig"
            )
        )

        cls.stage_source = (
            STAGE_PATH.read_text(
                encoding="utf-8"
            )
        )

        cls.widgets_source = (
            WIDGETS_PATH.read_text(
                encoding="utf-8"
            )
        )

        start = (
            cls.main_source.index(
                (
                    "def "
                    "_show_window_when_"
                    "startup_ready("
                )
            )
        )

        end = (
            cls.main_source.index(
                "def main() -> int:",
                start,
            )
        )

        cls.helper = (
            cls.main_source[
                start:end
            ]
        )

    def test_27b_hidden_reveal_lifecycle_restored(
        self,
    ):
        self.assertIn(
            "WA_DontShowOnScreen",
            self.helper,
        )

        self.assertIn(
            "window.hide()",
            self.helper,
        )

        self.assertIn(
            "window.show()",
            self.helper,
        )

    def test_stage_is_installed_before_main_window_construction(
        self,
    ):
        install_marker = (
            "install_startup_native_stage("
            "\n        MainWindow"
            "\n    )"
        )

        construct_marker = (
            "window = MainWindow()"
        )

        install = (
            self.main_source.index(
                install_marker
            )
        )

        construct = (
            self.main_source.index(
                construct_marker
            )
        )

        self.assertLess(
            install,
            construct,
        )

    def test_reveal_helper_does_not_install_stage_late(
        self,
    ):
        self.assertNotIn(
            "install_startup_native_stage",
            self.helper,
        )

    def test_stage_import_is_present(
        self,
    ):
        self.assertIn(
            (
                "from src.system."
                "startup_native_stage "
                "import "
                "install_startup_native_stage"
            ),
            self.main_source,
        )

    def test_stage_tracks_main_and_titlebars(
        self,
    ):
        for marker in (
            '"main": 0',
            '"titlebars": set()',
            '"QWindowIcon"',
            '"_q_titlebar"',
        ):
            self.assertIn(
                marker,
                self.stage_source,
            )

    def test_stage_matches_original_single_main_capture(
        self,
    ):
        self.assertIn(
            'not _state["main"]',
            self.stage_source,
        )

    def test_creation_and_moves_are_forced_offscreen(
        self,
    ):
        for marker in (
            "HCBT_CREATEWND",
            "HCBT_MOVESIZE",
            "HCBT_ACTIVATE",
            "OFFSCREEN_X",
            "OFFSCREEN_Y",
        ):
            self.assertIn(
                marker,
                self.stage_source,
            )

    def test_startup_hide_is_suppressed(
        self,
    ):
        self.assertIn(
            "def staged_hide(self):",
            self.stage_source,
        )

        self.assertIn(
            "_0337_stage_prepared",
            self.stage_source,
        )

        self.assertIn(
            "_0337_stage_complete",
            self.stage_source,
        )

    def test_first_show_clears_hidden_attribute(
        self,
    ):
        self.assertIn(
            (
                "self.setAttribute("
                "\n                "
                "hidden_attribute,"
                "\n                False,"
            ),
            self.stage_source,
        )

    def test_final_show_performs_native_handoff(
        self,
    ):
        for marker in (
            "_move_targets_onscreen()",
            (
                "self._0337_stage_complete "
                "= ("
            ),
            "return None",
        ):
            self.assertIn(
                marker,
                self.stage_source,
            )

    def test_surfaces_move_together_without_activation(
        self,
    ):
        for marker in (
            "BeginDeferWindowPos",
            "DeferWindowPos",
            "EndDeferWindowPos",
            "SWP_NOACTIVATE",
            (
                "DWMWA_TRANSITIONS_"
                "FORCEDISABLED"
            ),
        ):
            self.assertIn(
                marker,
                self.stage_source,
            )

    def test_no_cloak_or_opacity_experiment_remains(
        self,
    ):
        self.assertNotIn(
            "DWMWA_CLOAK",
            self.stage_source,
        )

        self.assertNotIn(
            "setWindowOpacity(",
            self.main_source,
        )

    def test_spotify_visual_readiness_remains(
        self,
    ):
        for marker in (
            "STARTUP_WINDOW_WARMUP_MS",
            "STARTUP_SPOTIFY_SETTLE_GRACE_MS",
            "STARTUP_REVEAL_FALLBACK_MS",
            "initial_content_settled",
            "initial_content_is_settled",
        ):
            self.assertIn(
                marker,
                self.main_source,
            )

        for marker in (
            (
                "_initial_playlist_"
                "metadata_settled"
            ),
            (
                "_initial_liked_songs_"
                "summary_settled"
            ),
            "artwork_is_settled",
        ):
            self.assertIn(
                marker,
                self.widgets_source,
            )


if __name__ == "__main__":
    unittest.main()
