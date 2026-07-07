from dataclasses import dataclass


@dataclass
class Song:
    title: str = ""
    artist: str = ""
    album: str = ""

    duration: str = "0:00"
    position: str = "0:00"

    playing: bool = False

    # Raw image data supplied by Windows Media.
    artwork_bytes: bytes | None = None

    # The Windows application providing the media session.
    source_app: str = ""