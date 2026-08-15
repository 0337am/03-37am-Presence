from __future__ import annotations

from collections import OrderedDict
import re

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


DISCORD_AVATAR_SIZE = 128
DISCORD_AVATAR_MAX_BYTES = (
    2 * 1024 * 1024
)
DISCORD_AVATAR_TIMEOUT_MS = 8000
DISCORD_AVATAR_CACHE_ENTRIES = 16

_DISCORD_AVATAR_HASH_PATTERN = re.compile(
    r"^[A-Za-z0-9_]+$"
)


def _valid_discord_image_size(
    size: int,
) -> bool:
    try:
        size = int(size)
    except (
        TypeError,
        ValueError,
    ):
        return False

    return bool(
        16 <= size <= 4096
        and size & (size - 1) == 0
    )


def discord_avatar_url(
    user_id,
    avatar_hash="",
    *,
    size: int = DISCORD_AVATAR_SIZE,
) -> str:
    user_id = str(
        user_id
        or ""
    ).strip()

    avatar_hash = str(
        avatar_hash
        or ""
    ).strip()

    if (
        not user_id
        or not user_id.isascii()
        or not user_id.isdigit()
        or not _valid_discord_image_size(
            size
        )
    ):
        return ""

    if avatar_hash:
        if not _DISCORD_AVATAR_HASH_PATTERN.fullmatch(
            avatar_hash
        ):
            return ""

        return (
            "https://cdn.discordapp.com/"
            f"avatars/{user_id}/{avatar_hash}.png"
            f"?size={int(size)}"
        )

    try:
        default_index = (
            int(user_id) >> 22
        ) % 6
    except ValueError:
        return ""

    return (
        "https://cdn.discordapp.com/"
        f"embed/avatars/{default_index}.png"
    )


class DiscordAvatarLoader(QObject):
    """
    Small UI-thread Discord avatar loader.

    Uses Qt's asynchronous networking stack and keeps
    only a tiny in-memory pixmap cache. No Discord token
    or authenticated HTTP request is involved.
    """

    avatar_ready = pyqtSignal(
        str,
        QPixmap,
    )
    avatar_failed = pyqtSignal(
        str
    )

    def __init__(
        self,
        parent=None,
        *,
        network_manager=None,
        max_bytes: int = (
            DISCORD_AVATAR_MAX_BYTES
        ),
        timeout_ms: int = (
            DISCORD_AVATAR_TIMEOUT_MS
        ),
        cache_entries: int = (
            DISCORD_AVATAR_CACHE_ENTRIES
        ),
    ):
        super().__init__(
            parent
        )

        self.max_bytes = max(
            1024,
            int(max_bytes),
        )

        self.timeout_ms = max(
            1000,
            int(timeout_ms),
        )

        self.cache_entries = max(
            1,
            int(cache_entries),
        )

        self.network_manager = (
            network_manager
            if network_manager is not None
            else QNetworkAccessManager(
                self
            )
        )

        self._cache = OrderedDict()
        self._pending = {}

    def request_avatar(
        self,
        user_id,
        avatar_hash="",
    ) -> str:
        url = discord_avatar_url(
            user_id,
            avatar_hash,
        )

        if not url:
            return ""

        key = url

        cached = self._cache.get(
            key
        )

        if cached is not None:
            self._cache.move_to_end(
                key
            )

            self.avatar_ready.emit(
                key,
                QPixmap(
                    cached
                ),
            )

            return key

        if key in self._pending:
            return key

        request = QNetworkRequest(
            QUrl(url)
        )

        request.setTransferTimeout(
            self.timeout_ms
        )

        reply = self.network_manager.get(
            request
        )

        self._pending[key] = reply

        reply.finished.connect(
            lambda current_key=key,
            current_reply=reply:
            self._finish_reply(
                current_key,
                current_reply,
            )
        )

        return key

    def _finish_reply(
        self,
        key: str,
        reply,
    ):
        current = self._pending.get(
            key
        )

        if current is not reply:
            reply.deleteLater()
            return

        self._pending.pop(
            key,
            None,
        )

        if (
            reply.error()
            != QNetworkReply.NetworkError.NoError
        ):
            reply.deleteLater()

            self.avatar_failed.emit(
                key
            )
            return

        payload = bytes(
            reply.readAll()
        )

        reply.deleteLater()

        if (
            not payload
            or len(payload)
            > self.max_bytes
        ):
            self.avatar_failed.emit(
                key
            )
            return

        pixmap = QPixmap()

        if (
            not pixmap.loadFromData(
                payload
            )
            or pixmap.isNull()
        ):
            self.avatar_failed.emit(
                key
            )
            return

        self._remember(
            key,
            pixmap,
        )

        self.avatar_ready.emit(
            key,
            QPixmap(
                pixmap
            ),
        )

    def _remember(
        self,
        key: str,
        pixmap: QPixmap,
    ):
        self._cache[key] = QPixmap(
            pixmap
        )

        self._cache.move_to_end(
            key
        )

        while (
            len(self._cache)
            > self.cache_entries
        ):
            self._cache.popitem(
                last=False
            )

    def shutdown(self):
        replies = tuple(
            self._pending.values()
        )

        self._pending.clear()

        for reply in replies:
            try:
                reply.abort()
            except Exception:
                pass
