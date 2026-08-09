from __future__ import annotations

import inspect
import threading
import unittest
from types import SimpleNamespace

import src.media.local_candidate_snapshot as snapshot_module
from src.media.local_candidate_snapshot import (
    LocalCandidateSnapshot,
)


class LocalCandidateSnapshotTests(
    unittest.TestCase
):
    def test_new_snapshot_is_unavailable(
        self,
    ):
        snapshot = (
            LocalCandidateSnapshot()
        )

        self.assertFalse(
            snapshot.available
        )

        self.assertIsNone(
            snapshot.get()
        )

    def test_replace_copies_mutable_iterable_to_tuple(
        self,
    ):
        first = object()
        second = object()

        original = [
            first,
            second,
        ]

        snapshot = (
            LocalCandidateSnapshot()
        )

        stored = snapshot.replace(
            original
        )

        original.clear()

        self.assertIsInstance(
            stored,
            tuple,
        )

        self.assertEqual(
            snapshot.get(),
            (
                first,
                second,
            ),
        )

    def test_empty_tuple_is_available_snapshot(
        self,
    ):
        snapshot = (
            LocalCandidateSnapshot()
        )

        snapshot.replace(
            ()
        )

        self.assertTrue(
            snapshot.available
        )

        self.assertEqual(
            snapshot.get(),
            (),
        )

    def test_replace_scan_result_uses_candidate_tuple(
        self,
    ):
        candidates = (
            object(),
            object(),
        )

        snapshot = (
            LocalCandidateSnapshot()
        )

        result = SimpleNamespace(
            candidates=candidates,
            unrelated=object(),
        )

        snapshot.replace_scan_result(
            result
        )

        self.assertIs(
            snapshot.get(),
            candidates,
        )

    def test_clear_returns_to_unavailable_state(
        self,
    ):
        snapshot = (
            LocalCandidateSnapshot()
        )

        snapshot.replace(
            (
                object(),
            )
        )

        snapshot.clear()

        self.assertFalse(
            snapshot.available
        )

        self.assertIsNone(
            snapshot.get()
        )

    def test_snapshot_is_plain_thread_safe_python(
        self,
    ):
        source = inspect.getsource(
            snapshot_module
        )

        for forbidden in (
            "PyQt",
            "QObject",
            "QThread",
            "QWidget",
            "SettingsPage",
            "LocalMusicQtScanRuntime",
        ):
            self.assertNotIn(
                forbidden,
                source,
            )

        snapshot = (
            LocalCandidateSnapshot()
        )

        failures = []

        def writer():
            try:
                for value in range(
                    250
                ):
                    snapshot.replace(
                        (
                            value,
                            value + 1,
                        )
                    )

            except Exception as error:
                failures.append(
                    error
                )

        def reader():
            try:
                for _index in range(
                    500
                ):
                    current = (
                        snapshot.get()
                    )

                    if current is not None:
                        if not isinstance(
                            current,
                            tuple,
                        ):
                            raise AssertionError(
                                (
                                    "Snapshot returned a "
                                    "mutable value."
                                )
                            )

            except Exception as error:
                failures.append(
                    error
                )

        threads = [
            threading.Thread(
                target=writer
            ),
            threading.Thread(
                target=reader
            ),
            threading.Thread(
                target=reader
            ),
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(
                timeout=3.0
            )

        self.assertFalse(
            any(
                thread.is_alive()
                for thread in threads
            )
        )

        self.assertEqual(
            failures,
            [],
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
