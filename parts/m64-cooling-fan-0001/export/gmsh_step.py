#!/usr/bin/env python3
"""gmsh 4.15.2 (OpenCASCADE kernel): facet mesh -> BRep -> STEP, per part.

FreeCAD 1.1.3 headless on this host has no mesh->shape converter
(MeshPart.meshPartFromMesh absent), so the STEP route uses gmsh's built-in
OCC facet-surface parametrization. FreeCAD still checks the STEP afterwards.
"""
import json, sys
from pathlib import Path
import gmsh

HERE = Path(__file__).resolve().parent
DER = HERE / "derived"
report = {"tool": "gmsh 4.15.2 (OpenCASCADE kernel)", "parts": {}}

for part in ("rotor", "housing"):
    gmsh.initialize()
    gmsh.option.setNumber("Mesh.StlOneSolidPerSurface", 0)
    gmsh.open(str(DER / f"m64-{part}-manifold.stl"))
    gmsh.model.mesh.removeDuplicateNodes()
    entry = {"input": f"m64-{part}-manifold.stl"}
    ok = False
    for ang in (0.7, 0.5, 0.35):
        try:
            gmsh.model.mesh.classifySurfaces(ang, False)
            gmsh.model.mesh.createGeometry()
            ok = True
            entry["parametrization_angle_rad"] = ang
            break
        except Exception as e:
            entry.setdefault("parametrization_failures", []).append(f"{ang}: {e}")
    if not ok:
        report["parts"][part] = {**entry, "status": "failed"}
        Path(HERE / "conversion-report.json").write_text(json.dumps(report, indent=2))
        gmsh.finalize()
        sys.exit(2)
    surfaces = gmsh.model.getEntities(2)
    volumes = gmsh.model.getEntities(3)
    stepf = DER / f"m64-{part}.step"
    if stepf.exists():
        stepf.unlink()
    gmsh.write(str(stepf))
    entry.update({
        "status": "ok",
        "brep_surfaces": len(surfaces),
        "brep_volumes": len(volumes),
        "step_bytes": stepf.stat().st_size,
    })
    report["parts"][part] = entry
    gmsh.finalize()
    print(part, entry)

Path(HERE / "conversion-report.json").write_text(json.dumps(report, indent=2))
print("GMSH_STEP_OK")
