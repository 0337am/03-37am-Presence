from __future__ import annotations

import ast
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.ui.spotify_liked_songs_detail import (
    SpotifyLikedSongsDetail,
)
from src.ui.spotify_page import (
    SpotifyPage,
)


class FakeRow:
    def __init__(
        self,
        *,
        title="Test Track",
        artist="Test Artist",
        album="Test Album",
    ):
        self.resolved_item = (
            SimpleNamespace(
                unified_track=(
                    SimpleNamespace(
                        title=title,
                        artist=artist,
                        album=album,
                    )
                )
            )
        )

        self.playing = False

    def set_playing(
        self,
        playing,
    ):
        self.playing = bool(
            playing
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


def detail_with_rows(
    *rows,
):
    detail = SimpleNamespace(
        rows=list(
            rows
        ),
        _current_song=None,
    )

    detail._normalize_identity = (
        SpotifyLikedSongsDetail
        ._normalize_identity
    )

    detail._row_identity = (
        SpotifyLikedSongsDetail
        ._row_identity
    )

    detail._artist_identity_matches = (
        SpotifyLikedSongsDetail
        ._artist_identity_matches
    )

    detail._refresh_playing_state = (
        lambda:
        SpotifyLikedSongsDetail
        ._refresh_playing_state(
            detail
        )
    )

    return detail


class SpotifyLikedSongsPlayingStateTests(
    unittest.TestCase
):
    def test_matching_spotify_song_highlights_row(
        self,
    ):
        matching = FakeRow(
            title="feelz",
            artist="Lil Peep",
            album="feelz",
        )

        other = FakeRow(
            title="Different",
            artist="Lil Peep",
            album="Different",
        )

        detail = detail_with_rows(
            matching,
            other,
        )

        SpotifyLikedSongsDetail.set_current_song(
            detail,
            song(
                title="  FEELZ ",
                artist="lil peep",
                album="FEELZ",
            ),
        )

        self.assertTrue(
            matching.playing
        )

        self.assertFalse(
            other.playing
        )

    def test_switching_song_moves_highlight(
        self,
    ):
        first = FakeRow(
            title="First",
            artist="Artist",
            album="One",
        )

        second = FakeRow(
            title="Second",
            artist="Artist",
            album="Two",
        )

        detail = detail_with_rows(
            first,
            second,
        )

        SpotifyLikedSongsDetail.set_current_song(
            detail,
            song(
                title="First",
                artist="Artist",
                album="One",
            ),
        )

        self.assertTrue(
            first.playing
        )

        self.assertFalse(
            second.playing
        )

        SpotifyLikedSongsDetail.set_current_song(
            detail,
            song(
                title="Second",
                artist="Artist",
                album="Two",
            ),
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
        row = FakeRow()

        detail = detail_with_rows(
            row
        )

        SpotifyLikedSongsDetail.set_current_song(
            detail,
            song(),
        )

        self.assertTrue(
            row.playing
        )

        SpotifyLikedSongsDetail.set_current_song(
            detail,
            song(
                playing=False
            ),
        )

        self.assertFalse(
            row.playing
        )

    def test_non_spotify_source_clears_highlight(
        self,
    ):
        row = FakeRow()

        detail = detail_with_rows(
            row
        )

        SpotifyLikedSongsDetail.set_current_song(
            detail,
            song(),
        )

        self.assertTrue(
            row.playing
        )

        SpotifyLikedSongsDetail.set_current_song(
            detail,
            song(
                source_app="Google Chrome",
            ),
        )

        self.assertFalse(
            row.playing
        )

    def test_duplicate_identity_does_not_guess(
        self,
    ):
        first = FakeRow(
            title="Duplicate",
            artist="Artist",
            album="Same Album",
        )

        second = FakeRow(
            title="Duplicate",
            artist="Artist",
            album="Same Album",
        )

        detail = detail_with_rows(
            first,
            second,
        )

        SpotifyLikedSongsDetail.set_current_song(
            detail,
            song(
                title="Duplicate",
                artist="Artist",
                album="Same Album",
            ),
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
        first = FakeRow(
            title="Duplicate",
            artist="Artist",
            album="Album One",
        )

        second = FakeRow(
            title="Duplicate",
            artist="Artist",
            album="Album Two",
        )

        detail = detail_with_rows(
            first,
            second,
        )

        SpotifyLikedSongsDetail.set_current_song(
            detail,
            song(
                title="Duplicate",
                artist="Artist",
                album="Album Two",
            ),
        )

        self.assertFalse(
            first.playing
        )

        self.assertTrue(
            second.playing
        )

    def test_spotify_page_forwards_to_both_details(
        self,
    ):
        current = song()

        playlist_observed = []
        liked_observed = []

        page = SimpleNamespace(
            _current_song=None,
            playlist_detail=(
                SimpleNamespace(
                    set_current_song=(
                        playlist_observed.append
                    )
                )
            ),
            liked_songs_detail=(
                SimpleNamespace(
                    set_current_song=(
                        liked_observed.append
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
            playlist_observed,
            [
                current,
            ],
        )

        self.assertEqual(
            liked_observed,
            [
                current,
            ],
        )

    def test_spotify_page_tolerates_missing_liked_detail(
        self,
    ):
        current = song()

        observed = []

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

        self.assertEqual(
            observed,
            [
                current,
            ],
        )

    def test_row_population_refreshes_playing_state(
        self,
    ):
        root = (
            Path(__file__)
            .resolve()
            .parents[1]
        )

        path = (
            root
            / "src"
            / "ui"
            / "spotify_liked_songs_detail.py"
        )

        source = path.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(
            source
        )

        classes = [
            node
            for node in tree.body
            if (
                isinstance(
                    node,
                    ast.ClassDef,
                )
                and node.name
                == "SpotifyLikedSongsDetail"
            )
        ]

        self.assertEqual(
            len(
                classes
            ),
            1,
        )

        population_loops = []

        for method in classes[0].body:
            if not isinstance(
                method,
                ast.FunctionDef,
            ):
                continue

            for index, statement in enumerate(
                method.body
            ):
                if not isinstance(
                    statement,
                    ast.For,
                ):
                    continue

                segment = (
                    ast.get_source_segment(
                        source,
                        statement,
                    )
                    or ""
                )

                if (
                    "self.rows.append"
                    not in segment
                ):
                    continue

                population_loops.append(
                    (
                        method,
                        index,
                    )
                )

        self.assertEqual(
            len(
                population_loops
            ),
            1,
        )

        method, loop_index = (
            population_loops[0]
        )

        self.assertLess(
            loop_index + 1,
            len(
                method.body
            ),
        )

        following = (
            method.body[
                loop_index + 1
            ]
        )

        self.assertIsInstance(
            following,
            ast.Expr,
        )

        call = following.value

        self.assertIsInstance(
            call,
            ast.Call,
        )

        self.assertIsInstance(
            call.func,
            ast.Attribute,
        )

        self.assertEqual(
            call.func.attr,
            "_refresh_playing_state",
        )


    def test_primary_artist_matches_spotify_collaboration(
        self,
    ):
        row = FakeRow(
            title="big city blues",
            artist="Lil Peep, Cold Hart",
            album="crybaby",
        )

        detail = detail_with_rows(
            row
        )

        SpotifyLikedSongsDetail.set_current_song(
            detail,
            song(
                title="big city blues",
                artist="Lil Peep",
                album="crybaby",
            ),
        )

        self.assertTrue(
            row.playing
        )

    def test_secondary_collaborator_does_not_match(
        self,
    ):
        row = FakeRow(
            title="big city blues",
            artist="Lil Peep, Cold Hart",
            album="crybaby",
        )

        detail = detail_with_rows(
            row
        )

        SpotifyLikedSongsDetail.set_current_song(
            detail,
            song(
                title="big city blues",
                artist="Cold Hart",
                album="crybaby",
            ),
        )

        self.assertFalse(
            row.playing
        )

    def test_primary_artist_fallback_keeps_album_disambiguation(
        self,
    ):
        first = FakeRow(
            title="Duplicate",
            artist="Primary Artist, Guest",
            album="Album One",
        )

        second = FakeRow(
            title="Duplicate",
            artist="Primary Artist, Guest",
            album="Album Two",
        )

        detail = detail_with_rows(
            first,
            second,
        )

        SpotifyLikedSongsDetail.set_current_song(
            detail,
            song(
                title="Duplicate",
                artist="Primary Artist",
                album="Album Two",
            ),
        )

        self.assertFalse(
            first.playing
        )

        self.assertTrue(
            second.playing
        )

if __name__ == "__main__":
    unittest.main()
