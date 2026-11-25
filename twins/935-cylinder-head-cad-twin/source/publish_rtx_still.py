#!/usr/bin/env python3
"""Publish one RTX still of the #707 capture on the twin page: captioned, reduced, under 1 MiB.

The still must be the one the capture receipt hashed. It is reduced to 1200 x 750, given the twin's
caption band, and entered in media/provenance.json with the hashes of its source and receipt. Only
pixels are published; the stage and the scene stay private.

Usage: publish_rtx_still.py CAPTURE_DIR MEDIA_DIR
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_media import caption  # noqa: E402

NAME = "rtx-camside.png"
SOURCE = "camside.png"
TEXT = ("RTX render (NVIDIA OVRTX 0.3.0) of the study twin's display colours: grey observed, orange inferred, "
        "blue fitted studs. Not measured, not a part.")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main(capture_dir, media_dir) -> None:
    from PIL import Image

    capture, media = Path(capture_dir), Path(media_dir)
    receipt = (capture / "capture.json").read_bytes()
    source = (capture / SOURCE).read_bytes()
    if sha256(source) != json.loads(receipt)["media_sha256"][SOURCE]:
        raise SystemExit("the still differs from its capture receipt")
    image = Image.open(capture / SOURCE).convert("RGB").resize((1200, 750), Image.LANCZOS)
    caption(image, TEXT).save(media / NAME, optimize=True)
    data = (media / NAME).read_bytes()
    if len(data) >= 1 << 20:
        raise SystemExit("the published still is not under 1 MiB")
    record = json.loads((media / "provenance.json").read_text())
    record["images"][NAME] = {"bytes": len(data), "sha256": sha256(data), "source_sha256": sha256(source),
                              "capture_receipt_sha256": sha256(receipt)}
    (media / "provenance.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record["images"][NAME]))


if __name__ == "__main__":
    main(*sys.argv[1:3])
