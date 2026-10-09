"""Independent QA and figures for the PicoGK monocoque study.

Reads output/monocoque-f0.stl only. Checks that every element fused into one
body and that no closed cavity is sealed (a sealed void would trap resin or
powder and hide from inspection), then renders evidence/picogk-*.png.

    python qa.py
"""
import json
import pathlib

import numpy as np
import pyvista as pv
import trimesh

HERE = pathlib.Path(__file__).resolve().parent
STL = HERE / "output" / "monocoque-f0.stl"
EVIDENCE = HERE.parent / "evidence"


def edge_counts(m):
    # One int64 key per undirected edge: far lighter than a 2-D unique on ~75 M edges.
    e = m.edges_sorted.astype(np.int64)
    _, n = np.unique(e[:, 0] * np.int64(len(m.vertices)) + e[:, 1], return_counts=True)
    return {"open": int((n == 1).sum()), "non_manifold": int((n > 2).sum()), "total": int(len(n))}


def check(mesh):
    degenerate = int((mesh.area_faces <= 1e-12).sum())
    if degenerate:
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.remove_unreferenced_vertices()
        mesh.merge_vertices()
    shells = mesh.split(only_watertight=False)
    signed = np.array([float(s.volume) for s in shells])
    tiny = 8.0 ** 3                                       # below (2 voxels)^3 at 4 mm: meshing slivers
    main = shells[int(np.argmax(signed))]
    # Where the sub-voxel fragments sit: 200 mm cells in x and z, densest first.
    frag = [s for s, v in zip(shells, signed) if abs(v) <= tiny]
    centres = np.array([s.bounds.mean(axis=0) for s in frag]) if frag else np.zeros((0, 3))
    cells = {}
    for x, _, z in centres:
        key = (int(x // 200) * 200, int(z // 200) * 200)
        cells[key] = cells.get(key, 0) + 1
    return {
        "main_body_watertight": bool(main.is_watertight),
        "main_body_edges": edge_counts(main),
        "fragment_volume_cm3": round(float(np.abs(signed[np.abs(signed) <= tiny]).sum()) / 1000, 2),
        "fragment_hotspots_x_z_mm": [{"x": k[0], "z": k[1], "count": c}
                                     for k, c in sorted(cells.items(), key=lambda kv: -kv[1])[:8]],
        "bodies": int((signed > tiny).sum()),
        "sealed_voids": int((signed < -tiny).sum()),
        "sub_voxel_shells": int((np.abs(signed) <= tiny).sum()),
        "largest_body_share": round(float(signed.max() / signed[signed > 0].sum()), 4),
        # where the extra bodies and sealed voids are, for diagnosis
        "extra_bodies": [{"volume_cm3": round(float(v) / 1000, 1), "centre_mm": [round(float(c), 0) for c in s.bounds.mean(axis=0)]}
                         for s, v in sorted(zip(shells, signed), key=lambda t: -t[1])[1:] if v > tiny][:20],
        "voids": [{"volume_cm3": round(float(-v) / 1000, 1), "centre_mm": [round(float(c), 0) for c in s.bounds.mean(axis=0)]}
                  for s, v in zip(shells, signed) if v < -tiny][:20],
        "volume_l": round(float(signed.sum()) / 1e6, 2),
        "triangles": int(len(mesh.faces)),
        "degenerate_faces_removed": degenerate,
        "bbox_mm": [round(float(v), 1) for v in (mesh.bounds[1] - mesh.bounds[0])],
    }


def render(mesh, door_x):
    EVIDENCE.mkdir(exist_ok=True)
    poly = pv.wrap(mesh)
    pl = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(2000, 900))
    pl.set_background("white")
    pl.subplot(0, 0)
    pl.add_mesh(poly, color="#3a3f47", smooth_shading=True, specular=0.4)
    pl.add_text("PicoGK closed-ring monocoque concept - plate 50-05a outline", font_size=11, color="black")
    c = np.array(poly.center)
    pl.camera_position = [tuple(c + np.array([4200.0, 3600.0, 2600.0])), tuple(c), (0, 0, 1)]   # front-left, above
    pl.subplot(0, 1)
    cut = poly.clip(normal="x", origin=(door_x, 0, 0), invert=True)
    pl.add_mesh(cut, color="#c9a46b")
    pl.add_text("section at mid-door, looking forward: sills, tunnel, sandwich floor", font_size=11, color="black")
    c = np.array(cut.center)
    pl.camera_position = [tuple(c + np.array([-6500.0, -1800.0, 1400.0])), tuple(c), (0, 0, 1)]
    pl.screenshot(str(EVIDENCE / "picogk-monocoque.png"))
    pl.close()

    pl = pv.Plotter(off_screen=True, window_size=(2000, 800))
    pl.set_background("white")
    half = poly.clip(normal="y", origin=(0, 0, 0), invert=True)
    pl.add_mesh(half, color="#c9a46b")
    pl.add_text("half model, cut on the centre line: rings, tunnel, bulkheads", font_size=11, color="black")
    pl.view_xz()
    pl.camera.azimuth = 180
    pl.screenshot(str(EVIDENCE / "picogk-monocoque-half.png"))
    pl.close()


def main():
    mesh = trimesh.load_mesh(STL, process=True)
    geo = json.loads((HERE / "input" / "geometry.json").read_text(encoding="utf-8"))
    door = geo["door_aperture"]
    result = check(mesh)
    edges = result["main_body_edges"]
    # Pass: one body, no sealed void, a closed main surface (no open edge) whose
    # non-manifold edges are marching-cubes touch points (< 1 per million edges).
    # Detached sub-voxel crumbs are reported (count, volume, location), not hidden.
    result["qa_rule"] = "bodies == 1, sealed_voids == 0, main body open edges == 0, non-manifold edges < 1e-6 of edges"
    result["qa_pass"] = (result["bodies"] == 1 and result["sealed_voids"] == 0 and edges["open"] == 0
                         and edges["non_manifold"] < 1e-6 * edges["total"])
    render(mesh, -(door["front_d"] + door["rear_d"]) / 2.0)
    (HERE / "output" / "monocoque-f0.qa.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=2))
    return 0 if result["qa_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
