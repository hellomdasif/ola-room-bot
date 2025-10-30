#!/usr/bin/env python3
"""
Utility to extract websocket payloads from `AutoOnline` logcat dumps.

Usage:
    python tools/ws_log_to_frames.py --input ws_capture.log \
        --output frames.txt --format python

The script scans the log for lines that look like:
    10-31 00:08:57.261 9435 9490 D AutoOnline: ws send base64=Ch0...

Consecutive lines that share the same timestamp/pid/tid are assumed to be
fragments of the same frame (logcat splits long strings). They are concatenated
and emitted as a single base64 payload in the requested format.
"""
from __future__ import annotations

import argparse
import base64
import re
import sys
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple


LINE_RE = re.compile(
    r"""
    ^(?P<date>\d{2}-\d{2})\s+
    (?P<time>\d{2}:\d{2}:\d{2}\.\d{3})\s+
    (?P<pid>\d+)\s+
    (?P<tid>\d+)\s+
    [VDIWEF]\s+
    AutoOnline:\s+
    ws\ send\ base64=(?P<data>\S+)
    """,
    re.VERBOSE,
)


def parse_frames(lines: Iterable[str]) -> List[str]:
    """Group logcat base64 fragments into full frames."""
    frames: List[str] = []
    current_key: Tuple[str, str, str] | None = None
    current_data: List[str] = []

    for line in lines:
        match = LINE_RE.match(line)
        if not match:
            # Flush any pending chunk when a non-matching line appears.
            if current_data:
                frames.append("".join(current_data))
                current_data = []
                current_key = None
            continue

        key = (match.group("time"), match.group("pid"), match.group("tid"))
        chunk = match.group("data").strip()

        starts_new_frame = chunk.startswith("C")

        if current_key is None or key != current_key or starts_new_frame:
            if current_data:
                frames.append("".join(current_data))
            current_key = key
            current_data = [chunk]
        else:
            current_data.append(chunk)

    if current_data:
        frames.append("".join(current_data))

    return frames


def validate_frames(frames: Sequence[str]) -> None:
    """Ensure every payload is valid base64."""
    for idx, item in enumerate(frames, start=1):
        try:
            base64.b64decode(item, validate=True)
        except (base64.binascii.Error, ValueError) as exc:
            raise SystemExit(f"Frame {idx} is not valid base64: {exc}") from exc


def format_frames(frames: Sequence[str], style: str) -> str:
    if style == "python":
        body = ",\n    ".join(f'"{item}"' for item in frames)
        return f"[\n    {body}\n]"
    if style == "plain":
        return "\n".join(frames)
    if style == "json":
        import json

        return json.dumps(list(frames), indent=2)
    raise SystemExit(f"Unknown output format: {style}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract websocket frames from AutoOnline logs.")
    parser.add_argument("--input", required=True, type=Path, help="Path to logcat dump.")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional file to write frames to. Defaults to stdout.",
    )
    parser.add_argument(
        "--format",
        choices=("python", "plain", "json"),
        default="python",
        help="Output representation; default is a Python list.",
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input file does not exist: {args.input}")

    frames = parse_frames(args.input.read_text().splitlines())
    validate_frames(frames)
    output = format_frames(frames, args.format)

    if args.output:
        args.output.write_text(output)
    else:
        sys.stdout.write(output)


if __name__ == "__main__":
    main()
