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
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python 2.py
```
