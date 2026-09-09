"""Persisted Spotify Playlist Dashboard-card assignments.

This module owns only the stable relationship between a Dashboard Playlist
Card instance and a Spotify playlist.

Dashboard geometry and visibility belong to the existing dashboard-layout
system and are deliberately not duplicated here.

No Spotify credentials, authentication secrets, network clients, Qt objects,
or playback behavior belong in this layer.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping


SCHEMA_VERSION = 1
MAX_CARDS = 24
MAX_FILE_BYTES = 256 * 1024

_CARD_ID_PATTERN = re.compile(
    r"^[A-Za-z0-9._-]{1,96}$"
)

_PLAYLIST_ID_PATTERN = re.compile(
    r"^[A-Za-z0-9]{1,128}$"
)

_CARD_PREFIX = "spotify_playlist_card."


class SpotifyPlaylistCardPreferencesError(ValueError):
    """Raised when Playlist Card preferences are invalid."""


def _normalise_text(
    value: object,
    *,
    field: str,
) -> str:
    if not isinstance(value, str):
        raise SpotifyPlaylistCardPreferencesError(
            f"{field} must be a string."
        )

    value = value.strip()

    if not value:
        raise SpotifyPlaylistCardPreferencesError(
            f"{field} must not be empty."
        )

    if "\x00" in value:
        raise SpotifyPlaylistCardPreferencesError(
            f"{field} contains an invalid NUL character."
        )

    return value


def normalise_spotify_playlist_id(
    value: object,
) -> str:
    playlist_id = _normalise_text(
        value,
        field="playlist_id",
    )

    if not _PLAYLIST_ID_PATTERN.fullmatch(
        playlist_id
    ):
        raise SpotifyPlaylistCardPreferencesError(
            "playlist_id is not a valid Spotify playlist ID."
        )

    return playlist_id


def spotify_playlist_uri(
    playlist_id: object,
) -> str:
    playlist_id = normalise_spotify_playlist_id(
        playlist_id
    )

    return (
        "spotify:playlist:"
        + playlist_id
    )


def new_spotify_playlist_card_id() -> str:
    return (
        _CARD_PREFIX
        + uuid.uuid4().hex
    )


def default_spotify_playlist_card_preferences_path(
    *,
    local_app_data: str | os.PathLike[str] | None = None,
) -> Path:
    if local_app_data is None:
        local_app_data = os.environ.get(
            "LOCALAPPDATA"
        )

    if not local_app_data:
        raise SpotifyPlaylistCardPreferencesError(
            "LOCALAPPDATA is unavailable."
        )

    return (
        Path(local_app_data)
        / "03-37am Presence"
        / "spotify_playlist_cards.json"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class SpotifyPlaylistCardConfig:
    """Stable playlist assignment for one Dashboard card instance."""

    card_id: str
    playlist_id: str
    playlist_uri: str

    def __post_init__(self) -> None:
        card_id = _normalise_text(
            self.card_id,
            field="card_id",
        )

        if not _CARD_ID_PATTERN.fullmatch(
            card_id
        ):
            raise SpotifyPlaylistCardPreferencesError(
                "card_id contains unsupported characters."
            )

        playlist_id = (
            normalise_spotify_playlist_id(
                self.playlist_id
            )
        )

        expected_uri = spotify_playlist_uri(
            playlist_id
        )

        playlist_uri = _normalise_text(
            self.playlist_uri,
            field="playlist_uri",
        )

        if playlist_uri != expected_uri:
            raise SpotifyPlaylistCardPreferencesError(
                "playlist_uri must exactly match playlist_id."
            )

        object.__setattr__(
            self,
            "card_id",
            card_id,
        )

        object.__setattr__(
            self,
            "playlist_id",
            playlist_id,
        )

        object.__setattr__(
            self,
            "playlist_uri",
            playlist_uri,
        )

    @classmethod
    def for_playlist(
        cls,
        playlist_id: object,
        *,
        card_id: str | None = None,
    ) -> "SpotifyPlaylistCardConfig":
        playlist_id = (
            normalise_spotify_playlist_id(
                playlist_id
            )
        )

        if card_id is None:
            card_id = (
                new_spotify_playlist_card_id()
            )

        return cls(
            card_id=card_id,
            playlist_id=playlist_id,
            playlist_uri=spotify_playlist_uri(
                playlist_id
            ),
        )

    @classmethod
    def from_payload(
        cls,
        payload: object,
    ) -> "SpotifyPlaylistCardConfig":
        if not isinstance(
            payload,
            Mapping,
        ):
            raise SpotifyPlaylistCardPreferencesError(
                "Playlist Card entry must be an object."
            )

        expected_keys = {
            "card_id",
            "playlist_id",
            "playlist_uri",
        }

        if set(payload) != expected_keys:
            raise SpotifyPlaylistCardPreferencesError(
                "Playlist Card entry has an unexpected shape."
            )

        return cls(
            card_id=payload["card_id"],
            playlist_id=payload["playlist_id"],
            playlist_uri=payload["playlist_uri"],
        )

    def to_payload(self) -> dict[str, str]:
        return {
            "card_id": self.card_id,
            "playlist_id": self.playlist_id,
            "playlist_uri": self.playlist_uri,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class SpotifyPlaylistCardPreferences:
    """All persisted Playlist Card assignments."""

    cards: tuple[
        SpotifyPlaylistCardConfig,
        ...
    ] = ()

    def __post_init__(self) -> None:
        cards = tuple(
            self.cards
        )

        if len(cards) > MAX_CARDS:
            raise SpotifyPlaylistCardPreferencesError(
                "Too many Spotify Playlist Cards."
            )

        seen = set()

        for card in cards:
            if not isinstance(
                card,
                SpotifyPlaylistCardConfig,
            ):
                raise SpotifyPlaylistCardPreferencesError(
                    "cards must contain SpotifyPlaylistCardConfig values."
                )

            if card.card_id in seen:
                raise SpotifyPlaylistCardPreferencesError(
                    "Duplicate Playlist Card ID."
                )

            seen.add(
                card.card_id
            )

        object.__setattr__(
            self,
            "cards",
            cards,
        )

    def get(
        self,
        card_id: object,
    ) -> SpotifyPlaylistCardConfig | None:
        card_id = _normalise_text(
            card_id,
            field="card_id",
        )

        for card in self.cards:
            if card.card_id == card_id:
                return card

        return None

    def with_card(
        self,
        card: SpotifyPlaylistCardConfig,
    ) -> "SpotifyPlaylistCardPreferences":
        if not isinstance(
            card,
            SpotifyPlaylistCardConfig,
        ):
            raise SpotifyPlaylistCardPreferencesError(
                "card must be a SpotifyPlaylistCardConfig."
            )

        cards = list(
            self.cards
        )

        for index, existing in enumerate(
            cards
        ):
            if (
                existing.card_id
                == card.card_id
            ):
                cards[index] = card

                return SpotifyPlaylistCardPreferences(
                    tuple(cards)
                )

        cards.append(
            card
        )

        return SpotifyPlaylistCardPreferences(
            tuple(cards)
        )

    def without_card(
        self,
        card_id: object,
    ) -> "SpotifyPlaylistCardPreferences":
        card_id = _normalise_text(
            card_id,
            field="card_id",
        )

        return SpotifyPlaylistCardPreferences(
            tuple(
                card
                for card in self.cards
                if card.card_id != card_id
            )
        )

    @classmethod
    def from_payload(
        cls,
        payload: object,
    ) -> "SpotifyPlaylistCardPreferences":
        if not isinstance(
            payload,
            Mapping,
        ):
            raise SpotifyPlaylistCardPreferencesError(
                "Playlist Card preferences must be an object."
            )

        if set(payload) != {
            "schema_version",
            "cards",
        }:
            raise SpotifyPlaylistCardPreferencesError(
                "Playlist Card preferences have an unexpected shape."
            )

        if (
            payload["schema_version"]
            != SCHEMA_VERSION
        ):
            raise SpotifyPlaylistCardPreferencesError(
                "Unsupported Playlist Card preferences schema."
            )

        raw_cards = payload["cards"]

        if not isinstance(
            raw_cards,
            list,
        ):
            raise SpotifyPlaylistCardPreferencesError(
                "cards must be a list."
            )

        return cls(
            tuple(
                SpotifyPlaylistCardConfig
                .from_payload(item)
                for item in raw_cards
            )
        )

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "cards": [
                card.to_payload()
                for card in self.cards
            ],
        }


class SpotifyPlaylistCardPreferencesStore:
    """Atomic LocalAppData persistence for Playlist Card assignments."""

    def __init__(
        self,
        path: str | os.PathLike[str] | None = None,
    ) -> None:
        if path is None:
            path = (
                default_spotify_playlist_card_preferences_path()
            )

        self.path = Path(
            path
        )

    def load(
        self,
    ) -> SpotifyPlaylistCardPreferences:
        if not self.path.exists():
            defaults = (
                SpotifyPlaylistCardPreferences()
            )

            self.save(
                defaults
            )

            return defaults

        try:
            size = self.path.stat().st_size

            if size > MAX_FILE_BYTES:
                raise SpotifyPlaylistCardPreferencesError(
                    "Playlist Card preferences file is too large."
                )

            raw = self.path.read_text(
                encoding="utf-8-sig",
            )

            payload = json.loads(
                raw
            )

            return (
                SpotifyPlaylistCardPreferences
                .from_payload(payload)
            )

        except (
            UnicodeError,
            json.JSONDecodeError,
            SpotifyPlaylistCardPreferencesError,
            TypeError,
            ValueError,
        ):
            return self._recover_invalid()

        except OSError as exc:
            raise SpotifyPlaylistCardPreferencesError(
                "Could not read Playlist Card preferences."
            ) from exc

    def save(
        self,
        preferences: SpotifyPlaylistCardPreferences,
    ) -> None:
        if not isinstance(
            preferences,
            SpotifyPlaylistCardPreferences,
        ):
            raise SpotifyPlaylistCardPreferencesError(
                "preferences must be SpotifyPlaylistCardPreferences."
            )

        payload = json.dumps(
            preferences.to_payload(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n"

        encoded = payload.encode(
            "utf-8"
        )

        if len(encoded) > MAX_FILE_BYTES:
            raise SpotifyPlaylistCardPreferencesError(
                "Playlist Card preferences are too large."
            )

        try:
            self.path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            temporary = self.path.with_name(
                "."
                + self.path.name
                + "."
                + uuid.uuid4().hex
                + ".tmp"
            )

            try:
                with temporary.open(
                    "xb"
                ) as handle:
                    handle.write(
                        encoded
                    )

                    handle.flush()

                    os.fsync(
                        handle.fileno()
                    )

                os.replace(
                    temporary,
                    self.path,
                )

            finally:
                try:
                    temporary.unlink(
                        missing_ok=True
                    )
                except OSError:
                    pass

        except OSError as exc:
            raise SpotifyPlaylistCardPreferencesError(
                "Could not save Playlist Card preferences."
            ) from exc

    def upsert(
        self,
        card: SpotifyPlaylistCardConfig,
    ) -> SpotifyPlaylistCardPreferences:
        preferences = (
            self.load()
            .with_card(card)
        )

        self.save(
            preferences
        )

        return preferences

    def remove(
        self,
        card_id: object,
    ) -> SpotifyPlaylistCardPreferences:
        preferences = (
            self.load()
            .without_card(card_id)
        )

        self.save(
            preferences
        )

        return preferences

    def reset(
        self,
    ) -> SpotifyPlaylistCardPreferences:
        preferences = (
            SpotifyPlaylistCardPreferences()
        )

        self.save(
            preferences
        )

        return preferences

    def _recover_invalid(
        self,
    ) -> SpotifyPlaylistCardPreferences:
        self._quarantine_invalid_file()

        preferences = (
            SpotifyPlaylistCardPreferences()
        )

        self.save(
            preferences
        )

        return preferences

    def _quarantine_invalid_file(
        self,
    ) -> Path | None:
        if not self.path.exists():
            return None

        timestamp = (
            datetime.now(
                timezone.utc
            )
            .strftime(
                "%Y%m%dT%H%M%SZ"
            )
        )

        candidate = self.path.with_name(
            self.path.name
            + ".corrupt-"
            + timestamp
        )

        suffix = 1

        while candidate.exists():
            candidate = self.path.with_name(
                self.path.name
                + ".corrupt-"
                + timestamp
                + f"-{suffix}"
            )

            suffix += 1

        try:
            os.replace(
                self.path,
                candidate,
            )
        except OSError as exc:
            raise SpotifyPlaylistCardPreferencesError(
                "Could not quarantine invalid Playlist Card preferences."
            ) from exc

        return candidate
