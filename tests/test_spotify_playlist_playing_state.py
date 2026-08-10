from __future__ import annotations

import unittest
from types import SimpleNamespace

from PyQt6.QtWidgets import QApplication

from src.ui.main_window import MainWindow
from src.ui.spotify_page import SpotifyPage
from src.ui.spotify_playlist_detail import (
    SpotifyPlaylistDetail,
    SpotifyPlaylistTrackRow,
)


class FakePlaylistRuntime:
    def load_playlist_items(
        self,
        *_args,
        **_kwargs,
    ):
        return None


def item(
    *,
    title="Test Track",
    artist="Test Artist",
    album="Test Album",
):
    return SimpleNamespace(
        is_local=False,
        local_available=None,
        position=0,
        unified_track=SimpleNamespace(
            title=title,
            artist=artist,
            album=album,
            duration_ms=180000,
            spotify_uri=(
                "spotify:track:"
                "0123456789ABCDEFGHIJKL"
            ),
            playable=True,
        ),
    )


def song(
    *,
    title="Test Track",
    artist="Test Artist",
    album="Test Album",
    playing=True,
    source_app="Spotify.exe",
):
    return SimpleNamespace(
        title=title,
        artist=artist,
        album=album,
        playing=playing,
        source_app=source_app,
    )


class SpotifyPlaylistPlayingStateTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = (
            QApplication.instance()
            or QApplication(
                []
            )
        )

    def make_row(
        self,
        **kwargs,
    ):
        row = (
            SpotifyPlaylistTrackRow(
                item(
                    **kwargs
                ),
                number=3,
            )
        )

        self.addCleanup(
            row.deleteLater
        )

        return row

    def make_detail(
        self,
    ):
        detail = SpotifyPlaylistDetail(
            FakePlaylistRuntime()
        )

        self.addCleanup(
            detail.deleteLater
        )

        return detail

    def test_row_playing_state_updates_visual_identity(
        self,
    ):
        row = self.make_row()

        self.assertFalse(
            row.playing
        )

        self.assertEqual(
            row.number_label.text(),
            "3",
        )

        self.assertTrue(
            row.set_playing(
                True
            )
        )

        self.assertTrue(
            row.playing
        )

        self.assertTrue(
            bool(
                row.property(
                    "playing"
                )
            )
        )

        self.assertEqual(
            row.number_label.text(),
            "3",
        )

        self.assertTrue(
            row.set_playing(
                False
            )
        )

        self.assertFalse(
            row.playing
        )

        self.assertEqual(
            row.number_label.text(),
            "3",
        )

    def test_matching_spotify_song_highlights_row(
        self,
    ):
        detail = self.make_detail()

        matching = self.make_row(
            title="STREETLIGHTS",
            artist="WesGhost",
            album="STREETLIGHTS",
        )

        other = self.make_row(
            title="Different Track",
            artist="WesGhost",
            album="Different Album",
        )

        detail.rows = [
            matching,
            other,
        ]

        detail.set_current_song(
            song(
                title="  STREETLIGHTS ",
                artist="wesghost",
                album="STREETLIGHTS",
            )
        )

        self.assertTrue(
            matching.playing
        )

        self.assertFalse(
            other.playing
        )

    def test_track_change_moves_highlight(
        self,
    ):
        detail = self.make_detail()

        first = self.make_row(
            title="First",
            artist="Artist",
        )

        second = self.make_row(
            title="Second",
            artist="Artist",
        )

        detail.rows = [
            first,
            second,
        ]

        detail.set_current_song(
            song(
                title="First",
                artist="Artist",
            )
        )

        self.assertTrue(
            first.playing
        )

        self.assertFalse(
            second.playing
        )

        detail.set_current_song(
            song(
                title="Second",
                artist="Artist",
            )
        )

        self.assertFalse(
            first.playing
        )

        self.assertTrue(
            second.playing
        )

    def test_paused_song_clears_highlight(
        self,
    ):
        detail = self.make_detail()

        row = self.make_row()

        detail.rows = [
            row,
        ]

        detail.set_current_song(
            song()
        )

        self.assertTrue(
            row.playing
        )

        detail.set_current_song(
            song(
                playing=False
            )
        )

        self.assertFalse(
            row.playing
        )

    def test_non_spotify_source_clears_highlight(
        self,
    ):
        detail = self.make_detail()

        row = self.make_row()

        detail.rows = [
            row,
        ]

        detail.set_current_song(
            song()
        )

        self.assertTrue(
            row.playing
        )

        detail.set_current_song(
            song(
                source_app=(
                    "Google Chrome"
                )
            )
        )

        self.assertFalse(
            row.playing
        )

    def test_duplicate_identity_does_not_guess(
        self,
    ):
        detail = self.make_detail()

        first = self.make_row(
            title="Duplicate",
            artist="Artist",
            album="Same Album",
        )

        second = self.make_row(
            title="Duplicate",
            artist="Artist",
            album="Same Album",
        )

        detail.rows = [
            first,
            second,
        ]

        detail.set_current_song(
            song(
                title="Duplicate",
                artist="Artist",
                album="Same Album",
            )
        )

        self.assertFalse(
            first.playing
        )

        self.assertFalse(
            second.playing
        )

    def test_album_disambiguates_duplicate_title_artist(
        self,
    ):
        detail = self.make_detail()

        first = self.make_row(
            title="Duplicate",
            artist="Artist",
            album="Album One",
        )

        second = self.make_row(
            title="Duplicate",
            artist="Artist",
            album="Album Two",
        )

        detail.rows = [
            first,
            second,
        ]

        detail.set_current_song(
            song(
                title="Duplicate",
                artist="Artist",
                album="Album Two",
            )
        )

        self.assertFalse(
            first.playing
        )

        self.assertTrue(
            second.playing
        )

    def test_newly_loaded_row_inherits_current_song(
        self,
    ):
        detail = self.make_detail()

        detail.set_current_song(
            song(
                title="Loaded Later",
                artist="Artist",
                album="Album",
            )
        )

        page = SimpleNamespace(
            items=(
                item(
                    title="Loaded Later",
                    artist="Artist",
                    album="Album",
                ),
            ),
            offset=0,
            limit=50,
            total=1,
            omitted_items=0,
            local_count=0,
            unavailable_local_count=0,
        )

        complete = (
            detail
            ._append_resolved_page(
                page,
                local_snapshot_available=True,
            )
        )

        self.assertTrue(
            complete
        )

        self.assertEqual(
            len(
                detail.rows
            ),
            1,
        )

        self.assertTrue(
            detail.rows[0].playing
        )

    def test_spotify_page_forwards_current_song(
        self,
    ):
        observed = []

        current = song()

        page = SimpleNamespace(
            _current_song=None,
            playlist_detail=(
                SimpleNamespace(
                    set_current_song=(
                        observed.append
                    )
                )
            ),
        )

        SpotifyPage.set_current_song(
            page,
            current,
        )

        self.assertIs(
            page._current_song,
            current,
        )

        self.assertEqual(
            observed,
            [
                current,
            ],
        )

    def test_main_window_forwards_media_truth_to_spotify(
        self,
    ):
        events = []

        current = song(
            title="Forwarded Song"
        )

        window = SimpleNamespace(
            dashboard_page=(
                SimpleNamespace(
                    restore_cached_song_artwork=(
                        lambda value:
                        events.append(
                            (
                                "restore",
                                value,
                            )
                        )
                    )
                )
            ),
            spotify_page=(
                SimpleNamespace(
                    set_current_song=(
                        lambda value:
                        events.append(
                            (
                                "spotify",
                                value,
                            )
                        )
                    )
                )
            ),
            presence_controller=(
                SimpleNamespace(
                    handle_song=(
                        lambda value:
                        events.append(
                            (
                                "presence",
                                value,
                            )
                        )
                    )
                )
            ),
            library_page=(
                SimpleNamespace(
                    add_song=(
                        lambda value:
                        events.append(
                            (
                                "library",
                                value,
                            )
                        )
                    )
                )
            ),
        )

        MainWindow.handle_song_update(
            window,
            current,
        )

        self.assertEqual(
            [
                name
                for (
                    name,
                    _value,
                )
                in events
            ],
            [
                "restore",
                "spotify",
                "presence",
                "library",
            ],
        )

        for (
            _name,
            value,
        ) in events:
            self.assertIs(
                value,
                current,
            )


    def test_missing_spotify_page_does_not_block_other_consumers(
        self,
    ):
        events = []

        current = song(
            title="Compatibility Song"
        )

        window = SimpleNamespace(
            dashboard_page=(
                SimpleNamespace(
                    restore_cached_song_artwork=(
                        lambda value:
                        events.append(
                            (
                                "restore",
                                value,
                            )
                        )
                    )
                )
            ),
            presence_controller=(
                SimpleNamespace(
                    handle_song=(
                        lambda value:
                        events.append(
                            (
                                "presence",
                                value,
                            )
                        )
                    )
                )
            ),
            library_page=(
                SimpleNamespace(
                    add_song=(
                        lambda value:
                        events.append(
                            (
                                "library",
                                value,
                            )
                        )
                    )
                )
            ),
        )

        MainWindow.handle_song_update(
            window,
            current,
        )

        self.assertEqual(
            [
                name
                for (
                    name,
                    _value,
                )
                in events
            ],
            [
                "restore",
                "presence",
                "library",
            ],
        )

        for (
            _name,
            value,
        ) in events:
            self.assertIs(
                value,
                current,
            )

if __name__ == "__main__":
    unittest.main()
