import unittest
from pathlib import Path


SPOTIFY_PAGE = Path(
    "src/ui/spotify_page.py"
)


def source():
    return SPOTIFY_PAGE.read_text(
        encoding="utf-8-sig"
    ).replace(
        "\r\n",
        "\n",
    )


class SpotifyArtistPageIntegrationTests(
    unittest.TestCase
):
    def test_page_imports_artist_detail(
        self,
    ):
        text = source()

        self.assertIn(
            (
                "from src.ui.spotify_artist_detail import (\n"
                "    SpotifyArtistDetail,\n"
                ")"
            ),
            text,
        )

    def test_artist_detail_uses_next_stack_index(
        self,
    ):
        text = source()

        self.assertIn(
            "SPOTIFY_ARTIST_DETAIL_INDEX = 5",
            text,
        )

    def test_constructor_accepts_artist_runtime(
        self,
    ):
        text = source()

        self.assertIn(
            "artist_runtime=None,",
            text,
        )

        self.assertIn(
            (
                "self.artist_runtime = (\n"
                "            artist_runtime\n"
                "        )"
            ),
            text,
        )

    def test_artist_detail_is_conditionally_installed(
        self,
    ):
        text = source()

        self.assertIn(
            (
                "if self.artist_runtime is not None:\n"
                "            self._install_artist_detail()"
            ),
            text,
        )

        self.assertIn(
            "SpotifyArtistDetail(",
            text,
        )

    def test_artist_detail_is_valid_section(
        self,
    ):
        text = source()

        start = text.index(
            "def _set_section("
        )

        end = text.index(
            "def show_home(",
            start,
        )

        block = text[
            start:end
        ]

        self.assertIn(
            "SPOTIFY_ARTIST_DETAIL_INDEX",
            block,
        )

    def test_artist_back_signal_is_connected(
        self,
    ):
        text = source()

        self.assertIn(
            (
                "artist_detail.back_requested.connect(\n"
                "                "
                "self._show_artist_detail_return_section\n"
                "            )"
            ),
            text,
        )

    def test_show_artist_detail_seeds_and_loads_component(
        self,
    ):
        text = source()

        start = text.index(
            "def show_artist_detail("
        )

        end = text.index(
            "def _show_playlist_detail_return_section(",
            start,
        )

        block = text[
            start:end
        ]

        self.assertIn(
            "artist_detail.set_artist_id(",
            block,
        )

        self.assertIn(
            "SPOTIFY_ARTIST_DETAIL_INDEX",
            block,
        )

        self.assertIn(
            "artist_detail.load()",
            block,
        )

    def test_search_artist_activation_is_wired(
        self,
    ):
        source = (
            (
                Path(
                    __file__
                )
                .resolve()
                .parents[
                    1
                ]
                / "src"
                / "ui"
                / "spotify_page.py"
            )
            .read_text(
                encoding="utf-8-sig"
            )
        )

        self.assertIn(
            (
                "self.search_page."
                "artist_activated.connect("
            ),
            source,
        )

        self.assertIn(
            (
                "self."
                "_handle_search_artist_activated"
            ),
            source,
        )


if __name__ == "__main__":
    unittest.main()
