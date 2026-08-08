from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


from src.spotify.credential_store import (
    MAX_SPOTIFY_CREDENTIAL_BYTES,
)
from src.spotify.credential_store import (
    SPOTIFY_CREDENTIAL_FILENAME,
)
from src.spotify.credential_store import (
    SpotifyCredentialStore,
)
from src.spotify.credential_store import (
    SpotifyCredentialStoreError,
)
from src.spotify.credential_store import (
    default_spotify_credential_path,
)
from src.spotify.models import (
    SpotifyTokenBundle,
)
from src.spotify.windows_dpapi import (
    WindowsDpapiError,
)


def make_token(
    *,
    suffix: str = "one",
) -> SpotifyTokenBundle:
    return SpotifyTokenBundle(
        access_token=(
            f"dummy-access-secret-{suffix}"
        ),
        refresh_token=(
            f"dummy-refresh-secret-{suffix}"
        ),
        token_type="Bearer",
        expires_in=3600,
        granted_scopes=(
            "user-read-private",
        ),
        obtained_at=1000.0,
        authorized_at=900.0,
    )


@unittest.skipUnless(
    os.name == "nt",
    "Spotify credential-store tests require Windows",
)
class SpotifyCredentialStoreTests(
    unittest.TestCase
):
    def test_default_path_uses_local_app_data(
        self,
    ):
        with TemporaryDirectory() as temp:
            with patch.dict(
                os.environ,
                {
                    "LOCALAPPDATA": temp,
                },
            ):
                path = (
                    default_spotify_credential_path()
                )

            self.assertEqual(
                path,
                (
                    Path(
                        temp
                    )
                    / "0337am Presence"
                    / "spotify_auth.dat"
                ),
            )

    def test_real_dpapi_store_round_trip_is_encrypted(
        self,
    ):
        token = make_token()

        with TemporaryDirectory() as temp:
            path = (
                Path(
                    temp
                )
                / SPOTIFY_CREDENTIAL_FILENAME
            )

            store = SpotifyCredentialStore(
                path
            )

            saved_path = store.save(
                token
            )

            self.assertEqual(
                saved_path,
                path,
            )

            protected = path.read_bytes()

            self.assertNotIn(
                token.access_token.encode(
                    "utf-8"
                ),
                protected,
            )

            self.assertNotIn(
                token.refresh_token.encode(
                    "utf-8"
                ),
                protected,
            )

            loaded = store.load()

            self.assertIsNotNone(
                loaded
            )

            self.assertEqual(
                loaded.access_token,
                token.access_token,
            )

            self.assertEqual(
                loaded.refresh_token,
                token.refresh_token,
            )

            self.assertEqual(
                loaded.token_type,
                token.token_type,
            )

            self.assertEqual(
                loaded.expires_in,
                token.expires_in,
            )

            self.assertEqual(
                loaded.granted_scopes,
                token.granted_scopes,
            )

            self.assertEqual(
                loaded.obtained_at,
                token.obtained_at,
            )

            self.assertEqual(
                loaded.authorized_at,
                token.authorized_at,
            )

    def test_atomic_overwrite_replaces_old_token(
        self,
    ):
        with TemporaryDirectory() as temp:
            path = (
                Path(
                    temp
                )
                / SPOTIFY_CREDENTIAL_FILENAME
            )

            store = SpotifyCredentialStore(
                path
            )

            store.save(
                make_token(
                    suffix="old"
                )
            )

            store.save(
                make_token(
                    suffix="new"
                )
            )

            loaded = store.load()

            self.assertIsNotNone(
                loaded
            )

            self.assertEqual(
                loaded.access_token,
                "dummy-access-secret-new",
            )

            leftovers = list(
                path.parent.glob(
                    f".{path.name}.*.tmp"
                )
            )

            self.assertEqual(
                leftovers,
                [],
            )

    def test_missing_store_returns_none(
        self,
    ):
        with TemporaryDirectory() as temp:
            path = (
                Path(
                    temp
                )
                / SPOTIFY_CREDENTIAL_FILENAME
            )

            store = SpotifyCredentialStore(
                path
            )

            self.assertIsNone(
                store.load()
            )

            self.assertFalse(
                store.exists
            )

    def test_delete_is_explicit_and_idempotent(
        self,
    ):
        with TemporaryDirectory() as temp:
            path = (
                Path(
                    temp
                )
                / SPOTIFY_CREDENTIAL_FILENAME
            )

            store = SpotifyCredentialStore(
                path
            )

            store.save(
                make_token()
            )

            self.assertTrue(
                store.delete()
            )

            self.assertFalse(
                path.exists()
            )

            self.assertFalse(
                store.delete()
            )

    def test_corrupt_ciphertext_is_quarantined(
        self,
    ):
        with TemporaryDirectory() as temp:
            path = (
                Path(
                    temp
                )
                / SPOTIFY_CREDENTIAL_FILENAME
            )

            corrupt = (
                b"not-a-valid-dpapi-payload"
            )

            path.write_bytes(
                corrupt
            )

            store = SpotifyCredentialStore(
                path,
                clock=lambda: (
                    1786194000.0
                ),
            )

            with self.assertRaises(
                SpotifyCredentialStoreError
            ) as context:
                store.load()

            failure = context.exception

            self.assertEqual(
                failure.error_code,
                "credential_corrupt",
            )

            self.assertFalse(
                path.exists()
            )

            self.assertIsNotNone(
                failure.quarantine_path
            )

            self.assertTrue(
                failure.quarantine_path.exists()
            )

            self.assertEqual(
                failure.quarantine_path.read_bytes(),
                corrupt,
            )

            self.assertNotIn(
                corrupt.decode(
                    "ascii"
                ),
                str(
                    failure
                ),
            )

    def test_unsupported_plaintext_schema_is_quarantined_safely(
        self,
    ):
        access_marker = (
            "do-not-echo-access-secret"
        )

        refresh_marker = (
            "do-not-echo-refresh-secret"
        )

        plaintext = json.dumps(
            {
                "schema": 999,
                "kind": (
                    "spotify_oauth_token"
                ),
                "token": {
                    "access_token": (
                        access_marker
                    ),
                    "refresh_token": (
                        refresh_marker
                    ),
                    "token_type": (
                        "Bearer"
                    ),
                    "expires_in": 3600,
                    "granted_scopes": [
                        "user-read-private",
                    ],
                    "obtained_at": 1000.0,
                    "authorized_at": 900.0,
                },
            }
        ).encode(
            "utf-8"
        )

        with TemporaryDirectory() as temp:
            path = (
                Path(
                    temp
                )
                / SPOTIFY_CREDENTIAL_FILENAME
            )

            path.write_bytes(
                b"dummy-encrypted-file"
            )

            store = SpotifyCredentialStore(
                path,
                unprotect_fn=(
                    lambda protected: plaintext
                ),
            )

            with self.assertRaises(
                SpotifyCredentialStoreError
            ) as context:
                store.load()

            failure = context.exception

            self.assertEqual(
                failure.error_code,
                "credential_corrupt",
            )

            rendered = (
                repr(
                    failure
                )
                + str(
                    failure
                )
            )

            self.assertNotIn(
                access_marker,
                rendered,
            )

            self.assertNotIn(
                refresh_marker,
                rendered,
            )

            self.assertFalse(
                path.exists()
            )

            self.assertIsNotNone(
                failure.quarantine_path
            )

    def test_oversized_file_is_quarantined_before_unprotect(
        self,
    ):
        calls = []

        def forbidden_unprotect(
            protected,
        ):
            calls.append(
                protected
            )

            raise AssertionError(
                "Oversized file reached DPAPI"
            )

        with TemporaryDirectory() as temp:
            path = (
                Path(
                    temp
                )
                / SPOTIFY_CREDENTIAL_FILENAME
            )

            path.write_bytes(
                b"x"
                * (
                    MAX_SPOTIFY_CREDENTIAL_BYTES
                    + 1
                )
            )

            store = SpotifyCredentialStore(
                path,
                unprotect_fn=(
                    forbidden_unprotect
                ),
            )

            with self.assertRaises(
                SpotifyCredentialStoreError
            ) as context:
                store.load()

            self.assertEqual(
                context.exception.error_code,
                "credential_corrupt",
            )

            self.assertEqual(
                calls,
                [],
            )

            self.assertFalse(
                path.exists()
            )

    def test_atomic_replace_failure_preserves_existing_file(
        self,
    ):
        existing = (
            b"existing-encrypted-credentials"
        )

        def fail_replace(
            source,
            destination,
        ):
            raise OSError(
                "simulated replace failure"
            )

        with TemporaryDirectory() as temp:
            path = (
                Path(
                    temp
                )
                / SPOTIFY_CREDENTIAL_FILENAME
            )

            path.write_bytes(
                existing
            )

            store = SpotifyCredentialStore(
                path,
                protect_fn=(
                    lambda plaintext: (
                        b"replacement-encrypted-data"
                    )
                ),
                replace_fn=(
                    fail_replace
                ),
            )

            with self.assertRaises(
                SpotifyCredentialStoreError
            ) as context:
                store.save(
                    make_token()
                )

            self.assertEqual(
                context.exception.error_code,
                "save_failed",
            )

            self.assertEqual(
                path.read_bytes(),
                existing,
            )

            leftovers = list(
                path.parent.glob(
                    f".{path.name}.*.tmp"
                )
            )

            self.assertEqual(
                leftovers,
                [],
            )

    def test_dpapi_protection_failure_is_wrapped_safely(
        self,
    ):
        access_marker = (
            "dummy-access-secret-protect-failure"
        )

        token = SpotifyTokenBundle(
            access_token=access_marker,
            refresh_token=(
                "dummy-refresh-secret-protect-failure"
            ),
            token_type="Bearer",
            expires_in=3600,
            granted_scopes=(
                "user-read-private",
            ),
            obtained_at=1000.0,
            authorized_at=900.0,
        )

        def fail_protect(
            plaintext,
        ):
            raise WindowsDpapiError(
                error_code="protect_failed",
                message=(
                    "simulated DPAPI failure"
                ),
            )

        with TemporaryDirectory() as temp:
            path = (
                Path(
                    temp
                )
                / SPOTIFY_CREDENTIAL_FILENAME
            )

            store = SpotifyCredentialStore(
                path,
                protect_fn=(
                    fail_protect
                ),
            )

            with self.assertRaises(
                SpotifyCredentialStoreError
            ) as context:
                store.save(
                    token
                )

            failure = context.exception

            self.assertEqual(
                failure.error_code,
                "protection_failed",
            )

            self.assertNotIn(
                access_marker,
                repr(
                    failure
                ),
            )

            self.assertIsNone(
                failure.__cause__
            )

            self.assertFalse(
                path.exists()
            )

    def test_save_rejects_non_token_input(
        self,
    ):
        with TemporaryDirectory() as temp:
            store = SpotifyCredentialStore(
                (
                    Path(
                        temp
                    )
                    / SPOTIFY_CREDENTIAL_FILENAME
                )
            )

            with self.assertRaises(
                TypeError
            ):
                store.save(
                    "not-a-token"
                )

    def test_invalid_exact_payload_shape_is_quarantined(
        self,
    ):
        plaintext = json.dumps(
            {
                "schema": 1,
                "kind": (
                    "spotify_oauth_token"
                ),
                "token": {},
                "unexpected": True,
            }
        ).encode(
            "utf-8"
        )

        with TemporaryDirectory() as temp:
            path = (
                Path(
                    temp
                )
                / SPOTIFY_CREDENTIAL_FILENAME
            )

            path.write_bytes(
                b"encrypted-placeholder"
            )

            store = SpotifyCredentialStore(
                path,
                unprotect_fn=(
                    lambda protected: plaintext
                ),
            )

            with self.assertRaises(
                SpotifyCredentialStoreError
            ) as context:
                store.load()

            self.assertEqual(
                context.exception.error_code,
                "credential_corrupt",
            )

            self.assertFalse(
                path.exists()
            )


class SpotifyCredentialStoreBoundaryTests(
    unittest.TestCase
):
    def test_store_does_not_use_settings_logging_or_plaintext_fallback(
        self,
    ):
        root = (
            Path(
                __file__
            )
            .resolve()
            .parents[1]
        )

        source = (
            root
            / "src"
            / "spotify"
            / "credential_store.py"
        ).read_text(
            encoding="utf-8"
        )

        forbidden = (
            "QSettings",
            "keyring",
            "client_secret",
            "logging.",
            "print(",
            "pickle",
            "settings_backup",
        )

        for marker in forbidden:
            with self.subTest(
                marker=marker
            ):
                self.assertNotIn(
                    marker,
                    source,
                )

    def test_store_requires_dpapi_and_atomic_replace(
        self,
    ):
        root = (
            Path(
                __file__
            )
            .resolve()
            .parents[1]
        )

        source = (
            root
            / "src"
            / "spotify"
            / "credential_store.py"
        ).read_text(
            encoding="utf-8"
        )

        required = (
            "protect_data",
            "unprotect_data",
            "os.replace",
            "spotify_auth.dat",
            "SPOTIFY_CREDENTIAL_SCHEMA",
        )

        for marker in required:
            with self.subTest(
                marker=marker
            ):
                self.assertIn(
                    marker,
                    source,
                )


if __name__ == "__main__":
    unittest.main()
