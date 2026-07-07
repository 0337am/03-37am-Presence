from src.spotify.spotify_reader import SpotifyReader


class SpotifyMusicSource:
    """
    Handles communication with Spotify.

    Right now this wraps our existing SpotifyReader.
    Later we can completely replace the internals without
    changing the rest of the application.
    """

    def __init__(self):
        self.reader = SpotifyReader()

    def get_current_song(self):
        """
        Returns the current song from Spotify.
        """

        return self.reader.get_current_song()