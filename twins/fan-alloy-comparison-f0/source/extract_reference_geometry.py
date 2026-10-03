#!/usr/bin/env python3
"""Extract only the public parametric rotor for mass/inertia and the closed-mesh witness."""
import argparse
import hashlib
import json
from pathlib import Path


def extract(source,output):
    import numpy as np
    import trimesh
    from pxr import Usd,UsdGeom
    stage=Usd.Stage.Open(str(source))
    if not stage or UsdGeom.GetStageMetersPerUnit(stage)!=1.:
        raise ValueError("Expected the existing metre-scale reference stage")
    rotor=UsdGeom.Mesh(stage.GetPrimAtPath("/World/Rotor"))
    if not rotor or not np.all(np.asarray(rotor.GetFaceVertexCountsAttr().Get())==3):
        raise ValueError("Expected the public reference triangular rotor mesh")
    model=trimesh.Trimesh(np.asarray(rotor.GetPointsAttr().Get())*1000.,
                         np.asarray(rotor.GetFaceVertexIndicesAttr().Get()).reshape(-1,3),process=True)
    if not model.is_watertight or not model.is_winding_consistent or model.volume<=0:
        raise ValueError("Mass requires a closed positive volume")
    output.mkdir(parents=True,exist_ok=False)
    model.export(output/"993-reference-review-mm.stl")
    np.savez_compressed(output/"993-reference-properties.npz",volume=model.volume,
                        inertia=model.moment_inertia,center=model.center_mass,bounds=model.bounds)
    # Match the executed witness: reopen the float32 STL rather than change serialization order.
    witness=trimesh.load(output/"993-reference-review-mm.stl",process=True)
    with (output/"993-witness.obj").open("w") as f:
        for v in witness.vertices:f.write("v "+" ".join(map(str,v))+"\n")
        for t in witness.faces:f.write("f "+" ".join(str(i+1) for i in t)+"\n")
    report={"source_usdz_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
            "purpose":"closed public 993 reference, not private 935 scan",
            "volume_mm3":float(model.volume),"triangles":len(model.faces),
            "units":"mm","rotation_axis":"parametric local Z, not a measured vehicle datum",
            "inertia_basis":"unit-density tensor about centre of mass, mm^5",
            "physical_validation":False,"manufacturing_authorized":False}
    (output/"geometry-extraction.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source",type=Path);parser.add_argument("output",type=Path)
    a=parser.parse_args();extract(a.source,a.output)
    print("Closed reference geometry extracted; no physical validation")
