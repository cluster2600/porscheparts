"""Editable CAD software witness, independent of the voxel-derived coupons."""
import math
from pathlib import Path
import shutil
import sys

sys.path.append("/opt/freecad/usr/lib")
import FreeCAD as App
import Part

output = Path(sys.argv[1])
output.mkdir(parents=True, exist_ok=False)
document = App.newDocument("StationCADCoupon")
cylinder = document.addObject("Part::Cylinder", "ParametricCylinder")
cylinder.Label = "CAD software witness - radius 3 mm, height 20 mm"
cylinder.Radius = 3
cylinder.Height = 20
document.recompute()
expected = math.pi * 3**2 * 20
assert abs(cylinder.Shape.Volume - expected) < 1e-6
document.saveAs(str(output / "cad-coupon.FCStd"))
Part.export([cylinder], str(output / "cad-coupon.step"))
App.closeDocument(document.Name)
reopened = App.openDocument(str(output / "cad-coupon.FCStd"))
assert reopened.ParametricCylinder.Radius.Value == 3
assert reopened.ParametricCylinder.Height.Value == 20
assert abs(reopened.ParametricCylinder.Shape.Volume - expected) < 1e-6
step = Part.read(str(output / "cad-coupon.step"))
assert abs(step.Volume - expected) < 1e-6
App.closeDocument(reopened.Name)
shutil.copy2(__file__, output / "source.py")
print("EDITABLE_CAD_COUPON_PASS software_witness_only manufacturing_authorized=false")
