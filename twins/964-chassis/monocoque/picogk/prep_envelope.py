"""Inputs of the PicoGK monocoque, from the plate-50-05a shell.

build_shell.py makes an open surface (apertures cut out). PicoGK needs a
closed solid and the apertures as fields, so this script writes, into
work/ (not versioned, regenerated in seconds):

- envelope.stl: the same 420 sections, closed at both ends, as one
  watertight solid: the outer mould line of the car;
- fields.bin + fields.json: every aperture of build_shell.opening_field()
  as its own channel, sampled every 10 mm on a half-car grid (y >= 0),
  float32, > 0 inside the aperture;
- stations.json: per-station roof, floor, belt and half width, for the
  members that follow the body (floor, sills, tunnel, rails).

    python3 prep_envelope.py      # cadsim image, shapely from the PYLIB
"""
import json
import pathlib
import struct
import sys

import numpy as np

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "source"))
import build_shell as bs  # noqa: E402

WORK = HERE / "work"
STEP_MM = 10.0
CHANNELS = ["door", "quarter_window", "rear_arch", "front_arch", "windscreen",
            "rear_window", "front_lid", "engine_lid", "engine_bay_underside"]


def envelope(d, zt, zb, w, zbelt):
    rings, v, f = bs.surface(d, zt, zb, w, zbelt)
    nr, n = len(rings[0]), len(d)
    caps = []
    for i, flip in ((0, True), (n - 1, False)):
        r = rings[i]
        c = len(v) + len(caps)
        caps.append([-d[i], 0.0, float(r[:, 1].mean())])
        for j in range(nr):
            a, b = i * nr + j, i * nr + (j + 1) % nr
            f = np.vstack([f, [c, b, a] if flip else [c, a, b]])
    v = np.vstack([v, caps])
    tri = v[f]
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    vol = np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6
    if vol < 0:                                  # outward normals for the voxelizer
        tri, nrm, vol = tri[:, ::-1], -nrm, -vol
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
    with (WORK / "envelope.stl").open("wb") as fh:
        fh.write(b"964 envelope from plate 50-05a, mm".ljust(80, b" "))
        fh.write(struct.pack("<I", len(tri)))
        rec = np.zeros(len(tri), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
        rec["n"], rec["v"] = nrm, tri
        fh.write(rec.tobytes())
    return len(tri), vol


def fields(p, d, zt, zb, w, zbelt):
    gd = np.arange(-720.0, 3100.0 + STEP_MM, STEP_MM)
    gy = np.arange(0.0, 900.0 + STEP_MM, STEP_MM)
    gz = np.arange(0.0, 1340.0 + STEP_MM, STEP_MM)
    D, Y, Z = np.meshgrid(gd, gy, gz, indexing="ij")
    pts = np.c_[-D.ravel(), Y.ravel(), Z.ravel()]
    stack = bs.opening_fields(pts, p, d, zt, zb, w, zbelt).astype(np.float32)
    assert stack.shape[0] == len(CHANNELS)
    stack.reshape(len(CHANNELS), len(gd), len(gy), len(gz)).tofile(WORK / "fields.bin")
    meta = {"channels": CHANNELS, "order": "channel, d, y, z (C order), float32",
            "d0": gd[0], "y0": gy[0], "z0": gz[0], "step_mm": STEP_MM,
            "nd": len(gd), "ny": len(gy), "nz": len(gz),
            "note": "y is |y|: the field is symmetric; values > 0 inside the aperture, distance-like in mm"}
    (WORK / "fields.json").write_text(json.dumps(meta, indent=1) + "\n")


def main():
    WORK.mkdir(exist_ok=True)
    p = json.loads(bs.PROFILES.read_text())
    d, zt, zb, w, zbelt = bs.stations(p)
    n, vol = envelope(d, zt, zb, w, zbelt)
    fields(p, d, zt, zb, w, zbelt)
    door = np.array(p["openings"]["door_aperture"])
    st = {"d": d.tolist(), "top": zt.tolist(), "bottom": zb.tolist(), "half_width": w.tolist(),
          "belt": zbelt.tolist(), "front_axle_d": bs.FRONT_AXLE_D, "rear_axle_d": bs.REAR_AXLE_D,
          "front_bulkhead_d": bs.FRONT_BULKHEAD_D, "rear_bulkhead_d": bs.REAR_BULKHEAD_D,
          "door_d": [float(door[:, 0].min()), float(door[:, 0].max())],
          "door_z": [float(door[:, 1].min()), float(door[:, 1].max())]}
    (WORK / "stations.json").write_text(json.dumps(st) + "\n")
    print(f"envelope.stl: {n} triangles, {vol / 1e9:.2f} m3; fields.bin and stations.json in {WORK}")


if __name__ == "__main__":
    main()
