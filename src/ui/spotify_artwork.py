from __future__ import annotations

from collections import OrderedDict
from urllib.parse import urlsplit

from PyQt6.QtCore import (
    QObject,
    QUrl,
    pyqtSignal,
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtNetwork import (
    QNetworkAccessManager,
    QNetworkReply,
    QNetworkRequest,
)


DEFAULT_SPOTIFY_ARTWORK_CACHE_ENTRIES = 128
DEFAULT_SPOTIFY_ARTWORK_MAX_BYTES = (
    4
    * 1024
    * 1024
)
DEFAULT_SPOTIFY_ARTWORK_TIMEOUT_MS = 8000


def _checked_positive_integer(
    value,
    name: str,
) -> int:
    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            int,
        )
    ):
        raise TypeError(
            name
            + " must be an integer"
        )

    if value <= 0:
        raise ValueError(
            name
            + " must be greater than zero"
        )

    return value


def validate_spotify_artwork_url(
    value,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            "artwork URL must be a string"
        )

    checked = value.strip()

    if not checked:
        raise ValueError(
            "artwork URL cannot be empty"
        )

    parsed = urlsplit(
        checked
    )

    if (
        parsed.scheme.casefold()
        != "https"
    ):
        raise ValueError(
            (
                "Spotify artwork must use "
                "HTTPS."
            )
        )

    if not parsed.hostname:
        raise ValueError(
            (
                "Spotify artwork URL must "
                "contain a host."
            )
        )

    if (
        parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError(
            (
                "Spotify artwork URL cannot "
                "contain credentials."
            )
        )

    return checked


class SpotifyArtworkLoader(
    QObject
):
    artwork_ready = pyqtSignal(
        str,
        object,
    )

    artwork_failed = pyqtSignal(
        str
    )

    def __init__(
        self,
        *,
        network_manager=None,
        cache_entries: int = (
            DEFAULT_SPOTIFY_ARTWORK_CACHE_ENTRIES
        ),
        max_bytes: int = (
            DEFAULT_SPOTIFY_ARTWORK_MAX_BYTES
        ),
        timeout_ms: int = (
            DEFAULT_SPOTIFY_ARTWORK_TIMEOUT_MS
        ),
        parent=None,
    ) -> None:
        super().__init__(
            parent
        )

        self._cache_entries = (
            _checked_positive_integer(
                cache_entries,
                "cache_entries",
            )
        )

        self._max_bytes = (
            _checked_positive_integer(
                max_bytes,
                "max_bytes",
            )
        )

        self._timeout_ms = (
            _checked_positive_integer(
                timeout_ms,
                "timeout_ms",
            )
        )

        if network_manager is None:
            network_manager = (
                QNetworkAccessManager(
                    self
                )
            )

        get = getattr(
            network_manager,
            "get",
            None,
        )

        if not callable(
            get
        ):
            raise TypeError(
                (
                    "network_manager must provide "
                    "a callable get method"
                )
            )

        self._network_manager = (
            network_manager
        )

        self._cache = OrderedDict()
        self._pending = {}

    @property
    def cache_size(
        self,
    ) -> int:
        return len(
            self._cache
        )

    @property
    def pending_count(
        self,
    ) -> int:
        return len(
            self._pending
        )

    def cached_pixmap(
        self,
        artwork_url,
    ):
        try:
            checked = (
                validate_spotify_artwork_url(
                    artwork_url
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

        pixmap = self._cache.get(
            checked
        )

        if pixmap is None:
            return None

        self._cache.move_to_end(
            checked
        )

        return pixmap

    def request(
        self,
        artwork_url,
    ) -> bool:
        checked = (
            validate_spotify_artwork_url(
                artwork_url
            )
        )

        cached = self.cached_pixmap(
            checked
        )

        if cached is not None:
            self.artwork_ready.emit(
                checked,
                cached,
            )

            return False

        if checked in self._pending:
            return False

        request = QNetworkRequest(
            QUrl(
                checked
            )
        )

        request.setRawHeader(
            b"Accept",
            b"image/*",
        )

        request.setRawHeader(
            b"User-Agent",
            b"03:37am Presence",
        )

        try:
            request.setTransferTimeout(
                self._timeout_ms
            )
        except Exception:
            pass

        try:
            reply = (
                self._network_manager
                .get(
                    request
                )
            )

        except Exception:
            self.artwork_failed.emit(
                checked
            )
            return False

        if reply is None:
            self.artwork_failed.emit(
                checked
            )
            return False

        finished = getattr(
            reply,
            "finished",
            None,
        )

        if finished is None:
            self.artwork_failed.emit(
                checked
            )
            return False

        self._pending[
            checked
        ] = reply

        finished.connect(
            lambda url=checked, active_reply=reply:
            self._finish_request(
                url,
                active_reply,
            )
        )

        return True

    def _finish_request(
        self,
        artwork_url: str,
        reply,
    ) -> None:
        active = self._pending.get(
            artwork_url
        )

        if active is not reply:
            return

        self._pending.pop(
            artwork_url,
            None,
        )

        try:
            error = reply.error()

            if (
                error
                != QNetworkReply.NetworkError.NoError
            ):
                self.artwork_failed.emit(
                    artwork_url
                )
                return

            payload = bytes(
                reply.readAll()
            )

            if (
                not payload
                or len(
                    payload
                )
                > self._max_bytes
            ):
                self.artwork_failed.emit(
                    artwork_url
                )
                return

            pixmap = QPixmap()

            if not pixmap.loadFromData(
                payload
            ):
                self.artwork_failed.emit(
                    artwork_url
                )
                return

            self._cache[
                artwork_url
            ] = pixmap

            self._cache.move_to_end(
                artwork_url
            )

            while (
                len(
                    self._cache
                )
                > self._cache_entries
            ):
                self._cache.popitem(
                    last=False
                )

            self.artwork_ready.emit(
                artwork_url,
                pixmap,
            )

        except Exception:
            self.artwork_failed.emit(
                artwork_url
            )

        finally:
            try:
                reply.deleteLater()
            except Exception:
                pass

    def clear_cache(
        self,
    ) -> None:
        self._cache.clear()

    def shutdown(
        self,
    ) -> None:
        replies = tuple(
            self._pending.values()
        )

        self._pending.clear()

        for reply in replies:
            try:
                reply.abort()
            except Exception:
                pass

            try:
                reply.deleteLater()
            except Exception:
                pass
