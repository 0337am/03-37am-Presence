from src.music.windows_media import WindowsMedia
from src.music.song import Song


class MusicManager:
    """
    Central music engine for the entire application.

    Every part of 03:37am Presence gets its song information
    from here.

    Dashboard
        │
        ├── Discord
        ├── Artwork
        └── Future integrations
    """

    def __init__(self):

        self.windows = WindowsMedia()

    def connect(self):

        print("🎵 Music Manager ready.")

    def get_current_song(self) -> Song:

        song = self.windows.get_current_song()

        if song is None:
            return Song()

        return song