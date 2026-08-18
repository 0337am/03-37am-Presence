import ast
from pathlib import Path
import unittest


class DashboardDiscordPresenceModeTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.dashboard_source = Path(
            "src/ui/dashboard.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        cls.main_source = Path(
            "src/ui/main_window.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        cls.dashboard_tree = ast.parse(
            cls.dashboard_source
        )

    @classmethod
    def dashboard_method(
        cls,
        name,
    ):
        lines = cls.dashboard_source.splitlines()

        for node in ast.walk(
            cls.dashboard_tree
        ):
            if (
                isinstance(
                    node,
                    ast.FunctionDef,
                )
                and node.name == name
            ):
                return "\n".join(
                    lines[
                        node.lineno - 1:
                        node.end_lineno
                    ]
                )

        raise AssertionError(
            f"Dashboard method not found: {name}"
        )

    def test_main_window_connects_applied_modes(self):
        self.assertIn(
            "self.presence_controller.mode_changed.connect(",
            self.main_source,
        )
        self.assertIn(
            "self.dashboard_page.set_discord_presence_mode",
            self.main_source,
        )

    def test_dashboard_accepts_generic_mode_payload(self):
        method = self.dashboard_method(
            "set_discord_presence_mode"
        )

        for token in (
            '"mode"',
            '"show_elapsed"',
            "_discord_preview_mode",
            "_discord_presence_payload",
            "_render_discord_presence_payload",
        ):
            self.assertIn(
                token,
                method,
            )

    def test_custom_renderer_uses_title_message_and_image(self):
        method = self.dashboard_method(
            "_render_discord_presence_payload"
        )

        for token in (
            '"title"',
            '"message"',
            '"image_bytes"',
            "QPixmap()",
            "loadFromData(",
            "preview_album.setHidden(True)",
            "activity_progress.setHidden(",
            "timer = getattr(",
            "discord_presence_preview_timer",
        ):
            self.assertIn(
                token,
                method,
            )

    def test_custom_elapsed_uses_independent_timer(self):
        renderer = self.dashboard_method(
            "_render_discord_presence_payload"
        )

        timer_method = self.dashboard_method(
            "refresh_discord_presence_preview_elapsed"
        )

        self.assertIn(
            '"show_elapsed"',
            renderer,
        )
        self.assertIn(
            "time.monotonic()",
            timer_method,
        )
        self.assertIn(
            "format_playback_time(",
            timer_method,
        )

    def test_smooth_music_preview_is_mode_guarded(self):
        method = self.dashboard_method(
            "refresh_playback_presentation"
        )

        self.assertIn(
            "_discord_music_preview_active()",
            method,
        )

    def test_song_updates_restore_non_music_preview(self):
        method = self.dashboard_method(
            "apply_song"
        )

        self.assertIn(
            "_restore_non_music_discord_preview()",
            method,
        )

    def test_artwork_refresh_restores_custom_preview(self):
        method = self.dashboard_method(
            "update_artwork"
        )

        self.assertGreaterEqual(
            method.count(
                "_restore_non_music_discord_preview()"
            ),
            3,
        )

    def test_shutdown_stops_presence_preview_timer(self):
        method = self.dashboard_method(
            "stop_media_worker"
        )

        self.assertIn(
            "discord_presence_preview_timer",
            method,
        )
        self.assertIn(
            "discord_presence_preview_timer.stop()",
            method,
        )

    def test_returning_to_music_invalidates_artwork_signature(self):
        method = self.dashboard_method(
            "set_discord_presence_mode"
        )

        music_branch = method.split(
            'if mode == "music":',
            1,
        )[1]

        before_apply = music_branch.split(
            "self.apply_song(",
            1,
        )[0]

        self.assertIn(
            "self._last_artwork_signature = None",
            before_apply,
        )


if __name__ == "__main__":
    unittest.main()
