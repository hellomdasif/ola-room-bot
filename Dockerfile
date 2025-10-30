FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY 2.py join_sequence.py ./
COPY tools/ws_log_to_frames.py tools/ws_log_to_frames.py

# The container expects OLA_AUTH_TOKEN (and optionally OLA_UID, OLA_WS_URL, OLA_ROOM_SIGNATURE).
CMD ["python", "2.py"]
