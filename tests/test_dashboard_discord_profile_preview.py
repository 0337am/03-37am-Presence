import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

DASHBOARD_PATH = (
    REPO_ROOT
    / "src"
    / "ui"
    / "dashboard.py"
)


class DashboardDiscordProfilePreviewTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.source = DASHBOARD_PATH.read_text(
            encoding="utf-8"
        )

    def _method_source(
        self,
        method_name: str,
        next_method_name: str,
    ) -> str:
        start = self.source.index(
            f"    def {method_name}"
        )
        end = self.source.index(
            f"    def {next_method_name}",
            start,
        )

        return self.source[
            start:end
        ]

    def test_dashboard_imports_preview_widget(self):
        self.assertIn(
            "from src.ui.discord_profile_preview import (",
            self.source,
        )
        self.assertIn(
            "    DiscordProfilePreview,",
            self.source,
        )

    def test_builder_uses_reusable_widget(self):
        builder = self._method_source(
            "build_discord_preview_card",
            "open_discord",
        )

        self.assertIn(
            "DiscordProfilePreview(",
            builder,
        )
        self.assertIn(
            "self.discord_profile_preview",
            builder,
        )
        self.assertNotIn(
            "self.preview_title = QLabel",
            builder,
        )
        self.assertNotIn(
            "self.preview_artwork = QLabel",
            builder,
        )

    def test_dashboard_fields_alias_new_preview(self):
        builder = self._method_source(
            "build_discord_preview_card",
            "open_discord",
        )

        required = (
            "activity_source_badge",
            "activity_application",
            "activity_artwork",
            "activity_title",
            "activity_artist",
            "activity_album",
            "activity_time",
        )

        for attribute in required:
            self.assertIn(
                f"self.preview_card.{attribute}",
                builder,
            )

    def test_dashboard_accepts_discord_identity_snapshot(self):
        method = self._method_source(
            "set_discord_profile_identity",
            "open_discord",
        )

        self.assertIn(
            "source.get(",
            method,
        )
        self.assertIn(
            '"display_name"',
            method,
        )
        self.assertIn(
            '"username"',
            method,
        )
        self.assertIn(
            '"user_id"',
            method,
        )
        self.assertIn(
            '"avatar_hash"',
            method,
        )
        self.assertIn(
            'f"@{username}"',
            method,
        )
        self.assertIn(
            "preview.set_profile(",
            method,
        )

    def test_dashboard_requests_real_discord_avatar(self):
        identity_method = self._method_source(
            "set_discord_profile_identity",
            "apply_discord_profile_avatar",
        )

        self.assertIn(
            "discord_avatar_loader",
            self.source,
        )
        self.assertIn(
            "request_avatar(",
            identity_method,
        )
        self.assertIn(
            "avatar_hash",
            identity_method,
        )

    def test_dashboard_applies_only_current_avatar(self):
        avatar_method = self._method_source(
            "apply_discord_profile_avatar",
            "open_discord",
        )

        self.assertIn(
            "_discord_profile_avatar_key",
            avatar_method,
        )
        self.assertIn(
            "avatar=pixmap",
            avatar_method,
        )
        self.assertIn(
            "pixmap.isNull()",
            avatar_method,
        )

    def test_open_discord_reuses_existing_handler(self):
        builder = self._method_source(
            "build_discord_preview_card",
            "open_discord",
        )

        self.assertIn(
            "open_discord_requested.connect(",
            builder,
        )
        self.assertIn(
            "self.open_discord",
            builder,
        )

    def test_profile_is_not_personally_hardcoded(self):
        builder = self._method_source(
            "build_discord_preview_card",
            "open_discord",
        )

        self.assertIn(
            'display_name="Your Discord profile"',
            builder,
        )
        self.assertIn(
            'status="Preview"',
            builder,
        )

    def test_theme_is_forwarded_to_preview(self):
        self.assertIn(
            "discord_preview.apply_theme(",
            self.source,
        )
        self.assertIn(
            "discord_preview.set_compact(",
            self.source,
        )

    def test_exact_title_album_duplicate_is_hidden(self):
        self.assertIn(
            "preview_album.casefold()",
            self.source,
        )
        self.assertIn(
            "== preview_title_key",
            self.source,
        )
        self.assertIn(
            "self.preview_album.setHidden(",
            self.source,
        )

    def test_progress_mirror_lives_in_smooth_method(self):
        method = self._method_source(
            "refresh_playback_presentation",
            "show_nothing_playing",
        )

        self.assertIn(
            "progress_value / 100",
            method,
        )
        self.assertIn(
            "discord_preview.activity_progress.setValue(",
            method,
        )

    def test_nothing_playing_hides_preview_progress(self):
        method = self._method_source(
            "show_nothing_playing",
            "show_worker_error",
        )

        self.assertIn(
            "discord_preview.activity_progress.setHidden(",
            method,
        )
        self.assertIn(
            "True",
            method,
        )


if __name__ == "__main__":
    unittest.main()
