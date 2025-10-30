# Ola Party Room Bot

Small utility that replays the Ola Party client’s HTTP + WebSocket handshake so an account can appear online automatically.  
This repository contains the replay script (`2.py`), the captured join sequence (`join_sequence.py`), and a helper to rebuild that sequence from fresh `logcat` dumps.

## Prerequisites

- Python 3.9+
- `OLA_AUTH_TOKEN` (URL‑encoded token captured from the Android client)
- Optional overrides: `OLA_UID`, `OLA_WS_URL`, `OLA_ROOM_SIGNATURE`

Install dependencies and run:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
OLA_AUTH_TOKEN='YOUR_TOKEN' python 2.py
```

The script stays connected until interrupted (`Ctrl+C`). It logs every frame it replays and sends the recorded heartbeat every 15 seconds.

## Regenerating the WebSocket Sequence

1. Capture a clean log on the device while joining a room:
   ```bash
   adb -s 127.0.0.1:26624 logcat -c
   adb -s 127.0.0.1:26624 logcat -s AutoOnline > auto_online.log
   ```
2. Stop logging after the join finishes.
3. Convert the capture:
   ```bash
   python tools/ws_log_to_frames.py --input auto_online.log --output join_sequence.pylist
   ```
4. Replace the list in `join_sequence.py` with the new frames.

## Docker / Coolify Deployment

The repository ships with a simple Dockerfile. Build or deploy it via Coolify, ensuring the required environment variable is provided:

```bash
docker build -t ola-room-bot .
docker run -e OLA_AUTH_TOKEN='YOUR_TOKEN' ola-room-bot
```

You can also pass `OLA_UID`, `OLA_WS_URL`, or `OLA_ROOM_SIGNATURE` if those differ from the defaults baked into the script.

## Repository Layout

- `2.py` – main bot script
- `join_sequence.py` – decoded list of WebSocket frames
- `tools/ws_log_to_frames.py` – helper to extract frames from logcat dumps
- `requirements.txt`, `Dockerfile` – deployment helpers
