"""Moves microphone audio from the one transmitter to every connected listener."""

import asyncio
import contextlib
from collections.abc import Awaitable, Callable, Iterable

from aiohttp import web

STATUS_INTERVAL_SECONDS = 5

Socket = web.WebSocketResponse


async def send_to_all(sockets: Iterable[Socket], send: Callable[[Socket], Awaitable[None]]) -> None:
    await asyncio.gather(*(send(socket) for socket in list(sockets)), return_exceptions=True)


class Relay:
    def __init__(self) -> None:
        self.transmitter: Socket | None = None
        self.listeners: set[Socket] = set()

    async def attach_transmitter(self, socket: Socket) -> None:
        previous, self.transmitter = self.transmitter, socket

        await self.update_transmitter()
        await self.update_listeners()

        if previous is not None:
            await previous.close()

    async def detach_transmitter(self, socket: Socket) -> None:
        if self.transmitter is not socket:
            return

        self.transmitter = None
        await self.update_listeners()

    async def add_listener(self, socket: Socket) -> None:
        self.listeners.add(socket)

        await self.update_listeners()
        await self.update_transmitter()

    async def remove_listener(self, socket: Socket) -> None:
        self.listeners.discard(socket)

        await self.update_transmitter()

    async def update_transmitter(self) -> None:
        """Tell the transmitter how many people listen, so it only uses the mic when needed."""
        if self.transmitter is None:
            return

        with contextlib.suppress(ConnectionError):
            await self.transmitter.send_json({"listeners": len(self.listeners)})

    async def update_listeners(self) -> None:
        status = {"transmitter": self.transmitter is not None}

        await send_to_all(self.listeners, lambda socket: socket.send_json(status))

    async def broadcast_audio(self, chunk: bytes) -> None:
        await send_to_all(self.listeners, lambda socket: socket.send_bytes(chunk))

    async def keep_listeners_updated(self) -> None:
        """Regular status messages let a listener notice a dead connection, e.g. after sleep."""
        while True:
            await asyncio.sleep(STATUS_INTERVAL_SECONDS)
            await self.update_listeners()
