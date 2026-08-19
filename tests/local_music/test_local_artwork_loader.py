from __future__ import annotations

import tempfile
import threading
import time
import unittest
from pathlib import Path

from PyQt6.QtCore import (
    QByteArray,
    QBuffer,
    QIODevice,
)
from PyQt6.QtGui import (
    QImage,
)
from PyQt6.QtWidgets import QApplication

from src.ui.local_artwork_loader import (
    DEFAULT_LOCAL_ARTWORK_CACHE_ENTRIES,
    LocalArtworkLoader,
)
from tests.repo_paths import REPO_ROOT


class LocalArtworkLoaderTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ) -> None:
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def setUp(
        self,
    ) -> None:
        self.loaders = []

        self._payload = (
            self.image_bytes()
        )

    def tearDown(
        self,
    ) -> None:
        for loader in self.loaders:
            loader.shutdown()

        self.app.processEvents()

    def make_loader(
        self,
        **kwargs,
    ) -> LocalArtworkLoader:
        loader = LocalArtworkLoader(
            **kwargs
        )

        self.loaders.append(
            loader
        )

        return loader

    @staticmethod
    def image_bytes(
    ) -> bytes:
        image = QImage(
            2,
            2,
            QImage.Format.Format_ARGB32,
        )

        image.fill(
            0
        )

        payload = QByteArray()

        buffer = QBuffer(
            payload
        )

        buffer.open(
            QIODevice.OpenModeFlag.WriteOnly
        )

        try:
            if not image.save(
                buffer,
                "PNG",
            ):
                raise RuntimeError(
                    "Could not build test PNG."
                )

        finally:
            buffer.close()

        return bytes(
            payload
        )

    def wait_until(
        self,
        predicate,
        timeout: float = 2.0,
    ) -> bool:
        deadline = (
            time.monotonic()
            + timeout
        )

        while (
            time.monotonic()
            < deadline
        ):
            self.app.processEvents()

            if predicate():
                return True

            time.sleep(
                0.005
            )

        self.app.processEvents()

        return bool(
            predicate()
        )

    def reference(
        self,
        name: str = "song.mp3",
    ) -> str:
        return str(
            (
                Path(
                    tempfile.gettempdir()
                )
                / name
            ).resolve()
        )

    def test_reader_runs_off_gui_thread(
        self,
    ):
        main_thread_id = (
            threading.get_ident()
        )

        worker_thread_ids = []
        ready = []

        loader = self.make_loader(
            reader=(
                lambda reference:
                    (
                        worker_thread_ids.append(
                            threading.get_ident()
                        )
                        or self._payload
                    )
            ),
        )

        loader.artwork_ready.connect(
            lambda reference, pixmap:
                ready.append(
                    (
                        reference,
                        pixmap,
                    )
                )
        )

        reference = self.reference()

        self.assertTrue(
            loader.request(
                reference
            )
        )

        self.assertTrue(
            self.wait_until(
                lambda: bool(
                    ready
                )
            )
        )

        self.assertEqual(
            len(
                worker_thread_ids
            ),
            1,
        )

        self.assertNotEqual(
            worker_thread_ids[0],
            main_thread_id,
        )

        self.assertEqual(
            ready[0][0],
            reference,
        )

        self.assertFalse(
            ready[0][1].isNull()
        )

    def test_missing_artwork_emits_failed(
        self,
    ):
        failed = []

        loader = self.make_loader(
            reader=(
                lambda reference:
                    None
            ),
        )

        loader.artwork_failed.connect(
            failed.append
        )

        reference = self.reference()

        self.assertTrue(
            loader.request(
                reference
            )
        )

        self.assertTrue(
            self.wait_until(
                lambda:
                    failed
                    == [reference]
            )
        )

    def test_invalid_image_bytes_emit_failed(
        self,
    ):
        failed = []

        loader = self.make_loader(
            reader=(
                lambda reference:
                    b"not-an-image"
            ),
        )

        loader.artwork_failed.connect(
            failed.append
        )

        reference = self.reference()

        self.assertTrue(
            loader.request(
                reference
            )
        )

        self.assertTrue(
            self.wait_until(
                lambda:
                    failed
                    == [reference]
            )
        )

    def test_reader_exception_emits_failed(
        self,
    ):
        failed = []

        def reader(
            reference,
        ):
            raise RuntimeError(
                "simulated read failure"
            )

        loader = self.make_loader(
            reader=reader,
        )

        loader.artwork_failed.connect(
            failed.append
        )

        reference = self.reference()

        self.assertTrue(
            loader.request(
                reference
            )
        )

        self.assertTrue(
            self.wait_until(
                lambda:
                    failed
                    == [reference]
            )
        )

    def test_duplicate_pending_request_is_deduplicated(
        self,
    ):
        started = threading.Event()
        release = threading.Event()

        self.addCleanup(
            release.set
        )

        calls = []

        def reader(
            reference,
        ):
            calls.append(
                reference
            )

            started.set()

            release.wait(
                2.0
            )

            return self._payload

        loader = self.make_loader(
            reader=reader,
        )

        ready = []

        loader.artwork_ready.connect(
            lambda reference, pixmap:
                ready.append(
                    reference
                )
        )

        reference = self.reference()

        self.assertTrue(
            loader.request(
                reference
            )
        )

        self.assertTrue(
            started.wait(
                1.0
            )
        )

        self.assertTrue(
            loader.request(
                reference
            )
        )

        self.assertEqual(
            calls,
            [reference],
        )

        release.set()

        self.assertTrue(
            self.wait_until(
                lambda:
                    ready
                    == [reference]
            )
        )

        self.assertEqual(
            calls,
            [reference],
        )

    def test_cache_hit_does_not_read_again(
        self,
    ):
        calls = []

        def reader(
            reference,
        ):
            calls.append(
                reference
            )

            return self._payload

        loader = self.make_loader(
            reader=reader,
        )

        ready = []

        loader.artwork_ready.connect(
            lambda reference, pixmap:
                ready.append(
                    reference
                )
        )

        reference = self.reference()

        self.assertTrue(
            loader.request(
                reference
            )
        )

        self.assertTrue(
            self.wait_until(
                lambda:
                    ready
                    == [reference]
            )
        )

        ready.clear()

        self.assertTrue(
            loader.request(
                reference
            )
        )

        self.assertEqual(
            ready,
            [reference],
        )

        self.assertEqual(
            calls,
            [reference],
        )

    def test_cache_is_lru_bounded(
        self,
    ):
        calls = []

        def reader(
            reference,
        ):
            calls.append(
                reference
            )

            return self._payload

        loader = self.make_loader(
            reader=reader,
            max_cache_entries=1,
        )

        ready = []

        loader.artwork_ready.connect(
            lambda reference, pixmap:
                ready.append(
                    reference
                )
        )

        first = self.reference(
            "first.mp3"
        )

        second = self.reference(
            "second.mp3"
        )

        self.assertTrue(
            loader.request(
                first
            )
        )

        self.assertTrue(
            self.wait_until(
                lambda:
                    first in ready
            )
        )

        self.assertTrue(
            loader.request(
                second
            )
        )

        self.assertTrue(
            self.wait_until(
                lambda:
                    second in ready
            )
        )

        self.assertEqual(
            calls.count(
                first
            ),
            1,
        )

        self.assertTrue(
            loader.request(
                first
            )
        )

        self.assertTrue(
            self.wait_until(
                lambda:
                    calls.count(
                        first
                    )
                    == 2
            )
        )

    def test_invalid_references_are_rejected_before_worker(
        self,
    ):
        calls = []

        loader = self.make_loader(
            reader=(
                lambda reference:
                    calls.append(
                        reference
                    )
            ),
        )

        for value in (
            None,
            "",
            "song.mp3",
            r"\\server\music\song.mp3",
        ):
            with self.subTest(
                value=value
            ):
                self.assertFalse(
                    loader.request(
                        value
                    )
                )

        self.assertEqual(
            calls,
            [],
        )

    def test_shutdown_stops_after_current_read(
        self,
    ):
        started = threading.Event()
        release = threading.Event()

        calls = []

        def reader(
            reference,
        ):
            calls.append(
                reference
            )

            started.set()

            release.wait(
                1.0
            )

            return self._payload

        loader = self.make_loader(
            reader=reader,
        )

        first = self.reference(
            "shutdown-first.mp3"
        )

        second = self.reference(
            "shutdown-second.mp3"
        )

        self.assertTrue(
            loader.request(
                first
            )
        )

        self.assertTrue(
            loader.request(
                second
            )
        )

        self.assertTrue(
            started.wait(
                1.0
            )
        )

        timer = threading.Timer(
            0.05,
            release.set,
        )

        timer.start()

        try:
            self.assertTrue(
                loader.shutdown(
                    1000
                )
            )

        finally:
            release.set()
            timer.cancel()

        self.assertFalse(
            loader._thread.isRunning()
        )

        self.assertEqual(
            calls,
            [first],
        )

    def test_shutdown_prevents_new_requests(
        self,
    ):
        loader = self.make_loader(
            reader=(
                lambda reference:
                    self._payload
            ),
        )

        self.assertTrue(
            loader.shutdown()
        )

        self.assertFalse(
            loader.request(
                self.reference()
            )
        )

    def test_thread_starts_lazily(
        self,
    ):
        loader = self.make_loader(
            reader=(
                lambda reference:
                    self._payload
            ),
        )

        self.assertFalse(
            loader._thread.isRunning()
        )

        self.assertTrue(
            loader.request(
                self.reference()
            )
        )

        self.assertTrue(
            self.wait_until(
                loader._thread.isRunning
            )
        )

    def test_max_cache_entries_validation(
        self,
    ):
        for value in (
            True,
            False,
            1.5,
            "128",
            None,
        ):
            with self.subTest(
                value=value
            ):
                with self.assertRaises(
                    TypeError
                ):
                    LocalArtworkLoader(
                        max_cache_entries=value
                    )

        for value in (
            0,
            -1,
        ):
            with self.subTest(
                value=value
            ):
                with self.assertRaises(
                    ValueError
                ):
                    LocalArtworkLoader(
                        max_cache_entries=value
                    )

    def test_reader_must_be_callable(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            LocalArtworkLoader(
                reader=object()
            )

    def test_shutdown_timeout_validation(
        self,
    ):
        loader = self.make_loader(
            reader=(
                lambda reference:
                    self._payload
            ),
        )

        for value in (
            True,
            False,
            1.5,
            "1000",
            None,
        ):
            with self.subTest(
                value=value
            ):
                with self.assertRaises(
                    TypeError
                ):
                    loader.shutdown(
                        value
                    )

        with self.assertRaises(
            ValueError
        ):
            loader.shutdown(
                -1
            )

    def test_default_cache_limit_is_bounded(
        self,
    ):
        self.assertEqual(
            DEFAULT_LOCAL_ARTWORK_CACHE_ENTRIES,
            128,
        )

    def test_source_has_no_network_or_playback_mechanisms(
        self,
    ):
        source_path = (
            REPO_ROOT
            / "src"
            / "ui"
            / "local_artwork_loader.py"
        )

        source = source_path.read_text(
            encoding="utf-8"
        )

        for forbidden in (
            "QNetworkAccessManager",
            "requests.",
            "urllib",
            "os.startfile",
            "spotify:local:",
            "QMediaPlayer",
            "SetForegroundWindow",
            "UIAutomation",
        ):
            with self.subTest(
                forbidden=forbidden
            ):
                self.assertNotIn(
                    forbidden,
                    source,
                )


if __name__ == "__main__":
    unittest.main()