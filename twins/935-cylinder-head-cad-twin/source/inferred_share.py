"""Where the inferred area of the v2 body lies, by hypothesis region (issue #697).

The scorecard counts a triangle of the CAD body as inferred when no acquired
scan facet (studs excluded) lies within SUPPORT_MM of its centroid. This
script repeats that split with a second distance tool (Open3D's raycasting
scene instead of Warp), checks the total against the committed scorecard, and
sorts the inferred area by where it lies:

  H04  port interiors: a point 1.5 mm outside the triangle, along its outward
       normal, falls in one of the two port voids of fit_ports.py;
  cav  another enclosed void of fit_ports.py (pockets, passages, chamber);
  H02  within PASSAGE_REACH_MM of a fitted stud-passage axis;
  rest everything else: fin roots and fin-gap floors (H01) and the outer
       closure, which this sort does not separate further.

Usage: inferred_share.py PRIVATE_DIR PARAMS_DIR
Reads PRIVATE_DIR/{scan-raw64.npz, v2-loft-s025.npz, occupancy-grid.json, occupancy-wn.npy};
writes PARAMS_DIR/inferred-share.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fit_ports import CAVITY_MIN_VOLUME_MM3, FLANGE_REACH_MM, PORT_MIN_VOLUME_MM3, cavities  # noqa: E402
from score_twin import SUPPORT_MM, hardware_mask, tri_props  # noqa: E402
from twin_common import write_json  # noqa: E402

PROBE_MM = 1.5
PASSAGE_REACH_MM = 7.5
STUDS = ("stud_x_minus_y_plus", "stud_x_plus_y_plus", "stud_x_minus_y_minus", "stud_x_plus_y_minus")


def distances(points, v, f):
    import open3d as o3d

    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(o3d.core.Tensor(v.astype(np.float32)), o3d.core.Tensor(f.astype(np.uint32)))
    return scene.compute_distance(o3d.core.Tensor(points.astype(np.float32))).numpy().astype(np.float64)


def main(private, params):
    from scipy import ndimage as ndi

    private, params = Path(private), Path(params)
    frame = json.loads((params / "frame.json").read_text())
    fits = json.loads((params / "feature-fits.json").read_text())
    port_fit = json.loads((params / "port-fit.json").read_text())
    card = json.loads((params / "scorecard-v2-loft-s025.json").read_text())

    raw = np.load(private / "scan-raw64.npz")
    rot = np.array(frame["rotation_scan_to_twin_rows"])
    sv = (raw["v"] - np.array(frame["origin_scan"])) @ rot.T
    sf = raw["f"]
    s_cen, _ = tri_props(sv, sf)
    keep = sf[~hardware_mask(s_cen, frame)]

    body = np.load(private / "v2-loft-s025.npz")
    tv, tf = body["v"], body["f"]
    t_cen, t_area = tri_props(tv, tf)
    d = distances(t_cen, sv, keep)
    inferred = d > SUPPORT_MM
    total = float(t_area.sum())

    # Regions: the port and cavity labels of fit_ports.py at its coarse pitch.
    grid = json.loads((private / "occupancy-grid.json").read_text())
    wn = np.load(private / grid["array"], mmap_mode="r")
    lab, count, org, h = cavities(wn, grid)
    vol = ndi.sum(lab > 0, lab, range(1, count + 1)) * h ** 3
    flanges = port_fit["flange_faces_y_mm"]
    port_labels, cavity_labels = [], []
    for i in range(count):
        if vol[i] < CAVITY_MIN_VOLUME_MM3:
            continue
        idx = np.argwhere(lab == i + 1)
        lo, hi = org + idx.min(axis=0) * h, org + idx.max(axis=0) * h
        reaches = hi[1] >= flanges["y_plus"] - FLANGE_REACH_MM or lo[1] <= flanges["y_minus"] + FLANGE_REACH_MM
        (port_labels if reaches and vol[i] >= PORT_MIN_VOLUME_MM3 else cavity_labels).append(i + 1)
    tri = tv[tf]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
    probe = t_cen + PROBE_MM * n
    ijk = np.floor((probe - org) / h).astype(int)
    inside = np.all((ijk >= 0) & (ijk < np.array(lab.shape)), axis=1)
    label = np.zeros(len(probe), dtype=lab.dtype)
    label[inside] = lab[tuple(ijk[inside].T)]
    in_port = np.isin(label, port_labels)
    in_cavity = np.isin(label, cavity_labels)
    near_passage = np.zeros(len(t_cen), dtype=bool)
    for name in STUDS:
        g = fits["group_datums"].get(name)
        if g is None:
            continue
        a = np.asarray(g["axis_direction"], float)
        a /= np.linalg.norm(a)
        rel = t_cen - np.asarray(g["axis_point"], float)
        near_passage |= np.linalg.norm(rel - np.outer(rel @ a, a), axis=1) < PASSAGE_REACH_MM
    region = np.full(len(t_cen), "rest", dtype=object)
    region[near_passage] = "H02"
    region[in_cavity] = "cav"
    region[in_port] = "H04"
    inferred_area = float(t_area[inferred].sum())
    by_region = {}
    for key, what in (("H04", "port interiors (the two port voids)"),
                      ("cav", "other enclosed voids: pockets, passages and the chamber"),
                      ("H02", "stud passages, within 7.5 mm of a fitted passage axis"),
                      ("rest", "everything else: fin roots and fin-gap floors (H01) and the outer closure")):
        sel = inferred & (region == key)
        by_region[key] = {"what": what, "inferred_mm2": round(float(t_area[sel].sum()), 1),
                          "share_of_body_area": round(float(t_area[sel].sum()) / total, 4),
                          "share_of_inferred_area": round(float(t_area[sel].sum()) / inferred_area, 4)}
    record = {
        "schema": "935-cad-twin-inferred-share/1",
        "body": "v2-loft-s025 (private), the reference CAD body",
        "support_threshold_mm": SUPPORT_MM,
        "distance_tool": "Open3D RaycastingScene.compute_distance (float32), scan facets with the studs removed by "
                         "score_twin.hardware_mask",
        "body_area_mm2": round(total, 1),
        "inferred_mm2": round(inferred_area, 1),
        "inferred_share_of_body_area": round(inferred_area / total, 5),
        "scorecard": {"record": "params/scorecard-v2-loft-s025.json", "inferred_mm2": card["twin_area_inferred_mm2"],
                      "inferred_share": round(1.0 - card["twin_area_observed_supported_share"], 5),
                      "difference_mm2": round(inferred_area - card["twin_area_inferred_mm2"], 1)},
        "probe_mm": PROBE_MM,
        "port_labels": len(port_labels),
        "cavity_labels": len(cavity_labels),
        "by_region": by_region,
        "claims": "a sort of the CAD body's unobserved area by where it lies; no region gained acquired data. The "
                  "declared port continuation (H17) lives in the port domain, not in this body",
    }
    write_json(params / "inferred-share.json", record)
    print(json.dumps(record, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:3])
