"""Refine the diagnostic air grid without recomputing thickness or changing geometry."""
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
from screen_935_print_geometry import cavity_screen, digest

for name in ["coarse", "fine"]:
    start = time.monotonic()
    path = ROOT / f"935-head-reconstructed-study-{name}-mm.npz"
    parent = ROOT / f"{name}-pitch2/report.json"
    expected = json.loads(parent.read_text())["input_sha256"]
    assert digest(path) == expected
    data = np.load(path, allow_pickle=False)
    report, points = cavity_screen(data["vertices"], data["triangles"], 1.0)
    report.update(input_sha256=expected, parent_report_sha256=digest(parent),
                  script_sha256=digest(ROOT / "scripts/screen_935_print_geometry.py"),
                  elapsed_seconds=time.monotonic() - start, print_ready=False,
                  interpretation="Resolution comparison, not a convergence or depowdering certificate")
    assert digest(path) == expected
    (ROOT / f"{name}-cavities-pitch1.json").write_text(json.dumps(report, indent=2) + "\n")
    np.savez_compressed(ROOT / f"{name}-cavities-pitch1.npz", nominal_enclosed_air_centres=points)
    print(name, json.dumps(report), flush=True)
