from __future__ import annotations

import unittest

from PyQt6.QtCore import (
    QBuffer,
    QByteArray,
    QIODevice,
    QObject,
    pyqtSignal,
)
from PyQt6.QtGui import QImage
from PyQt6.QtNetwork import (
    QNetworkReply,
)
from PyQt6.QtWidgets import (
    QApplication,
)

from src.ui.spotify_artwork import (
    SpotifyArtworkLoader,
    validate_spotify_artwork_url,
)


def make_valid_png_bytes(
) -> bytes:
    image = QImage(
        2,
        2,
        QImage.Format.Format_ARGB32,
    )

    image.fill(
        0xFFFFFFFF
    )

    buffer = QBuffer()

    if not buffer.open(
        QIODevice.OpenModeFlag.WriteOnly
    ):
        raise RuntimeError(
            "Could not open PNG test buffer."
        )

    try:
        if not image.save(
            buffer,
            "PNG",
        ):
            raise RuntimeError(
                "Qt could not encode PNG test data."
            )

        payload = bytes(
            buffer.data()
        )

    finally:
        buffer.close()

    if not payload:
        raise RuntimeError(
            "PNG test payload is empty."
        )

    return payload


PNG_BYTES = make_valid_png_bytes()


class FakeReply(
    QObject
):
    finished = pyqtSignal()

    def __init__(
        self,
        *,
        payload=PNG_BYTES,
        error=(
            QNetworkReply
            .NetworkError
            .NoError
        ),
    ):
        super().__init__()

        self.payload = payload
        self.network_error = error
        self.aborted = False

    def error(
        self,
    ):
        return self.network_error

    def readAll(
        self,
    ):
        return QByteArray(
            self.payload
        )

    def abort(
        self,
    ):
        self.aborted = True


class FakeNetworkManager:
    def __init__(
        self,
    ):
        self.requests = []
        self.replies = []

    def get(
        self,
        request,
    ):
        self.requests.append(
            request
        )

        reply = FakeReply()

        self.replies.append(
            reply
        )

        return reply


class SpotifyArtworkLoaderTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = (
            QApplication.instance()
            or QApplication(
                []
            )
        )

    def test_https_artwork_url_is_accepted(
        self,
    ):
        value = (
            "https://i.scdn.co/image/example"
        )

        self.assertEqual(
            validate_spotify_artwork_url(
                value
            ),
            value,
        )

    def test_non_https_artwork_url_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            validate_spotify_artwork_url(
                "http://i.scdn.co/image/example"
            )

    def test_url_credentials_are_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            validate_spotify_artwork_url(
                (
                    "https://user:password@"
                    "i.scdn.co/image/example"
                )
            )

    def test_request_uses_network_manager(
        self,
    ):
        manager = FakeNetworkManager()

        loader = SpotifyArtworkLoader(
            network_manager=manager
        )

        loader.request(
            "https://i.scdn.co/image/a"
        )

        self.assertEqual(
            len(
                manager.requests
            ),
            1,
        )

        self.assertEqual(
            (
                manager.requests[0]
                .url()
                .toString()
            ),
            "https://i.scdn.co/image/a",
        )

        loader.shutdown()

    def test_successful_reply_emits_pixmap_and_caches_it(
        self,
    ):
        manager = FakeNetworkManager()

        loader = SpotifyArtworkLoader(
            network_manager=manager
        )

        received = []

        loader.artwork_ready.connect(
            lambda url, pixmap:
            received.append(
                (
                    url,
                    pixmap,
                )
            )
        )

        url = (
            "https://i.scdn.co/image/a"
        )

        loader.request(
            url
        )

        manager.replies[0].finished.emit()

        self.assertEqual(
            len(
                received
            ),
            1,
        )

        self.assertEqual(
            received[0][0],
            url,
        )

        self.assertFalse(
            received[0][1].isNull()
        )

        self.assertEqual(
            loader.cache_size,
            1,
        )

    def test_cached_request_does_not_fetch_again(
        self,
    ):
        manager = FakeNetworkManager()

        loader = SpotifyArtworkLoader(
            network_manager=manager
        )

        url = (
            "https://i.scdn.co/image/a"
        )

        loader.request(
            url
        )

        manager.replies[0].finished.emit()

        loader.request(
            url
        )

        self.assertEqual(
            len(
                manager.requests
            ),
            1,
        )

    def test_duplicate_pending_request_is_deduplicated(
        self,
    ):
        manager = FakeNetworkManager()

        loader = SpotifyArtworkLoader(
            network_manager=manager
        )

        url = (
            "https://i.scdn.co/image/a"
        )

        self.assertTrue(
            loader.request(
                url
            )
        )

        self.assertFalse(
            loader.request(
                url
            )
        )

        self.assertEqual(
            len(
                manager.requests
            ),
            1,
        )

        loader.shutdown()

    def test_network_failure_emits_failed(
        self,
    ):
        class FailingManager:
            def __init__(
                self,
            ):
                self.reply = FakeReply(
                    error=(
                        QNetworkReply
                        .NetworkError
                        .ConnectionRefusedError
                    )
                )

            def get(
                self,
                request,
            ):
                return self.reply

        manager = FailingManager()

        loader = SpotifyArtworkLoader(
            network_manager=manager
        )

        failed = []

        loader.artwork_failed.connect(
            failed.append
        )

        url = (
            "https://i.scdn.co/image/fail"
        )

        loader.request(
            url
        )

        manager.reply.finished.emit()

        self.assertEqual(
            failed,
            [
                url
            ],
        )

    def test_invalid_or_oversized_image_is_rejected(
        self,
    ):
        manager = FakeNetworkManager()

        loader = SpotifyArtworkLoader(
            network_manager=manager,
            max_bytes=4,
        )

        failed = []

        loader.artwork_failed.connect(
            failed.append
        )

        url = (
            "https://i.scdn.co/image/large"
        )

        loader.request(
            url
        )

        manager.replies[0].payload = (
            b"12345"
        )

        manager.replies[0].finished.emit()

        self.assertEqual(
            failed,
            [
                url
            ],
        )

        self.assertEqual(
            loader.cache_size,
            0,
        )

    def test_shutdown_aborts_pending_requests(
        self,
    ):
        manager = FakeNetworkManager()

        loader = SpotifyArtworkLoader(
            network_manager=manager
        )

        loader.request(
            "https://i.scdn.co/image/a"
        )

        reply = manager.replies[0]

        loader.shutdown()

        self.assertTrue(
            reply.aborted
        )

        self.assertEqual(
            loader.pending_count,
            0,
        )
