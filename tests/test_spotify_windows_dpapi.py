from __future__ import annotations

import os
from pathlib import Path
import unittest


from src.spotify.windows_dpapi import (
    WindowsDpapiError,
)
from src.spotify.windows_dpapi import (
    protect_data,
)
from src.spotify.windows_dpapi import (
    unprotect_data,
)


@unittest.skipUnless(
    os.name == "nt",
    "Windows DPAPI tests require Windows",
)
class WindowsDpapiLiveTests(
    unittest.TestCase
):
    def test_real_dpapi_round_trip(
        self,
    ):
        plaintext = (
            b"spotify-test-credential-"
            b"0123456789"
        )

        protected = protect_data(
            plaintext
        )

        recovered = unprotect_data(
            protected
        )

        self.assertEqual(
            recovered,
            plaintext,
        )

    def test_ciphertext_does_not_contain_plaintext(
        self,
    ):
        plaintext = (
            b"highly-distinct-spotify-"
            b"credential-marker"
        )

        protected = protect_data(
            plaintext
        )

        self.assertNotEqual(
            protected,
            plaintext,
        )

        self.assertNotIn(
            plaintext,
            protected,
        )

    def test_tampered_ciphertext_is_rejected(
        self,
    ):
        protected = bytearray(
            protect_data(
                b"spotify-dpapi-integrity-test"
            )
        )

        index = len(
            protected
        ) // 2

        protected[
            index
        ] ^= 0x01

        with self.assertRaises(
            WindowsDpapiError
        ) as context:
            unprotect_data(
                bytes(
                    protected
                )
            )

        self.assertEqual(
            context.exception.error_code,
            "unprotect_failed",
        )

    def test_protect_rejects_empty_data(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            protect_data(
                b""
            )

    def test_unprotect_rejects_empty_data(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            unprotect_data(
                b""
            )

    def test_protect_rejects_non_bytes(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            protect_data(
                "not-bytes"
            )

    def test_unprotect_rejects_non_bytes(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            unprotect_data(
                "not-bytes"
            )

    def test_dpapi_error_does_not_echo_credentials(
        self,
    ):
        marker = (
            b"credential-that-must-not-appear"
        )

        with self.assertRaises(
            WindowsDpapiError
        ) as context:
            unprotect_data(
                marker
            )

        rendered = repr(
            context.exception
        )

        self.assertNotIn(
            marker.decode(
                "ascii"
            ),
            rendered,
        )


class WindowsDpapiBoundaryTests(
    unittest.TestCase
):
    def test_module_has_no_persistence_or_settings_layer(
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
            / "windows_dpapi.py"
        ).read_text(
            encoding="utf-8"
        )

        forbidden = (
            "QSettings",
            "spotify_auth.dat",
            "json.dump",
            "write_text",
            "write_bytes",
            "keyring",
        )

        for marker in forbidden:
            with self.subTest(
                marker=marker
            ):
                self.assertNotIn(
                    marker,
                    source,
                )

    def test_module_uses_current_user_dpapi_without_machine_scope(
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
            / "windows_dpapi.py"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "CryptProtectData",
            source,
        )

        self.assertIn(
            "CryptUnprotectData",
            source,
        )

        self.assertNotIn(
            "CRYPTPROTECT_LOCAL_MACHINE",
            source,
        )


if __name__ == "__main__":
    unittest.main()
