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


class SpotifyAlbumProductionWiringTests(
    unittest.TestCase
):
    def test_main_window_imports_album_service(
        self,
    ):
        text = source()

        self.assertIn(
            (
                "from src.spotify.album_service import (\n"
                "    SpotifyAlbumService,\n"
                ")"
            ),
            text,
        )

    def test_main_window_imports_album_runtime(
        self,
    ):
        text = source()

        self.assertIn(
            (
                "from src.spotify.qt_album_runtime import (\n"
                "    SpotifyQtAlbumRuntime,\n"
                ")"
            ),
            text,
        )

    def test_album_service_uses_existing_session_manager(
        self,
    ):
        text = source()

        self.assertIn(
            (
                "self.spotify_album_service = (\n"
                "            SpotifyAlbumService(\n"
                "                self.spotify_session_manager\n"
                "            )\n"
                "        )"
            ),
            text,
        )

    def test_album_runtime_uses_album_service(
        self,
    ):
        text = source()

        self.assertIn(
            "self.spotify_album_runtime = (",
            text,
        )

        self.assertIn(
            "SpotifyQtAlbumRuntime(",
            text,
        )

        self.assertIn(
            "lambda service=spotify_album_service:",
            text,
        )

    def test_spotify_page_receives_album_runtime(
        self,
    ):
        text = source()

        self.assertIn(
            (
                "album_runtime=(\n"
                "                self.spotify_album_runtime\n"
                "            ),"
            ),
            text,
        )

    def test_shutdown_includes_album_runtime(
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

        shutdown_block = text[
            start:end
        ]

        self.assertIn(
            '"spotify_album_runtime"',
            shutdown_block,
        )


if __name__ == "__main__":
    unittest.main()
