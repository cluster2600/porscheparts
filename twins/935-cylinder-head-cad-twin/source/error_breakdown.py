"""Where a twin surface still misses the scan, by surface class.

Scan facets (bare head, twin frame) are measured against a twin surface with
the Warp kernel of score_twin.py and grouped by the direction of their normal
and by Z zone. For each class the output gives its share of the scan area and
how many points of the whole scan area it leaves outside 0.2 and 0.5 mm, so
the next feature is chosen on measured gain.

Usage: error_breakdown.py PRIVATE_DIR TWIN_SURFACE(.stl) OUT.json
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from twin_common import face_geometry, write_json  # noqa: E402

ZONES = (("deck_zone", -5.0, 12.0), ("fin_zone", 12.0, 83.0), ("cam_zone", 83.0, 200.0))


def classes(n):
    nz = n[:, 2]
    return (("up_facing_horizontal", nz > 0.94), ("down_facing_horizontal", nz < -0.94),
            ("vertical", np.abs(nz) < 0.17), ("sloped", (np.abs(nz) >= 0.17) & (np.abs(nz) <= 0.94)))


def main(private, twin, out):
    import trimesh
    from score_twin import warp_distances

    bare = np.load(Path(private) / "bare-scan-twin.npz")
    cen, n, area = face_geometry(bare["v"], bare["f"])
    m = trimesh.load(twin, process=False, force="mesh")
    d = warp_distances(cen, np.asarray(m.vertices, dtype=np.float64), np.asarray(m.faces, dtype=np.int64))
    total = float(area.sum())

    def row(sel):
        a = area[sel]
        return {"scan_area_share": round(float(a.sum() / total), 4),
                "within_0.2_mm": round(float(a[d[sel] <= 0.2].sum() / max(a.sum(), 1e-12)), 4),
                "points_outside_0.2_mm": round(100 * float(a[d[sel] > 0.2].sum() / total), 2),
                "points_outside_0.5_mm": round(100 * float(a[d[sel] > 0.5].sum() / total), 2)}

    res = {"schema": "935-cad-twin-error-breakdown/1", "twin_surface": Path(twin).name,
           "scan_area_mm2": round(total, 1), "all": row(np.ones(len(d), dtype=bool)), "by_class": {}, "by_zone_and_class": {}}
    for name, sel in classes(n):
        res["by_class"][name] = row(sel)
        for zone, lo, hi in ZONES:
            res["by_zone_and_class"][f"{zone}/{name}"] = row(sel & (cen[:, 2] > lo) & (cen[:, 2] < hi))
    write_json(Path(out), res)
    print("all", res["all"])
    for k, v in res["by_class"].items():
        print(f"{k:24s}", v)
    for k, v in res["by_zone_and_class"].items():
        if v["points_outside_0.2_mm"] >= 1.0:
            print(f"  {k:36s}", v)


if __name__ == "__main__":
    main(*sys.argv[1:4])
