#!/usr/bin/env python3
"""Publish the rendered meme into the make.fun output directory.

Standard library only: no Pillow, no network, no clock. The renderer in
art/render.py is the only thing that needs Pillow; this copier just moves the
finished PNG into place, refusing to publish anything that breaks the gate.

Two runs write identical bytes by construction: the source is a committed file
and nothing here transforms it. The assertions below make that explicit rather
than assumed -- if the committed art ever drifts out of the gate, this fails
loudly instead of shipping an entry that scores nothing.
"""

from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "art" / "entry.png"

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_EDGE = 1024
MIN_EDGE = 1024
MAX_BYTES = 1048576


def ihdr_size(data: bytes) -> tuple[int, int]:
    """Return (width, height) straight from the IHDR chunk.

    Reads the spec offsets directly, so the check needs no image library: 8
    bytes of signature, a 4-byte length, the "IHDR" tag, then two big-endian
    uint32 dimensions.
    """
    assert data[:8] == PNG_SIGNATURE, "not a PNG: bad signature"
    assert data[12:16] == b"IHDR", "not a PNG: first chunk is not IHDR"
    return struct.unpack(">II", data[16:24])


def main() -> int:
    output_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    if not SOURCE.exists():
        print(
            "error: source image missing: %s\n"
            "       render it first with: python3 art/render.py" % SOURCE,
            file=sys.stderr,
        )
        return 1

    data = SOURCE.read_bytes()

    problems: list[str] = []
    try:
        width, height = ihdr_size(data)
    except AssertionError as exc:
        # A malformed file cannot be described by dimensions at all, so report
        # the parse failure and stop rather than inventing a width.
        print("error: " + str(exc), file=sys.stderr)
        return 1

    if (width, height) != (MAX_EDGE, MIN_EDGE):
        problems.append(
            f"image is {width}x{height}; the gate wants exactly {MAX_EDGE}x{MIN_EDGE}"
        )
    if len(data) > MAX_BYTES:
        problems.append(f"image is {len(data)} bytes; the cap is {MAX_BYTES}")

    if problems:
        for p in problems:
            print("error: " + p, file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    dest = output_dir / "entry.png"
    dest.write_bytes(data)
    print(f"wrote {dest} ({width}x{height}, {len(data)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
