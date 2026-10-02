// v2: fast linear-deflection STEP conversion (optimal mode was intractable at 70k facets).
import os, sys, json, time

root = os.environ.get("M64_EXPORT_DIR", ".")
stl = os.path.join(root, "m64-cylinder-head-decimated.stl")
step = os.path.join(root, "m64-cylinder-head.step")
report = os.path.join(root, "conversion-report.json")

t0 = time.time()
import Mesh, MeshPart, Part

mesh = Mesh.Mesh(stl)
stats0 = {"facets": mesh.CountFacets, "solid": mesh.isSolid(), "self_intersect": mesh.hasSelfIntersections()}
shape = MeshPart.shapeFromMesh(mesh, {"MaxLinearDeflection": 0.05, "RunInParallel": True})
Part.export([shape], step)

out = dict(stats0)
out.update({
    "faces": len(shape.Faces),
    "solids": len(shape.Solids),
    "shells": len(shape.Shells),
    "valid": shape.isValid(),
    "volume_mm3": shape.Volume,
    "conversion_seconds": round(time.time() - t0, 1),
    "tool": "FreeCAD MeshPart.shapeFromMesh linear-deflection 0.05mm (no removeSplitter: optimal mode intractable)",
    "input": "m64-cylinder-head-decimated.stl (PicoGK station export, voxel 2mm, decimated 70868->~4000 faces)",
})
with open(report, "w") as f:
    json.dump(out, f, indent=1)
print("FREECAD_STEP_OK", out["faces"], "faces", out["solids"], "solids")
