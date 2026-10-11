#!/usr/bin/env python3
"""Exact keep-in and region bodies of the bionic wheel center cap (closed STLs).

    python bionic_keepins.py

Writes source/bionic-keepins/*.stl, referenced by source/bionic.json:
  face_shell.stl   domed 2 mm face + 1.5 mm outer skirt with rolled lip
                   (76 mm face, 46 mm crown height, skirt to z = 31)
  barbs.stl        four lead-in barbs on the clip tabs (disjoint convex hulls)
  lip_seat.stl     thin ring at the skirt lip, the support region (wheel face)
  above_face.stl   void above the domed face (keeps the visible face clean)
Axis Z, clip end at z = 0, values of source/picogk.json (F0 concept).
"""
from pathlib import Path

import numpy as np
import trimesh

OUT = Path(__file__).resolve().parent / "bionic-keepins"
R, H, DOME, FACE_T = 38.0, 46.0, 3.0, 2.0
SKIRT_W, Z_SKIRT = 1.5, 31.0
R_RING_O = 31.5
TAB_HALF_W, BARB, BARB_H = 4.0, 1.5, 4.0
RS = (R * R + DOME * DOME) / (2 * DOME)
CZ = H - RS


def dome(r):
    return CZ + np.sqrt(RS * RS - r * r)


def revolve(profile, sections=180):
    p = np.asarray(profile, float)
    if not np.allclose(p[0], p[-1]):
        p = np.vstack([p, p[:1]])
    m = trimesh.creation.revolve(p, sections=sections)
    if m.volume < 0:
        m.invert()
    assert m.is_watertight, "profile did not revolve into a closed body"
    return m


def face_shell():
    edge = 1.5
    top = [(r, dome(r)) for r in np.linspace(0, R - edge, 40)]
    zc = dome(R - edge) - edge                      # rounded rim, centre of the edge arc
    rim = [(R - edge + edge * np.sin(a), zc + edge * np.cos(a)) for a in np.linspace(0.15, np.pi / 2, 8)]
    lip_c = (R - SKIRT_W / 2, Z_SKIRT + SKIRT_W / 2)
    lip = [(lip_c[0] + SKIRT_W / 2 * np.cos(a), lip_c[1] - SKIRT_W / 2 * np.sin(a)) for a in np.linspace(0, np.pi, 10)]
    r_in = R - SKIRT_W
    under = [(r, dome(r) - FACE_T) for r in np.linspace(r_in, 0, 40)]
    prof = top + rim + lip + under
    # revolve wants the profile ordered without repeated axis points beyond the ends
    return revolve(prof)


def barbs():
    parts = []
    da = TAB_HALF_W - 0.6
    for k in range(4):
        a = k * np.pi / 2
        pts = []
        for s in (-1, 1):
            for r, z in ((R_RING_O - 0.6, 0.3), (R_RING_O, 0.3), (R_RING_O + BARB, 0.3 + BARB_H), (R_RING_O - 0.6, 0.3 + BARB_H)):
                t = s * da / r
                pts.append((r * np.cos(a + t), r * np.sin(a + t), z))
        parts.append(trimesh.convex.convex_hull(np.array(pts)))
    return trimesh.util.concatenate(parts)


def above_face():
    """Void: everything above the domed face surface, up to z = 48, out to
    r = 39, so no member can grow on the visible face."""
    top = [(r, dome(r)) for r in np.linspace(0, R + 1.0, 60)]
    return revolve(top + [(R + 1.0, H + 2.0), (0.0, H + 2.0)])


def lip_seat():
    return revolve([(36.2, 30.5), (38.6, 30.5), (38.6, 31.5), (36.2, 31.5)])


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for name, m in (("face_shell", face_shell()), ("barbs", barbs()), ("lip_seat", lip_seat()),
                    ("above_face", above_face())):
        m.export(OUT / f"{name}.stl")
        print(name, len(m.faces), "faces", round(float(m.volume), 1), "mm3", np.round(m.bounds, 2).tolist())
