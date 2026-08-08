from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
from numbers import Real
import time
from typing import cast
from urllib.parse import urlsplit

from src.spotify.constants import (
    SPOTIFY_CALLBACK_PATH,
)
from src.spotify.constants import (
    SPOTIFY_CALLBACK_PORT,
)
from src.spotify.constants import (
    SPOTIFY_LOOPBACK_HOST,
)
from src.spotify.constants import (
    build_loopback_redirect_uri,
)


MAX_CALLBACK_TARGET_BYTES = 8192
CALLBACK_POLL_SECONDS = 0.25

SUCCESS_PAGE = (
    "<!doctype html>"
    "<html>"
    "<head>"
    "<meta charset=\"utf-8\">"
    "<meta name=\"viewport\" "
    "content=\"width=device-width,initial-scale=1\">"
    "<title>03:37am Presence</title>"
    "</head>"
    "<body>"
    "<h1>Spotify connection received.</h1>"
    "<p>You can return to 03:37am Presence.</p>"
    "</body>"
    "</html>"
).encode(
    "utf-8"
)


class LoopbackCallbackError(
    RuntimeError
):
    pass


class LoopbackCallbackTimeout(
    TimeoutError,
    LoopbackCallbackError,
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class LoopbackCallbackResult:
    callback_url: str = field(
        repr=False
    )
    request_target: str = field(
        repr=False
    )


class _LoopbackHttpServer(
    HTTPServer
):
    allow_reuse_address = False

    def __init__(
        self,
        server_address,
        handler_class,
    ) -> None:
        self.callback_target: str | None = None

        super().__init__(
            server_address,
            handler_class,
        )


class _CallbackHandler(
    BaseHTTPRequestHandler
):
    protocol_version = "HTTP/1.1"
    server_version = "0337amSpotifyCallback/1.0"
    sys_version = ""

    def log_message(
        self,
        format,
        *args,
    ) -> None:
        # Callback URLs contain OAuth data and must never be
        # written to stdout/stderr by the HTTP handler.
        return

    def _send_plain_response(
        self,
        status: int,
        body: bytes,
    ) -> None:
        self.send_response(
            status
        )

        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8",
        )

        self.send_header(
            "Content-Length",
            str(
                len(
                    body
                )
            ),
        )

        self.send_header(
            "Cache-Control",
            "no-store",
        )

        self.send_header(
            "Connection",
            "close",
        )

        self.end_headers()

        self.wfile.write(
            body
        )

        self.close_connection = True

    def do_GET(
        self,
    ) -> None:
        target = self.path

        if len(
            target.encode(
                "utf-8",
                errors="replace",
            )
        ) > MAX_CALLBACK_TARGET_BYTES:
            self._send_plain_response(
                414,
                b"Request target is too long.",
            )
            return

        parts = urlsplit(
            target
        )

        if (
            parts.scheme
            or parts.netloc
        ):
            self._send_plain_response(
                400,
                b"Invalid callback target.",
            )
            return

        if parts.path != SPOTIFY_CALLBACK_PATH:
            self._send_plain_response(
                404,
                b"Not found.",
            )
            return

        server = cast(
            _LoopbackHttpServer,
            self.server,
        )

        if server.callback_target is not None:
            self._send_plain_response(
                409,
                b"Callback already received.",
            )
            return

        server.callback_target = target

        self.send_response(
            200
        )

        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8",
        )

        self.send_header(
            "Content-Length",
            str(
                len(
                    SUCCESS_PAGE
                )
            ),
        )

        self.send_header(
            "Cache-Control",
            "no-store",
        )

        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; "
            "style-src 'unsafe-inline'",
        )

        self.send_header(
            "Referrer-Policy",
            "no-referrer",
        )

        self.send_header(
            "Connection",
            "close",
        )

        self.end_headers()

        self.wfile.write(
            SUCCESS_PAGE
        )

        self.close_connection = True

    def do_POST(
        self,
    ) -> None:
        self._send_plain_response(
            405,
            b"Method not allowed.",
        )


class SpotifyLoopbackCallbackServer:
    def __init__(
        self,
        *,
        host: str = SPOTIFY_LOOPBACK_HOST,
        port: int = SPOTIFY_CALLBACK_PORT,
    ) -> None:
        if host != SPOTIFY_LOOPBACK_HOST:
            raise ValueError(
                "Spotify callback server may bind only to 127.0.0.1"
            )

        if (
            isinstance(
                port,
                bool,
            )
            or not isinstance(
                port,
                int,
            )
        ):
            raise TypeError(
                "callback server port must be an integer"
            )

        if not 0 <= port <= 65535:
            raise ValueError(
                "callback server port must be between 0 and 65535"
            )

        self._server = _LoopbackHttpServer(
            (
                host,
                port,
            ),
            _CallbackHandler,
        )

        self._closed = False
        self._consumed = False

        bound_host, bound_port = (
            self._server.server_address[:2]
        )

        if bound_host != SPOTIFY_LOOPBACK_HOST:
            self._server.server_close()
            self._closed = True

            raise LoopbackCallbackError(
                "callback server did not bind to 127.0.0.1"
            )

        self._port = int(
            bound_port
        )

    @property
    def host(
        self,
    ) -> str:
        return SPOTIFY_LOOPBACK_HOST

    @property
    def port(
        self,
    ) -> int:
        return self._port

    @property
    def redirect_uri(
        self,
    ) -> str:
        return build_loopback_redirect_uri(
            self._port
        )

    @property
    def closed(
        self,
    ) -> bool:
        return self._closed

    def close(
        self,
    ) -> None:
        if self._closed:
            return

        self._server.server_close()
        self._closed = True

    def wait_for_callback(
        self,
        *,
        timeout_seconds: float = 120.0,
    ) -> LoopbackCallbackResult:
        if self._closed:
            raise LoopbackCallbackError(
                "callback server is closed"
            )

        if self._consumed:
            raise LoopbackCallbackError(
                "callback server has already been consumed"
            )

        if (
            isinstance(
                timeout_seconds,
                bool,
            )
            or not isinstance(
                timeout_seconds,
                Real,
            )
        ):
            raise TypeError(
                "callback timeout must be a number"
            )

        timeout = float(
            timeout_seconds
        )

        if timeout <= 0:
            raise ValueError(
                "callback timeout must be positive"
            )

        self._consumed = True

        deadline = (
            time.monotonic()
            + timeout
        )

        try:
            while (
                self._server.callback_target
                is None
            ):
                remaining = (
                    deadline
                    - time.monotonic()
                )

                if remaining <= 0:
                    raise LoopbackCallbackTimeout(
                        "Spotify authorization callback timed out."
                    )

                self._server.timeout = min(
                    CALLBACK_POLL_SECONDS,
                    remaining,
                )

                self._server.handle_request()

            target = (
                self._server.callback_target
            )

            if target is None:
                raise LoopbackCallbackError(
                    "callback target disappeared unexpectedly"
                )

            callback_url = (
                f"http://{SPOTIFY_LOOPBACK_HOST}:"
                f"{self._port}{target}"
            )

            return LoopbackCallbackResult(
                callback_url=callback_url,
                request_target=target,
            )
        finally:
            self.close()

    def __enter__(
        self,
    ) -> "SpotifyLoopbackCallbackServer":
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.close()
