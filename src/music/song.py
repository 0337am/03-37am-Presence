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
    # True when the media session explicitly reports Repeat One.
    # False means a known non-track repeat mode.
    # None means the source did not expose a trustworthy mode.
    repeat_track: bool | None = None
    # True or False when the media session reports
    # trustworthy shuffle state. None means unknown.
    shuffle_active: bool | None = None

    # Normalized media repeat state:
    # "off", "context", "track", or None when unknown.
    repeat_mode: str | None = None
