"""v1 feature tree, fins: locate and fit the fin faces on acquired facets.

Upstream audit for fin_stack.py. The first body stack (label a) looked for
horizontal faces with a 0.1 mm window. In the fin pack it found levels near
only 7 of the 28 fin faces and left single bands from z = 7.6 to 38.1 mm and
from 50.0 to 69.4 mm (fin zone: 17% of scan area within 0.2 mm). The fins are
normal to the bore axis, but their faces are cast and drafted: each spreads
over 1 to 2 mm of Z. This script therefore

  1. histograms facet area along Z at 0.25 mm, separately for up-facing and
     down-facing facets with |n_z| > NZ_MIN, smoothed over 5 bins;
  2. takes each local maximum as one fin face and fits it twice on the facets
     within REACH_MM: as a constant level and as a tilted plane;
  3. writes the fitted scalars (no geometry) to PARAMS/fin-faces.json.

Usage: fit_fins.py PRIVATE_DIR PARAMS_DIR
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from twin_common import face_geometry, write_json  # noqa: E402

NZ_MIN = 0.94
BIN_MM = 0.25
REACH_MM = 1.6
MIN_FACE_AREA_MM2 = 150.0
Z_RANGE_MM = (11.0, 83.0)


def face_peaks(z, a):
    edges = np.arange(Z_RANGE_MM[0], Z_RANGE_MM[1] + BIN_MM, BIN_MM)
    h, _ = np.histogram(z, bins=edges, weights=a)
    sm = np.convolve(h, np.ones(5) / 5.0, mode="same")
    return [float(edges[i] + BIN_MM / 2) for i in range(2, len(sm) - 2)
            if sm[i] > 30.0 and sm[i] == sm[max(0, i - 4):i + 5].max()]


def wfit(p, w, cols):
    a = np.column_stack([np.ones(len(p))] + cols)
    sw = np.sqrt(w)
    co, *_ = np.linalg.lstsq(a * sw[:, None], p[:, 2] * sw, rcond=None)
    r = p[:, 2] - a @ co
    return co, float(np.sqrt((w * r * r).sum() / w.sum()))


def main(private, params):
    private, params = Path(private), Path(params)
    bare = np.load(private / "bare-scan-twin.npz")
    cen, n, area = face_geometry(bare["v"], bare["f"])
    faces = []
    for sign, side in ((-1, "bottom"), (1, "top")):
        fam = (sign * n[:, 2] > NZ_MIN) & (cen[:, 2] > Z_RANGE_MM[0]) & (cen[:, 2] < Z_RANGE_MM[1])
        for zp in face_peaks(cen[fam, 2], area[fam]):
            sel = (sign * n[:, 2] > NZ_MIN) & (np.abs(cen[:, 2] - zp) < REACH_MM)
            p, w = cen[sel], area[sel]
            if w.sum() < MIN_FACE_AREA_MM2:
                continue
            c0, r0 = wfit(p, w, [])
            c1, r1 = wfit(p, w, [p[:, 0], p[:, 1]])
            faces.append({
                "side": side,
                "area_mm2": round(float(w.sum()), 1),
                "z_level_mm": round(float(c0[0]), 3),
                "rms_level_mm": round(r0, 3),
                "plane_z_at_axis_mm": round(float(c1[0]), 3),
                "plane_slope_xy": [round(float(c1[1]), 6), round(float(c1[2]), 6)],
                "plane_tilt_deg": round(float(np.degrees(np.arctan(np.hypot(c1[1], c1[2])))), 3),
                "plane_tilt_azimuth_deg": round(float(np.degrees(np.arctan2(c1[2], c1[1]))), 1),
                "rms_plane_mm": round(r1, 3),
                # 2nd..98th percentile of the fitted plane's Z over its own facets.
                "plane_z_span_mm": [round(float(v), 3) for v in np.percentile(
                    c1[0] + c1[1] * p[:, 0] + c1[2] * p[:, 1], (2, 98))],
            })
    faces.sort(key=lambda f: f["z_level_mm"])
    tops = [f for f in faces if f["side"] == "top"]
    bottoms = [f for f in faces if f["side"] == "bottom"]
    out = {
        "schema": "935-cad-twin-fin-faces/1",
        "method": "area histogram along Z of acquired facets with |n_z| > %.2f, %.2f mm bins, "
                  "5-bin smoothing; each peak fitted on facets within %.1f mm" % (NZ_MIN, BIN_MM, REACH_MM),
        "evidence_class": "fitted on acquired scan facets; cast surfaces, no physical calibration",
        "faces": faces,
        "summary": {
            "top_faces": len(tops),
            "bottom_faces": len(bottoms),
            "top_pitch_median_mm": round(float(np.median(np.diff([f["z_level_mm"] for f in tops]))), 3),
            "top_tilt_median_deg": round(float(np.median([f["plane_tilt_deg"] for f in tops])), 3),
            "bottom_tilt_median_deg": round(float(np.median([f["plane_tilt_deg"] for f in bottoms])), 3),
            "top_rms_level_median_mm": round(float(np.median([f["rms_level_mm"] for f in tops])), 3),
            "top_rms_plane_median_mm": round(float(np.median([f["rms_plane_mm"] for f in tops])), 3),
            "bottom_rms_level_median_mm": round(float(np.median([f["rms_level_mm"] for f in bottoms])), 3),
        },
    }
    write_json(params / "fin-faces.json", out)
    print(out["summary"])


if __name__ == "__main__":
    main(*sys.argv[1:3])
