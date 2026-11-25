#!/usr/bin/env python3
"""Picture of the two support layouts of the print body, side by side.

    support-build-processor.png   top row: the rule layout (support_design.py); bottom row: the blocks
                                  PySLM prepared (support_build_processor.py); the same two views

Drawn on 1 mm blocks of the 0.25 mm grid, as support-layout.png is: a block is drawn when half of it is
envelope, or half of it is part. Blue: a support standing on the plate; orange: on the part; purple: a
processor column that ends in the air. Red: down-facing surface within 45 degrees of straight down that
the layout leaves without a support, drawn wherever a 1 mm block holds any of it.

Usage: render_support_build_processor.py OCC_DIR RULE_DIR PRIVATE_DIR MEDIA_DIR
Run under GALLIUM_DRIVER=llvmpipe LIBGL_ALWAYS_SOFTWARE=1 PYOPENGL_PLATFORM=egl xvfb-run -a.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import support_build_processor as sbp  # noqa: E402
import support_design as sd  # noqa: E402
from render_build_sim import camera, look  # noqa: E402
from render_media import caption, sha256  # noqa: E402
from render_support_design import BLOCK, blocks, surface  # noqa: E402

CAPTION = "Two support layouts of a study print body: by rule, and by an open library. Not a build file."
COLOURS = {"plate": "#3b6fb6", "part": "#e08a2e", "air": "#8e44ad", "bare": "#c0392b"}


def any_block(mask: np.ndarray) -> np.ndarray:
    pad = [(0, (-s) % BLOCK) for s in mask.shape]
    a = np.pad(mask, pad)
    n = [s // BLOCK for s in a.shape]
    return a.reshape(n[0], BLOCK, n[1], BLOCK, n[2], BLOCK).any(axis=(1, 3, 5))


def layers_of(envelope, solid, ref, plate_level, part):
    runs = sbp.column_runs(envelope, solid, plate_level)
    label = sbp.landing_labels(envelope, runs)
    sup = sbp.supported_mask(envelope, ref["i"], ref["j"], ref["k"])
    bare = np.zeros(solid.shape, dtype=bool)
    bare[ref["i"][~sup], ref["j"][~sup], ref["k"][~sup] - 1] = True       # the air voxel just under the surface
    out = {"plate": blocks(label == 1) & ~part, "part": blocks(label == 2) & ~part, "air": blocks(label == 3) & ~part,
           "bare": any_block(bare)}
    return out, float((~sup).sum() * sbp.PITCH ** 2)


def main(occ_dir, rule_dir, private, media) -> None:
    import pyvista as pv

    occ_dir, rule_dir, private, media = Path(occ_dir), Path(rule_dir), Path(private), Path(media)
    grid, solid = sbp.load_grid(occ_dir)
    plate_level = int(np.flatnonzero(solid.any(axis=(0, 1)))[0])
    t = sd.transitions(solid, sbp.PITCH, sbp.OVERHANG_DEG)
    ref = {key: t[key][t["over"]] for key in ("i", "j", "k")}
    del t
    part = blocks(solid)
    rows = {}
    rule = np.load(rule_dir / "support-envelope.npy")
    rows["rule"] = layers_of(rule, solid, ref, plate_level, part)
    del rule
    proc = np.load(private / "pyslm-envelope.npy")
    rows["processor"] = layers_of(proc, solid, ref, plate_level, part)
    del proc, solid

    pitch = sbp.PITCH * BLOCK
    lowest = int(np.flatnonzero(part.any(axis=(0, 1)))[0])
    extent = np.array(part.shape, dtype=float) * pitch
    box = np.array([[0.0, 0.0, lowest * pitch - 24.0], extent])
    titles = {"rule": "by rule (support_design.py)", "processor": "by PySLM 0.6.1, its defaults, 45 degrees"}
    pv.global_theme.background = "white"
    plotter = pv.Plotter(off_screen=True, shape=(2, 2), window_size=(1700, 1700), border=False)
    for row, name in enumerate(("rule", "processor")):
        layers, bare_area = rows[name]
        for column, azimuth in enumerate((-58.0, 122.0)):
            plotter.subplot(row, column)
            plate = pv.Box(bounds=(-8.0, extent[0] + 8.0, -8.0, extent[1] + 8.0, lowest * pitch - 24.0, lowest * pitch))
            plotter.add_mesh(plate, color="#b8bcc2")
            plotter.add_mesh(surface(part, pitch), color="#d9dbde", opacity=0.55)
            for key, mask in layers.items():
                if mask.any():
                    plotter.add_mesh(surface(mask, pitch), color=COLOURS[key])
            look(plotter, camera(box, 850 / 850, azimuth=azimuth))
            text = (f"{titles[name]}\nblue: on the plate  orange: on the part" if column == 0 else
                    f"red: overhang left bare, {bare_area:,.0f} mm2\npurple: column ending in the air")
            plotter.add_text(text, position="upper_left", font_size=14, color="black")
    image = caption(plotter.screenshot(return_img=True), CAPTION)
    plotter.close()
    out = media / "support-build-processor.png"
    image.save(out, optimize=True)
    record = json.loads((media / "provenance.json").read_text())
    record["colours"]["support build processor"] = (
        "top row the rule layout, bottom row PySLM's blocks; grey: print body and plate; blue: support standing on the plate; "
        "orange: on the part; purple: a processor column ending in the air; red: overhang within 45 degrees left without support")
    record["images"]["support-build-processor.png"] = {"bytes": out.stat().st_size, "sha256": sha256(out)}
    (media / "provenance.json").write_text(json.dumps(record, indent=2) + "\n")
    drawn = {name: {key: float(mask.sum()) * pitch ** 3 for key, mask in layers.items()} for name, (layers, _) in rows.items()}
    print(json.dumps({"blocks_mm": pitch, "drawn_mm3": drawn, "bytes": out.stat().st_size, "sha256": sha256(out)}))


if __name__ == "__main__":
    main(*sys.argv[1:])
