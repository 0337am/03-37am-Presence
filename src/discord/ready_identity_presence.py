from __future__ import annotations

import json
import struct

from pypresence import Presence
from pypresence.exceptions import (
    DiscordError,
    DiscordNotFound,
    InvalidID,
    InvalidPipe,
)
from pypresence.utils import get_ipc_path


PROFILE_IDENTITY_FIELDS = (
    "user_id",
    "username",
    "display_name",
    "avatar_hash",
)


class ReadyIdentityPresence(Presence):
    """
    pypresence Presence client that retains the local Discord
    READY user's non-secret profile identity.

    Rich Presence transport remains owned by pypresence. This
    class only preserves identity fields that pypresence 4.6.1
    otherwise parses and discards during the IPC handshake.
    """

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )

        self.ready_identity = {}

    @staticmethod
    def identity_from_ready_payload(
        payload,
    ) -> dict:
        if not isinstance(
            payload,
            dict,
        ):
            return {}

        data = payload.get(
            "data"
        )

        if not isinstance(
            data,
            dict,
        ):
            return {}

        user = data.get(
            "user"
        )

        if not isinstance(
            user,
            dict,
        ):
            return {}

        user_id = str(
            user.get("id")
            or ""
        ).strip()

        username = str(
            user.get("username")
            or ""
        ).strip()

        global_name = str(
            user.get("global_name")
            or ""
        ).strip()

        avatar_hash = str(
            user.get("avatar")
            or ""
        ).strip()

        display_name = (
            global_name
            or username
        )

        identity = {}

        values = {
            "user_id": user_id,
            "username": username,
            "display_name": display_name,
            "avatar_hash": avatar_hash,
        }

        for key in PROFILE_IDENTITY_FIELDS:
            value = values.get(
                key,
                "",
            )

            if value:
                identity[key] = value

        return identity

    async def handshake(self):
        ipc_path = get_ipc_path(
            self.pipe
        )

        if not ipc_path:
            raise DiscordNotFound

        await self.create_reader_writer(
            ipc_path
        )

        self.send_data(
            0,
            {
                "v": 1,
                "client_id": self.client_id,
            },
        )

        preamble = await self.sock_reader.read(
            8
        )

        if len(preamble) < 8:
            raise InvalidPipe

        _, length = struct.unpack(
            "<ii",
            preamble,
        )

        payload = json.loads(
            await self.sock_reader.read(
                length
            )
        )

        if "code" in payload:
            if (
                payload.get("message")
                == "Invalid Client ID"
            ):
                raise InvalidID

            raise DiscordError(
                payload["code"],
                payload["message"],
            )

        self.ready_identity = (
            self.identity_from_ready_payload(
                payload
            )
        )

        if self._events_on:
            self.sock_reader.feed_data = (
                self.on_event
            )
