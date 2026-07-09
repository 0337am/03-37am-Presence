from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote, urlparse

from src.artwork.cloudinary_preferences import (
    CloudinaryPreferences,
    CloudinaryPreferencesStore,
)


class ArtworkUploader:
    """
    Uploads artwork to the current user's Cloudinary account.

    Uploads use only the user's cloud name and unsigned
    upload preset. API keys and API secrets are never
    required or stored.
    """

    MAX_ARTWORK_BYTES = 10 * 1024 * 1024
    MAX_RESPONSE_BYTES = 2 * 1024 * 1024
    REQUEST_TIMEOUT_SECONDS = 30
    CACHE_VERSION = 1

    _CLOUD_NAME_PATTERN = re.compile(
        r"^[A-Za-z0-9_-]{1,128}$"
    )

    def __init__(
        self,
        preferences_store: (
            CloudinaryPreferencesStore
            | None
        ) = None,
        urlopen: Callable[..., Any] | None = None,
    ):
        self.preferences_store = (
            preferences_store
            or CloudinaryPreferencesStore()
        )

        self._urlopen = (
            urlopen
            or urllib.request.urlopen
        )

        self.cache_path = (
            self._get_cache_path()
        )

        self.cache = self._load_cache()

        self.last_error = ""

        self._configuration_warning_shown = (
            False
        )

    @property
    def is_configured(self) -> bool:
        preferences = (
            self.preferences_store.load()
        )

        return bool(
            preferences.enabled
            and preferences.configured
        )

    def get_or_upload(
        self,
        artwork_bytes: (
            bytes
            | bytearray
            | memoryview
            | None
        ),
    ) -> str | None:
        """
        Return a cached URL or upload new artwork.

        This method may perform a network request and
        must be called outside the UI thread.
        """

        self.last_error = ""

        if artwork_bytes is None:
            return None

        try:
            image_bytes = bytes(
                artwork_bytes
            )

        except (
            TypeError,
            ValueError,
        ):
            return self._fail(
                "Artwork data was not valid bytes."
            )

        if not image_bytes:
            return None

        if (
            len(image_bytes)
            > self.MAX_ARTWORK_BYTES
        ):
            return self._fail(
                "Artwork was not uploaded because "
                "the image is larger than 10 MB."
            )

        image_type = (
            self._detect_image_type(
                image_bytes
            )
        )

        if image_type is None:
            return self._fail(
                "Artwork was not uploaded because "
                "its image format was not recognised."
            )

        preferences = (
            self.preferences_store.load()
        )

        if not (
            preferences.enabled
            and preferences.configured
        ):
            self._show_configuration_warning()
            return None

        if not self._is_valid_cloud_name(
            preferences.cloud_name
        ):
            return self._fail(
                "The saved Cloudinary cloud name "
                "is invalid."
            )

        artwork_hash = hashlib.sha256(
            image_bytes
        ).hexdigest()

        cache_key = self._cache_key(
            preferences,
            artwork_hash,
        )

        cached_url = self.cache.get(
            cache_key
        )

        if self._is_valid_https_url(
            cached_url
        ):
            return str(
                cached_url
            )

        extension, mime_type = image_type

        return self._upload(
            artwork_bytes=image_bytes,
            artwork_hash=artwork_hash,
            extension=extension,
            mime_type=mime_type,
            preferences=preferences,
            cache_key=cache_key,
        )

    def clear_cache(self):
        self.cache = {}

        try:
            self.cache_path.unlink(
                missing_ok=True
            )

        except OSError as error:
            self._fail(
                "Artwork URL cache could not "
                f"be cleared: {error}"
            )

    def _upload(
        self,
        artwork_bytes: bytes,
        artwork_hash: str,
        extension: str,
        mime_type: str,
        preferences: CloudinaryPreferences,
        cache_key: str,
    ) -> str | None:
        cloud_name = quote(
            preferences.cloud_name,
            safe="",
        )

        endpoint = (
            "https://api.cloudinary.com/v1_1/"
            f"{cloud_name}/image/upload"
        )

        boundary = (
            "----0337amPresence"
            + uuid.uuid4().hex
        )

        body = self._build_multipart_body(
            boundary=boundary,
            upload_preset=(
                preferences.upload_preset
            ),
            filename=(
                f"{artwork_hash}.{extension}"
            ),
            mime_type=mime_type,
            file_bytes=artwork_bytes,
        )

        request = urllib.request.Request(
            endpoint,
            data=body,
            headers={
                "Content-Type": (
                    "multipart/form-data; "
                    f"boundary={boundary}"
                ),
                "Content-Length": str(
                    len(body)
                ),
                "Accept": "application/json",
                "User-Agent": (
                    "03:37am-Presence/2.1"
                ),
            },
            method="POST",
        )

        try:
            with self._urlopen(
                request,
                timeout=(
                    self.REQUEST_TIMEOUT_SECONDS
                ),
            ) as response:
                response_bytes = response.read(
                    self.MAX_RESPONSE_BYTES + 1
                )

            if (
                len(response_bytes)
                > self.MAX_RESPONSE_BYTES
            ):
                return self._fail(
                    "Cloudinary returned an "
                    "unexpectedly large response."
                )

            result = json.loads(
                response_bytes.decode(
                    "utf-8"
                )
            )

            if not isinstance(
                result,
                dict,
            ):
                raise TypeError(
                    "Cloudinary response was not "
                    "a JSON object."
                )

            secure_url = result.get(
                "secure_url"
            )

            if not self._is_valid_https_url(
                secure_url
            ):
                return self._fail(
                    "Cloudinary did not return a "
                    "valid HTTPS artwork URL."
                )

            self.cache[cache_key] = str(
                secure_url
            )

            self._save_cache()

            print(
                "Artwork uploaded to the user's "
                "Cloudinary account."
            )

            return str(
                secure_url
            )

        except urllib.error.HTTPError as error:
            return self._fail(
                "Cloudinary artwork upload failed: "
                + self._read_http_error(
                    error
                )
            )

        except urllib.error.URLError as error:
            reason = getattr(
                error,
                "reason",
                error,
            )

            return self._fail(
                "Cloudinary artwork upload failed: "
                f"{reason}"
            )

        except (
            TimeoutError,
            socket.timeout,
        ):
            return self._fail(
                "Cloudinary artwork upload "
                "timed out."
            )

        except (
            json.JSONDecodeError,
            UnicodeDecodeError,
            TypeError,
            ValueError,
        ) as error:
            return self._fail(
                "Cloudinary response could not "
                f"be read: {error}"
            )

        except OSError as error:
            return self._fail(
                "Cloudinary artwork upload failed: "
                f"{error}"
            )

    def _get_cache_path(self) -> Path:
        local_app_data = os.getenv(
            "LOCALAPPDATA",
            "",
        ).strip()

        if local_app_data:
            data_directory = (
                Path(local_app_data)
                / "0337am Presence"
            )
        else:
            data_directory = (
                Path.home()
                / ".0337am-presence"
            )

        return (
            data_directory
            / "cloudinary_artwork_urls.json"
        )

    def _load_cache(
        self,
    ) -> dict[str, str]:
        if not self.cache_path.exists():
            return {}

        try:
            with self.cache_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                payload = json.load(
                    file
                )

            if not isinstance(
                payload,
                dict,
            ):
                raise TypeError(
                    "Artwork URL cache must "
                    "be a JSON object."
                )

            if (
                payload.get("version")
                != self.CACHE_VERSION
            ):
                return {}

            entries = payload.get(
                "entries"
            )

            if not isinstance(
                entries,
                dict,
            ):
                raise TypeError(
                    "Artwork URL cache entries "
                    "must be a JSON object."
                )

            return {
                key: str(value)
                for key, value
                in entries.items()
                if self._is_valid_cache_entry(
                    key,
                    value,
                )
            }

        except (
            OSError,
            json.JSONDecodeError,
            TypeError,
        ):
            self._quarantine_invalid_cache()
            return {}

    def _save_cache(self):
        self.cache_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = (
            self.cache_path.with_suffix(
                self.cache_path.suffix
                + ".tmp"
            )
        )

        payload = {
            "version": self.CACHE_VERSION,
            "entries": self.cache,
        }

        try:
            with temporary_path.open(
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    payload,
                    file,
                    indent=2,
                    sort_keys=True,
                )

                file.write("\n")
                file.flush()

                os.fsync(
                    file.fileno()
                )

            with temporary_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                verified_payload = (
                    json.load(file)
                )

            if verified_payload != payload:
                raise ValueError(
                    "Temporary artwork URL cache "
                    "failed validation."
                )

            temporary_path.replace(
                self.cache_path
            )

        except (
            OSError,
            ValueError,
        ) as error:
            self._fail(
                "Artwork URL cache could not "
                f"be saved: {error}"
            )

        finally:
            temporary_path.unlink(
                missing_ok=True
            )

    def _quarantine_invalid_cache(
        self,
    ) -> Path | None:
        if not self.cache_path.exists():
            return None

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        invalid_path = (
            self.cache_path.with_name(
                f"{self.cache_path.stem}"
                f".invalid_{timestamp}"
                f"{self.cache_path.suffix}"
            )
        )

        try:
            self.cache_path.replace(
                invalid_path
            )

        except OSError:
            return None

        return invalid_path

    def _show_configuration_warning(self):
        if self._configuration_warning_shown:
            return

        self._configuration_warning_shown = (
            True
        )

        self._fail(
            "Personal Cloudinary artwork hosting "
            "is not enabled or configured."
        )

    def _fail(
        self,
        message: str,
    ) -> None:
        self.last_error = str(
            message
        )

        print(
            self.last_error
        )

        return None

    @staticmethod
    def _cache_key(
        preferences: CloudinaryPreferences,
        artwork_hash: str,
    ) -> str:
        account_scope = (
            preferences.cloud_name
            + "\0"
            + preferences.upload_preset
        ).encode(
            "utf-8"
        )

        scope_hash = hashlib.sha256(
            account_scope
        ).hexdigest()

        return (
            f"{scope_hash}:{artwork_hash}"
        )

    @staticmethod
    def _build_multipart_body(
        boundary: str,
        upload_preset: str,
        filename: str,
        mime_type: str,
        file_bytes: bytes,
    ) -> bytes:
        boundary_bytes = boundary.encode(
            "ascii"
        )

        return b"".join(
            [
                (
                    b"--"
                    + boundary_bytes
                    + b"\r\n"
                ),
                (
                    b"Content-Disposition: "
                    b"form-data; "
                    b'name="upload_preset"'
                    b"\r\n\r\n"
                ),
                upload_preset.encode(
                    "utf-8"
                ),
                (
                    b"\r\n--"
                    + boundary_bytes
                    + b"\r\n"
                ),
                (
                    "Content-Disposition: "
                    "form-data; "
                    'name="file"; '
                    f'filename="{filename}"'
                    "\r\n"
                ).encode(
                    "utf-8"
                ),
                (
                    f"Content-Type: "
                    f"{mime_type}"
                    "\r\n\r\n"
                ).encode(
                    "ascii"
                ),
                file_bytes,
                (
                    b"\r\n--"
                    + boundary_bytes
                    + b"--\r\n"
                ),
            ]
        )

    @staticmethod
    def _detect_image_type(
        artwork_bytes: bytes,
    ) -> tuple[str, str] | None:
        if artwork_bytes.startswith(
            b"\x89PNG\r\n\x1a\n"
        ):
            return (
                "png",
                "image/png",
            )

        if artwork_bytes.startswith(
            b"\xff\xd8\xff"
        ):
            return (
                "jpg",
                "image/jpeg",
            )

        if (
            artwork_bytes.startswith(
                b"RIFF"
            )
            and artwork_bytes[8:12]
            == b"WEBP"
        ):
            return (
                "webp",
                "image/webp",
            )

        if artwork_bytes.startswith(
            (
                b"GIF87a",
                b"GIF89a",
            )
        ):
            return (
                "gif",
                "image/gif",
            )

        return None

    @classmethod
    def _is_valid_cloud_name(
        cls,
        value: Any,
    ) -> bool:
        return bool(
            isinstance(
                value,
                str,
            )
            and cls._CLOUD_NAME_PATTERN
            .fullmatch(value)
        )

    @staticmethod
    def _is_valid_https_url(
        value: Any,
    ) -> bool:
        if not isinstance(
            value,
            str,
        ):
            return False

        try:
            parsed = urlparse(
                value
            )

        except ValueError:
            return False

        return bool(
            parsed.scheme == "https"
            and parsed.netloc
            and parsed.hostname
            and parsed.username is None
            and parsed.password is None
        )

    @classmethod
    def _is_valid_cache_entry(
        cls,
        key: Any,
        value: Any,
    ) -> bool:
        return bool(
            isinstance(
                key,
                str,
            )
            and len(key) == 129
            and key[64] == ":"
            and cls._is_hex_digest(
                key[:64]
            )
            and cls._is_hex_digest(
                key[65:]
            )
            and cls._is_valid_https_url(
                value
            )
        )

    @staticmethod
    def _is_hex_digest(
        value: str,
    ) -> bool:
        return bool(
            len(value) == 64
            and all(
                character
                in "0123456789abcdef"
                for character in value
            )
        )

    @staticmethod
    def _read_http_error(
        error: urllib.error.HTTPError,
    ) -> str:
        try:
            response_bytes = error.read(
                ArtworkUploader
                .MAX_RESPONSE_BYTES
            )

            response_data = json.loads(
                response_bytes.decode(
                    "utf-8"
                )
            )

            cloudinary_error = (
                response_data.get(
                    "error",
                    {},
                )
            )

            message = cloudinary_error.get(
                "message"
            )

            if (
                isinstance(
                    message,
                    str,
                )
                and message.strip()
            ):
                return message.strip()

        except (
            OSError,
            ValueError,
            UnicodeDecodeError,
            AttributeError,
        ):
            pass

        reason = getattr(
            error,
            "reason",
            "Upload failed",
        )

        return (
            f"HTTP {error.code}: {reason}"
        )
