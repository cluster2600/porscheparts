"""Supports for the print body prepared by an open build processor (PySLM), set against the rule layout.

support_design.py lays block supports out by declared rules. This tool hands the same print body, in the
same orientation, to PySLM's GridBlockSupportGenerator at the revision the repository already pins, with
the library's own defaults and a stated critical angle, and measures what it prepares against the rule
layout on the same 0.25 mm grid, with the same code for both. What is compared was fixed beforehand in
params/support-build-processor-plan.json.

Sub-commands (run in the PySLM environment, Python 3.11, NumPy 1.26):

  witness OUT.json
      the voxeliser on closed meshes of known volume, then PySLM on the T block of support_design.py
  prepare MESH.stl OCC_DIR PLAN.json PRIVATE_DIR
      PySLM on the print body, flange y+ on the plate; its support blocks are kept privately as meshes
  compare OCC_DIR RULE_DIR PRIVATE_DIR PLAN.json OUT.json
      both layouts voxelised on the occupancy grid and measured; the private processor envelope is saved
      for the picture
  truss PRIVATE_DIR OUT.json
      PySLM's grid truss of every block, after the comparison and outside it

PySLM projects height maps through OpenGL: run `prepare` and `witness` under
`GALLIUM_DRIVER=llvmpipe LIBGL_ALWAYS_SOFTWARE=1 xvfb-run -a`.

This is an open research library, not the machine maker's processor: no machine file, no exposure
parameters and no maker's support templates come out of it.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import resource
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import support_design as sd  # noqa: E402

PITCH = 0.25
TOLERANCE_VOXELS = 2              # at most two air voxels (0.5 mm) between a support and what it touches
JITTER = (1.0e-4 * math.sqrt(2.0), 1.0e-4 * math.sqrt(3.0))   # mm: keeps the column rays off mesh edges
OVERHANG_DEG = 45.0


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def peak_rss_gib() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2 ** 20


# --------------------------------------------------------------------------
# voxeliser


def voxelise(meshes, shape, pitch=PITCH, origin=(0.0, 0.0, 0.0)) -> np.ndarray:
    """Winding number of closed, outward-wound triangle meshes at the voxel centres of a grid, > 0 inside.

    Voxel (i, j, k) has its centre at origin + (i, j, k) * pitch. A vertical ray goes up every column; each
    triangle it crosses adds +1 above the crossing when it faces down (entering) and -1 when it faces up.
    Overlapping meshes add up, so the union is where the sum is positive.
    """

    diff = np.zeros((shape[0], shape[1], shape[2] + 1), dtype=np.int16)
    o = np.asarray(origin, dtype=np.float64)
    for vertices, faces in meshes:
        t = (np.asarray(vertices, dtype=np.float64)[np.asarray(faces)] - o) / pitch   # (n, 3, 3), in voxel units
        t[:, :, 0] -= JITTER[0] / pitch
        t[:, :, 1] -= JITTER[1] / pitch
        a, b, c = t[:, 0], t[:, 1], t[:, 2]
        cross = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
        keep = np.abs(cross) > 1e-12
        t, cross = t[keep], cross[keep]
        lo = np.ceil(t[:, :, :2].min(axis=1)).astype(np.int64)
        hi = np.floor(t[:, :, :2].max(axis=1)).astype(np.int64)
        lo = np.maximum(lo, 0)
        hi[:, 0] = np.minimum(hi[:, 0], shape[0] - 1)
        hi[:, 1] = np.minimum(hi[:, 1], shape[1] - 1)
        nx, ny = np.maximum(hi[:, 0] - lo[:, 0] + 1, 0), np.maximum(hi[:, 1] - lo[:, 1] + 1, 0)
        count = nx * ny
        for start in range(0, len(t), 200_000):
            sl = slice(start, start + 200_000)
            n = count[sl]
            if n.sum() == 0:
                continue
            tri = np.repeat(np.arange(start, start + len(n)), n)
            first = np.repeat(np.cumsum(n) - n, n)
            local = np.arange(n.sum()) - first
            w = np.repeat(nx[sl], n)
            ci = lo[tri, 0] + local % np.maximum(w, 1)
            cj = lo[tri, 1] + local // np.maximum(w, 1)
            a, b, c = t[tri, 0], t[tri, 1], t[tri, 2]
            # barycentric coordinates of the column in the triangle's projection
            d = cross[tri]
            l1 = ((b[:, 0] - ci) * (c[:, 1] - cj) - (b[:, 1] - cj) * (c[:, 0] - ci)) / d
            l2 = ((c[:, 0] - ci) * (a[:, 1] - cj) - (c[:, 1] - cj) * (a[:, 0] - ci)) / d
            l3 = 1.0 - l1 - l2
            inside = (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
            z = l1 * a[:, 2] + l2 * b[:, 2] + l3 * c[:, 2]
            sign = np.where(d < 0, 1, -1).astype(np.int16)     # projected clockwise: the face looks down
            ci, cj, z, sign = ci[inside], cj[inside], z[inside], sign[inside]
            kk = np.clip(np.ceil(z), 0, shape[2]).astype(np.int64)
            np.add.at(diff, (ci, cj, kk), sign)
    return np.cumsum(diff, axis=2, dtype=np.int16)[:, :, :-1] > 0


# --------------------------------------------------------------------------
# PySLM


class _Tally(logging.Handler):
    """Counts the library's own log messages: they say which regions it skipped and why."""

    KEYS = {"Could not flatten region": "could_not_flatten", "skipping shape (area too small)": "area_too_small",
            "no valid regions identified": "no_valid_region", "PROJECTIONS NOT MATCHING": "projections_not_matching",
            "Creating Base-plate support": "base_plate_block", "Processing subregion": "subregions"}

    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.counts = Counter()

    def emit(self, record):
        message = record.getMessage()
        for text, key in self.KEYS.items():
            if text in message:
                self.counts[key] += 1


def generator_settings(gen) -> dict:
    names = ["rayProjectionResolution", "minimumAreaThreshold", "innerSupportEdgeGap", "outerSupportEdgeGap",
             "lowerProjectionOffset", "upperProjectionOffset", "triangulationSpacing", "simplifyPolygonFactor",
             "splineSimplificationFactor", "gridSpacing", "supportWallThickness", "supportBorderDistance", "trussWidth",
             "trussAngle", "supportTeethHeight", "supportTeethTopLength", "supportTeethBottomLength",
             "supportTeethBaseInterval", "supportTeethUpperPenetration", "useUpperSupportTeeth", "useLowerSupportTeeth"]
    out = {}
    for name in names:
        # the stored value: at this revision the supportTeethBottomLength getter returns the top length
        value = getattr(gen, "_" + name) if hasattr(gen, "_" + name) else getattr(gen, name, None)
        out[name] = list(value) if isinstance(value, (list, tuple)) else value
    return out


def release_canvases() -> None:
    """Let Qt delete each height-map canvas once PySLM has read it.

    PySLM opens one vispy canvas per height map and closes it, but the window is only destroyed when Qt
    processes its events, which nothing does in a script. Under Xvfb with llvmpipe the 52nd canvas of a
    process then fails its framebuffer check and the library stops (`witness`, case G1). This wrapper calls
    the library's own function unchanged and processes Qt's events after it; the height map is not touched.
    """

    import gc

    import vispy.app
    from pyslm.support import render

    if getattr(render.projectHeightMap, "_released", False):
        return
    original = render.projectHeightMap

    def wrapped(*args, **kwargs):
        out = original(*args, **kwargs)
        vispy.app.process_events()
        gc.collect()
        vispy.app.process_events()
        return out

    wrapped._released = True
    render.projectHeightMap = wrapped


UPSTREAM_SUPPORT_PY = "3332ca5ddecd3b692d727efecb36a3b76dea2f84069c7d9b3fbc340eed77b723"
PATCHED_SUPPORT_PY = "fea7275ce46ad8d4f9c9471457c260111e7a1278b2dce315d126c8341e957c52"   # process-20261016 patch


def installed_library() -> dict:
    """Versions and source hashes of the PySLM actually imported, and which declared state it is in."""

    import inspect
    from importlib.metadata import version

    import pyslm.support

    folder = Path(inspect.getfile(pyslm.support.BlockSupportGenerator)).parent
    hashes = {name: sha256(folder / name) for name in ("support.py", "gridBlockSupport.py", "utils.py", "geometry.py", "render.py")}
    state = {UPSTREAM_SUPPORT_PY: "upstream, unpatched",
             PATCHED_SUPPORT_PY: "declared fallback 1: parts/993-eng-carrier-0001/source/process-20261016/pyslm-support-projection.patch "
                                 "(the extrusion keeps its 3D vertex correspondence); the rest upstream"}.get(hashes["support.py"], "unknown")
    packages = {n: version(n) for n in ("PythonSLM", "numpy", "trimesh", "shapely", "pyclipr", "manifold3d", "vispy", "PyQt5",
                                        "scipy", "scikit-image", "networkx", "rtree", "triangle", "mapbox_earcut", "matplotlib")}
    return {"packages": packages, "source_sha256": hashes, "state": state}


def run_pyslm(mesh, angle_deg=OVERHANG_DEG, spline=True):
    """identifySupportRegions on a mesh already in the build frame with its lowest point on z = 0."""

    import pyslm
    import pyslm.support

    release_canvases()
    part = pyslm.Part("print_body")
    part.setGeometry(mesh, fixGeometry=False, mergeVertices=False)
    part.dropToPlatform(0.0)
    gen = pyslm.support.GridBlockSupportGenerator()
    if not spline:
        gen.splineSimplificationFactor = None
    tally = _Tally()
    root = logging.getLogger()
    root.addHandler(tally)
    root.setLevel(logging.INFO)
    started = time.time()
    try:
        blocks = gen.identifySupportRegions(part, angle_deg, True)
    finally:
        root.removeHandler(tally)
    seconds = time.time() - started
    overhang = pyslm.support.getOverhangMesh(part, angle_deg, splitMesh=False)
    return part, gen, blocks, dict(tally.counts), seconds, overhang


def blocks_to_arrays(blocks):
    out = []
    for b in blocks:
        m = b.supportVolume
        out.append((np.asarray(m.vertices, dtype=np.float64), np.asarray(m.faces, dtype=np.int64)))
    return out


def block_stats(blocks) -> dict:
    volumes = [float(b.supportVolume.volume) for b in blocks]
    closed = [bool(b.supportVolume.is_watertight) for b in blocks]
    return {"blocks": len(blocks), "closed_blocks": int(sum(closed)),
            "intersecting_the_part": int(sum(bool(b.intersectsPart) for b in blocks)),
            "mesh_volume_mm3": float(sum(volumes)), "smallest_block_mm3": float(min(volumes)) if volumes else 0.0,
            "largest_block_mm3": float(max(volumes)) if volumes else 0.0}


# --------------------------------------------------------------------------
# measures shared by both layouts


def column_runs(envelope: np.ndarray, solid: np.ndarray, plate_level: int, tol: int = TOLERANCE_VOXELS) -> dict:
    """Ends of the vertical runs of envelope voxels: what each run stands on and what it touches at its top."""

    up = np.zeros_like(envelope)
    up[:, :, :-1] = envelope[:, :, 1:]
    down = np.zeros_like(envelope)
    down[:, :, 1:] = envelope[:, :, :-1]
    top = envelope & ~up
    foot = envelope & ~down
    # solid within tol + 1 voxels above a top, below a foot
    solid_above = np.zeros_like(solid)
    solid_below = np.zeros_like(solid)
    for s in range(1, tol + 2):
        solid_above[:, :, :-s] |= solid[:, :, s:]
        solid_below[:, :, s:] |= solid[:, :, :-s]
    ti, tj, tk = np.nonzero(top)
    fi, fj, fk = np.nonzero(foot)
    # as in support_design.py: a column stands on the plate only when no part lies anywhere under it
    anything_below = np.logical_or.accumulate(solid, axis=2)
    nothing_below = ~anything_below[fi, fj, np.maximum(fk - 1, 0)] | (fk == 0)
    del anything_below
    on_part = solid_below[fi, fj, fk]
    on_plate = ~on_part & nothing_below & (fk <= plate_level + 1 + tol)
    in_air = ~on_plate & ~on_part
    touches = solid_above[ti, tj, tk]
    return {"top": (ti, tj, tk), "foot": (fi, fj, fk), "foot_on_plate": on_plate, "foot_on_part": on_part,
            "foot_in_air": in_air, "top_touches_part": touches}


def landing_labels(envelope: np.ndarray, runs: dict) -> np.ndarray:
    """Each envelope voxel labelled by what its column stands on: 1 the plate, 2 the part, 3 nothing (air)."""

    label = np.zeros(envelope.shape, dtype=np.int8)
    fi, fj, fk = runs["foot"]
    label[fi, fj, fk] = np.where(runs["foot_on_plate"], 1, np.where(runs["foot_on_part"], 2, 3)).astype(np.int8)
    for k in range(1, envelope.shape[2]):                   # carry each foot's label up its run
        carry = envelope[:, :, k] & (label[:, :, k] == 0)
        label[:, :, k][carry] = label[:, :, k - 1][carry]
    return label


def runs_volume(envelope: np.ndarray, runs: dict) -> dict:
    """Envelope volume split by what the column stands on (each run's voxels follow its foot)."""

    v = PITCH ** 3
    label = landing_labels(envelope, runs)
    return {"on_plate_mm3": float((label == 1).sum() * v), "on_part_mm3": float((label == 2).sum() * v),
            "ending_in_air_mm3": float((label == 3).sum() * v)}


def supported_mask(envelope: np.ndarray, i, j, k, tol: int = TOLERANCE_VOXELS) -> np.ndarray:
    hit = np.zeros(len(i), dtype=bool)
    for g in range(0, tol + 1):
        kk = k - 1 - g
        ok = kk >= 0
        hit[ok] |= envelope[i[ok], j[ok], kk[ok]]
    return hit


def unsupported_patches(shape, i, j, k, plate_level: int) -> dict:
    """Unsupported transitions grouped 26-connected, as the rule groups its patches."""

    a = PITCH ** 2
    if len(i) == 0:
        return {"count": 0, "projected_area_mm2": 0.0, "largest_patch_mm2": 0.0, "largest_inscribed_width_mm": 0.0,
                "widest_patches": []}
    surface = np.zeros(shape, dtype=bool)
    surface[i, j, k] = True
    labels, count = ndimage.label(surface, structure=sd.FULL)
    patch = labels[i, j, k]
    del labels, surface
    order = np.argsort(patch, kind="stable")
    bounds = np.flatnonzero(np.diff(patch[order])) + 1
    rows = []
    for group in np.split(order, bounds):
        gi, gj, gk = i[group], j[group], k[group]
        foot = np.zeros((gi.max() - gi.min() + 1, gj.max() - gj.min() + 1), dtype=bool)
        foot[gi - gi.min(), gj - gj.min()] = True
        rows.append({"projected_area_mm2": float(len(group) * a), "inscribed_width_mm": sd.inscribed_width(foot, PITCH),
                     "height_above_plate_mm": float((gk.min() - plate_level) * PITCH),
                     "centre_build_frame_mm": [round(float(gi.mean() * PITCH), 2), round(float(gj.mean() * PITCH), 2),
                                               round(float(gk.mean() * PITCH), 2)]})
    rows.sort(key=lambda r: (-r["inscribed_width_mm"], -r["projected_area_mm2"]))
    return {"count": int(count), "projected_area_mm2": float(len(i) * a),
            "largest_patch_mm2": max(r["projected_area_mm2"] for r in rows),
            "largest_inscribed_width_mm": rows[0]["inscribed_width_mm"], "widest_patches": rows[:8]}


def measure(envelope: np.ndarray, solid: np.ndarray, ref: dict, plate_level: int) -> dict:
    a, v = PITCH ** 2, PITCH ** 3
    runs = column_runs(envelope, solid, plate_level)
    i, j, k = ref["i"], ref["j"], ref["k"]
    sup = supported_mask(envelope, i, j, k)
    ti, tj, tk = runs["top"]
    fi, fj, fk = runs["foot"]
    top_contact = float(runs["top_touches_part"].sum() * a)
    foot_contact = float(runs["foot_on_part"].sum() * a)
    return {
        "supported_projected_area_mm2": float(sup.sum() * a),
        "supported_share_of_the_reference_surface": float(sup.mean()) if len(sup) else 0.0,
        "envelope_volume_mm3": float(envelope.sum() * v),
        "envelope_by_landing": runs_volume(envelope, runs),
        "contact_with_the_part_projected_mm2": {"under_the_supported_surface": top_contact, "at_the_foot": foot_contact,
                                                "total": top_contact + foot_contact},
        "plate_contact_projected_mm2": float(runs["foot_on_plate"].sum() * a),
        "column_tops_in_air_projected_mm2": float((~runs["top_touches_part"]).sum() * a),
        "column_feet_in_air_projected_mm2": float(runs["foot_in_air"].sum() * a),
        # feet and tops come out of np.nonzero in the same (i, j, k) order, one of each per run
        "tallest_column_mm": float(((tk - fk + 1) * PITCH).max()) if len(tk) else 0.0,
        "unsupported_reference_surface": unsupported_patches(envelope.shape, i[~sup], j[~sup], k[~sup], plate_level),
        "_supported": sup, "_runs": runs,
    }


# --------------------------------------------------------------------------
# witness


def _box(lo, hi):
    import trimesh

    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    return trimesh.creation.box(extents=hi - lo, transform=trimesh.transformations.translation_matrix((lo + hi) / 2))


def witness(out) -> None:
    """Hand-checked answers before the head.

    V1  a box 10.3 x 20.1 x 30.7 mm placed off the grid: 6,355.71 mm3
    V2  a 30 mm cube with a 10 mm square hole through it: 27,000 - 3,000 = 24,000 mm3
    V3  two boxes overlapping by half: the union, 1.5 x the volume of one, counted once
    P1  PySLM on the T block of support_design.py (stem 20 x 20 x 30 mm, cap 40 x 40 x 10 mm), at 45 degrees with
        the generator's defaults: one block under the cap, standing on the plate. Its own mesh volume and its
        voxelised volume must agree within 1 %; its area is set against the cap annulus shrunk by the inner edge
        gap (39.6^2 - 20.4^2 = 1,152 mm2), as information: the library traces it from a height map
    """

    import trimesh

    cases = []

    def add(name, quantity, expected, measured, tol):
        err = (measured - expected) / expected
        cases.append({"witness": name, "quantity": quantity, "expected": round(expected, 3), "measured": round(measured, 3),
                      "relative_error": round(err, 5), "tolerance": tol, "within_tolerance": bool(abs(err) <= tol)})

    shape = (200, 200, 200)
    b = _box((3.13, 7.71, 5.29), (13.43, 27.81, 35.99))
    vox = voxelise([(b.vertices, b.faces)], shape)
    add("V1 box off the grid", "volume_mm3", 10.3 * 20.1 * 30.7, vox.sum() * PITCH ** 3, 0.01)

    cube = _box((5.07, 5.11, 5.13), (35.07, 35.11, 35.13))
    hole = _box((15.07, 15.11, 0.0), (25.07, 25.11, 40.0))
    ring = trimesh.boolean.difference([cube, hole], engine="manifold")
    vox = voxelise([(ring.vertices, ring.faces)], shape)
    add("V2 cube with a hole through it", "volume_mm3", 24000.0, vox.sum() * PITCH ** 3, 0.01)

    one = _box((2.03, 2.07, 2.11), (22.03, 12.07, 12.11))
    two = _box((12.03, 2.07, 2.11), (32.03, 12.07, 12.11))
    vox = voxelise([(one.vertices, one.faces), (two.vertices, two.faces)], shape)
    add("V3 two overlapping boxes", "volume_mm3", 3000.0, vox.sum() * PITCH ** 3, 0.01)

    # P1: a round cap on a round stem, 64 sides each
    stem = trimesh.creation.cylinder(radius=10.0, height=30.0, sections=64)
    stem.apply_translation((0.0, 0.0, 15.0))
    cap = trimesh.creation.cylinder(radius=20.0, height=10.0, sections=64)
    cap.apply_translation((0.0, 0.0, 35.0))
    tee = trimesh.boolean.union([stem, cap], engine="manifold")
    tee.apply_translation((22.0, 22.0, 0.0))
    part, gen, blocks, counts, seconds, overhang = run_pyslm(tee)
    stats = block_stats(blocks)
    origin = np.zeros(3)
    vox = voxelise(blocks_to_arrays(blocks), (180, 180, 180), origin=origin)
    solid = voxelise([(tee.vertices, tee.faces)], (180, 180, 180), origin=origin)
    add("P1 round T in PySLM", "voxelised block volume against the block meshes", stats["mesh_volume_mm3"],
        float((vox & ~solid).sum() * PITCH ** 3), 0.01)
    ring = 64 / 2 * math.sin(2 * math.pi / 64)                      # area of a 64-gon over r^2
    hand = ring * (19.8 ** 2 - 10.2 ** 2)
    footprint = (vox & ~solid).any(axis=2).sum() * PITCH ** 2
    cases.append({"witness": "P1 round T in PySLM", "quantity": "block footprint against the cap annulus less the inner edge gap "
                  "of 0.2 mm at both rims (information: the library traces it from a height map)",
                  "hand_value": round(hand, 3), "measured": round(float(footprint), 3),
                  "relative_difference": round(float(footprint) / hand - 1.0, 4)})
    cases.append({"witness": "P1 round T in PySLM", "quantity": "blocks and the library's own messages (information)",
                  "measured": {**stats, "log": counts, "seconds": round(seconds, 2),
                               "overhang_face_area_mm2": round(float(overhang.area), 3)}})

    # P2: the square T of support_design.py. Its cap underside is an annulus bounded by two loops of four edges.
    stem = _box((-10, -10, 0), (10, 10, 30))
    cap = _box((-20, -20, 30), (20, 20, 40))
    tee = trimesh.boolean.union([stem, cap], engine="manifold")
    tee.apply_translation((22.0, 22.0, 0.0))
    part, gen, blocks, counts, seconds, overhang = run_pyslm(tee)
    from pyslm.support import utils
    subs = utils.getOverhangMesh(part, OVERHANG_DEG, True)
    cases.append({"witness": "P2 square T in PySLM", "quantity": "what the library does with the cap underside (information)",
                  "measured": {**block_stats(blocks), "log": counts,
                               "overhang_face_area_mm2": round(float(overhang.area), 3),
                               "area_after_splitting_into_regions_mm2": round(float(sum(s.area for s in subs)), 3)},
                  "reading": "trimesh 5 splits the overhang with repair=True, which fills boundary loops of three or four edges. "
                             "The annulus 40 x 40 - 20 x 20 (1,200 mm2) comes back closed, 3,200 mm2, with no outline; PySLM "
                             "cannot flatten it, logs a warning and leaves the cap unsupported"})

    # G1: many height-map canvases in one process, as on the head, through release_canvases()
    from pyslm.support import render

    release_canvases()
    rng = np.random.default_rng(1)
    drawn = 0
    for n in range(120):
        w, h = rng.integers(5, 400, size=2)
        ball = trimesh.creation.icosphere(subdivisions=3, radius=1.0)
        ball.apply_scale((w * 0.1, h * 0.1, 3.0))
        ball.apply_translation((50.0, 50.0, 20.0))
        image = render.projectHeightMap(ball, 0.2, bool(n % 2), ball.bounds.copy())
        if image is None or abs(image.shape[0] - h) > 1 or abs(image.shape[1] - w) > 1:
            break
        drawn += 1
    cases.append({"witness": "G1 height-map canvases in one process", "quantity": "canvases drawn in a row, of 120",
                  "expected": 120, "measured": drawn, "within_tolerance": drawn == 120,
                  "note": "without release_canvases() the 52nd canvas of this sequence fails its framebuffer check "
                          "(Qt 5.15, Xvfb, llvmpipe), and PySLM stopped at the 14th height map of the print body"})

    rep = {"schema": "935-cad-twin-support-build-processor-witness/1", "date": time.strftime("%Y-%m-%d"),
           "pitch_mm": PITCH, "library": installed_library(), "settings": generator_settings(gen),
           "passed": all(c.get("within_tolerance", True) for c in cases), "cases": cases}
    Path(out).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(rep, indent=1))
    assert rep["passed"]


# --------------------------------------------------------------------------
# the print body


def load_grid(occ_dir: Path):
    grid = json.loads((occ_dir / "occupancy-grid.json").read_text())
    inside = np.load(occ_dir / grid["array"], mmap_mode="r") > 0.5
    labels, count = ndimage.label(inside)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    inside = labels == int(sizes.argmax())
    del labels
    solid = np.ascontiguousarray(inside.transpose(0, 2, 1)[:, :, ::-1])      # (x, z, -y): support_design.py
    return grid, solid


def to_build_frame(vertices: np.ndarray, grid: dict) -> np.ndarray:
    """Twin (x, y, z) to the build frame (x, z, -y) in which voxel (i, k, m) is centred at (i, k, m) * pitch."""

    h, ny = grid["pitch_mm"], grid["shape"][1]
    out = np.empty_like(vertices, dtype=np.float64)
    out[:, 0] = vertices[:, 0] - grid["x0"]
    out[:, 1] = vertices[:, 2] - grid["z0"]
    out[:, 2] = (ny - 1) * h + grid["y0"] - vertices[:, 1]
    return out


def prepare(mesh_path, occ_dir, plan_file, private) -> None:
    import trimesh

    mesh_path, occ_dir, private = Path(mesh_path), Path(occ_dir), Path(private)
    plan = json.loads(Path(plan_file).read_text())
    assert plan["orientation"]["build_direction"] == "-y"
    started = time.time()
    grid = json.loads((occ_dir / "occupancy-grid.json").read_text())
    raw = trimesh.load_mesh(mesh_path, process=False)
    mesh = trimesh.Trimesh(to_build_frame(np.asarray(raw.vertices), grid), np.asarray(raw.faces), process=True)
    lowest = float(mesh.vertices[:, 2].min())
    mesh.apply_translation((0.0, 0.0, -lowest))
    report = {"library": installed_library(),
              "mesh_file": mesh_path.name, "mesh_sha256": sha256(mesh_path), "triangles": int(len(mesh.faces)),
              "watertight": bool(mesh.is_watertight), "volume_mm3": float(mesh.volume),
              "lowest_point_in_the_grid_frame_mm": lowest}
    spline = True
    try:
        part, gen, blocks, counts, seconds, overhang = run_pyslm(mesh, plan["parameters"]["overhang_angle_deg"], spline)
    except Exception as exc:                                                  # declared fallback 2 only
        if "spline" not in repr(exc).lower() and "MultiPolygon" not in repr(exc):
            raise
        report["fallback"] = f"splineSimplificationFactor None after: {exc!r}"
        spline = False
        part, gen, blocks, counts, seconds, overhang = run_pyslm(mesh, plan["parameters"]["overhang_angle_deg"], spline)
    report.update({"settings": generator_settings(gen), "seconds": round(seconds, 1), "log": counts,
                   "overhang_face_area_mm2": float(overhang.area),
                   "overhang_projected_area_mm2": float(np.abs(overhang.area_faces * overhang.face_normals[:, 2]).sum()),
                   **block_stats(blocks)})
    # What the region split does before the library sees a region: trimesh fills loops of three or four edges.
    from pyslm.support import utils
    from pyslm.support.support import SupportStructure
    subs = utils.getOverhangMesh(part, plan["parameters"]["overhang_angle_deg"], True)
    failed = []
    for sub in subs:
        try:
            SupportStructure.flattenSupportRegion(sub)
        except Exception:  # noqa: BLE001 - the library swallows the same error
            failed.append(float(sub.area))
    report["regions"] = {"count": len(subs), "area_after_the_split_mm2": float(sum(s.area for s in subs)),
                         "not_flattened": len(failed), "not_flattened_area_mm2": float(sum(failed)),
                         "largest_not_flattened_mm2": max(failed) if failed else 0.0}
    arrays = blocks_to_arrays(blocks)
    private.mkdir(parents=True, exist_ok=True)
    payload = {}
    for n, (v, f) in enumerate(arrays):
        payload[f"v{n:05d}"] = (v + np.array([0.0, 0.0, lowest])).astype(np.float64)    # back to the grid frame
        payload[f"f{n:05d}"] = f.astype(np.int32)
    payload["intersects"] = np.array([bool(b.intersectsPart) for b in blocks])
    np.savez_compressed(private / "pyslm-blocks.npz", **payload)
    report["blocks_file"] = "pyslm-blocks.npz"
    report["blocks_sha256"] = sha256(private / "pyslm-blocks.npz")
    report["wall_seconds"] = round(time.time() - started, 1)
    report["peak_rss_gib"] = round(peak_rss_gib(), 2)
    (private / "pyslm-prepare.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "settings"}, indent=1))


def compare(occ_dir, rule_dir, private, plan_file, out) -> None:
    occ_dir, rule_dir, private = Path(occ_dir), Path(rule_dir), Path(private)
    started = time.time()
    plan = json.loads(Path(plan_file).read_text())
    grid, solid = load_grid(occ_dir)
    occupancy_sha = sha256(occ_dir / grid["array"])
    assert occupancy_sha == plan["input"]["occupancy"].split("sha256 ")[1].split(",")[0]
    plate_level = int(np.flatnonzero(solid.any(axis=(0, 1)))[0])
    t = sd.transitions(solid, PITCH, OVERHANG_DEG)
    ref = {key: t[key][t["over"]] for key in ("i", "j", "k")}

    rule_meta = json.loads((rule_dir / "support-envelope.json").read_text())
    assert rule_meta["occupancy_sha256"] == occupancy_sha
    rule = np.load(rule_dir / "support-envelope.npy")
    assert rule.shape == solid.shape

    prep = json.loads((private / "pyslm-prepare.json").read_text())
    assert sha256(private / prep["blocks_file"]) == prep["blocks_sha256"]
    data = np.load(private / prep["blocks_file"])
    n = len([k for k in data.files if k.startswith("v")])
    meshes = [(data[f"v{q:05d}"], data[f"f{q:05d}"]) for q in range(n)]
    raw = voxelise(meshes, solid.shape)
    # each block alone, on its own box of the grid: the voxeliser against the library's mesh volumes
    one_by_one = 0
    for v_, f_ in meshes:
        lo = np.floor(v_.min(axis=0) / PITCH).astype(int) - 1
        hi = np.ceil(v_.max(axis=0) / PITCH).astype(int) + 2
        one_by_one += int(voxelise([(v_, f_)], tuple(hi - lo), origin=lo * PITCH).sum())
    inside_part = raw & solid
    below_plate = raw & ~solid
    below_plate[:, :, plate_level + 1:] = False
    proc = raw & ~solid
    proc[:, :, :plate_level + 1] = False
    del raw

    mine = measure(rule, solid, ref, plate_level)
    theirs = measure(proc, solid, ref, plate_level)
    committed = json.loads((Path(plan_file).parent / "support-design.json").read_text())
    # The rule's own adjacency is exact (tolerance 0); the planned 0.5 mm tolerance is reported beside it.
    strict = float(supported_mask(rule, ref["i"], ref["j"], ref["k"], tol=0).sum() * PITCH ** 2)
    check = {"supported_projected_area_mm2": (strict, committed["supported"]["projected_area_mm2"]),
             "envelope_volume_mm3": (mine["envelope_volume_mm3"], committed["supported"]["envelope_volume_mm3"]),
             "landing_area_on_part_mm2": (mine["contact_with_the_part_projected_mm2"]["at_the_foot"],
                                          committed["supported"]["landing_area_on_part_mm2"])}
    consistency = {key: {"measured_here": a, "committed": b, "equal": bool(abs(a - b) < 1e-6)} for key, (a, b) in check.items()}
    assert all(c["equal"] for c in consistency.values()), consistency
    consistency["supported_projected_area_mm2"]["at_the_planned_tolerance"] = mine["supported_projected_area_mm2"]
    consistency["note"] = ("the supported area is checked at the rule's own adjacency (no air voxel between surface and support); "
                           "at the planned 0.5 mm tolerance the same layout reads the value given beside it")

    a, v = PITCH ** 2, PITCH ** 3
    s_rule, s_proc = mine.pop("_supported"), theirs.pop("_supported")
    runs_proc = theirs.pop("_runs")
    mine.pop("_runs")
    # the processor's top contacts outside the reference surface, or under rule-exempted surface
    ti, tj, tk = runs_proc["top"]
    touch = runs_proc["top_touches_part"]
    ref_set = np.zeros(solid.shape, dtype=bool)
    ref_set[ref["i"], ref["j"], ref["k"]] = True
    near_ref = np.zeros(len(ti), dtype=bool)
    for g in range(1, TOLERANCE_VOXELS + 2):
        kk = np.minimum(tk + g, solid.shape[2] - 1)
        near_ref |= ref_set[ti, tj, kk]
    regions = {
        "reference_surface_projected_mm2": float(len(s_rule) * a),
        "supported_by_both_mm2": float((s_rule & s_proc).sum() * a),
        "supported_by_the_processor_only_mm2": float((~s_rule & s_proc).sum() * a),
        "supported_by_the_rule_only_mm2": float((s_rule & ~s_proc).sum() * a),
        "supported_by_neither_mm2": float((~s_rule & ~s_proc).sum() * a),
        "envelope_in_both_mm3": float((rule & proc).sum() * v),
        "envelope_of_the_processor_only_mm3": float((proc & ~rule).sum() * v),
        "envelope_of_the_rule_only_mm3": float((rule & ~proc).sum() * v),
        "processor_top_contacts_off_the_reference_surface_mm2": float((touch & ~near_ref).sum() * a),
    }
    np.save(private / "pyslm-envelope.npy", proc)
    # the rule's own kind, for the picture's colours: 1 plate, 2 part, 3 ends in air (processor only)
    record = {
        "schema": "935-cad-twin-support-build-processor/1", "date": time.strftime("%Y-%m-%d"),
        "scope": "supports for the print body prepared by PySLM's block support generator with its defaults at a 45 degree critical "
                 "angle, flange y+ on the plate, measured against the rule layout on the 0.25 mm occupancy grid by the same code. "
                 "An open research library, not the machine maker's build processor; geometry only",
        "plan_file": "params/" + Path(plan_file).name, "plan_sha256": sha256(Path(plan_file)),
        "occupancy_sha256": occupancy_sha, "rule_envelope_sha256": sha256(rule_dir / "support-envelope.npy"),
        "processor_run": {k: v for k, v in prep.items()},
        "voxelised": {"blocks": n, "inside_the_part_dropped_mm3": float(inside_part.sum() * v),
                      "at_or_below_the_plate_level_dropped_mm3": float(below_plate.sum() * v),
                      "kept_mm3": float(proc.sum() * v),
                      "blocks_one_by_one_mm3": float(one_by_one * v),
                      "one_by_one_against_the_block_meshes": float(one_by_one * v / max(prep["mesh_volume_mm3"], 1e-9) - 1.0),
                      "overlap_between_blocks_mm3": float(one_by_one * v - (proc.sum() + inside_part.sum() + below_plate.sum()) * v),
                      "union_against_the_block_meshes": float((proc.sum() + inside_part.sum() + below_plate.sum()) * v
                                                              / max(prep["mesh_volume_mm3"], 1e-9) - 1.0)},
        "plate_level_mm": plate_level * PITCH,
        "consistency_with_the_committed_rule_layout": consistency,
        "rule_layout": mine, "processor_layout": theirs, "regions": regions,
        "private_outputs": {"pyslm-envelope.npy": sha256(private / "pyslm-envelope.npy")},
        "gates": {"prepared_by_the_machine_makers_build_processor": False, "support_parameters_from_the_machine_maker": False,
                  "removal_judged_by_a_person": False, "build_file_written": False, "metal_print_authorized": False},
        "seconds": round(time.time() - started, 1), "peak_rss_gib": round(peak_rss_gib(), 2),
    }
    Path(out).write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps({k: record[k] for k in ("voxelised", "consistency_with_the_committed_rule_layout", "regions", "seconds")}, indent=1))


def diagnose(mesh_path, occ_dir, out) -> None:
    """Where the library's own region steps drop overhang before any projection (a reading of its code path).

    For each overhang region the generator would process: flattenSupportRegion, simplify, the outer edge inset
    and the minimum area, then the MultiPolygon branch, exactly as identifySupportRegions takes them.
    """

    import shapely
    import trimesh
    import pyslm
    import pyslm.support
    from pyslm.support import utils
    from pyslm.support.support import SupportStructure

    grid = json.loads((Path(occ_dir) / "occupancy-grid.json").read_text())
    raw = trimesh.load_mesh(mesh_path, process=False)
    mesh = trimesh.Trimesh(to_build_frame(np.asarray(raw.vertices), grid), np.asarray(raw.faces), process=True)
    mesh.apply_translation((0.0, 0.0, -float(mesh.vertices[:, 2].min())))
    part = pyslm.Part("print_body")
    part.setGeometry(mesh, fixGeometry=False, mergeVertices=False)
    part.dropToPlatform(0.0)
    gen = pyslm.support.GridBlockSupportGenerator()
    steps = {}
    sizes = []
    for sub in utils.getOverhangMesh(part, OVERHANG_DEG, True):
        projected = float(np.abs(sub.area_faces * sub.face_normals[:, 2]).sum())
        sizes.append(projected)
        flattened = None
        try:
            polygon = SupportStructure.flattenSupportRegion(sub)
        except Exception:  # noqa: BLE001 - the library catches the same error and skips the region
            key = "could not be flattened"
        else:
            flattened = float(polygon.area)
            inset = polygon.simplify(gen.simplifyPolygonFactor, preserve_topology=False).buffer(-gen.outerSupportEdgeGap)
            if inset is None or inset.area < gen.minimumAreaThreshold:
                key = "under the minimum area once inset"
            elif isinstance(inset, shapely.geometry.MultiPolygon):
                kept = [p for p in inset.geoms if (lambda t: t.is_closed and t.area > gen.minimumAreaThreshold)(
                    trimesh.load_path(p, process=False))]
                key = "split by the inset, a piece kept" if kept else "split by the inset, every piece refused as an open path"
            else:
                key = "kept for projection"
        row = steps.setdefault(key, {"regions": 0, "projected_area_mm2": 0.0, "largest_projected_mm2": 0.0,
                                     "flattened_area_mm2": 0.0})
        row["regions"] += 1
        row["projected_area_mm2"] += projected
        row["largest_projected_mm2"] = max(row["largest_projected_mm2"], projected)
        row["flattened_area_mm2"] += flattened or 0.0
    sizes = np.array(sizes)
    edges = [0.0, 0.5, 1.0, 5.0, 50.0, 1e9]
    rep = {"mesh_file": Path(mesh_path).name, "mesh_sha256": sha256(Path(mesh_path)), "library": installed_library(),
           "regions": len(sizes), "projected_area_mm2": float(sizes.sum()),
           "regions_by_projected_area_mm2": {f"{a:g} to {b:g}" if b < 1e9 else f"{a:g} and more": int(((sizes >= a) & (sizes < b)).sum())
                                             for a, b in zip(edges[:-1], edges[1:])},
           "steps": steps,
           "reading": "flattenSupportRegion keeps only the first polygon of a region's outline; the inset is "
                      "outerSupportEdgeGap; a MultiPolygon piece is loaded with trimesh.load_path(process=False), whose "
                      "entities trimesh 5.1.1 does not report closed, so the piece is refused"}
    Path(out).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: v for k, v in rep.items() if k != "library"}, indent=1))


def assemble(primary, sensitivity, plan_file, witness_file, out) -> None:
    """The committed record: the planned run in full, the unplanned 1.0 mm run as a sensitivity row."""

    primary, sensitivity = Path(primary), Path(sensitivity)
    record = json.loads((primary / "support-build-processor.json").read_text())
    assert record["plan_sha256"] == sha256(Path(plan_file))
    prep = record["processor_run"]
    record["witness_file"] = "params/" + Path(witness_file).name
    record["witness_sha256"] = sha256(Path(witness_file))
    record["private_outputs"].update({"pyslm-blocks.npz": prep["blocks_sha256"],
                                      "pyslm-prepare.json": sha256(primary / "pyslm-prepare.json")})
    record["diagnosis_of_the_dropped_overhang"] = json.loads((primary / "pyslm-diagnose.json").read_text())
    record["diagnosis_of_the_dropped_overhang"].pop("library", None)
    truss_file = primary / "pyslm-truss.json"
    record["truss_after_the_comparison"] = (json.loads(truss_file.read_text()) if truss_file.exists() else
                                           {"status": "not run"})
    record["truss_after_the_comparison"].pop("settings", None)
    other = json.loads((sensitivity / "support-build-processor.json").read_text())
    op = other["processor_layout"]
    record["sensitivity_not_in_the_plan"] = {
        "why": "the 1.0 mm surface of the same occupancy, run although the primary finished, to see how much the "
               "result depends on the tessellation the library reads its face normals from",
        "mesh_file": other["processor_run"]["mesh_file"], "mesh_sha256": other["processor_run"]["mesh_sha256"],
        "triangles": other["processor_run"]["triangles"],
        "library_state": other["processor_run"]["library"]["state"],
        "spline_fallback": other["processor_run"].get("fallback", "not needed: splineSimplificationFactor stayed at 20"),
        "log": other["processor_run"]["log"], "blocks": other["processor_run"]["blocks"],
        "block_mesh_volume_mm3": other["processor_run"]["mesh_volume_mm3"],
        "voxelised": other["voxelised"],
        "processor_layout": op, "regions": other["regions"],
        "blocks_sha256": other["processor_run"]["blocks_sha256"],
        "envelope_sha256": other["private_outputs"]["pyslm-envelope.npy"]}
    record["deviations_from_the_plan"] = [
        "declared fallback 1 applied: upstream PySLM raised its extrusion error on the print body (value array of shape "
        "(411,) against an index of (406,)); support.py was patched with the carrier's historical patch "
        "(process-20261016/pyslm-support-projection.patch, installed support.py sha256 " + PATCHED_SUPPORT_PY + ")",
        "declared fallback 2 applied on the 0.5 mm surface: the spline simplification raised \"MultiPolygon error please "
        "submit a bug report\"; the run was repeated with splineSimplificationFactor None",
        "not declared: release_canvases() processes Qt's events after each height map, because the 52nd canvas of a "
        "process fails under Xvfb and llvmpipe (witness G1); the library's code and its height maps are unchanged",
        "the consistency check of the supported area is made at the rule's own adjacency (tolerance 0): at the planned "
        "0.5 mm tolerance the rule layout reads 12,376.0 mm2 against its committed 12,375.875 mm2, two voxels more",
        "the 1.0 mm surface ran as a sensitivity although the primary finished; it does not replace the primary"]
    record["for_issue_706"] = {
        "counts_as_prepared_by_a_build_processor": False,
        "why": "PySLM is an open research library, not the machine maker's build processor, and on this body with its "
               f"defaults it supports {record['processor_layout']['supported_share_of_the_reference_surface']:.1%} of the overhang "
               f"the rule layout starts from ({op['supported_share_of_the_reference_surface']:.1%} on the 1.0 mm surface)",
        "the_missing_tool": "the machine maker's build processor for the selected machine, or a commercial preparation "
                            "suite with a build processor for it (for example Materialise Magics): none is installed or "
                            "licensed here",
        "what_it_would_add": ["support templates and exposure parameters qualified by the maker for the alloy and the machine",
                              "a machine build file, with scan order and support exposure",
                              "support types beyond blocks (cones, lattices, contour and gusset supports) chosen per surface",
                              "checks the library does not make: recoater collision, powder removal, thermal load on supports"]}
    Path(out).write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps({"bytes": Path(out).stat().st_size}))


def truss(private, out) -> None:
    """PySLM's grid truss for every block, with the generator's defaults; outside the comparison."""

    import pyslm
    import pyslm.support
    import trimesh

    from pyslm.support.support import BlockSupportBase, BlockSupportGenerator

    private = Path(private)
    prep = json.loads((private / "pyslm-prepare.json").read_text())
    data = np.load(private / prep["blocks_file"])
    n = len([k for k in data.files if k.startswith("v")])
    saved = [BlockSupportBase(supportObject=None, supportVolume=trimesh.Trimesh(data[f"v{q:05d}"], data[f"f{q:05d}"], process=False),
                              supportSurface=None, intersectsPart=bool(data["intersects"][q])) for q in range(n)]
    # The generator wraps the saved blocks exactly as it wraps its own, with the settings transfer of this
    # revision (which hands the teeth height to the top length).
    gen = pyslm.support.GridBlockSupportGenerator()
    original = BlockSupportGenerator.identifySupportRegions
    BlockSupportGenerator.identifySupportRegions = lambda self, part, angle, find=True: saved
    try:
        grid_blocks = gen.identifySupportRegions(None, OVERHANG_DEG, True)
    finally:
        BlockSupportGenerator.identifySupportRegions = original
    started = time.time()
    done, failed, area, triangles = 0, [], 0.0, 0
    for q, block in enumerate(grid_blocks):
        if block.supportVolume.volume <= 0.0:
            failed.append({"block": q, "error": "empty support volume"})
            continue
        try:
            geom = block.geometry()
            area += float(geom.area)
            triangles += int(len(geom.faces))
            done += 1
        except Exception as exc:  # noqa: BLE001 - every failure is recorded
            failed.append({"block": q, "volume_mm3": float(block.supportVolume.volume), "error": repr(exc)[:300]})
        print(q, done, len(failed), round(time.time() - started), flush=True)
    rep = {"blocks": n, "finished": done, "failed": failed, "truss_surface_area_mm2": area, "truss_triangles": triangles,
           "settings": generator_settings(gen), "seconds": round(time.time() - started, 1), "peak_rss_gib": round(peak_rss_gib(), 2)}
    Path(out).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: v for k, v in rep.items() if k != "failed"}, indent=1))


if __name__ == "__main__":
    {"witness": witness, "prepare": prepare, "compare": compare, "diagnose": diagnose, "truss": truss,
     "assemble": assemble}[sys.argv[1]](*sys.argv[2:])
