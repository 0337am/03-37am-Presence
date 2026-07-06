from dataclasses import dataclass


@dataclass
class Song:
    title: str
    artist: str
    album: str
    duration: int
    position: int
    playing: bool


class SpotifyReader:

    def get_current_song(self) -> Song:
        """
        Temporary fake data.
        Later this will read Spotify automatically.
        """

        return Song(
            title="GONE",
            artist="WESGHOST",
            album="Single",
            duration=148,
            position=53,
            playing=True
        )