#!/usr/bin/env python3
"""
Full script to enter a room, join the websocket, and stay online by sending
the correct "Join Room" and "Heartbeat" packets.

Dependencies:
    pip install requests websocket-client
"""
from __future__ import annotations

import binascii
import os
import ssl
import sys
import time
import threading
import base64  # <-- We need this for the new base64 payloads
from typing import Optional

import requests
import websocket

from join_sequence import JOIN_SEQUENCE_B64


# ---------------------------------------------------------------------------
# 1. Credentials (from your script and logs)
# ---------------------------------------------------------------------------
UID = os.environ.get("OLA_UID")
if not UID:
    raise SystemExit("Environment variable OLA_UID is required (numeric account id).")
AUTH_TOKEN = os.environ.get("OLA_AUTH_TOKEN")
if not AUTH_TOKEN:
    raise SystemExit("Environment variable OLA_AUTH_TOKEN is required (URL-encoded token).")

WS_URL = os.environ.get("OLA_WS_URL")
if not WS_URL:
    raise SystemExit("Environment variable OLA_WS_URL is required (full websocket URL).")


# ---------------------------------------------------------------------------
# 2. NEW "Join Room" and "Heartbeat" Packets (from your new log)
# ---------------------------------------------------------------------------


# Steady-state heartbeat captured after join (00:08:57.718+)
HEARTBEAT_B64 = "ChsKC2lreGRfcm9vbV9kEMK48LSjMyIFZW5fY2EQCxoXc180MzA1NjAyNzA1XzQ0NjM4NDM2OTJa"

try:
    JOIN_SEQUENCE = [base64.b64decode(frame) for frame in JOIN_SEQUENCE_B64]
    HEARTBEAT_PAYLOAD = base64.b64decode(HEARTBEAT_B64)
except binascii.Error as exc:
    print(f"Error decoding base64 payloads: {exc}")
    sys.exit(1)


# ---------------------------------------------------------------------------
# 3. HTTP "enter room" call (This is correct)
# ---------------------------------------------------------------------------
ROOM_URL = "https://mm-turnover.ihago.net/api/1802/1012"
SIGNATURE = os.environ.get("OLA_ROOM_SIGNATURE", "e9a3e9f0b6770d8b98c3d3cd730bde10")
DATA_PAYLOAD = (
    '{"cmd":1012,"appId":1802,"version":0,"jsonMsg":{"cmd":1012,"seq":"5","uid":'
    f"{UID}" ',"sid":0,"ssid":0,"appId":1802,"usedChannel":1855}}'
)

HTTP_HEADERS = {
    "x-appid": "1802", "country": "IN", "x-authtoken": AUTH_TOKEN, "osversion": "12",
    "stype": "1", "machine": "OnePlus PJE110", "hdid": "3390e1a3d2931a3e10acd093c452151d",
    "x-authtype": "3", "language": "en", "version": "3.1.8", "x-cpuarch": "aarch64",
    "x-devicetype": "OnePlus PJE110", "x-sdk-ver": "32", "x-os-ver": "12",
    "x-auth-token": AUTH_TOKEN, "x-ostype": "android", "x-client-net": "1",
    "x-app-lastver": "", "x-deviceid": "3390e1a3d2931a3e10acd093c452151d",
    "x-lang": "en_IN", "x-app-ver": "30108", "content-type": "application/x-www-form-urlencoded",
    "accept-encoding": "gzip", "user-agent": "okhttp/3.12.1",
}


# ---------------------------------------------------------------------------
# 4. Websocket headers (This is correct)
# ---------------------------------------------------------------------------
WS_HEADERS = [
    "X-CpuArch: aarch64", "X-App-Channel: official", "X-DeviceType: OnePlus PJE110",
    "X-Sdk-Ver: 32", "X-Client-Net: 1", "X-Lang: en_ca", "X-App-Ver: 30108",
    "X-Os-Ver: 12", f"X-Auth-Token: {AUTH_TOKEN}", "X-OsType: android",
    "X-DeviceId: 3390e1a3d2931a3e10acd093c452151d", "User-Agent: okhttp/3.12.1",
]


# ---------------------------------------------------------------------------
# 5. The Bot Logic
# ---------------------------------------------------------------------------
global running
running = True

def enter_room() -> None:
    """Step 1: Replay the HTTP join-room call."""
    print("Step 1: Entering room via HTTP …", flush=True)
    payload = f"sign={SIGNATURE}&data={DATA_PAYLOAD}"
    response = requests.post(ROOM_URL, headers=HTTP_HEADERS, data=payload, timeout=10)
    if response.status_code != 200 or '"result":1' not in response.text:
        raise RuntimeError(f"Room join failed ({response.status_code}): {response.text}")
    print("Step 1: Room join acknowledged.")


def connect_ws() -> websocket.WebSocket:
    """Step 2: Open the websocket."""
    print("Step 2: Opening websocket …", flush=True)
    ws = websocket.create_connection(
        WS_URL,
        header=WS_HEADERS,
        timeout=10,
        sslopt={"cert_reqs": ssl.CERT_NONE},
    )
    print("Step 2: Websocket connected.")
    return ws


def join_ws_room(ws: websocket.WebSocket):
    """Send the captured boot sequence to mimic the native client."""
    print("Step 3: Replaying initial websocket sequence …", flush=True)
    for idx, frame in enumerate(JOIN_SEQUENCE, start=1):
        print(f"  → frame {idx}/{len(JOIN_SEQUENCE)} ", end="", flush=True)
        ws.send_binary(frame)
        try:
            ws.settimeout(1.0)
            _ = ws.recv()
            print("(reply)")
        except websocket.WebSocketTimeoutException:
            print("(no reply)")
        finally:
            ws.settimeout(None)
        time.sleep(0.15)
    print("Step 3: Sequence complete.")
    

def heartbeat_loop(ws: websocket.WebSocket):
    """Step 4: Send the real heartbeat in a loop."""
    global running
    try:
        while running:
            time.sleep(15)  # Send heartbeat every 15 seconds
            print("(Sending heartbeat to stay online...)", flush=True)
            ws.send_binary(HEARTBEAT_PAYLOAD)
            
            # Optional: Listen for server replies
            # try:
            #     ws.settimeout(1.0)
            #     reply = ws.recv()
            #     print(f"(Server replied: {reply[:50]}...)")
            # except websocket.WebSocketTimeoutException:
            #     pass # No reply is fine
            # finally:
            #     ws.settimeout(None)

    except Exception as e:
        if running:
            print(f"\nHeartbeat loop failed: {e}")
        running = False


def main() -> None:
    global running
    ws = None
    try:
        # Step 1: Tell server we want to join
        enter_room()
        
        # Step 2: Open the WebSocket connection
        ws = connect_ws()

        # Step 3: Send the one-time "Join Room" packet
        join_ws_room(ws)
        
        # Step 4: Start sending the correct heartbeat
        print("Step 4: Starting keep-alive loop (Press ENTER to stop).")
        heartbeat_thread = threading.Thread(target=heartbeat_loop, args=(ws,))
        heartbeat_thread.daemon = True
        heartbeat_thread.start()

        print("\nSUCCESS: You should now be ONLINE and IN THE CHATROOM.")
        print("Process will keep running; press Ctrl+C to stop.")

        while running:
            time.sleep(60)

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        running = False
        if ws:
            ws.close()
        print("Websocket closed; offline now.")


if __name__ == "__main__":
    main()
