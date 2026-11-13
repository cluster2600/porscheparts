"""Independent geometry check of a stage converted by simready_convert.py.

It shares no code with the producer and trusts neither the converter nor the
values the converter authored about itself (extents, normals):

  STEP side  build123d / OCCT re-reads the STEP: exact-solid volume, surface
             area and optimal bounding box, in the length unit the STEP file
             declares (read from its text, not assumed).
  USD side   plain `usd-core` re-opens the stage. Every Mesh is taken from its
             points, composed to world space through its transform stack,
             scaled by the authored metersPerUnit and mapped from the authored
             upAxis to the Z-up STEP frame. Volume is the divergence-theorem
             sum over the triangles, which is an enclosed volume only if the
             mesh is closed and consistently wound. That is tested on the
             topology welded by position: no edge used once or more than
             twice, every shared edge traversed once each way. An edge used
             once is accepted only if vertices of the facing boundary lie on
             it within the weld tolerance (a T-junction of zero width), and
             is reported as a non-conforming tessellation.

The gates are screens for a unit, axis or gross conversion error (a factor
1000 or 25.4, swapped extents, a missing body). They are not an accuracy
claim for the tessellation and say nothing about the scanned specimen.

The result is merged as `independent_check` into the entry of SUMMARY.json
whose recorded STEP and stage SHA-256 both match the files given here; a
mismatch is refused, so a check can never attach to another conversion.

Interpreter: the twin venv (build123d, usd-core, numpy, scipy). No NVIDIA package.

Usage: simready_check.py STEP STAGE.usdc SUMMARY.json
                         [--bbox-tol-mm 0.1] [--volume-rel-tol 0.01]

Exit status: 0 within the gates, 1 outside them or not checkable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import numpy as np

MM = 0.001  # metres
WELD_MM = 1.0e-4
INTEGRATION_EPS = 1.0e-7


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def step_entities(path: Path):
    """Entities of a STEP file, whitespace removed and upper-cased, streamed."""
    pending = ""
    with path.open("r", errors="replace") as stream:
        for block in iter(lambda: stream.read(1 << 20), ""):
            *complete, pending = (pending + block).split(";")
            for entity in complete:
                if "UNIT" in entity.upper():
                    yield re.sub(r"\s+", "", entity).upper()


def step_length_unit(path: Path) -> str:
    """Length unit declared in the STEP text; 'unknown' if not exactly one."""
    units = set()
    for entity in step_entities(path):
        if "LENGTH_UNIT()" not in entity:
            continue
        if "CONVERSION_BASED_UNIT" in entity:
            name = re.search(r"CONVERSION_BASED_UNIT\('([^']*)'", entity)
            units.add(name.group(1).lower() if name else "conversion_based")
        elif "SI_UNIT(.MILLI.,.METRE.)" in entity:
            units.add("millimetre")
        elif "SI_UNIT($,.METRE.)" in entity:
            units.add("metre")
        else:
            units.add("other_si")
    return units.pop() if len(units) == 1 else "unknown"


def step_reference(path: Path) -> dict:
    """Exact-solid quantities from OCCT. import_step returns millimetres.

    Volume and area use the adaptive integration of BRepGProp with an explicit
    relative tolerance. The default integration behind build123d's `.volume`
    is not accurate enough to judge a tessellation: measured on the two port
    lofts it is off by +0.17% and -0.21%, the size of the difference under
    test. Its value is kept beside the adaptive one so the gap stays visible.
    """
    from build123d import import_step
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps

    shape = import_step(str(path))
    solids = shape.solids()
    volume, volume_error = 0.0, 0.0
    for solid in solids:
        properties = GProp_GProps()
        volume_error = max(volume_error, abs(BRepGProp.VolumeProperties_s(
            solid.wrapped, properties, INTEGRATION_EPS, False, False)))
        volume += properties.Mass()
    properties = GProp_GProps()
    area_error = abs(BRepGProp.SurfaceProperties_s(shape.wrapped, properties, INTEGRATION_EPS, False))
    box = shape.bounding_box()
    return {
        "solids": len(solids),
        "faces": len(shape.faces()),
        "valid": bool(shape.is_valid),
        "integration_relative_tolerance": INTEGRATION_EPS,
        "volume_mm3": float(volume),
        "volume_integration_error_reported": float(f"{volume_error:.1e}"),
        "volume_default_integration_mm3": float(sum(s.volume for s in solids)),
        "area_mm2": float(properties.Mass()),
        "area_integration_error_reported": float(f"{area_error:.1e}"),
        "bbox_min_mm": [float(v) for v in box.min],
        "bbox_max_mm": [float(v) for v in box.max],
    }


def axis_to_step_frame(up_axis: str) -> np.ndarray:
    """Row-vector matrix taking stage coordinates to the Z-up STEP frame."""
    if up_axis == "Z":
        return np.eye(3)
    if up_axis == "Y":
        # A Z-up model shown Y-up is turned -90 degrees about X:
        # (x, y, z)_Z -> (x, z, -y)_Y. This is its inverse.
        return np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, -1.0, 0.0]])
    raise ValueError(f"unsupported upAxis {up_axis!r}")


def split_t_junctions(positions: np.ndarray, free: np.ndarray) -> tuple[int, int, float]:
    """Split each open edge at the boundary vertices lying on it.

    Returns the edges still unmatched afterwards, the vertex-on-edge
    incidences used, and the largest vertex-to-edge distance accepted.
    """
    from scipy.spatial import cKDTree

    boundary = np.unique(free)
    tree = cKDTree(positions[boundary])
    pieces, incidences, gap = [], 0, 0.0
    for a, b in free:
        start, span = positions[a], positions[b] - positions[a]
        length2 = float(span @ span)
        near = boundary[tree.query_ball_point(start + span / 2, np.sqrt(length2) / 2 + WELD_MM)]
        near = near[(near != a) & (near != b)]
        chain = [a, b]
        if len(near):
            t = ((positions[near] - start) @ span) / length2
            distance = np.linalg.norm(positions[near] - start - np.outer(t, span), axis=1)
            on = (t > 0) & (t < 1) & (distance <= WELD_MM)
            if on.any():
                chain = [a, *near[on][np.argsort(t[on])], b]
                incidences += int(on.sum())
                gap = max(gap, float(distance[on].max()))
        pieces.extend(zip(chain[:-1], chain[1:]))
    _, uses = np.unique(np.sort(np.array(pieces), axis=1), axis=0, return_counts=True)
    return int((uses != 2).sum()), incidences, gap


def pinched_vertices(tri: np.ndarray, edge_of_half: np.ndarray, uses: np.ndarray) -> int:
    """Welded vertices whose triangles form more than one fan."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    n = len(tri)
    order = np.argsort(edge_of_half, kind="stable")
    paired = order[uses[edge_of_half[order]] == 2]
    first, second = paired[0::2], paired[1::2]
    # Half-edge j lies in triangle j % n and runs from corner j // n to the next.
    corner = lambda half, end: 3 * (half % n) + (half // n + end) % 3
    vertex = tri.reshape(-1)
    links = []
    for end in (0, 1):
        mine = corner(first, end)
        same = vertex[corner(second, 0)] == vertex[mine]
        links.append(np.stack([mine, np.where(same, corner(second, 0), corner(second, 1))]))
    rows, cols = np.concatenate(links, axis=1)
    _, label = connected_components(coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(3 * n, 3 * n)),
                                    directed=False)
    fans = np.unique(np.stack([vertex, label], axis=1), axis=0)[:, 0]
    return int((np.bincount(fans) > 1).sum())


def stage_measure(path: Path) -> dict:
    from pxr import Usd, UsdGeom

    stage = Usd.Stage.Open(str(path))
    if stage is None:
        raise RuntimeError("stage cannot be opened")
    if not stage.HasAuthoredMetadata("metersPerUnit") or not stage.HasAuthoredMetadata("upAxis"):
        raise RuntimeError("metersPerUnit or upAxis is not authored; refusing to assume a fallback")
    meters_per_unit = float(UsdGeom.GetStageMetersPerUnit(stage))
    up_axis = str(UsdGeom.GetStageUpAxis(stage))
    to_mm = meters_per_unit / MM
    frame = axis_to_step_frame(up_axis)
    cache = UsdGeom.XformCache(Usd.TimeCode.Default())

    lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
    volume = area = open_length = t_gap = 0.0
    meshes = triangles = open_edges = non_manifold_edges = degenerate = 0
    miswound_edges = unmatched_edges = t_incidences = pinched = 0
    for prim in Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies()):
        if not prim.IsA(UsdGeom.Mesh):
            continue
        mesh = UsdGeom.Mesh(prim)
        points = np.asarray(mesh.GetPointsAttr().Get(), dtype=np.float64)
        counts = np.asarray(mesh.GetFaceVertexCountsAttr().Get(), dtype=np.int64)
        indices = np.asarray(mesh.GetFaceVertexIndicesAttr().Get(), dtype=np.int64)
        if len(points) == 0 or len(counts) == 0:
            continue
        matrix = np.array(cache.GetLocalToWorldTransform(prim), dtype=np.float64)  # p' = p M
        world = (points @ matrix[:3, :3] + matrix[3, :3]) @ frame * to_mm
        # Fan triangulation of each polygon.
        starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
        tris = []
        for k in range(1, int(counts.max()) - 1):
            sel = counts > k + 1
            tris.append(np.stack([indices[starts[sel]], indices[starts[sel] + k],
                                  indices[starts[sel] + k + 1]], axis=1))
        tri = np.concatenate(tris)
        flip = (mesh.GetOrientationAttr().Get() == UsdGeom.Tokens.leftHanded) \
            != (np.linalg.det(matrix[:3, :3] @ frame) < 0)
        a, b, c = (world[tri[:, i]] for i in range(3))
        centre = world.mean(axis=0)
        signed = float(np.einsum("ij,ij->i", a - centre, np.cross(b - centre, c - centre)).sum() / 6.0)
        volume += -signed if flip else signed
        tri_area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
        area += float(tri_area.sum())
        degenerate += int((tri_area < 1.0e-12).sum())
        lo, hi = np.minimum(lo, world.min(axis=0)), np.maximum(hi, world.max(axis=0))
        meshes += 1
        triangles += len(tri)
        # Topology of this mesh after welding coincident points.
        _, first, welded = np.unique(np.round(world / WELD_MM).astype(np.int64), axis=0,
                                     return_index=True, return_inverse=True)
        positions = world[first]
        wt = welded.reshape(-1)[tri]
        wt = wt[(wt[:, 0] != wt[:, 1]) & (wt[:, 1] != wt[:, 2]) & (wt[:, 2] != wt[:, 0])]
        half = np.concatenate([wt[:, [0, 1]], wt[:, [1, 2]], wt[:, [2, 0]]])  # directed
        unique_edges, edge_of_half, uses = np.unique(np.sort(half, axis=1), axis=0,
                                                     return_inverse=True, return_counts=True)
        edge_of_half = edge_of_half.reshape(-1)
        ascending = np.bincount(edge_of_half, weights=half[:, 0] < half[:, 1], minlength=len(uses))
        miswound_edges += int(((uses == 2) & (ascending != 1)).sum())
        non_manifold_edges += int((uses > 2).sum())
        pinched += pinched_vertices(wt, edge_of_half, uses)
        free = unique_edges[uses == 1]
        if len(free):
            open_edges += len(free)
            open_length += float(np.linalg.norm(positions[free[:, 0]] - positions[free[:, 1]], axis=1).sum())
            left, used, gap = split_t_junctions(positions, free)
            unmatched_edges += left
            t_incidences += used
            t_gap = max(t_gap, gap)
    if meshes == 0:
        raise RuntimeError("stage holds no mesh")
    return {
        "openusd": ".".join(map(str, Usd.GetVersion())),
        "meters_per_unit_authored": meters_per_unit,
        "up_axis_authored": up_axis,
        "scale_to_mm_applied": to_mm,
        "axis_mapping_applied": "identity (stage is Z-up like the STEP)" if up_axis == "Z"
                                else "(x, y, z) -> (x, -z, y)",
        "meshes": meshes,
        "triangles": triangles,
        "degenerate_triangles": degenerate,
        "weld_tolerance_mm": WELD_MM,
        "open_edges_after_weld": open_edges,
        "open_edge_length_mm": open_length,
        "t_junction_vertices_on_open_edges": t_incidences,
        "t_junction_gap_max_mm": t_gap,
        "open_edges_after_t_junction_split": unmatched_edges,
        "miswound_edges_after_weld": miswound_edges,
        "pinched_vertices_after_weld": pinched,
        "conforming_as_converted": open_edges == 0,
        "non_manifold_edges_after_weld": non_manifold_edges,
        "encloses_a_volume": unmatched_edges == 0 and non_manifold_edges == 0 and miswound_edges == 0,
        "volume_mm3": volume,
        "area_mm2": area,
        "bbox_min_mm": lo.tolist(),
        "bbox_max_mm": hi.tolist(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("step", type=Path)
    parser.add_argument("stage", type=Path)
    parser.add_argument("summary", type=Path)
    parser.add_argument("--bbox-tol-mm", type=float, default=0.1)
    parser.add_argument("--volume-rel-tol", type=float, default=0.01)
    args = parser.parse_args(argv)
    for path in (args.step, args.stage, args.summary):
        if not path.is_file():
            parser.error(f"not a file: {path}")

    started = time.monotonic()
    summary = json.loads(args.summary.read_text())
    step_hash, stage_hash = sha256(args.step), sha256(args.stage)
    entries = [e for e in summary.get("inputs", [])
               if e.get("sha256") == step_hash and e.get("conversion", {}).get("output_sha256") == stage_hash]
    if len(entries) != 1:
        print(f"refused: {args.summary.name} has {len(entries)} entry for this STEP and stage pair", file=sys.stderr)
        return 1

    unit = step_length_unit(args.step)
    check: dict = {"step_sha256": step_hash, "stage_sha256": stage_hash,
                   "step_length_unit_declared": unit,
                   "gates": {"bbox_corner_mm": args.bbox_tol_mm, "volume_relative": args.volume_rel_tol,
                             "encloses_a_volume": True, "step_solid_valid": True,
                             "meaning": "screen for unit, axis or gross conversion errors; not a tessellation accuracy claim"}}
    try:
        if unit != "millimetre":
            raise RuntimeError(f"STEP length unit is {unit!r}; this check compares millimetres only")
        from importlib.metadata import version

        check["tools"] = {"build123d": version("build123d"), "numpy": np.__version__}
        ref = step_reference(args.step)
        usd = stage_measure(args.stage)
        check["tools"]["openusd"] = usd.pop("openusd")
        corner = np.abs(np.array([usd["bbox_min_mm"], usd["bbox_max_mm"]])
                        - np.array([ref["bbox_min_mm"], ref["bbox_max_mm"]]))
        extent = np.array(ref["bbox_max_mm"]) - np.array(ref["bbox_min_mm"])
        volume_rel = (usd["volume_mm3"] - ref["volume_mm3"]) / ref["volume_mm3"]
        area_rel = (usd["area_mm2"] - ref["area_mm2"]) / ref["area_mm2"]
        # Four decimals for millimetres; small tolerances and errors keep their magnitude.
        number = lambda v: float(f"{v:.2e}") if 0 < abs(v) < 1.0e-3 else round(v, 4)
        rounded = lambda d: {k: ([number(x) for x in v] if isinstance(v, list)
                                 else number(v) if isinstance(v, float) else v) for k, v in d.items()}
        check.update(
            step=rounded(ref), stage=rounded(usd),
            bbox_corner_difference_mm=[[round(float(v), 5) for v in row] for row in corner],
            bbox_corner_difference_max_mm=round(float(corner.max()), 5),
            bbox_corner_difference_max_relative_to_extent=float(f"{(corner / extent).max():.3e}"),
            volume_relative_difference=float(f"{volume_rel:.3e}"),
            area_relative_difference=float(f"{area_rel:.3e}"),
        )
        failures = []
        if not ref["valid"]:
            failures.append("STEP solid is not valid for OCCT")
        if not usd["encloses_a_volume"]:
            failures.append(
                f"mesh does not enclose a volume: {usd['open_edges_after_t_junction_split']} open edges "
                f"left after splitting T-junctions, {usd['non_manifold_edges_after_weld']} non-manifold "
                f"and {usd['miswound_edges_after_weld']} miswound edges")
        if corner.max() > args.bbox_tol_mm:
            failures.append("bounding box corner outside the gate")
        if abs(volume_rel) > args.volume_rel_tol:
            failures.append("volume outside the gate")
        # Reported, not gated: defects that leave the enclosed volume defined.
        observations = []
        if not usd["conforming_as_converted"]:
            observations.append(
                f"non-conforming tessellation: {usd['open_edges_after_weld']} edges are used once and "
                f"close only through {usd['t_junction_vertices_on_open_edges']} T-junction vertices "
                f"(largest gap {usd['t_junction_gap_max_mm']:.1e} mm)")
        if usd["pinched_vertices_after_weld"]:
            observations.append(f"{usd['pinched_vertices_after_weld']} welded vertices carry more than one fan")
        check["observations"] = observations
        check["failures"] = failures
        check["passed"] = not failures
    except Exception as exc:
        check["passed"] = False
        check["failures"] = [f"{type(exc).__name__}: {exc}"[:240]]
    check["wall_seconds"] = round(time.monotonic() - started, 2)

    entries[0]["independent_check"] = check
    temporary = args.summary.with_name(f".{args.summary.name}.tmp")
    temporary.write_text(json.dumps(summary, indent=2) + "\n")
    os.replace(temporary, args.summary)
    print(json.dumps({k: check.get(k) for k in (
        "passed", "failures", "observations", "bbox_corner_difference_max_mm",
        "volume_relative_difference", "area_relative_difference")}, indent=1))
    return 0 if check["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
