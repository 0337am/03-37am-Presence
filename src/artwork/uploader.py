from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


class ArtworkUploader:
    """
    Uploads album artwork to Cloudinary using an unsigned preset.

    Uploaded URLs are cached locally using a hash of the image,
    preventing the same cover from being uploaded repeatedly.
    """

    MAX_ARTWORK_BYTES = 10 * 1024 * 1024

    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]

        load_dotenv(
            self.project_root / ".env",
            override=False,
        )

        self.cloud_name = os.getenv(
            "CLOUDINARY_CLOUD_NAME",
            "",
        ).strip()

        self.upload_preset = os.getenv(
            "CLOUDINARY_UPLOAD_PRESET",
            "",
        ).strip()

        self.cache_path = self._get_cache_path()
        self.cache = self._load_cache()

        self._configuration_warning_shown = False

    @property
    def is_configured(self) -> bool:
        return bool(
            self.cloud_name
            and self.upload_preset
        )

    def get_or_upload(
        self,
        artwork_bytes: bytes | None,
    ) -> str | None:
        """
        Returns a cached URL or uploads new artwork.

        This method performs a network request and should only be
        called from a background worker.
        """

        if not artwork_bytes:
            return None

        if len(artwork_bytes) > self.MAX_ARTWORK_BYTES:
            print(
                "Discord artwork was not uploaded because "
                "the image is larger than 10 MB."
            )
            return None

        artwork_hash = hashlib.sha256(
            artwork_bytes
        ).hexdigest()

        cached_url = self.cache.get(artwork_hash)

        if self._is_valid_url(cached_url):
            return cached_url

        if not self.is_configured:
            self._show_configuration_warning()
            return None

        return self._upload(
            artwork_bytes=artwork_bytes,
            artwork_hash=artwork_hash,
        )

    def _upload(
        self,
        artwork_bytes: bytes,
        artwork_hash: str,
    ) -> str | None:
        upload_endpoint = (
            "https://api.cloudinary.com/v1_1/"
            f"{self.cloud_name}/image/upload"
        )

        filename, mime_type = self._detect_image_type(
            artwork_bytes,
            artwork_hash,
        )

        files = {
            "file": (
                filename,
                artwork_bytes,
                mime_type,
            )
        }

        form_data = {
            "upload_preset": self.upload_preset,
        }

        try:
            response = requests.post(
                upload_endpoint,
                data=form_data,
                files=files,
                timeout=(5, 30),
            )

            response.raise_for_status()

            result = response.json()
            secure_url = result.get("secure_url")

            if not self._is_valid_url(secure_url):
                print(
                    "Cloudinary did not return a valid HTTPS "
                    "artwork URL."
                )
                return None

            self.cache[artwork_hash] = secure_url
            self._save_cache()

            print("Artwork uploaded to Cloudinary.")
            return secure_url

        except requests.RequestException as error:
            message = self._get_cloudinary_error(error)

            print("Cloudinary artwork upload failed:")
            print(message)

            return None

        except (TypeError, ValueError, KeyError) as error:
            print("Cloudinary response could not be read:")
            print(error)

            return None

    def _get_cache_path(self) -> Path:
        local_app_data = os.getenv(
            "LOCALAPPDATA",
            "",
        ).strip()

        if local_app_data:
            cache_directory = (
                Path(local_app_data)
                / "0337am Presence"
            )
        else:
            cache_directory = (
                self.project_root
                / ".cache"
            )

        return cache_directory / "artwork_urls.json"

    def _load_cache(self) -> dict[str, str]:
        if not self.cache_path.exists():
            return {}

        try:
            content = self.cache_path.read_text(
                encoding="utf-8"
            )

            loaded = json.loads(content)

            if not isinstance(loaded, dict):
                return {}

            valid_cache = {}

            for key, value in loaded.items():
                if (
                    isinstance(key, str)
                    and self._is_valid_url(value)
                ):
                    valid_cache[key] = value

            return valid_cache

        except (
            OSError,
            json.JSONDecodeError,
        ):
            return {}

    def _save_cache(self):
        try:
            self.cache_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            temporary_path = (
                self.cache_path.with_suffix(".tmp")
            )

            temporary_path.write_text(
                json.dumps(
                    self.cache,
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )

            temporary_path.replace(
                self.cache_path
            )

        except OSError as error:
            print("Artwork URL cache could not be saved:")
            print(error)

    def _show_configuration_warning(self):
        if self._configuration_warning_shown:
            return

        self._configuration_warning_shown = True

        print(
            "Cloudinary artwork upload is not configured. "
            "Check CLOUDINARY_CLOUD_NAME and "
            "CLOUDINARY_UPLOAD_PRESET in .env."
        )

    @staticmethod
    def _detect_image_type(
        artwork_bytes: bytes,
        artwork_hash: str,
    ) -> tuple[str, str]:
        if artwork_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return (
                f"{artwork_hash}.png",
                "image/png",
            )

        if artwork_bytes.startswith(b"\xff\xd8\xff"):
            return (
                f"{artwork_hash}.jpg",
                "image/jpeg",
            )

        if (
            artwork_bytes.startswith(b"RIFF")
            and artwork_bytes[8:12] == b"WEBP"
        ):
            return (
                f"{artwork_hash}.webp",
                "image/webp",
            )

        return (
            f"{artwork_hash}.img",
            "application/octet-stream",
        )

    @staticmethod
    def _is_valid_url(value: Any) -> bool:
        return (
            isinstance(value, str)
            and value.startswith("https://")
        )

    @staticmethod
    def _get_cloudinary_error(
        error: requests.RequestException,
    ) -> str:
        response = error.response

        if response is not None:
            try:
                response_data = response.json()

                cloudinary_error = response_data.get(
                    "error",
                    {},
                )

                message = cloudinary_error.get(
                    "message"
                )

                if message:
                    return str(message)

            except (
                ValueError,
                AttributeError,
            ):
                pass

            return (
                f"HTTP {response.status_code}: "
                f"{response.reason}"
            )

        return str(error)