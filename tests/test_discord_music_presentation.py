import unittest

from src.discord.presence import (
    DiscordPresence,
)
from src.music.song import Song


class FakeRpc:
    def __init__(self):
        self.updates = []

    def update(
        self,
        **options,
    ):
        self.updates.append(
            dict(options)
        )

    def clear(self):
        pass


class FakeArtworkUploader:
    is_configured = True

    def get_or_upload(
        self,
        _artwork_bytes,
    ):
        return (
            "https://example.invalid/"
            "artwork.png"
        )


class DiscordMusicPresentationTests(
    unittest.TestCase
):
    def publish(
        self,
        *,
        title="Track",
        artist="Artist",
        album="Album",
        playing=True,
    ):
        presence = DiscordPresence(
            artwork_uploader=(
                FakeArtworkUploader()
            )
        )

        presence.rpc = FakeRpc()

        presence._publish_song(
            Song(
                title=title,
                artist=artist,
                album=album,
                duration="3:00",
                position="0:30",
                playing=playing,
                artwork_bytes=b"art",
                source_app="Spotify.exe",
            )
        )

        self.assertEqual(
            len(presence.rpc.updates),
            1,
        )

        return presence.rpc.updates[0]

    def test_playing_state_contains_artist_only(self):
        options = self.publish(
            title="Rob And Scam",
            artist="Juice WRLD",
            album="Outsiders (Sessions)",
        )

        self.assertEqual(
            options["details"],
            "Rob And Scam",
        )

        self.assertEqual(
            options["state"],
            "by Juice WRLD",
        )

        self.assertNotIn(
            "Outsiders",
            options["state"],
        )

    def test_distinct_album_is_preserved(self):
        options = self.publish(
            title="Rob And Scam",
            artist="Juice WRLD",
            album="Outsiders (Sessions)",
        )

        self.assertEqual(
            options["large_text"],
            "Outsiders (Sessions)",
        )

    def test_exact_duplicate_album_is_removed(self):
        options = self.publish(
            title="fomo",
            artist="Fixupboy",
            album="fomo",
        )

        self.assertEqual(
            options["state"],
            "by Fixupboy",
        )

        self.assertNotIn(
            "large_text",
            options,
        )

    def test_duplicate_ignores_case_and_whitespace(self):
        options = self.publish(
            title="fomo",
            artist="Fixupboy",
            album="  FOMO  ",
        )

        self.assertNotIn(
            "large_text",
            options,
        )

    def test_single_suffix_duplicate_is_removed(self):
        options = self.publish(
            title="Example Song",
            artist="Artist",
            album="Example Song - Single",
        )

        self.assertNotIn(
            "large_text",
            options,
        )

    def test_parenthesized_single_duplicate_is_removed(self):
        options = self.publish(
            title="Example Song",
            artist="Artist",
            album="Example Song (Single)",
        )

        self.assertNotIn(
            "large_text",
            options,
        )

    def test_real_album_named_single_is_preserved(self):
        options = self.publish(
            title="Example Song",
            artist="Artist",
            album="Single",
        )

        self.assertEqual(
            options["large_text"],
            "Single",
        )

    def test_paused_state_does_not_contain_album(self):
        options = self.publish(
            title="Track",
            artist="Artist",
            album="Real Album",
            playing=False,
        )

        self.assertEqual(
            options["state"],
            "Paused \u2022 Artist",
        )

        self.assertEqual(
            options["large_text"],
            "Real Album",
        )

    def test_missing_album_does_not_repeat_title(self):
        options = self.publish(
            title="Track",
            artist="Artist",
            album="",
        )

        self.assertNotIn(
            "large_text",
            options,
        )

    def test_unknown_album_is_not_published(self):
        options = self.publish(
            title="Track",
            artist="Artist",
            album="Unknown Album",
        )

        self.assertNotIn(
            "large_text",
            options,
        )


if __name__ == "__main__":
    unittest.main()
