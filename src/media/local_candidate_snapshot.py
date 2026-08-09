from __future__ import annotations

from collections.abc import Iterable
from threading import RLock


class LocalCandidateSnapshot:
    """Thread-neutral snapshot of indexed local music candidates."""

    def __init__(
        self,
    ) -> None:
        self._lock = RLock()
        self._candidates = None

    @property
    def available(
        self,
    ) -> bool:
        with self._lock:
            return (
                self._candidates
                is not None
            )

    def replace(
        self,
        candidates: Iterable,
    ) -> tuple:
        if candidates is None:
            raise TypeError(
                "candidates cannot be None"
            )

        if isinstance(
            candidates,
            (
                str,
                bytes,
                bytearray,
            ),
        ):
            raise TypeError(
                (
                    "candidates must be an "
                    "iterable of candidate objects"
                )
            )

        if isinstance(
            candidates,
            tuple,
        ):
            checked = candidates

        else:
            try:
                checked = tuple(
                    candidates
                )

            except TypeError as error:
                raise TypeError(
                    (
                        "candidates must be an "
                        "iterable of candidate objects"
                    )
                ) from error

        with self._lock:
            self._candidates = (
                checked
            )

        return checked

    def replace_scan_result(
        self,
        result,
    ) -> tuple:
        try:
            candidates = (
                result.candidates
            )

        except AttributeError as error:
            raise TypeError(
                (
                    "result must provide "
                    "candidates"
                )
            ) from error

        return self.replace(
            candidates
        )

    def clear(
        self,
    ) -> None:
        with self._lock:
            self._candidates = None

    def get(
        self,
    ) -> tuple | None:
        with self._lock:
            return self._candidates
