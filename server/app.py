"""Web server: hosts the listening page and relays audio from the baby Mac."""

import asyncio
import hmac
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from aiohttp import WSMsgType, web

from relay import Relay

STATIC_DIR = Path(__file__).parent / "static"
HEARTBEAT_SECONDS = 20
AUTH_TIMEOUT_SECONDS = 10
WRONG_PASSWORD_DELAY_SECONDS = 1
WRONG_PASSWORD_CODE = 4001

log = logging.getLogger("server")


@dataclass(frozen=True)
class Secrets:
    transmitter_token: str
    listen_password: str


RELAY = web.AppKey("relay", Relay)
SECRETS = web.AppKey("secrets", Secrets)


def secrets_match(given: str, expected: str) -> bool:
    return hmac.compare_digest(given.encode(), expected.encode())


async def index(request: web.Request) -> web.FileResponse:
    return web.FileResponse(STATIC_DIR / "index.html")


async def transmit(request: web.Request) -> web.WebSocketResponse:
    relay = request.app[RELAY]
    token = request.headers.get("Authorization", "").removeprefix("Bearer ")

    if not secrets_match(token, request.app[SECRETS].transmitter_token):
        raise web.HTTPUnauthorized()

    socket = web.WebSocketResponse(heartbeat=HEARTBEAT_SECONDS)
    await socket.prepare(request)
    await relay.attach_transmitter(socket)
    log.info("Transmitter connected")

    try:
        async for message in socket:
            if message.type == WSMsgType.BINARY:
                await relay.broadcast_audio(message.data)
    finally:
        await relay.detach_transmitter(socket)
        log.info("Transmitter disconnected")

    return socket


async def is_authorized_listener(socket: web.WebSocketResponse, password: str) -> bool:
    try:
        message = await socket.receive_json(timeout=AUTH_TIMEOUT_SECONDS)
    except (TimeoutError, TypeError, ValueError):
        return False

    given = message.get("password") if isinstance(message, dict) else None

    return isinstance(given, str) and secrets_match(given, password)


async def listen(request: web.Request) -> web.WebSocketResponse:
    relay = request.app[RELAY]
    socket = web.WebSocketResponse(heartbeat=HEARTBEAT_SECONDS)
    await socket.prepare(request)

    if not await is_authorized_listener(socket, request.app[SECRETS].listen_password):
        await asyncio.sleep(WRONG_PASSWORD_DELAY_SECONDS)
        await socket.close(code=WRONG_PASSWORD_CODE, message=b"Wrong password")
        return socket

    await relay.add_listener(socket)
    log.info("Listener joined (%d listening)", len(relay.listeners))

    try:
        async for _ in socket:
            pass
    finally:
        await relay.remove_listener(socket)
        log.info("Listener left (%d listening)", len(relay.listeners))

    return socket


async def run_status_updates(app: web.Application):
    task = asyncio.create_task(app[RELAY].keep_listeners_updated())

    yield

    task.cancel()


def create_app() -> web.Application:
    app = web.Application()
    app[RELAY] = Relay()
    app[SECRETS] = Secrets(
        transmitter_token=os.environ["TRANSMITTER_TOKEN"],
        listen_password=os.environ["LISTEN_PASSWORD"],
    )
    app.cleanup_ctx.append(run_status_updates)

    app.router.add_get("/", index)
    app.router.add_get("/transmit", transmit)
    app.router.add_get("/listen", listen)
    app.router.add_static("/static", STATIC_DIR)

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    web.run_app(create_app(), port=int(os.environ.get("PORT", "8080")))
