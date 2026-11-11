# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "sounddevice", "websockets>=14"]
# ///
"""Baby Mac transmitter: sends the microphone to the server while someone is listening."""

import asyncio
import json
import logging
import os
import subprocess

import numpy as np
import sounddevice as sd
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed

SAMPLE_RATE = 16_000
CHUNK_FRAMES = SAMPLE_RATE // 10
SILENCE_WARNING_CHUNKS = 50
MU = 255

log = logging.getLogger("transmitter")


def transmit_url(server_url: str) -> str:
    websocket_url = server_url.rstrip("/").replace("https://", "wss://", 1).replace("http://", "ws://", 1)

    return f"{websocket_url}/transmit"


def mulaw_encode(samples: np.ndarray) -> bytes:
    """Squeezes each sample into one byte, keeping quiet sounds clear. player.js undoes this."""
    clipped = np.clip(samples, -1.0, 1.0)
    compressed = np.sign(clipped) * np.log1p(MU * np.abs(clipped)) / np.log1p(MU)

    return np.round((compressed + 1) * 127.5).astype(np.uint8).tobytes()


def keep_mac_awake() -> None:
    """Stops the Mac from sleeping for as long as this process runs."""
    subprocess.Popen(["/usr/bin/caffeinate", "-i", "-w", str(os.getpid())])


class Microphone:
    """Streams the mic to the server, and only opens it while switched on."""

    def __init__(self, socket: ClientConnection) -> None:
        self.socket = socket
        self.loop = asyncio.get_running_loop()
        self.stream: sd.InputStream | None = None
        self.silent_chunks = 0

    def switch(self, on: bool) -> None:
        if on and self.stream is None:
            self.stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=CHUNK_FRAMES,
                callback=self.on_audio,
            )
            self.stream.start()
            log.info("Microphone on")
        elif not on and self.stream is not None:
            self.stream.close()
            self.stream = None
            log.info("Microphone off")

    def on_audio(self, indata: np.ndarray, frames: int, time, status) -> None:
        samples = indata[:, 0]

        self.warn_if_blocked(samples)

        asyncio.run_coroutine_threadsafe(self.socket.send(mulaw_encode(samples)), self.loop)

    def warn_if_blocked(self, samples: np.ndarray) -> None:
        """A real room is never perfectly silent; exact zeros mean macOS is blocking the mic."""
        self.silent_chunks = 0 if samples.any() else self.silent_chunks + 1

        if self.silent_chunks == SILENCE_WARNING_CHUNKS:
            log.warning(
                "Microphone is sending pure silence. Allow access in "
                "System Settings > Privacy & Security > Microphone."
            )


async def stream_while_connected(socket: ClientConnection) -> None:
    microphone = Microphone(socket)

    try:
        async for message in socket:
            microphone.switch(on=json.loads(message)["listeners"] > 0)
    finally:
        microphone.switch(on=False)


async def main() -> None:
    server_url = os.environ["BABY_MONITOR_SERVER"]
    headers = {"Authorization": f"Bearer {os.environ['BABY_MONITOR_TOKEN']}"}

    keep_mac_awake()

    async for socket in connect(transmit_url(server_url), additional_headers=headers):
        log.info("Connected to %s", server_url)

        try:
            await stream_while_connected(socket)
        except ConnectionClosed:
            pass

        log.info("Disconnected, reconnecting")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(main())
