#!/usr/bin/env python3
"""Read actual CalculiX eigenvalues; do not infer a qualified rotating speed."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re


def summarize(case):
    preparation = json.loads((case / "preparation.json").read_text())
    if hashlib.sha256((case / "modal.inp").read_bytes()).hexdigest() != preparation["modal_deck_sha256"]:
        raise ValueError("Input deck hash mismatch")
    log = (case / "log.ccx").read_text()
    if "Job finished" not in log or "*ERROR" in log:
        raise ValueError("CalculiX did not complete normally")
    text = (case / "modal.dat").read_text().split("P A R T I C I P A T I O N")[0]
    modes = []
    for line in text.splitlines():
        fields = line.split()
        if len(fields) != 5 or not fields[0].isdigit():
            continue
        number = int(fields[0])
        eigenvalue, angular, frequency, imaginary = map(float, fields[1:])
        if not all(math.isfinite(v) for v in (eigenvalue, angular, frequency, imaginary)) or min(eigenvalue, angular, frequency) <= 0 or imaginary != 0:
            raise ValueError("Invalid eigenvalue")
        if not math.isclose(angular, frequency * 2 * math.pi, rel_tol=1e-6):
            raise ValueError("Frequency unit conversion mismatch")
        modes.append({"mode": number, "frequency_hz": frequency, "angular_frequency_rad_s": angular})
    if [m["mode"] for m in modes] != list(range(1, preparation["requested_modes"] + 1)):
        raise ValueError("Incomplete mode output")
    version = re.search(r"Version ([0-9.]+)", log)
    return {"status": "completed_unprestressed_fixed_bore_modal_screen", "solver": "CalculiX",
            "solver_version": version[1] if version else "unknown", "modes": modes,
            "worker_image_id": "sha256:1dc508c2bfab4d9911707fbfd9cacdf43faf84956a1502805194e3e70e18ae68",
            "runtime": "Linux amd64 CPU; network disabled; 4 CPUs, 6 GiB container limit",
            "source_deck_sha256": preparation["source_deck_sha256"],
            "assumptions": preparation,
            "mesh_independence_demonstrated": False, "rotating_modes_validated": False,
            "safe_rpm_range": None, "fatigue_validated": False, "scan_used": False,
            "file_sha256": {name: hashlib.sha256((case / name).read_bytes()).hexdigest()
                            for name in ("modal.inp", "preparation.json", "modal.dat", "log.ccx")}}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("case", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    with args.output.open("x") as stream:
        json.dump(summarize(args.case), stream, indent=2, allow_nan=False)
        stream.write("\n")
    print("Modal screening summarized; no safe speed or fatigue claim")
