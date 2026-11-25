"""Private review renders of the valve, seat and guide bodies and of the declared port domains.

Visual inspection only: a render shows misplaced or missing bodies, holes and
stray pieces; it establishes no dimension. The CAD body is cut by the plane
through the two valve axes (x = mean x of the two axis points) and seen from
the cut side, with the bodies and the port domains of params/port-domain.json
inside it. Run with software rendering (GALLIUM_DRIVER=llvmpipe).

Usage: render_valves_ports.py BODY_STL BODIES_DIR DOMAIN_DIR PARAMS_DIR OUT_PNG
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

COLOURS = {"valve": "#c0392b", "insert": "#2e86c1", "guide": "#d4ac0d"}
VIEWS = (("section through the valve axes, from +x", (1, 0, 0), (0, 0, 1)),
         ("same, tilted", (1, -0.35, -0.35), (0, 0, 1)),
         ("from the chamber (deck side)", (0, 0, -1), (0, 1, 0)),
         ("valves at the published largest lifts", (1, 0, 0), (0, 0, 1)))


def poly(path):
    import pyvista as pv
    import trimesh

    m = trimesh.load(path, process=False, force="mesh")
    return pv.PolyData(np.asarray(m.vertices), np.column_stack((np.full(len(m.faces), 3), m.faces)).ravel())


def main(body_stl, bodies_dir, domain_dir, params, out_png):
    import pyvista as pv

    pv.OFF_SCREEN = True
    bodies_dir, domain_dir, params = Path(bodies_dir), Path(domain_dir), Path(params)
    fits = json.loads((params / "feature-fits.json").read_text())
    x_cut = float(np.mean([fits["group_datums"][v]["axis_point"][0] for v in ("valve_y_minus", "valve_y_plus")]))
    body = poly(body_stl).clip(normal=(1, 0, 0), origin=(x_cut, 0, 0), invert=True)
    parts = {}
    for f in sorted(bodies_dir.glob("*.step")):
        kind = f.stem.split("_")[0]
        stl = bodies_dir / f"{f.stem}.render.stl"
        if not stl.exists():
            from build123d import export_stl, import_step

            export_stl(import_step(str(f)), str(stl), tolerance=0.02, angular_tolerance=0.2)
        parts[f.stem] = (poly(stl), COLOURS[kind])
    lifted = poly(bodies_dir / "valves-at-largest-lift.stl")
    domains = [poly(p) for p in sorted(domain_dir.glob("port-domain-port_*.stl"))]
    p = pv.Plotter(off_screen=True, shape=(2, 2), window_size=(1800, 1400))
    for i, (label, direction, up) in enumerate(VIEWS):
        p.subplot(i // 2, i % 2)
        p.add_mesh(body, color="#b8b8bc", opacity=0.35 if i != 2 else 0.25)
        for name, (mesh, colour) in parts.items():
            if i == 3 and name.startswith("valve_"):
                continue
            p.add_mesh(mesh, color=colour)
        if i == 3:
            p.add_mesh(lifted, color=COLOURS["valve"])
        for d in domains:
            p.add_mesh(d, color="#48c9b0", opacity=0.25)
        p.add_text(label, font_size=11)
        p.view_vector(direction, viewup=up)
        p.enable_parallel_projection()
        p.reset_camera()
    p.screenshot(out_png)
    p.close()
    print("wrote", out_png)


if __name__ == "__main__":
    main(*sys.argv[1:6])
