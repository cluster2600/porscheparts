"""Public images of the 935 fan twin, rendered from private CAD.

Writes media/preview.png (three-quarter view) and media/views.png (front,
side, top) from a private STL, and media/preview.json with the SHA-256 of
that STL and of each image. The CAD itself is not published.

Run in the cadsim image (pyvista/VTK):
  docker run --rm --user $(id -u):$(id -g) -e HOME=/tmp -v $PWD:/repo -w /repo \
    3dprinting993-cadsim:dev python3 twins/935-horizontal-fan-cad-twin/source/render_views.py \
    work/flat-fan/private/cad/rotor-nominal.stl
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

TWIN = Path(__file__).resolve().parents[1]
COLOR = "#b5bac0"


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(stl: str) -> int:
    import pyvista as pv
    pv.OFF_SCREEN = True
    mesh = pv.read(stl)
    media = TWIN / "media"
    media.mkdir(exist_ok=True)

    def scene(p, view):
        p.set_background("white")
        p.add_mesh(mesh, color=COLOR, smooth_shading=True, specular=0.3, specular_power=15, ambient=0.25, diffuse=0.8)
        if view == "iso":
            p.view_vector((0.9, -1.7, 1.0), viewup=(0, 0, 1))
        else:
            {"front": p.view_xz, "side": p.view_yz, "top": p.view_xy}[view]()
            p.enable_parallel_projection()
        p.reset_camera()
        p.camera.zoom(1.15 if view == "iso" else 1.05)

    p = pv.Plotter(off_screen=True, window_size=(1400, 900), lighting="three lights")
    scene(p, "iso")
    p.enable_anti_aliasing("ssaa")
    p.screenshot(str(media / "preview.png"))
    p.close()
    b = mesh.bounds
    dims = [round(b[1] - b[0], 1), round(b[3] - b[2], 1), round(b[5] - b[4], 1)]
    p = pv.Plotter(off_screen=True, shape=(1, 3), window_size=(1800, 620), border=False, lighting="three lights")
    labels = {"front": f"front (X-Z)  {dims[0]} x {dims[2]} mm", "side": f"side (Y-Z)  {dims[1]} x {dims[2]} mm",
              "top": f"top (X-Y)  {dims[0]} x {dims[1]} mm"}
    for i, view in enumerate(("front", "side", "top")):
        p.subplot(0, i)
        scene(p, view)
        p.add_text(labels[view], position="lower_edge", font_size=10, color="#2b2f33")
    p.screenshot(str(media / "views.png"))
    p.close()
    info = {
        "subject": "935 horizontal fan rotor, top-down CAD twin, nominal 40 degree blade pitch",
        "kind": "geometry_render",
        "note": "Geometry views of a CAD reconstruction fitted to a private scan (scale owner-declared, hypotheses in hypotheses.json). Not a photograph, not evidence of fit, function or manufacturing release. Rendered from private CAD whose SHA-256 is recorded; the CAD itself is not published.",
        "sources": [{"path": "private:" + Path(stl).name, "sha256": sha256(Path(stl))}],
        "bounding_box_mm": dims,
        "images": ["preview.png", "views.png"],
        "generator": "twins/935-horizontal-fan-cad-twin/source/render_views.py",
        "license": "Repository LICENSE; publication of scan-derived renders to be confirmed by the owner.",
        "image_sha256": {n: sha256(media / n) for n in ("preview.png", "views.png")},
    }
    (media / "preview.json").write_text(json.dumps(info, indent=2) + "\n")
    print(json.dumps({"dims": dims}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:]))
