import hashlib
import queue
import threading
import time

from src.discord.ready_identity_presence import (
    ReadyIdentityPresence as Presence,
)

from src.artwork.uploader import (
    ArtworkUploader,
)
from src.discord.identity_preferences import (
    DEFAULT_DISCORD_APPLICATION_ID,
    safe_discord_application_id,
)


try:
    from pypresence.types import ActivityType
except ImportError:
    ActivityType = None


_NO_ITEM = object()
_STOP = object()


class DiscordPresence:
    """
    Maintains Discord Rich Presence on a background thread.

    Discord operations never run on Qt's UI thread.
    """

    RECONNECT_DELAY_SECONDS = 5.0
    MIN_UPDATE_INTERVAL_SECONDS = 15.0

    def __init__(
        self,
        artwork_uploader=None,
        client_id=None,
    ):
        requested_client_id = (
            DEFAULT_DISCORD_APPLICATION_ID
            if client_id is None
            else client_id
        )

        self.client_id = (
            safe_discord_application_id(
                requested_client_id
            )
        )

        self.artwork_uploader = (
            artwork_uploader
            or ArtworkUploader()
        )

        self.rpc = None

        self._updates = queue.Queue(maxsize=1)
        self._stop_event = threading.Event()
        self._thread = None

        self._identity_lock = threading.Lock()
        self._reconnect_event = threading.Event()

        self._state_lock = threading.Lock()
        self._connected = False
        self._last_error = ""

        self._profile_identity_lock = (
            threading.Lock()
        )
        self._profile_identity = {}

    @property
    def profile_identity(self) -> dict:
        with self._profile_identity_lock:
            return dict(
                self._profile_identity
            )

    def _set_profile_identity(
        self,
        identity,
    ):
        source = (
            identity
            if isinstance(identity, dict)
            else {}
        )

        snapshot = {}

        for key in (
            "user_id",
            "username",
            "display_name",
            "avatar_hash",
        ):
            value = str(
                source.get(key)
                or ""
            ).strip()

            if value:
                snapshot[key] = value

        with self._profile_identity_lock:
            self._profile_identity = snapshot

    @property
    def is_connected(self) -> bool:
        with self._state_lock:
            return self._connected

    @property
    def is_running(self) -> bool:
        thread = self._thread

        return (
            thread is not None
            and thread.is_alive()
            and not self._stop_event.is_set()
        )

    @property
    def last_error(self) -> str:
        with self._state_lock:
            return self._last_error

    @property
    def active_client_id(self) -> str:
        with self._identity_lock:
            return self.client_id

    def request_client_id(
        self,
        client_id,
    ) -> str:
        requested = (
            safe_discord_application_id(
                client_id
            )
        )

        with self._identity_lock:
            changed = (
                requested
                != self.client_id
            )

            self.client_id = requested

        if (
            changed
            and self.is_running
        ):
            self._reconnect_event.set()

        return requested

    def connect(self) -> bool:
        if self.is_running:
            return True

        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._run,
            name="DiscordPresenceWorker",
            daemon=True,
        )

        self._thread.start()

        print("Discord worker started.")
        return True

    def update_song(self, song):
        if self._stop_event.is_set():
            return

        self._replace_queued_item(song)

    def close(self):
        if self._stop_event.is_set():
            return

        self._stop_event.set()
        self._replace_queued_item(_STOP)

        thread = self._thread

        if thread is not None and thread.is_alive():
            thread.join(timeout=5.0)

        self._thread = None

    def _run(self):
        pending_song = _NO_ITEM
        last_published_item = _NO_ITEM
        last_presence_key = _NO_ITEM
        last_playing_state = _NO_ITEM
        last_update_time = 0.0

        try:
            while not self._stop_event.is_set():
                if self._reconnect_event.is_set():
                    self._reconnect_event.clear()

                    self._disconnect(
                        clear_presence=True
                    )

                    if (
                        last_published_item
                        is not _NO_ITEM
                    ):
                        pending_song = (
                            last_published_item
                        )

                    last_presence_key = _NO_ITEM
                    last_playing_state = _NO_ITEM
                    last_update_time = 0.0

                if self.rpc is None:
                    if not self._open_connection():
                        self._stop_event.wait(
                            self.RECONNECT_DELAY_SECONDS
                        )
                        continue

                    last_presence_key = _NO_ITEM
                    last_playing_state = _NO_ITEM
                    last_update_time = 0.0

                queued_item = self._get_queued_item(
                    timeout=0.5
                )

                if queued_item is _STOP:
                    break

                if queued_item is not _NO_ITEM:
                    pending_song = queued_item

                    newest_item = self._drain_queue()

                    if newest_item is _STOP:
                        break

                    if newest_item is not _NO_ITEM:
                        pending_song = newest_item

                if pending_song is _NO_ITEM:
                    continue

                pending_playing_state = getattr(
                    pending_song,
                    "playing",
                    _NO_ITEM,
                )

                if (
                    pending_playing_state
                    is not _NO_ITEM
                ):
                    pending_playing_state = bool(
                        pending_playing_state
                    )

                playback_state_changed = (
                    pending_playing_state
                    is not _NO_ITEM
                    and last_playing_state
                    is not _NO_ITEM
                    and pending_playing_state
                    != last_playing_state
                )

                elapsed = (
                    time.monotonic()
                    - last_update_time
                )

                if (
                    elapsed
                    < self.MIN_UPDATE_INTERVAL_SECONDS
                    and not playback_state_changed
                ):
                    continue

                presence_key = self._make_presence_key(
                    pending_song
                )

                if presence_key == last_presence_key:
                    pending_song = _NO_ITEM
                    continue

                try:
                    self._publish_song(pending_song)

                except Exception as error:
                    self._record_error(
                        f"Discord update failed: {error}"
                    )

                    self._disconnect()
                    continue

                last_published_item = (
                    pending_song
                )
                last_presence_key = presence_key
                last_playing_state = (
                    pending_playing_state
                )
                last_update_time = time.monotonic()
                pending_song = _NO_ITEM

        finally:
            self._disconnect(clear_presence=True)

    def _open_connection(self) -> bool:
        try:
            client_id = (
                self.active_client_id
            )

            rpc = Presence(
                client_id
            )
            rpc.connect()

            self.rpc = rpc

            self._set_profile_identity(
                getattr(
                    rpc,
                    "ready_identity",
                    {},
                )
            )

            self._set_connection_state(
                connected=True,
                error="",
            )

            print("Connected to Discord!")
            return True

        except Exception as error:
            self.rpc = None

            self._set_connection_state(
                connected=False,
                error=(
                    "Discord connection failed: "
                    f"{error}"
                ),
            )

            self._print_error_once()
            return False

    @staticmethod
    def _discord_music_identity(
        value,
    ) -> str:
        normalized = " ".join(
            str(
                value
                or ""
            ).strip().split()
        ).casefold()

        for suffix in (
            " - single",
            " (single)",
            " [single]",
        ):
            if normalized.endswith(
                suffix
            ):
                normalized = normalized[
                    :-len(suffix)
                ].strip()
                break

        return normalized

    @classmethod
    def _discord_album_for_track(
        cls,
        title,
        album,
    ) -> str:
        raw_album = str(
            album
            or ""
        ).strip()

        if (
            not raw_album
            or raw_album.casefold()
            in {
                "unknown",
                "unknown album",
                "none",
            }
        ):
            return ""

        title_identity = (
            cls._discord_music_identity(
                title
            )
        )

        album_identity = (
            cls._discord_music_identity(
                raw_album
            )
        )

        if (
            title_identity
            and album_identity
            and title_identity
            == album_identity
        ):
            return ""

        return raw_album

    def _publish_song(self, song):
        if (
            song is None
            or not getattr(song, "title", "")
        ):
            self.rpc.clear()
            print("Discord presence cleared.")
            return

        title = self._discord_text(
            getattr(song, "title", ""),
            fallback="Unknown track",
        )

        artist = self._discord_text(
            getattr(song, "artist", ""),
            fallback="Unknown artist",
        )

        raw_album = self._discord_album_for_track(
            getattr(song, "title", ""),
            getattr(song, "album", ""),
        )

        album_is_available = bool(
            raw_album
        )

        album = (
            self._discord_text(
                raw_album,
                fallback="",
            )
            if album_is_available
            else ""
        )

        playing = bool(
            getattr(song, "playing", False)
        )

        if playing:
            state = self._discord_text(
                f"by {artist}",
                fallback="Now playing",
            )
        else:
            state = self._discord_text(
                f"Paused \u2022 {artist}",
                fallback="Paused",
            )

        options = {
            "details": title,
            "state": state,
        }

        if ActivityType is not None:
            options["activity_type"] = (
                ActivityType.LISTENING
            )

        if playing:
            position_seconds = self._time_to_seconds(
                getattr(
                    song,
                    "position",
                    "0:00",
                )
            )

            options["start"] = (
                int(time.time())
                - position_seconds
            )

        artwork_bytes = getattr(
            song,
            "artwork_bytes",
            None,
        )

        local_artwork_available = bool(
            artwork_bytes
        )

        artwork_url = None

        try:
            if (
                local_artwork_available
                and self.artwork_uploader.is_configured
            ):
                artwork_url = (
                    self.artwork_uploader
                    .get_or_upload(
                        artwork_bytes
                    )
                )

        except Exception as error:
            print(
                "Artwork upload failed; "
                "continuing without Discord artwork: "
                f"{error}"
            )

        if artwork_url:
            options["large_image"] = (
                artwork_url
            )

            if album_is_available:
                options["large_text"] = (
                    self._discord_text(
                        album,
                        fallback="",
                    )
                )

        self.rpc.update(
            **options
        )

        status = (
            "Playing"
            if playing
            else "Paused"
        )

        if artwork_url:
            artwork_status = (
                "personal Cloudinary artwork"
            )

        elif local_artwork_available:
            artwork_status = (
                "local artwork kept on device"
            )

        else:
            artwork_status = (
                "no local artwork"
            )

        album_status = (
            f", album: {album}"
            if album_is_available
            else ", no distinct album supplied"
        )

        print(
            f"Discord updated: {title} - {artist} "
            f"({status}, {artwork_status}"
            f"{album_status})"
        )

    def _disconnect(
        self,
        clear_presence: bool = False,
    ):
        rpc = self.rpc
        self.rpc = None

        if rpc is not None:
            if clear_presence:
                try:
                    rpc.clear()
                except Exception:
                    pass

            try:
                rpc.close()
            except Exception:
                pass

        self._set_connection_state(
            connected=False,
            error=self.last_error,
        )

    def _replace_queued_item(self, item):
        while True:
            try:
                self._updates.get_nowait()
            except queue.Empty:
                break

        try:
            self._updates.put_nowait(item)
        except queue.Full:
            pass

    def _get_queued_item(
        self,
        timeout: float,
    ):
        try:
            return self._updates.get(
                timeout=timeout
            )
        except queue.Empty:
            return _NO_ITEM

    def _drain_queue(self):
        newest_item = _NO_ITEM

        while True:
            try:
                item = self._updates.get_nowait()
            except queue.Empty:
                return newest_item

            if item is _STOP:
                return _STOP

            newest_item = item

    @staticmethod
    def _make_presence_key(song):
        if song is None:
            return ("nothing-playing",)

        artwork_bytes = getattr(
            song,
            "artwork_bytes",
            None,
        )

        if artwork_bytes:
            artwork_key = hashlib.sha256(
                artwork_bytes
            ).hexdigest()
        else:
            artwork_key = ""

        return (
            getattr(song, "title", ""),
            getattr(song, "artist", ""),
            getattr(song, "album", ""),
            bool(
                getattr(
                    song,
                    "playing",
                    False,
                )
            ),
            getattr(song, "duration", ""),
            artwork_key,
        )

    @staticmethod
    def _time_to_seconds(
        value: str,
    ) -> int:
        try:
            parts = [
                int(part)
                for part in str(value).split(":")
            ]

            total = 0

            for part in parts:
                total = total * 60 + part

            return max(0, total)

        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _discord_text(
        value,
        fallback: str,
        maximum_utf16_bytes: int = 256,
    ) -> str:
        text = str(
            value or fallback
        ).strip()

        if not text:
            text = fallback

        while (
            len(text.encode("utf-16-le"))
            > maximum_utf16_bytes
        ):
            text = text[:-1]

        if len(text) == 1:
            text += " "

        return text

    def _record_error(
        self,
        message: str,
    ):
        with self._state_lock:
            changed = (
                message
                != self._last_error
            )

            self._last_error = message
            self._connected = False

        if changed:
            print(message)

    def _print_error_once(self):
        error = self.last_error

        if error:
            print(error)
            print(
                "Discord will be retried automatically."
            )

    def _set_connection_state(
        self,
        connected: bool,
        error: str,
    ):
        with self._state_lock:
            self._connected = connected
            self._last_error = error