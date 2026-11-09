"""T4: OpenUSD stage of the twin with observed / inferred / hardware layers.

  /Head935                    default prim, Z-up, millimetres (metersPerUnit 0.001)
    BareHead                  twin surface; per-face displayColor: observed grey,
                              inferred orange (farther than SUPPORT_MM from the scan)
    Hardware/Stud_NN          analytic cylinders from the fitted studs (blue)
    Datums                    frame, deck, register and flange data as customData

The observed/inferred colouring is a visual aid; the evidence is the
independent scorecard. Validated with the OpenUSD 26 UsdValidation framework (all registered validators).

Usage: export_usd.py PRIVATE_DIR PARAMS_DIR SURFACE.stl OUT.usda
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

SUPPORT_MM = 0.2


def classify(tv, tf, bare_v, bare_f):
    import warp as wp

    wp.config.quiet = True
    wp.init()

    @wp.kernel
    def dist(mesh: wp.uint64, pts: wp.array(dtype=wp.vec3), out: wp.array(dtype=float)):
        i = wp.tid()
        q = wp.mesh_query_point_no_sign(mesh, pts[i], 1.0e6)
        out[i] = wp.length(pts[i] - wp.mesh_eval_position(mesh, q.face, q.u, q.v))

    used = np.unique(bare_f)
    remap = -np.ones(len(bare_v), dtype=np.int64)
    remap[used] = np.arange(len(used))
    m = wp.Mesh(points=wp.array(bare_v[used].astype(np.float32), dtype=wp.vec3),
                indices=wp.array(remap[bare_f].astype(np.int32).ravel(), dtype=wp.int32))
    cen = tv[tf].mean(axis=1)
    out = wp.zeros(len(cen), dtype=float)
    wp.launch(dist, dim=len(cen), inputs=[m.id, wp.array(cen.astype(np.float32), dtype=wp.vec3), out])
    return out.numpy()


def main(private, params, surface, out):
    import trimesh
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdValidation, Vt

    private, params = Path(private), Path(params)
    frame = json.loads((params / "frame.json").read_text())
    hyp = json.loads((params.parent / "hypotheses.json").read_text())
    occ = json.loads((params / "occupancy-summary.json").read_text())
    colours = hyp["display_colours"]
    mesh = trimesh.load(surface, process=False, force="mesh")
    tv, tf = np.asarray(mesh.vertices), np.asarray(mesh.faces)
    bare = np.load(private / "bare-scan-twin.npz")
    d = classify(tv, tf, bare["v"], bare["f"])
    inferred = d > SUPPORT_MM

    stage = Usd.Stage.CreateNew(str(out))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 0.001)
    root = UsdGeom.Xform.Define(stage, "/Head935")
    stage.SetDefaultPrim(root.GetPrim())
    Usd.ModelAPI(root.GetPrim()).SetKind("component")
    root.GetPrim().SetCustomDataByKey("porscheparts:twin", "935-cylinder-head-cad-twin")
    root.GetPrim().SetCustomDataByKey("porscheparts:scan_sha256", frame["scan_sha256"])
    root.GetPrim().SetCustomDataByKey("porscheparts:hypotheses", hyp["register_id"])
    root.GetPrim().SetCustomDataByKey("porscheparts:claims", "study twin; not measured, not functional, not released")

    m = UsdGeom.Mesh.Define(stage, "/Head935/BareHead")
    m.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(tv.astype(np.float32)))
    m.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(tf), 3, dtype=np.int32)))
    m.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(tf.astype(np.int32).ravel()))
    m.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    m.CreateExtentAttr([Gf.Vec3f(*tv.min(axis=0)), Gf.Vec3f(*tv.max(axis=0))])
    col = np.where(inferred[:, None], np.array(colours["inferred_closure"]), np.array(colours["observed"]))
    pv = UsdGeom.PrimvarsAPI(m).CreatePrimvar("displayColor", Sdf.ValueTypeNames.Color3fArray, UsdGeom.Tokens.uniform)
    pv.Set(Vt.Vec3fArray.FromNumpy(col.astype(np.float32)))
    m.GetPrim().SetCustomDataByKey("porscheparts:inferred_area_share",
                                   float(mesh.area_faces[inferred].sum() / mesh.area))

    UsdGeom.Scope.Define(stage, "/Head935/Hardware")
    n = 0
    for s in occ["studs"]:
        if not s["accepted"]:
            continue
        n += 1
        ax = np.array(s["axis"], dtype=float)
        ax /= np.linalg.norm(ax)
        c0 = np.array(s["point_on_axis"], dtype=float)
        t0 = s.get("seat_level_along_axis", 0.0)
        length = s["protrusion_mm"]
        centre = c0 + (t0 + length / 2) * ax
        cyl = UsdGeom.Cylinder.Define(stage, f"/Head935/Hardware/Stud_{n:02d}")
        cyl.CreateRadiusAttr(float(s["radius_mm"]))
        cyl.CreateHeightAttr(float(length))
        cyl.CreateAxisAttr(UsdGeom.Tokens.z)
        rot = Gf.Rotation(Gf.Vec3d(0, 0, 1), Gf.Vec3d(*ax))
        xf = UsdGeom.Xformable(cyl)
        xf.AddTranslateOp().Set(Gf.Vec3d(*centre))
        xf.AddOrientOp().Set(Gf.Quatf(rot.GetQuat()))
        cyl.CreateDisplayColorAttr([Gf.Vec3f(*colours["hardware"])])
        cyl.GetPrim().SetCustomDataByKey("porscheparts:provenance", "fitted to scan facets; thread form not modelled")

    datums = UsdGeom.Xform.Define(stage, "/Head935/Datums")
    datums.GetPrim().SetCustomDataByKey("porscheparts:frame_definition", frame["definition"])
    datums.GetPrim().SetCustomDataByKey("porscheparts:levels_twin_mm", json.dumps(frame["levels_twin"]))
    datums.GetPrim().SetCustomDataByKey("porscheparts:rings", json.dumps(
        [{k: r[k] for k in ("name", "diameter_mm", "depth_below_deck_mm")} for r in frame["rings"]]))
    stage.GetRootLayer().Save()

    # OpenUSD 26 validation framework (replaces the removed ComplianceChecker).
    registry = UsdValidation.ValidationRegistry()
    validators = registry.GetOrLoadAllValidators()
    errors = UsdValidation.ValidationContext(validators).Validate(Usd.Stage.Open(str(out)))
    by_type = {}
    for e in errors:
        by_type.setdefault(str(e.GetType()).split(".")[-1], []).append(f"{e.GetName()}: {e.GetMessage()[:160]}")
    report = {
        "schema": "935-cad-twin-usd/1",
        "surface_triangles": int(len(tf)),
        "studs": n,
        "inferred_face_share": round(float(inferred.mean()), 5),
        "inferred_area_share": round(float(mesh.area_faces[inferred].sum() / mesh.area), 5),
        "validators_run": len(validators),
        "validation_findings_by_type": {k: v[:20] for k, v in by_type.items()},
        "validation_error_count": len(by_type.get("Error", [])),
        "usd_version": ".".join(map(str, Usd.GetVersion())),
        "pending": "NVIDIA usd-convert-cad STEP->USD and omni.asset_validator need the 10 GB SimReady image "
                   "(not pulled: insufficient free disk on this host; see README)",
    }
    (params / "usd-summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:5])
