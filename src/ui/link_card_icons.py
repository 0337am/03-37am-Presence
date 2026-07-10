from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import ipaddress
import os
from pathlib import Path
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import (
    HTTPRedirectHandler,
    ProxyHandler,
    Request,
    build_opener,
)

from PyQt6.QtCore import (
    QByteArray,
    QBuffer,
    QIODevice,
    QObject,
    Qt,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QImageReader

from src.ui.custom_cards import (
    display_domain,
    normalize_web_url,
)


MAX_PAGE_BYTES = 768 * 1024
MAX_ICON_BYTES = 2 * 1024 * 1024
MAX_ICON_PIXELS = 16 * 1024 * 1024
MAX_ICON_EDGE = 128
MAX_ICON_CANDIDATES = 12
FETCH_TIMEOUT_SECONDS = 7
USER_AGENT = (
    "03:37am Presence/2.2 "
    "Link Card Icon Fetcher"
)
_LOCAL_HOST_SUFFIXES = (
    ".localhost",
    ".local",
    ".internal",
    ".home",
    ".lan",
)


def _cache_root(
    root: Path | str | None = None,
) -> Path:
    if root is not None:
        return Path(root)

    local_app_data = str(
        os.getenv("LOCALAPPDATA", "") or ""
    ).strip()

    if local_app_data:
        base = Path(local_app_data)
    else:
        base = Path.home() / ".0337am-presence"

    return (
        base
        / "0337am Presence"
        / "link_card_icons"
    )


def canonical_origin(url: str) -> str:
    normalized = normalize_web_url(url)
    parsed = urlsplit(normalized)
    hostname = parsed.hostname or ""

    try:
        hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError as error:
        raise ValueError(
            "Website address contains an invalid host."
        ) from error

    hostname = hostname.casefold()

    if ":" in hostname:
        hostname = f"[{hostname}]"

    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError(
            "Website address contains an invalid port."
        ) from error

    default_port = 443 if parsed.scheme == "https" else 80
    netloc = hostname

    if port is not None and port != default_port:
        netloc = f"{hostname}:{port}"

    return urlunsplit(
        (parsed.scheme, netloc, "", "", "")
    ).rstrip("/")


def favicon_cache_key(url: str) -> str:
    origin = canonical_origin(url)
    return hashlib.sha256(
        origin.encode("utf-8")
    ).hexdigest()


def favicon_cache_path(
    url: str,
    root: Path | str | None = None,
) -> Path:
    return _cache_root(root) / (
        f"favicon_{favicon_cache_key(url)}.png"
    )


def cached_favicon_path(
    url: str,
    root: Path | str | None = None,
) -> Path | None:
    try:
        path = favicon_cache_path(url, root)
    except (TypeError, ValueError):
        return None

    if not path.is_file():
        return None

    return path


def remove_cached_favicon(
    url: str,
    root: Path | str | None = None,
) -> bool:
    path = favicon_cache_path(url, root)

    try:
        path.unlink()
    except FileNotFoundError:
        return False

    return True


def domain_initial(url: str) -> str:
    try:
        domain = display_domain(url)
    except (TypeError, ValueError):
        return "↗"

    for character in domain:
        if character.isalnum():
            return character.upper()

    return "↗"


def _normalise_icon_bytes(data: bytes) -> bytes:
    if not isinstance(data, bytes) or not data:
        raise ValueError(
            "The website returned an empty icon."
        )

    if len(data) > MAX_ICON_BYTES:
        raise ValueError(
            "The website icon is too large."
        )

    source_buffer = QBuffer()
    source_buffer.setData(QByteArray(data))

    if not source_buffer.open(
        QIODevice.OpenModeFlag.ReadOnly
    ):
        raise ValueError(
            "The website icon could not be read."
        )

    reader = QImageReader(source_buffer)
    reader.setAutoTransform(True)
    announced_size = reader.size()

    if (
        announced_size.isValid()
        and announced_size.width() > 0
        and announced_size.height() > 0
        and (
            announced_size.width()
            * announced_size.height()
            > MAX_ICON_PIXELS
        )
    ):
        source_buffer.close()
        raise ValueError(
            "The website icon dimensions are too large."
        )

    image = reader.read()
    source_buffer.close()

    if image.isNull():
        raise ValueError(
            "The website did not provide a supported image icon."
        )

    if image.width() * image.height() > MAX_ICON_PIXELS:
        raise ValueError(
            "The website icon dimensions are too large."
        )

    if (
        image.width() > MAX_ICON_EDGE
        or image.height() > MAX_ICON_EDGE
    ):
        image = image.scaled(
            MAX_ICON_EDGE,
            MAX_ICON_EDGE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    output = QByteArray()
    output_buffer = QBuffer(output)

    if not output_buffer.open(
        QIODevice.OpenModeFlag.WriteOnly
    ):
        raise ValueError(
            "The website icon could not be prepared."
        )

    saved = image.save(output_buffer, "PNG")
    output_buffer.close()

    if not saved:
        raise ValueError(
            "The website icon could not be converted."
        )

    return bytes(output)


def save_favicon_bytes(
    url: str,
    data: bytes,
    root: Path | str | None = None,
) -> Path:
    normalized_png = _normalise_icon_bytes(data)
    path = favicon_cache_path(url, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(".tmp.png")

    try:
        with temporary_path.open("wb") as handle:
            handle.write(normalized_png)
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(temporary_path, path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    return path


class _IconHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.base_href = ""
        self.candidates: list[tuple[int, str]] = []

    def handle_starttag(self, tag, attrs):
        name = str(tag or "").casefold()
        values = {
            str(key or "").casefold(): str(value or "").strip()
            for key, value in attrs
        }

        if name == "base" and not self.base_href:
            self.base_href = values.get("href", "")
            return

        if name != "link":
            return

        href = values.get("href", "")
        rel_tokens = {
            token.casefold()
            for token in values.get("rel", "").split()
            if token.strip()
        }

        if not href:
            return

        if "apple-touch-icon-precomposed" in rel_tokens:
            score = 500
        elif "apple-touch-icon" in rel_tokens:
            score = 450
        elif "icon" in rel_tokens:
            score = 400
        elif "mask-icon" in rel_tokens:
            score = 300
        else:
            return

        sizes = values.get("sizes", "")

        for token in sizes.casefold().split():
            if "x" not in token:
                continue

            width_text, _, height_text = token.partition("x")

            try:
                width = int(width_text)
                height = int(height_text)
            except ValueError:
                continue

            score += min(max(width, height), 512)

        media_type = values.get("type", "").casefold()

        if "svg" in media_type:
            score -= 25
        elif "png" in media_type:
            score += 20

        self.candidates.append((score, href))


def extract_icon_candidates(
    html_text: str,
    page_url: str,
) -> tuple[str, ...]:
    parser = _IconHTMLParser()

    try:
        parser.feed(str(html_text or ""))
    except Exception:
        pass

    base_url = page_url

    if parser.base_href:
        potential_base = urljoin(
            page_url,
            parser.base_href,
        )

        try:
            base_url = normalize_web_url(potential_base)
        except (TypeError, ValueError):
            base_url = page_url

    ordered = sorted(
        parser.candidates,
        key=lambda item: item[0],
        reverse=True,
    )
    candidates: list[str] = []
    seen: set[str] = set()

    for _, href in ordered:
        try:
            candidate = normalize_web_url(
                urljoin(base_url, href)
            )
        except (TypeError, ValueError):
            continue

        if candidate in seen:
            continue

        seen.add(candidate)
        candidates.append(candidate)

        if len(candidates) >= MAX_ICON_CANDIDATES:
            break

    origin = canonical_origin(page_url)

    for fallback in (
        f"{origin}/apple-touch-icon.png",
        f"{origin}/favicon.ico",
    ):
        if fallback not in seen:
            candidates.append(fallback)
            seen.add(fallback)

    return tuple(candidates[:MAX_ICON_CANDIDATES])


def validate_public_fetch_url(url: str) -> str:
    normalized = normalize_web_url(url)
    parsed = urlsplit(normalized)
    hostname = (parsed.hostname or "").casefold()

    if (
        hostname == "localhost"
        or hostname.endswith(_LOCAL_HOST_SUFFIXES)
    ):
        raise ValueError(
            "Website icons cannot be fetched from local network addresses."
        )

    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError(
            "Website address contains an invalid port."
        ) from error

    expected_port = 443 if parsed.scheme == "https" else 80

    if port not in (None, expected_port):
        raise ValueError(
            "Website icons can only be fetched over standard web ports."
        )

    try:
        literal_ip = ipaddress.ip_address(hostname)
    except ValueError:
        literal_ip = None

    if literal_ip is not None:
        addresses = {literal_ip}
    else:
        try:
            resolved = socket.getaddrinfo(
                hostname,
                expected_port,
                type=socket.SOCK_STREAM,
            )
        except OSError as error:
            raise ValueError(
                "The website address could not be resolved."
            ) from error

        addresses = set()

        for result in resolved:
            address_text = result[4][0]

            try:
                addresses.add(
                    ipaddress.ip_address(address_text)
                )
            except ValueError:
                continue

    if not addresses:
        raise ValueError(
            "The website address could not be resolved."
        )

    if any(not address.is_global for address in addresses):
        raise ValueError(
            "Website icons cannot be fetched from local or private network addresses."
        )

    return normalized


class _SafeRedirectHandler(HTTPRedirectHandler):
    def redirect_request(
        self,
        req,
        fp,
        code,
        msg,
        headers,
        newurl,
    ):
        target = validate_public_fetch_url(
            urljoin(req.full_url, newurl)
        )
        return super().redirect_request(
            req,
            fp,
            code,
            msg,
            headers,
            target,
        )


def _read_limited(response, limit: int) -> bytes:
    content_length = response.headers.get("Content-Length")

    if content_length:
        try:
            announced_length = int(content_length)
        except ValueError:
            announced_length = None

        if (
            announced_length is not None
            and announced_length > limit
        ):
            raise ValueError(
                "The website response is too large."
            )

    data = response.read(limit + 1)

    if len(data) > limit:
        raise ValueError(
            "The website response is too large."
        )

    return data


def _build_opener():
    return build_opener(
        ProxyHandler({}),
        _SafeRedirectHandler(),
    )


def _open_public_url(
    opener,
    url: str,
    accept: str,
):
    validated = validate_public_fetch_url(url)
    request = Request(
        validated,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": accept,
            "Cache-Control": "no-cache",
        },
    )
    response = opener.open(
        request,
        timeout=FETCH_TIMEOUT_SECONDS,
    )
    validate_public_fetch_url(response.geturl())
    return response


def _decode_page(data: bytes, response) -> str:
    charset = response.headers.get_content_charset() or "utf-8"

    try:
        return data.decode(charset, errors="replace")
    except LookupError:
        return data.decode("utf-8", errors="replace")


def fetch_website_icon_bytes(url: str) -> bytes:
    page_url = canonical_origin(url) + "/"
    opener = _build_opener()
    candidates: list[str] = []

    try:
        with _open_public_url(
            opener,
            page_url,
            "text/html,application/xhtml+xml,image/*;q=0.8,*/*;q=0.2",
        ) as response:
            final_page_url = normalize_web_url(response.geturl())
            content_type = (
                response.headers.get_content_type() or ""
            ).casefold()

            if content_type.startswith("image/"):
                return _normalise_icon_bytes(
                    _read_limited(response, MAX_ICON_BYTES)
                )

            page_data = _read_limited(
                response,
                MAX_PAGE_BYTES,
            )
            page_text = _decode_page(page_data, response)
            candidates.extend(
                extract_icon_candidates(
                    page_text,
                    final_page_url,
                )
            )
    except (
        HTTPError,
        URLError,
        OSError,
        TypeError,
        ValueError,
    ):
        candidates.extend(
            extract_icon_candidates("", page_url)
        )

    seen: set[str] = set()
    last_error: Exception | None = None

    for candidate in candidates:
        if candidate in seen:
            continue

        seen.add(candidate)

        try:
            with _open_public_url(
                opener,
                candidate,
                "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.2",
            ) as response:
                data = _read_limited(
                    response,
                    MAX_ICON_BYTES,
                )
                return _normalise_icon_bytes(data)
        except (
            HTTPError,
            URLError,
            OSError,
            TypeError,
            ValueError,
        ) as error:
            last_error = error
            continue

    if last_error is not None:
        raise ValueError(
            "No usable website icon was found."
        ) from last_error

    raise ValueError(
        "No website icon was found."
    )


class WebsiteIconFetchWorker(QObject):
    icon_ready = pyqtSignal(bytes)
    failed = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    @pyqtSlot()
    def run(self):
        try:
            icon_bytes = fetch_website_icon_bytes(
                self.url
            )
        except Exception as error:
            self.failed.emit(str(error))
        else:
            self.icon_ready.emit(icon_bytes)
        finally:
            self.finished.emit()
