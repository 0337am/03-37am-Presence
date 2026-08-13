from __future__ import annotations

import ntpath
from collections import OrderedDict
from pathlib import Path
from queue import Queue

from PyQt6.QtCore import (
    QObject,
    QThread,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QPixmap

from src.media.local_artwork import (
    read_local_artwork,
)


DEFAULT_LOCAL_ARTWORK_CACHE_ENTRIES = 128
DEFAULT_LOCAL_ARTWORK_SHUTDOWN_MS = 5000


def _is_absolute_reference(
    value: str,
) -> bool:
    return bool(
        Path(value).is_absolute()
        or ntpath.isabs(value)
    )


def _is_network_reference(
    value: str,
) -> bool:
    normalized = (
        value
        .strip()
        .replace("/", "\\")
    )

    return normalized.startswith(
        "\\\\"
    )


class _LocalArtworkThread(QThread):
    artwork_loaded = pyqtSignal(
        str,
        object,
    )

    def __init__(
        self,
        reader,
        parent=None,
    ) -> None:
        super().__init__(
            parent
        )

        self._reader = reader
        self._queue = Queue()

    def enqueue(
        self,
        reference: str,
    ) -> None:
        self._queue.put(
            reference
        )

    def stop(
        self,
    ) -> None:
        self.requestInterruption()

        self._queue.put(
            None
        )

    def run(
        self,
    ) -> None:
        while not self.isInterruptionRequested():
            reference = (
                self._queue.get()
            )

            if (
                reference is None
                or self.isInterruptionRequested()
            ):
                return

            try:
                artwork_bytes = (
                    self._reader(
                        reference
                    )
                )

            except Exception:
                artwork_bytes = None

            if self.isInterruptionRequested():
                return

            self.artwork_loaded.emit(
                reference,
                artwork_bytes,
            )


class LocalArtworkLoader(QObject):
    artwork_ready = pyqtSignal(
        str,
        QPixmap,
    )

    artwork_failed = pyqtSignal(
        str,
    )

    def __init__(
        self,
        parent=None,
        *,
        reader=None,
        max_cache_entries: int = (
            DEFAULT_LOCAL_ARTWORK_CACHE_ENTRIES
        ),
    ) -> None:
        super().__init__(
            parent
        )

        if reader is None:
            reader = (
                read_local_artwork
            )

        if not callable(
            reader
        ):
            raise TypeError(
                "reader must be callable"
            )

        if (
            isinstance(
                max_cache_entries,
                bool,
            )
            or not isinstance(
                max_cache_entries,
                int,
            )
        ):
            raise TypeError(
                (
                    "max_cache_entries must "
                    "be an integer"
                )
            )

        if max_cache_entries <= 0:
            raise ValueError(
                (
                    "max_cache_entries must "
                    "be positive"
                )
            )

        self._max_cache_entries = (
            max_cache_entries
        )

        self._cache: OrderedDict[
            str,
            QPixmap,
        ] = OrderedDict()

        self._pending: set[str] = set()

        self._shutdown = False

        self._thread = (
            _LocalArtworkThread(
                reader,
                parent=self,
            )
        )

        self._thread.artwork_loaded.connect(
            self._handle_artwork_loaded
        )

    def request(
        self,
        local_path,
    ) -> bool:
        if self._shutdown:
            return False

        if not isinstance(
            local_path,
            (
                str,
                Path,
            ),
        ):
            return False

        reference = str(
            local_path
        ).strip()

        if (
            not reference
            or not _is_absolute_reference(
                reference
            )
            or _is_network_reference(
                reference
            )
        ):
            return False

        cached = self._cache.get(
            reference
        )

        if cached is not None:
            self._cache.move_to_end(
                reference
            )

            self.artwork_ready.emit(
                reference,
                QPixmap(
                    cached
                ),
            )

            return True

        if reference in self._pending:
            return True

        self._pending.add(
            reference
        )

        self._thread.enqueue(
            reference
        )

        if not self._thread.isRunning():
            self._thread.start()

        return True

    @pyqtSlot(
        str,
        object,
    )
    def _handle_artwork_loaded(
        self,
        reference: str,
        artwork_bytes,
    ) -> None:
        self._pending.discard(
            reference
        )

        if self._shutdown:
            return

        if not isinstance(
            artwork_bytes,
            (
                bytes,
                bytearray,
                memoryview,
            ),
        ):
            self.artwork_failed.emit(
                reference
            )

            return

        normalized_bytes = bytes(
            artwork_bytes
        )

        if not normalized_bytes:
            self.artwork_failed.emit(
                reference
            )

            return

        pixmap = QPixmap()

        if (
            not pixmap.loadFromData(
                normalized_bytes
            )
            or pixmap.isNull()
        ):
            self.artwork_failed.emit(
                reference
            )

            return

        self._cache[
            reference
        ] = QPixmap(
            pixmap
        )

        self._cache.move_to_end(
            reference
        )

        while (
            len(
                self._cache
            )
            > self._max_cache_entries
        ):
            self._cache.popitem(
                last=False
            )

        self.artwork_ready.emit(
            reference,
            QPixmap(
                pixmap
            ),
        )

    def shutdown(
        self,
        timeout_ms: int = (
            DEFAULT_LOCAL_ARTWORK_SHUTDOWN_MS
        ),
    ) -> bool:
        if (
            isinstance(
                timeout_ms,
                bool,
            )
            or not isinstance(
                timeout_ms,
                int,
            )
        ):
            raise TypeError(
                "timeout_ms must be an integer"
            )

        if timeout_ms < 0:
            raise ValueError(
                "timeout_ms cannot be negative"
            )

        if self._shutdown:
            return not self._thread.isRunning()

        self._shutdown = True

        self._pending.clear()
        self._cache.clear()

        if not self._thread.isRunning():
            return True

        self._thread.stop()

        return bool(
            self._thread.wait(
                timeout_ms
            )
        )