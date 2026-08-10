import unittest
from pathlib import Path


MAIN_WINDOW = Path(
    "src/ui/main_window.py"
)


def source():
    return MAIN_WINDOW.read_text(
        encoding="utf-8-sig"
    ).replace(
        "\r\n",
        "\n",
    )


class SpotifyArtistProductionWiringTests(
    unittest.TestCase
):
    def test_main_window_imports_artist_service(
        self,
    ):
        text = source()

        self.assertIn(
            (
                "from src.spotify.artist_service import (\n"
                "    SpotifyArtistService,\n"
                ")"
            ),
            text,
        )

    def test_main_window_imports_artist_runtime(
        self,
    ):
        text = source()

        self.assertIn(
            (
                "from src.spotify.qt_artist_runtime import (\n"
                "    SpotifyQtArtistRuntime,\n"
                ")"
            ),
            text,
        )

    def test_artist_service_uses_existing_session_manager(
        self,
    ):
        text = source()

        self.assertIn(
            (
                "self.spotify_artist_service = (\n"
                "            SpotifyArtistService(\n"
                "                self.spotify_session_manager\n"
                "            )\n"
                "        )"
            ),
            text,
        )

    def test_artist_runtime_uses_artist_service(
        self,
    ):
        text = source()

        self.assertIn(
            "self.spotify_artist_runtime = (",
            text,
        )

        self.assertIn(
            "SpotifyQtArtistRuntime(",
            text,
        )

        self.assertIn(
            "lambda service=spotify_artist_service:",
            text,
        )

    def test_spotify_page_receives_artist_runtime(
        self,
    ):
        text = source()

        self.assertIn(
            (
                "artist_runtime=(\n"
                "                self.spotify_artist_runtime\n"
                "            ),"
            ),
            text,
        )

    def test_shutdown_includes_artist_runtime(
        self,
    ):
        text = source()

        start = text.index(
            "for spotify_runtime_name in ("
        )

        end = text.index(
            "):",
            start,
        )

        block = text[
            start:end
        ]

        self.assertIn(
            '"spotify_artist_runtime"',
            block,
        )


if __name__ == "__main__":
    unittest.main()