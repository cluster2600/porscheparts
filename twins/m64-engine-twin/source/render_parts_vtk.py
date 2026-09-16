#!/usr/bin/env python3
"""Images de presentation des pieces acceptees, par VTK (pyvista) hors ecran.

Voie de secours de la suite (visualisation ParaView/VTK) quand OVRTX ne peut
pas creer d'instance Vulkan sur le noeud loue. Une image ne prouve ni cote, ni
ajustement, ni tenue : elle illustre une geometrie d'agent non revue.

Usage : render_parts_vtk.py SUMMARY.json RESULTS_ROOT OUT_DIR
RESULTS_ROOT contient <composant>/part.step (copies locales des STEP acceptes).
"""
import hashlib
import json
from pathlib import Path
import sys


def tessellate(step: Path):
    import cadquery as cq
    import numpy as np
    import pyvista as pv

    shape = cq.importers.importStep(str(step)).val()
    vertices, triangles = shape.tessellate(0.2, 0.3)
    points = np.array([(v.x, v.y, v.z) for v in vertices])
    faces = np.hstack([[3, *t] for t in triangles])
    return pv.PolyData(points, faces).compute_normals(split_vertices=True, feature_angle=35)


def render(step: Path, png: Path, title: str) -> dict:
    import pyvista as pv

    pv.OFF_SCREEN = True
    mesh = tessellate(step)
    plotter = pv.Plotter(off_screen=True, window_size=(1600, 1200))
    plotter.set_background("#f4f2ee")
    plotter.add_mesh(mesh, color="#9aa3ad", smooth_shading=True, specular=0.4, specular_power=20)
    plotter.add_mesh(mesh.extract_feature_edges(40), color="#2b2f36", line_width=1.2)
    plotter.enable_eye_dome_lighting()
    plotter.view_isometric()
    plotter.camera.zoom(1.15)
    plotter.add_text(title, position="upper_left", font_size=12, color="#2b2f36")
    plotter.add_text("jumeau de conception - geometrie d'agent non revue", position="lower_left",
                     font_size=9, color="#6b7078")
    plotter.screenshot(str(png))
    plotter.close()
    bounds = mesh.bounds
    return {"png": png.name, "png_sha256": hashlib.sha256(png.read_bytes()).hexdigest(),
            "step_sha256": hashlib.sha256(step.read_bytes()).hexdigest(),
            "triangles": int(mesh.n_cells),
            "bbox_mm": [round(bounds[1] - bounds[0], 1), round(bounds[3] - bounds[2], 1), round(bounds[5] - bounds[4], 1)]}


def main(summary_path, results_root, out_dir):
    summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    root, out = Path(results_root), Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    index = {"renderer": "pyvista/VTK hors ecran (voie ParaView/VTK de docs/AI_DIGITAL_TWIN_STACK.md)",
             "ovrtx_status": "bloque sur le noeud loue : vkCreateInstance ERROR_INCOMPATIBLE_DRIVER",
             "status": "illustration_unreviewed", "manufacturing_authorized": False, "parts": {}}
    for cid, result in sorted(summary.items()):
        step = root / cid / "part.step"
        if result.get("status") != "accepted_unreviewed" or not step.exists():
            continue
        import cadquery as cq
        faces = len(cq.importers.importStep(str(step)).val().Faces())
        title = f"{cid}  -  {faces} faces BRep"
        index["parts"][cid] = render(step, out / f"{cid}.png", title)
        print(cid, index["parts"][cid]["bbox_mm"], flush=True)
    (out / "renders.json").write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(*sys.argv[1:4])
