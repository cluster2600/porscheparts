# FreeCAD headless STEP conversion for the PicoGK head envelope STL.
# Design intent: planar-face merge (optimal) to keep the STEP face count sane.
import os, sys, json, time

stl = "/workspace/parts/m64-cylinder-head-0001/export/m64-cylinder-head.stl"
step = "/workspace/parts/m64-cylinder-head-0001/export/m64-cylinder-head.step"
report = "/workspace/parts/m64-cylinder-head-0001/export/freecad-convert-stats.json"

t0 = time.time()
import Mesh, MeshPart, Part

mesh = Mesh.Mesh(stl)
stats0 = {"facets": mesh.CountFacets, "solid": mesh.isSolid(), "self_intersect": mesh.hasSelfIntersections()}
shape = MeshPart.shapeFromMesh(mesh, {"MaxLinearDeflection": 0.001, "Optimal": True})
shape = shape.removeSplitter()
Part.export([shape], step)

out = dict(stats0)
out.update({
    "faces": len(shape.Faces),
    "solids": len(shape.Solids),
    "shells": len(shape.Shells),
    "valid": shape.isValid(),
    "volume_mm3": shape.Volume,
    "conversion_seconds": round(time.time() - t0, 1),
    "tool": "MeshPart.shapeFromMesh optimal + removeSplitter",
})
with open(report, "w") as f:
    json.dump(out, f, indent=1)
print("FREECAD_STEP_OK", out["faces"], "faces", out["solids"], "solids")
