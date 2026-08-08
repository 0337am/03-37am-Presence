from __future__ import annotations

from urllib.parse import (
    parse_qs,
    urlsplit,
)
import unittest

from src.spotify.constants import (
    SPOTIFY_API_BASE_URL,
)
from src.spotify.web_api import (
    MAX_SPOTIFY_API_URL_LENGTH,
    SpotifyWebApiClient,
    SpotifyWebApiError,
)
from tests.test_spotify_web_api import (
    FakeResponse,
    RecordingUrlOpen,
)


class SpotifyGenericWebApiRequestTests(
    unittest.TestCase
):
    def client_for(
        self,
        expected_url,
        payload=None,
        *,
        response_url=None,
    ):
        if payload is None:
            payload = {
                "ok": True,
            }

        if response_url is None:
            response_url = (
                expected_url
            )

        response = FakeResponse(
            payload,
            url=response_url,
        )

        transport = (
            RecordingUrlOpen(
                response
            )
        )

        client = (
            SpotifyWebApiClient(
                urlopen=transport
            )
        )

        return (
            client,
            transport,
            response,
        )

    def test_generic_get_builds_relative_spotify_api_request(
        self,
    ):
        expected_url = (
            f"{SPOTIFY_API_BASE_URL}"
            "/search"
            "?q=juice+wrld"
            "&type=track%2Calbum"
            "&limit=20"
            "&offset=0"
        )

        client, transport, response = (
            self.client_for(
                expected_url,
                {
                    "tracks": {
                        "items": [],
                    },
                },
            )
        )

        payload = client.get_json(
            "test-access-token",
            "/search",
            query={
                "q": "juice wrld",
                "type": "track,album",
                "limit": 20,
                "offset": 0,
            },
        )

        self.assertEqual(
            payload,
            {
                "tracks": {
                    "items": [],
                },
            },
        )

        self.assertEqual(
            len(
                transport.requests
            ),
            1,
        )

        request = (
            transport.requests[0]
        )

        self.assertEqual(
            request.full_url,
            expected_url,
        )

        self.assertEqual(
            request.get_method(),
            "GET",
        )

        self.assertEqual(
            request.get_header(
                "Authorization"
            ),
            "Bearer test-access-token",
        )

        self.assertTrue(
            response.closed
        )

    def test_query_values_are_encoded_safely(
        self,
    ):
        expected_url = (
            f"{SPOTIFY_API_BASE_URL}"
            "/search"
            "?q=A%26B+%2F+100%25"
            "&type=track"
        )

        client, transport, _ = (
            self.client_for(
                expected_url
            )
        )

        client.get_json(
            "token",
            "/search",
            query={
                "q": "A&B / 100%",
                "type": "track",
            },
        )

        parsed = urlsplit(
            transport.requests[
                0
            ].full_url
        )

        query = parse_qs(
            parsed.query
        )

        self.assertEqual(
            query[
                "q"
            ],
            [
                "A&B / 100%",
            ],
        )

        self.assertEqual(
            query[
                "type"
            ],
            [
                "track",
            ],
        )

    def test_boolean_query_values_are_lowercase(
        self,
    ):
        expected_url = (
            f"{SPOTIFY_API_BASE_URL}"
            "/example"
            "?active=true"
            "&shuffle=false"
        )

        client, transport, _ = (
            self.client_for(
                expected_url
            )
        )

        client.get_json(
            "token",
            "/example",
            query={
                "active": True,
                "shuffle": False,
            },
        )

        self.assertTrue(
            transport.requests[
                0
            ].full_url.endswith(
                (
                    "?active=true"
                    "&shuffle=false"
                )
            )
        )

    def test_none_query_values_are_omitted(
        self,
    ):
        expected_url = (
            f"{SPOTIFY_API_BASE_URL}"
            "/search"
            "?q=test"
        )

        client, transport, _ = (
            self.client_for(
                expected_url
            )
        )

        client.get_json(
            "token",
            "/search",
            query={
                "q": "test",
                "market": None,
            },
        )

        self.assertEqual(
            transport.requests[
                0
            ].full_url,
            expected_url,
        )

    def test_empty_query_mapping_adds_no_question_mark(
        self,
    ):
        expected_url = (
            f"{SPOTIFY_API_BASE_URL}"
            "/me/player/devices"
        )

        client, transport, _ = (
            self.client_for(
                expected_url
            )
        )

        client.get_json(
            "token",
            "/me/player/devices",
            query={},
        )

        self.assertEqual(
            transport.requests[
                0
            ].full_url,
            expected_url,
        )

    def test_absolute_and_scheme_relative_paths_are_rejected(
        self,
    ):
        transport = (
            RecordingUrlOpen(
                FakeResponse(
                    {}
                )
            )
        )

        client = SpotifyWebApiClient(
            urlopen=transport
        )

        invalid_paths = (
            "https://api.spotify.com/v1/me",
            "//api.spotify.com/v1/me",
            "search",
            "",
            "/",
        )

        for path in invalid_paths:
            with self.subTest(
                path=path
            ):
                with self.assertRaises(
                    ValueError
                ):
                    client.get_json(
                        "token",
                        path,
                    )

        self.assertEqual(
            transport.requests,
            [],
        )

    def test_path_cannot_embed_query_or_fragment(
        self,
    ):
        transport = (
            RecordingUrlOpen(
                FakeResponse(
                    {}
                )
            )
        )

        client = SpotifyWebApiClient(
            urlopen=transport
        )

        for path in (
            "/search?q=test",
            "/search#fragment",
        ):
            with self.subTest(
                path=path
            ):
                with self.assertRaises(
                    ValueError
                ):
                    client.get_json(
                        "token",
                        path,
                    )

        self.assertEqual(
            transport.requests,
            [],
        )

    def test_path_traversal_is_rejected_in_plain_and_encoded_forms(
        self,
    ):
        transport = (
            RecordingUrlOpen(
                FakeResponse(
                    {}
                )
            )
        )

        client = SpotifyWebApiClient(
            urlopen=transport
        )

        for path in (
            "/../me",
            "/foo/./bar",
            "/%2e%2e/me",
            "/foo/%2E/bar",
            "/%252e%252e/me",
        ):
            with self.subTest(
                path=path
            ):
                with self.assertRaises(
                    ValueError
                ):
                    client.get_json(
                        "token",
                        path,
                    )

        self.assertEqual(
            transport.requests,
            [],
        )

    def test_path_whitespace_control_and_backslash_are_rejected(
        self,
    ):
        transport = (
            RecordingUrlOpen(
                FakeResponse(
                    {}
                )
            )
        )

        client = SpotifyWebApiClient(
            urlopen=transport
        )

        for path in (
            "/search path",
            "/search\n",
            "/foo\\bar",
            "/foo/%0a/bar",
        ):
            with self.subTest(
                path=repr(
                    path
                )
            ):
                with self.assertRaises(
                    ValueError
                ):
                    client.get_json(
                        "token",
                        path,
                    )

        self.assertEqual(
            transport.requests,
            [],
        )

    def test_path_type_is_validated_before_network(
        self,
    ):
        transport = (
            RecordingUrlOpen(
                FakeResponse(
                    {}
                )
            )
        )

        client = SpotifyWebApiClient(
            urlopen=transport
        )

        for path in (
            None,
            123,
            object(),
        ):
            with self.subTest(
                value=type(
                    path
                ).__name__
            ):
                with self.assertRaises(
                    TypeError
                ):
                    client.get_json(
                        "token",
                        path,
                    )

        self.assertEqual(
            transport.requests,
            [],
        )

    def test_query_must_be_mapping(
        self,
    ):
        transport = (
            RecordingUrlOpen(
                FakeResponse(
                    {}
                )
            )
        )

        client = SpotifyWebApiClient(
            urlopen=transport
        )

        for query in (
            "q=test",
            [
                (
                    "q",
                    "test",
                ),
            ],
            123,
        ):
            with self.subTest(
                value=type(
                    query
                ).__name__
            ):
                with self.assertRaises(
                    TypeError
                ):
                    client.get_json(
                        "token",
                        "/search",
                        query=query,
                    )

        self.assertEqual(
            transport.requests,
            [],
        )

    def test_query_keys_are_strict(
        self,
    ):
        transport = (
            RecordingUrlOpen(
                FakeResponse(
                    {}
                )
            )
        )

        client = SpotifyWebApiClient(
            urlopen=transport
        )

        invalid_queries = (
            {
                "": "test",
            },
            {
                "bad key": "test",
            },
            {
                "bad\nkey": "test",
            },
            {
                123: "test",
            },
        )

        for query in invalid_queries:
            with self.subTest(
                query=repr(
                    query
                )
            ):
                with self.assertRaises(
                    (
                        TypeError,
                        ValueError,
                    )
                ):
                    client.get_json(
                        "token",
                        "/search",
                        query=query,
                    )

        self.assertEqual(
            transport.requests,
            [],
        )

    def test_query_value_types_are_strict(
        self,
    ):
        transport = (
            RecordingUrlOpen(
                FakeResponse(
                    {}
                )
            )
        )

        client = SpotifyWebApiClient(
            urlopen=transport
        )

        for value in (
            1.5,
            [],
            {},
            object(),
        ):
            with self.subTest(
                value=type(
                    value
                ).__name__
            ):
                with self.assertRaises(
                    TypeError
                ):
                    client.get_json(
                        "token",
                        "/search",
                        query={
                            "q": value,
                        },
                    )

        self.assertEqual(
            transport.requests,
            [],
        )

    def test_query_control_characters_are_rejected(
        self,
    ):
        transport = (
            RecordingUrlOpen(
                FakeResponse(
                    {}
                )
            )
        )

        client = SpotifyWebApiClient(
            urlopen=transport
        )

        for value in (
            "bad\nvalue",
            "bad\rvalue",
            "bad\x7fvalue",
        ):
            with self.subTest(
                value=repr(
                    value
                )
            ):
                with self.assertRaises(
                    ValueError
                ):
                    client.get_json(
                        "token",
                        "/search",
                        query={
                            "q": value,
                        },
                    )

        self.assertEqual(
            transport.requests,
            [],
        )

    def test_request_url_length_is_bounded(
        self,
    ):
        transport = (
            RecordingUrlOpen(
                FakeResponse(
                    {}
                )
            )
        )

        client = SpotifyWebApiClient(
            urlopen=transport
        )

        oversized_query = (
            "x"
            * MAX_SPOTIFY_API_URL_LENGTH
        )

        with self.assertRaises(
            ValueError
        ):
            client.get_json(
                "token",
                "/search",
                query={
                    "q": oversized_query,
                },
            )

        self.assertEqual(
            transport.requests,
            [],
        )

    def test_untrusted_generic_response_url_is_rejected(
        self,
    ):
        expected_url = (
            f"{SPOTIFY_API_BASE_URL}"
            "/search?q=test"
        )

        client, _, _ = (
            self.client_for(
                expected_url,
                response_url=(
                    "https://example.com/stolen"
                ),
            )
        )

        with self.assertRaises(
            SpotifyWebApiError
        ) as caught:
            client.get_json(
                "secret-token",
                "/search",
                query={
                    "q": "test",
                },
            )

        self.assertEqual(
            caught.exception.error_code,
            "untrusted_response",
        )

        self.assertNotIn(
            "secret-token",
            str(
                caught.exception
            ),
        )

    def test_generic_get_validates_access_token_before_network(
        self,
    ):
        expected_url = (
            f"{SPOTIFY_API_BASE_URL}"
            "/search"
        )

        client, transport, _ = (
            self.client_for(
                expected_url
            )
        )

        for token in (
            "",
            "   ",
            "token with spaces",
        ):
            with self.subTest(
                token=repr(
                    token
                )
            ):
                with self.assertRaises(
                    ValueError
                ):
                    client.get_json(
                        token,
                        "/search",
                    )

        with self.assertRaises(
            TypeError
        ):
            client.get_json(
                None,
                "/search",
            )

        self.assertEqual(
            transport.requests,
            [],
        )






class SpotifyPrivateTransportGuardTests(
    unittest.TestCase
):
    def client_for(
        self,
        expected_url,
        payload=None,
    ):
        if payload is None:
            payload = {
                "ok": True,
            }

        response = FakeResponse(
            payload,
            url=expected_url,
        )

        transport = RecordingUrlOpen(
            response
        )

        client = SpotifyWebApiClient(
            urlopen=transport
        )

        return (
            client,
            transport,
            response,
        )

    def test_private_transport_accepts_trusted_generic_spotify_url(
        self,
    ):
        expected_url = (
            f"{SPOTIFY_API_BASE_URL}"
            "/search?q=test&type=track"
        )

        client, transport, response = (
            self.client_for(
                expected_url,
                {
                    "tracks": {
                        "items": [],
                    },
                },
            )
        )

        payload = client._get_json(
            expected_url,
            "test-access-token",
        )

        self.assertEqual(
            payload,
            {
                "tracks": {
                    "items": [],
                },
            },
        )

        self.assertEqual(
            len(
                transport.requests
            ),
            1,
        )

        self.assertEqual(
            transport.requests[
                0
            ].full_url,
            expected_url,
        )

        self.assertTrue(
            response.closed
        )

    def test_private_transport_rejects_untrusted_urls_before_network(
        self,
    ):
        transport = RecordingUrlOpen(
            FakeResponse(
                {}
            )
        )

        client = SpotifyWebApiClient(
            urlopen=transport
        )

        invalid_urls = (
            "https://example.com/v1/search",
            "http://api.spotify.com/v1/search",
            (
                "https://api.spotify.com.evil.example"
                "/v1/search"
            ),
            (
                "https://api.spotify.com@evil.example"
                "/v1/search"
            ),
            "https://api.spotify.com/v10/search",
            (
                "https://api.spotify.com"
                "/v1/../accounts"
            ),
            (
                "https://api.spotify.com"
                "/v1/%2e%2e/accounts"
            ),
            (
                "https://api.spotify.com"
                "/v1/search#fragment"
            ),
        )

        for url in invalid_urls:
            with self.subTest(
                url=url
            ):
                with self.assertRaises(
                    ValueError
                ):
                    client._get_json(
                        url,
                        "secret-token",
                    )

        self.assertEqual(
            transport.requests,
            [],
        )



class SpotifyGenericRequestBoundaryTests(
    unittest.TestCase
):
    def test_public_generic_request_method_exists(
        self,
    ):
        self.assertTrue(
            callable(
                getattr(
                    SpotifyWebApiClient,
                    "get_json",
                    None,
                )
            )
        )

    def test_generic_layer_remains_transport_only(
        self,
    ):
        root = (
            __import__(
                "pathlib"
            )
            .Path(
                __file__
            )
            .resolve()
            .parents[1]
        )

        source = (
            root
            / "src"
            / "spotify"
            / "web_api.py"
        ).read_text(
            encoding="utf-8"
        )

        forbidden = (
            "QSettings",
            "PyQt6",
            "SpotifyCredentialStore",
            "windows_dpapi",
            "spotify_auth.dat",
            "client_secret",
            "logging.",
            "print(",
        )

        for marker in forbidden:
            with self.subTest(
                marker=marker
            ):
                self.assertNotIn(
                    marker,
                    source,
                )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
