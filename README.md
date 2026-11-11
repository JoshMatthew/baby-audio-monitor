# Baby Monitor

Listen to the baby's room from anywhere, using a Mac left in the room.

- **Transmitter** (`transmitter/`): a Python script that runs in the background on the baby Mac. It starts at login, restarts itself if it stops, keeps the Mac from sleeping, and only turns the microphone on while someone is listening.
- **Server** (`server/`): relays the sound and hosts the listening page. Deploys to Fly.io (or any host that runs a Dockerfile).
- **Receiver**: the web page at your server's address. Open it on your laptop or phone. It reconnects by itself after your laptop wakes up, as long as the tab stays open.

## 1. Deploy the server on Fly.io

It costs about $2 a month, and Fly asks for a card when you sign up.

1. Make two secrets on any Mac, one for the transmitter and one for listening:
   ```sh
   openssl rand -hex 24
   openssl rand -hex 24
   ```
2. Install the Fly CLI and sign up:
   ```sh
   brew install flyctl
   fly auth signup
   ```
3. From this repo's folder, create the app. Pick a name when it asks; it finds the `Dockerfile` on its own:
   ```sh
   fly launch --no-deploy
   ```
4. Save the two secrets on the server:
   ```sh
   fly secrets set TRANSMITTER_TOKEN=<first secret> LISTEN_PASSWORD=<second secret>
   ```
5. Deploy on a single machine. It must be one, because the baby Mac and your laptop have to reach the same server:
   ```sh
   fly deploy --ha=false
   ```
6. Your listening page is `https://<app name>.fly.dev`.

To ship server changes later, run `fly deploy --ha=false` again.

## 2. Install the transmitter on the baby Mac

1. Get this repo onto the baby Mac (`git clone`, or download the ZIP from GitHub and unzip it).
2. In Terminal, from the repo folder:
   ```sh
   ./transmitter/install.sh
   ```
3. Paste the server address and the transmitter token when it asks. It installs [uv](https://docs.astral.sh/uv/) if needed, which downloads Python and the script's libraries on the first run.
4. Allow the microphone: on the baby Mac, open the listening page and click **Start listening**. The transmitter opens the mic for the first time, and macOS should ask for microphone access. Click **Allow**.
5. Keep the baby Mac plugged in with the lid open. Closing the lid still puts it to sleep.

Check that it's running:

```sh
tail -f ~/Library/Logs/baby-monitor.log
```

You should see `Connected to ...`, then `Microphone on` while someone listens. If the log says the microphone is sending pure silence, macOS is blocking it: open **System Settings > Privacy & Security > Microphone** and turn on the entry for `uv` or `python`.

## 3. Listen

Open your server address, enter the listening password, and click **Start listening**. The bar shows how loud the room is, even with the volume down. While listening it uses about 58 MB of data per hour.

## Update or remove the transmitter

Run `./transmitter/install.sh` again after pulling changes. To remove it:

```sh
./transmitter/uninstall.sh
```

## Run the server locally

```sh
cd server
TRANSMITTER_TOKEN=dev-token LISTEN_PASSWORD=dev-password uv run --with-requirements requirements.txt app.py
```

Then open http://localhost:8080 and point a transmitter at it:

```sh
BABY_MONITOR_SERVER=http://localhost:8080 BABY_MONITOR_TOKEN=dev-token uv run --script transmitter/transmitter.py
```
# baby-audio-monitor
