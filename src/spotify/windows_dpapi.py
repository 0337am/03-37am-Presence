from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import os


CRYPTPROTECT_UI_FORBIDDEN = 0x00000001

SPOTIFY_DPAPI_ENTROPY = (
    b"03:37am Presence|Spotify OAuth|v1"
)


class _DataBlob(
    ctypes.Structure
):
    _fields_ = [
        (
            "cbData",
            wintypes.DWORD,
        ),
        (
            "pbData",
            ctypes.POINTER(
                ctypes.c_ubyte
            ),
        ),
    ]


@dataclass(
    frozen=True,
    slots=True,
)
class WindowsDpapiError(
    RuntimeError
):
    error_code: str
    message: str
    winerror: int | None = None

    def __post_init__(
        self,
    ) -> None:
        RuntimeError.__init__(
            self,
            self.message,
        )


def _validate_bytes(
    value: bytes,
    *,
    name: str,
) -> bytes:
    if not isinstance(
        value,
        bytes,
    ):
        raise TypeError(
            f"{name} must be bytes"
        )

    if not value:
        raise ValueError(
            f"{name} cannot be empty"
        )

    return value


def _blob_from_bytes(
    value: bytes,
) -> tuple[
    _DataBlob,
    ctypes.Array,
]:
    buffer = (
        ctypes.c_ubyte
        * len(
            value
        )
    ).from_buffer_copy(
        value
    )

    blob = _DataBlob(
        cbData=len(
            value
        ),
        pbData=ctypes.cast(
            buffer,
            ctypes.POINTER(
                ctypes.c_ubyte
            ),
        ),
    )

    return (
        blob,
        buffer,
    )


def _require_windows(
    operation: str,
) -> None:
    if os.name != "nt":
        raise WindowsDpapiError(
            error_code="platform_unsupported",
            message=(
                "Windows data protection is "
                f"required to {operation} Spotify credentials."
            ),
        )


def _load_windows_apis():
    _require_windows(
        "protect"
    )

    crypt32 = ctypes.WinDLL(
        "crypt32",
        use_last_error=True,
    )

    kernel32 = ctypes.WinDLL(
        "kernel32",
        use_last_error=True,
    )

    crypt_protect = (
        crypt32.CryptProtectData
    )

    crypt_protect.argtypes = [
        ctypes.POINTER(
            _DataBlob
        ),
        wintypes.LPCWSTR,
        ctypes.POINTER(
            _DataBlob
        ),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(
            _DataBlob
        ),
    ]

    crypt_protect.restype = (
        wintypes.BOOL
    )

    crypt_unprotect = (
        crypt32.CryptUnprotectData
    )

    crypt_unprotect.argtypes = [
        ctypes.POINTER(
            _DataBlob
        ),
        ctypes.c_void_p,
        ctypes.POINTER(
            _DataBlob
        ),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(
            _DataBlob
        ),
    ]

    crypt_unprotect.restype = (
        wintypes.BOOL
    )

    local_free = (
        kernel32.LocalFree
    )

    local_free.argtypes = [
        ctypes.c_void_p,
    ]

    local_free.restype = (
        ctypes.c_void_p
    )

    return (
        crypt_protect,
        crypt_unprotect,
        local_free,
    )


def _copy_and_free_output(
    output_blob: _DataBlob,
    local_free,
) -> bytes:
    if (
        output_blob.cbData <= 0
        or not output_blob.pbData
    ):
        raise WindowsDpapiError(
            error_code="invalid_output",
            message=(
                "Windows returned invalid protected data."
            ),
        )

    pointer = ctypes.cast(
        output_blob.pbData,
        ctypes.c_void_p,
    )

    try:
        return ctypes.string_at(
            output_blob.pbData,
            output_blob.cbData,
        )
    finally:
        if pointer.value:
            local_free(
                pointer
            )


def protect_data(
    plaintext: bytes,
) -> bytes:
    plaintext = _validate_bytes(
        plaintext,
        name="plaintext",
    )

    (
        crypt_protect,
        _,
        local_free,
    ) = _load_windows_apis()

    input_blob, input_buffer = (
        _blob_from_bytes(
            plaintext
        )
    )

    entropy_blob, entropy_buffer = (
        _blob_from_bytes(
            SPOTIFY_DPAPI_ENTROPY
        )
    )

    output_blob = _DataBlob()

    ctypes.set_last_error(
        0
    )

    succeeded = crypt_protect(
        ctypes.byref(
            input_blob
        ),
        None,
        ctypes.byref(
            entropy_blob
        ),
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(
            output_blob
        ),
    )

    # Keep both input buffers alive until the
    # Windows call has completed.
    _ = (
        input_buffer,
        entropy_buffer,
    )

    if not succeeded:
        winerror = (
            ctypes.get_last_error()
        )

        raise WindowsDpapiError(
            error_code="protect_failed",
            message=(
                "Windows could not protect "
                "Spotify credentials."
            ),
            winerror=winerror,
        )

    return _copy_and_free_output(
        output_blob,
        local_free,
    )


def unprotect_data(
    ciphertext: bytes,
) -> bytes:
    ciphertext = _validate_bytes(
        ciphertext,
        name="ciphertext",
    )

    (
        _,
        crypt_unprotect,
        local_free,
    ) = _load_windows_apis()

    input_blob, input_buffer = (
        _blob_from_bytes(
            ciphertext
        )
    )

    entropy_blob, entropy_buffer = (
        _blob_from_bytes(
            SPOTIFY_DPAPI_ENTROPY
        )
    )

    output_blob = _DataBlob()

    ctypes.set_last_error(
        0
    )

    succeeded = crypt_unprotect(
        ctypes.byref(
            input_blob
        ),
        None,
        ctypes.byref(
            entropy_blob
        ),
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(
            output_blob
        ),
    )

    _ = (
        input_buffer,
        entropy_buffer,
    )

    if not succeeded:
        winerror = (
            ctypes.get_last_error()
        )

        raise WindowsDpapiError(
            error_code="unprotect_failed",
            message=(
                "Windows could not unlock "
                "Spotify credentials."
            ),
            winerror=winerror,
        )

    return _copy_and_free_output(
        output_blob,
        local_free,
    )
