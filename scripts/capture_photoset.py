#!/usr/bin/env python3
"""Capture a photogrammetry set with a tethered camera and write its manifest.

A reconstruction is only true to a scale factor, so this tool refuses to record a
set without a declared scale reference: give the physical reference placed in the
scene and its certified length. Without it the resulting mesh is a shape, not a
measurement.

Examples:
  capture_photoset.py --out work/images/door-strap --count 36 --step-deg 10 \\
      --scale-reference "calibrated 100.00 mm scale bar, laid on the turntable"

  capture_photoset.py --out work/images/test --count 4 --dry-run \\
      --scale-reference "none, framing test only"

Hardware paths use gphoto2 for the camera and an optional serial turntable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path


def camera_model() -> str:
    if shutil.which("gphoto2") is None:
        return "unknown (gphoto2 not installed)"
    result = subprocess.run(["gphoto2", "--auto-detect"], capture_output=True, text=True)
    lines = [line.strip() for line in result.stdout.splitlines()[2:] if line.strip()]
    return lines[0] if lines else "no camera detected"


def rotate(port: str | None, command: str, degrees: float) -> None:
    if port is None:
        return
    try:
        import serial  # type: ignore
    except ImportError:  # pragma: no cover - depends on the host
        raise SystemExit("turntable control needs pyserial: pip install pyserial")
    payload = (command.format(deg=degrees) + "\n").encode("ascii")
    with serial.Serial(port, 115200, timeout=10) as link:
        link.write(payload)
        link.readline()


def capture(target: Path, dry_run: bool) -> bool:
    if dry_run:
        target.write_bytes(b"placeholder for a captured frame\n")
        return True
    if shutil.which("gphoto2") is None:
        raise SystemExit("gphoto2 is not installed; install it or use --dry-run")
    result = subprocess.run(
        ["gphoto2", "--capture-image-and-download", "--filename", str(target)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr.strip()[:300], file=sys.stderr)
    return result.returncode == 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True, type=Path, help="directory receiving the images")
    parser.add_argument("--count", type=int, default=36, help="number of frames")
    parser.add_argument("--step-deg", type=float, default=10.0, help="turntable step between frames")
    parser.add_argument(
        "--scale-reference",
        required=True,
        help="physical length reference present in the scene, with its certified value",
    )
    parser.add_argument("--subject", default="", help="what is being captured")
    parser.add_argument("--turntable-port", help="serial port of the turntable, if any")
    parser.add_argument("--turntable-command", default="G91 G0 A{deg}", help="rotation command template")
    parser.add_argument("--dry-run", action="store_true", help="write placeholder frames, no hardware")
    args = parser.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)
    frames = []
    for index in range(args.count):
        target = args.out / f"frame_{index:04d}.jpg"
        print(f"  frame {index + 1}/{args.count} -> {target.name}", flush=True)
        if not capture(target, args.dry_run):
            print(f"capture failed at frame {index}", file=sys.stderr)
            return 1
        frames.append(
            {
                "file": target.name,
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "nominal_angle_deg": round(index * args.step_deg, 3),
                "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            }
        )
        if index < args.count - 1:
            rotate(args.turntable_port, args.turntable_command, args.step_deg)

    manifest = {
        "captured_on": date.today().isoformat(),
        "subject": args.subject,
        "camera": camera_model(),
        "turntable": args.turntable_port or "none, frames positioned by hand",
        "step_deg": args.step_deg,
        "scale_reference": args.scale_reference,
        "dry_run": args.dry_run,
        "frames": frames,
        "note": (
            "Photogrammetry is scale free. Recover scale from the reference above "
            "before any dimension from this set is treated as a measurement."
        ),
    }
    manifest_path = args.out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(frames)} frames and manifest written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
