# FreeCAD headless: decimated watertight mesh -> single-assembly STEP + STL.
# Run: /usr/bin/freecadcmd this-script.py
import FreeCAD as App
import Part
import Mesh, MeshPart, Import, json, os, sys

here = os.path.dirname(os.path.abspath(__file__))
derived = os.path.join(here, "derived")
out = os.path.join(here, "m64-cooling-fan.step")

shapes = []
info = {}
for part in ("rotor", "housing"):
    m = Mesh.Mesh(os.path.join(derived, "m64-%s-decim.stl" % part))
    info[part] = {"mesh_faces": m.CountFacets, "mesh_solid": m.isSolid(),
                  "mesh_self_intersect": m.hasSelfIntersections()}
    shp = MeshPart.meshShape(m, 0.0, 0.0)  # linear facets, no optimisation
    if shp.isNull():
        print("FAIL: empty shape for", part); sys.exit(1)
    shp.fix(1e-7, 1e-7, 1e-7)
    info[part]["shape_faces"] = len(shp.Faces)
    info[part]["shape_valid"] = shp.isValid()
    info[part]["volume_mm3"] = shp.Volume
    info[part]["solids"] = len(shp.Solids)
    shapes.append(shp)

comp = Part.makeCompound(shapes)
doc = App.newDocument("fan")
obj = doc.addObject("Part::Feature", "M64Fan")
obj.Shape = comp
obj.Label = "m64-cooling-fan-0001-rotor+housing"
Import.export([obj], out)

# also re-export an assembly STL from the same compound for print review
stl = os.path.join(here, "m64-cooling-fan.stl")
MeshPart.meshFromShape(Shape=comp, LinearDeflection=0.25, AngularDeflection=0.35).write(stl)

with open(os.path.join(derived, "freecad-conversion-info.json"), "w") as f:
    json.dump(info, f, indent=2)
print("STEP_FACES_TOTAL", sum(v["shape_faces"] for v in info.values()))
print("CONVERT_OK")
