from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
import unittest
from urllib.parse import parse_qs
from urllib.parse import urlencode
from urllib.parse import urlsplit

from src.spotify.auth_state import (
    AuthorizationCallback,
)
from src.spotify.auth_state import (
    OAuthValidationError,
)
from src.spotify.auth_state import (
    build_authorization_request,
)
from src.spotify.auth_state import (
    generate_oauth_state,
)
from src.spotify.auth_state import (
    parse_authorization_callback,
)
from src.spotify.auth_state import (
    validate_loopback_redirect_uri,
)
from src.spotify.constants import (
    SPOTIFY_ACCOUNT_SCOPES,
)
from src.spotify.constants import (
    SPOTIFY_AUTHORIZE_URL,
)
from src.spotify.constants import (
    SPOTIFY_CALLBACK_PORT,
)
from src.spotify.constants import (
    SPOTIFY_CONNECT_SCOPES,
)
from src.spotify.constants import (
    SPOTIFY_LIBRARY_READ_SCOPES,
)
from src.spotify.constants import (
    SPOTIFY_LOOPBACK_REGISTRATION_URI,
)
from src.spotify.constants import (
    SPOTIFY_PLAYBACK_CONTROL_SCOPES,
)
from src.spotify.constants import (
    SPOTIFY_PLAYBACK_READ_SCOPES,
)
from src.spotify.constants import (
    SPOTIFY_PLAYLIST_READ_SCOPES,
)
from src.spotify.constants import (
    SPOTIFY_RECENTLY_PLAYED_SCOPES,
)
from src.spotify.constants import (
    build_loopback_redirect_uri,
)
from src.spotify.constants import (
    combine_scopes,
)
from src.spotify.constants import (
    normalize_scopes,
)
from src.spotify.models import (
    SpotifyAccount,
)
from src.spotify.models import (
    SpotifyTokenBundle,
)
from src.spotify.pkce import (
    PKCE_ALLOWED_CHARACTERS,
)
from src.spotify.pkce import (
    derive_code_challenge,
)
from src.spotify.pkce import (
    generate_code_verifier,
)
from src.spotify.pkce import (
    generate_pkce_pair,
)
from src.spotify.pkce import (
    validate_code_verifier,
)


RFC_7636_VERIFIER = (
    "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
)

RFC_7636_CHALLENGE = (
    "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
)

TEST_STATE = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopq"
)

TEST_CLIENT_ID = (
    "0123456789abcdef"
    "0123456789abcdef"
)

TEST_PORT = 54321


class SpotifyConstantsTests(
    unittest.TestCase
):
    def test_registration_uri_uses_fixed_loopback_port(
        self,
    ):
        self.assertEqual(
            SPOTIFY_CALLBACK_PORT,
            43821,
        )

        self.assertEqual(
            SPOTIFY_LOOPBACK_REGISTRATION_URI,
            "http://127.0.0.1:43821/callback",
        )

    def test_dynamic_redirect_uri(
        self,
    ):
        self.assertEqual(
            build_loopback_redirect_uri(
                TEST_PORT
            ),
            (
                "http://127.0.0.1:"
                f"{TEST_PORT}/callback"
            ),
        )

    def test_invalid_redirect_port_is_rejected(
        self,
    ):
        for value in (
            0,
            65536,
            -1,
        ):
            with self.subTest(
                value=value
            ):
                with self.assertRaises(
                    ValueError
                ):
                    build_loopback_redirect_uri(
                        value
                    )

        with self.assertRaises(
            TypeError
        ):
            build_loopback_redirect_uri(
                True
            )

    def test_scope_groups_are_feature_specific(
        self,
    ):
        self.assertEqual(
            SPOTIFY_CONNECT_SCOPES,
            SPOTIFY_ACCOUNT_SCOPES,
        )

        self.assertEqual(
            SPOTIFY_CONNECT_SCOPES,
            (
                "user-read-private",
            ),
        )

        self.assertEqual(
            SPOTIFY_PLAYBACK_READ_SCOPES,
            (
                "user-read-playback-state",
            ),
        )

        self.assertEqual(
            SPOTIFY_PLAYBACK_CONTROL_SCOPES,
            (
                "user-modify-playback-state",
            ),
        )

        self.assertEqual(
            SPOTIFY_LIBRARY_READ_SCOPES,
            (
                "user-library-read",
            ),
        )

        self.assertEqual(
            SPOTIFY_PLAYLIST_READ_SCOPES,
            (
                "playlist-read-private",
                "playlist-read-collaborative",
            ),
        )

        self.assertEqual(
            SPOTIFY_RECENTLY_PLAYED_SCOPES,
            (
                "user-read-recently-played",
            ),
        )

    def test_scope_combination_is_ordered_and_deduplicated(
        self,
    ):
        scopes = combine_scopes(
            SPOTIFY_ACCOUNT_SCOPES,
            SPOTIFY_PLAYBACK_READ_SCOPES,
            SPOTIFY_ACCOUNT_SCOPES,
        )

        self.assertEqual(
            scopes,
            (
                "user-read-private",
                "user-read-playback-state",
            ),
        )

    def test_scope_normalization_rejects_ambiguous_input(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            normalize_scopes(
                "user-read-private"
            )

        with self.assertRaises(
            ValueError
        ):
            normalize_scopes(
                ()
            )

        with self.assertRaises(
            ValueError
        ):
            normalize_scopes(
                (
                    "user-read-private extra",
                )
            )


class SpotifyPkceTests(
    unittest.TestCase
):
    def test_rfc_7636_known_vector(
        self,
    ):
        self.assertEqual(
            derive_code_challenge(
                RFC_7636_VERIFIER
            ),
            RFC_7636_CHALLENGE,
        )

    def test_generated_verifier_uses_valid_characters(
        self,
    ):
        verifier = generate_code_verifier(
            64
        )

        self.assertEqual(
            len(
                verifier
            ),
            64,
        )

        self.assertTrue(
            set(
                verifier
            ).issubset(
                set(
                    PKCE_ALLOWED_CHARACTERS
                )
            )
        )

    def test_boundary_verifier_lengths_are_supported(
        self,
    ):
        self.assertEqual(
            len(
                generate_code_verifier(
                    43
                )
            ),
            43,
        )

        self.assertEqual(
            len(
                generate_code_verifier(
                    128
                )
            ),
            128,
        )

    def test_invalid_verifier_lengths_are_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            generate_code_verifier(
                42
            )

        with self.assertRaises(
            ValueError
        ):
            generate_code_verifier(
                129
            )

    def test_invalid_verifier_character_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            validate_code_verifier(
                ("A" * 42) + "!"
            )

    def test_pkce_pair_matches_verifier(
        self,
    ):
        pair = generate_pkce_pair()

        self.assertEqual(
            pair.challenge,
            derive_code_challenge(
                pair.verifier
            ),
        )

        self.assertNotIn(
            pair.verifier,
            repr(
                pair
            ),
        )


class SpotifyModelTests(
    unittest.TestCase
):
    def test_token_model_tracks_access_expiry_and_authorization_time(
        self,
    ):
        token = SpotifyTokenBundle(
            access_token="access-secret",
            refresh_token="refresh-secret",
            expires_in=3600,
            granted_scopes=(
                "user-read-private",
                "user-read-private",
            ),
            obtained_at=1000,
            authorized_at=500,
        )

        self.assertEqual(
            token.expires_at,
            4600.0,
        )

        self.assertEqual(
            token.authorized_at,
            500.0,
        )

        self.assertEqual(
            token.granted_scopes,
            (
                "user-read-private",
            ),
        )

        self.assertTrue(
            token.has_refresh_token
        )

        self.assertFalse(
            token.is_access_token_expired(
                4569,
                skew_seconds=30,
            )
        )

        self.assertTrue(
            token.is_access_token_expired(
                4570,
                skew_seconds=30,
            )
        )

    def test_token_repr_hides_credentials(
        self,
    ):
        token = SpotifyTokenBundle(
            access_token="very-secret-access",
            refresh_token="very-secret-refresh",
        )

        rendered = repr(
            token
        )

        self.assertNotIn(
            "very-secret-access",
            rendered,
        )

        self.assertNotIn(
            "very-secret-refresh",
            rendered,
        )

    def test_invalid_token_data_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            SpotifyTokenBundle(
                access_token=""
            )

        with self.assertRaises(
            ValueError
        ):
            SpotifyTokenBundle(
                access_token="token",
                expires_in=0,
            )

        with self.assertRaises(
            TypeError
        ):
            SpotifyTokenBundle(
                access_token="token",
                expires_in=True,
            )

        with self.assertRaises(
            ValueError
        ):
            SpotifyTokenBundle(
                access_token="token",
                authorized_at=-1,
            )

    def test_account_uses_stable_account_id_model(
        self,
    ):
        account = SpotifyAccount(
            account_id="stable-account-id",
            display_name="03:37am",
            user_id="legacy-user-id",
            uri="spotify:user:legacy-user-id",
        )

        self.assertEqual(
            account.account_id,
            "stable-account-id",
        )

        self.assertEqual(
            account.display_name,
            "03:37am",
        )

    def test_account_model_is_immutable(
        self,
    ):
        account = SpotifyAccount(
            account_id="stable-account-id"
        )

        with self.assertRaises(
            FrozenInstanceError
        ):
            account.account_id = "changed"


class SpotifyAuthorizationTests(
    unittest.TestCase
):
    def setUp(
        self,
    ):
        self.redirect_uri = (
            build_loopback_redirect_uri(
                TEST_PORT
            )
        )

    def test_oauth_state_is_random_and_url_safe(
        self,
    ):
        first = generate_oauth_state()
        second = generate_oauth_state()

        self.assertNotEqual(
            first,
            second,
        )

        self.assertGreaterEqual(
            len(
                first
            ),
            32,
        )

        self.assertTrue(
            all(
                character.isalnum()
                or character in "-_"
                for character in first
            )
        )

    def test_authorization_request_is_pkce_only(
        self,
    ):
        request = build_authorization_request(
            TEST_CLIENT_ID,
            self.redirect_uri,
            state=TEST_STATE,
            code_verifier=RFC_7636_VERIFIER,
        )

        parsed = urlsplit(
            request.url
        )

        query = parse_qs(
            parsed.query
        )

        self.assertEqual(
            (
                f"{parsed.scheme}://"
                f"{parsed.netloc}"
                f"{parsed.path}"
            ),
            SPOTIFY_AUTHORIZE_URL,
        )

        self.assertEqual(
            query["client_id"],
            [
                TEST_CLIENT_ID,
            ],
        )

        self.assertEqual(
            query["response_type"],
            [
                "code",
            ],
        )

        self.assertEqual(
            query["redirect_uri"],
            [
                self.redirect_uri,
            ],
        )

        self.assertEqual(
            query["state"],
            [
                TEST_STATE,
            ],
        )

        self.assertEqual(
            query["scope"],
            [
                "user-read-private",
            ],
        )

        self.assertEqual(
            query["code_challenge_method"],
            [
                "S256",
            ],
        )

        self.assertEqual(
            query["code_challenge"],
            [
                RFC_7636_CHALLENGE,
            ],
        )

        self.assertNotIn(
            "client_secret",
            query,
        )

    def test_authorization_request_can_add_feature_scopes(
        self,
    ):
        scopes = combine_scopes(
            SPOTIFY_ACCOUNT_SCOPES,
            SPOTIFY_PLAYBACK_READ_SCOPES,
            SPOTIFY_PLAYBACK_CONTROL_SCOPES,
        )

        request = build_authorization_request(
            TEST_CLIENT_ID,
            self.redirect_uri,
            scopes=scopes,
            state=TEST_STATE,
            code_verifier=RFC_7636_VERIFIER,
        )

        self.assertEqual(
            request.scopes,
            scopes,
        )

        query = parse_qs(
            urlsplit(
                request.url
            ).query
        )

        self.assertEqual(
            query["scope"],
            [
                (
                    "user-read-private "
                    "user-read-playback-state "
                    "user-modify-playback-state"
                ),
            ],
        )

    def test_authorization_request_repr_hides_state_and_verifier(
        self,
    ):
        request = build_authorization_request(
            TEST_CLIENT_ID,
            self.redirect_uri,
            state=TEST_STATE,
            code_verifier=RFC_7636_VERIFIER,
        )

        rendered = repr(
            request
        )

        self.assertNotIn(
            TEST_STATE,
            rendered,
        )

        self.assertNotIn(
            RFC_7636_VERIFIER,
            rendered,
        )

    def test_localhost_redirect_is_rejected(
        self,
    ):
        with self.assertRaises(
            OAuthValidationError
        ):
            validate_loopback_redirect_uri(
                (
                    "http://localhost:"
                    f"{TEST_PORT}/callback"
                )
            )

    def test_non_loopback_redirect_is_rejected(
        self,
    ):
        with self.assertRaises(
            OAuthValidationError
        ):
            validate_loopback_redirect_uri(
                (
                    "http://192.168.1.5:"
                    f"{TEST_PORT}/callback"
                )
            )

    def test_https_loopback_redirect_is_rejected(
        self,
    ):
        with self.assertRaises(
            OAuthValidationError
        ):
            validate_loopback_redirect_uri(
                (
                    "https://127.0.0.1:"
                    f"{TEST_PORT}/callback"
                )
            )

    def test_registered_redirect_contains_required_port(
        self,
    ):
        self.assertEqual(
            validate_loopback_redirect_uri(
                SPOTIFY_LOOPBACK_REGISTRATION_URI
            ),
            SPOTIFY_LOOPBACK_REGISTRATION_URI,
        )

    def test_redirect_query_and_fragment_are_rejected(
        self,
    ):
        for suffix in (
            "?x=1",
            "#fragment",
        ):
            with self.subTest(
                suffix=suffix
            ):
                with self.assertRaises(
                    OAuthValidationError
                ):
                    validate_loopback_redirect_uri(
                        (
                            self.redirect_uri
                            + suffix
                        )
                    )

    def test_callback_success(
        self,
    ):
        query = urlencode(
            {
                "code": "authorization-code",
                "state": TEST_STATE,
            }
        )

        callback = (
            f"{self.redirect_uri}?"
            f"{query}"
        )

        result = parse_authorization_callback(
            callback,
            expected_redirect_uri=self.redirect_uri,
            expected_state=TEST_STATE,
        )

        self.assertTrue(
            result.approved
        )

        self.assertFalse(
            result.denied
        )

        self.assertEqual(
            result.code,
            "authorization-code",
        )

        self.assertNotIn(
            "authorization-code",
            repr(
                result
            ),
        )

    def test_callback_access_denied_is_a_valid_result(
        self,
    ):
        query = urlencode(
            {
                "error": "access_denied",
                "state": TEST_STATE,
                "error_description": (
                    "User declined access"
                ),
            }
        )

        result = parse_authorization_callback(
            (
                f"{self.redirect_uri}?"
                f"{query}"
            ),
            expected_redirect_uri=self.redirect_uri,
            expected_state=TEST_STATE,
        )

        self.assertTrue(
            result.denied
        )

        self.assertFalse(
            result.approved
        )

        self.assertEqual(
            result.error,
            "access_denied",
        )

    def test_callback_state_mismatch_is_rejected(
        self,
    ):
        different_state = (
            "Z" * len(
                TEST_STATE
            )
        )

        query = urlencode(
            {
                "code": "authorization-code",
                "state": different_state,
            }
        )

        with self.assertRaises(
            OAuthValidationError
        ):
            parse_authorization_callback(
                (
                    f"{self.redirect_uri}?"
                    f"{query}"
                ),
                expected_redirect_uri=self.redirect_uri,
                expected_state=TEST_STATE,
            )

    def test_callback_missing_state_is_rejected(
        self,
    ):
        with self.assertRaises(
            OAuthValidationError
        ):
            parse_authorization_callback(
                (
                    f"{self.redirect_uri}"
                    "?code=authorization-code"
                ),
                expected_redirect_uri=self.redirect_uri,
                expected_state=TEST_STATE,
            )

    def test_callback_duplicate_state_is_rejected(
        self,
    ):
        callback = (
            f"{self.redirect_uri}"
            "?code=authorization-code"
            f"&state={TEST_STATE}"
            f"&state={TEST_STATE}"
        )

        with self.assertRaises(
            OAuthValidationError
        ):
            parse_authorization_callback(
                callback,
                expected_redirect_uri=self.redirect_uri,
                expected_state=TEST_STATE,
            )

    def test_callback_with_code_and_error_is_rejected(
        self,
    ):
        query = urlencode(
            {
                "code": "authorization-code",
                "error": "access_denied",
                "state": TEST_STATE,
            }
        )

        with self.assertRaises(
            OAuthValidationError
        ):
            parse_authorization_callback(
                (
                    f"{self.redirect_uri}?"
                    f"{query}"
                ),
                expected_redirect_uri=self.redirect_uri,
                expected_state=TEST_STATE,
            )

    def test_callback_wrong_target_is_rejected(
        self,
    ):
        wrong_redirect = (
            build_loopback_redirect_uri(
                TEST_PORT + 1
            )
        )

        query = urlencode(
            {
                "code": "authorization-code",
                "state": TEST_STATE,
            }
        )

        with self.assertRaises(
            OAuthValidationError
        ):
            parse_authorization_callback(
                (
                    f"{wrong_redirect}?"
                    f"{query}"
                ),
                expected_redirect_uri=self.redirect_uri,
                expected_state=TEST_STATE,
            )

    def test_callback_without_code_or_error_is_rejected(
        self,
    ):
        with self.assertRaises(
            OAuthValidationError
        ):
            parse_authorization_callback(
                (
                    f"{self.redirect_uri}"
                    f"?state={TEST_STATE}"
                ),
                expected_redirect_uri=self.redirect_uri,
                expected_state=TEST_STATE,
            )


class SpotifyFoundationBoundaryTests(
    unittest.TestCase
):
    def test_foundation_contains_no_client_secret_contract(
        self,
    ):
        root = (
            Path(
                __file__
            )
            .resolve()
            .parents[1]
        )

        production_files = (
            "src/spotify/constants.py",
            "src/spotify/models.py",
            "src/spotify/pkce.py",
            "src/spotify/auth_state.py",
        )

        combined = "\n".join(
            (
                root
                / relative
            ).read_text(
                encoding="utf-8"
            )
            for relative in production_files
        )

        forbidden = (
            "client_"
            + "secret"
        )

        self.assertNotIn(
            forbidden,
            combined,
        )

    def test_foundation_has_no_network_browser_or_persistence_layer(
        self,
    ):
        root = (
            Path(
                __file__
            )
            .resolve()
            .parents[1]
        )

        production_files = (
            "src/spotify/constants.py",
            "src/spotify/models.py",
            "src/spotify/pkce.py",
            "src/spotify/auth_state.py",
        )

        combined = "\n".join(
            (
                root
                / relative
            ).read_text(
                encoding="utf-8"
            )
            for relative in production_files
        )

        forbidden = (
            "urllib.request",
            "http.server",
            "webbrowser",
            "QSettings",
            "keyring",
            "requests.",
        )

        for marker in forbidden:
            with self.subTest(
                marker=marker
            ):
                self.assertNotIn(
                    marker,
                    combined,
                )


if __name__ == "__main__":
    unittest.main()
