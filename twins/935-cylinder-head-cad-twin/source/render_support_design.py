#!/usr/bin/env python3
"""Picture of the support layout of the print body.

    support-layout.png   the print body in grey on its plate with the support
                         envelope, from two sides: blue where a support stands
                         on the plate, orange where it stands on the part, red
                         where no straight lateral access exists

Drawn on 1 mm blocks of the 0.25 mm grid (a block is drawn when half of it is
envelope, or half of it is part). The envelope is the air column that holds a
block support, not the thin walls themselves.

Usage: render_support_design.py OCC_DIR SUPPORT_DIR MEDIA_DIR
Run as render_build_sim.py: under xvfb-run, software OpenGL, and on WSL inside
`bwrap --dev-bind / / --dev /dev --proc /proc`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_build_sim import camera, look  # noqa: E402
from render_media import caption, sha256  # noqa: E402

CAPTION = "Support layout of a study print body, by declared rules. Not a build file."
BLOCK = 4
COLOURS = {"plate": "#3b6fb6", "part": "#e08a2e", "hidden": "#c0392b"}


def blocks(mask: np.ndarray) -> np.ndarray:
    pad = [(0, (-s) % BLOCK) for s in mask.shape]
    a = np.pad(mask, pad)
    n = [s // BLOCK for s in a.shape]
    return a.reshape(n[0], BLOCK, n[1], BLOCK, n[2], BLOCK).mean(axis=(1, 3, 5), dtype=np.float32) >= 0.5


def surface(mask: np.ndarray, pitch: float):
    import pyvista as pv

    grid = pv.ImageData(dimensions=tuple(s + 1 for s in mask.shape), spacing=(pitch,) * 3)
    grid.cell_data["on"] = mask.ravel(order="F").astype(np.uint8)
    return grid.threshold(0.5, scalars="on").extract_surface()


def main(occ_dir, support_dir, media) -> None:
    import pyvista as pv

    occ_dir, support_dir, media = Path(occ_dir), Path(support_dir), Path(media)
    grid = json.loads((occ_dir / "occupancy-grid.json").read_text())
    pitch = float(grid["pitch_mm"]) * BLOCK
    inside = np.load(occ_dir / grid["array"], mmap_mode="r") > 0.5
    part = blocks(np.ascontiguousarray(inside.transpose(0, 2, 1)[:, :, ::-1]))
    del inside
    kind = np.load(support_dir / "support-kind.npy")
    lowest = int(np.flatnonzero(part.any(axis=(0, 1)))[0])
    layers = {"plate": blocks((kind & 3) == 1) & ~part, "part": blocks((kind & 3) == 2) & ~part,
              "hidden": blocks(kind >= 4) & ~part}
    for name in ("plate", "part"):
        layers[name] &= ~layers["hidden"]
    extent = np.array(part.shape, dtype=float) * pitch
    box = np.array([[0.0, 0.0, lowest * pitch - 24.0], extent])
    pv.global_theme.background = "white"
    plotter = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(1700, 900), border=False)
    for column, azimuth in enumerate((-58.0, 122.0)):
        plotter.subplot(0, column)
        plate = pv.Box(bounds=(-8.0, extent[0] + 8.0, -8.0, extent[1] + 8.0, lowest * pitch - 24.0, lowest * pitch))
        plotter.add_mesh(plate, color="#b8bcc2")
        plotter.add_mesh(surface(part, pitch), color="#d9dbde", opacity=0.55)
        for name, mask in layers.items():
            if mask.any():
                plotter.add_mesh(surface(mask, pitch), color=COLOURS[name])
        look(plotter, camera(box, 850 / 900, azimuth=azimuth))
        plotter.add_text(("blue: support standing on the plate\norange: support standing on the part" if column == 0
                          else "red: no straight lateral access\ngrey: print body, seen through"),
                         position="upper_left", font_size=16, color="black")
    image = caption(plotter.screenshot(return_img=True), CAPTION)
    plotter.close()
    image.save(media / "support-layout.png", optimize=True)

    laid = json.loads((support_dir / "support-envelope.json").read_text())
    record = json.loads((media / "provenance.json").read_text())
    record["inputs"]["build_sim_support_rules_sha256"] = laid["rules_sha256"]
    record["inputs"]["build_sim_occupancy_sha256"] = laid["occupancy_sha256"]
    record["colours"]["support layout"] = ("grey: print body and plate; blue: support envelope standing on the plate; orange: standing "
                                           "on the part; red: no straight lateral access")
    record["images"]["support-layout.png"] = {"bytes": (media / "support-layout.png").stat().st_size,
                                              "sha256": sha256(media / "support-layout.png")}
    (media / "provenance.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"blocks_mm": pitch, "drawn_mm3": {name: float(mask.sum()) * pitch ** 3 for name, mask in layers.items()},
                      "bytes": record["images"]["support-layout.png"]["bytes"]}))


if __name__ == "__main__":
    main(*sys.argv[1:])
