#!/usr/bin/env python3
"""Export a hypothesis candidate only after byte-bound digital geometry admission."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from prepare_aligned import admit, module, sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("mesh","raw-report","contacts","contact-source","validator-source","output"):
        p.add_argument("--"+key,type=Path,required=True)
    a=p.parse_args()
    a.output.mkdir(exist_ok=False)
    v,f,report=admit(a.mesh,a.raw_report,a.contacts,a.contact_source,a.validator_source)
    helper=module(a.validator_source,"qualified_export_helper")
    path=a.output/"935-bare-head-hypothesis-build-mm.3mf"
    helper.write_3mf(path,v,f)
    dtype=np.dtype([("normal","<f4",(3,)),("vertices","<f4",(3,3)),("attribute","<u2")])
    maximum=0.
    stl=a.output/"935-bare-head-hypothesis-build-mm.stl"
    with stl.open("xb") as stream:
        stream.write(b"935 hypothesis; mm; physical/process qualification pending".ljust(80,b"\0"))
        stream.write(np.asarray([len(f)],dtype="<u4").tobytes())
        for start in range(0,len(f),100000):
            xyz=v[f[start:start+100000]]
            normal=np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0])
            normal/=np.linalg.norm(normal,axis=1)[:,None]
            rows=np.zeros(len(xyz),dtype=dtype)
            rows["normal"],rows["vertices"]=normal,xyz
            maximum=max(maximum,float(np.linalg.norm(rows["vertices"].astype(float)-xyz,axis=2).max()))
            stream.write(rows.tobytes())
    report.update({"source_sha256":sha(Path(__file__)),"three_mf_sha256":sha(path),
                   "three_mf_all_coordinates_indices_and_units_roundtrip_exact":True,
                   "stl_sha256":sha(stl),"stl_float32_max_corner_rounding_mm":maximum,
                   "stl_geometry_reimport_still_required":True,
                   "supports_and_machine_exposure_qualified":False,
                   "manufacturing_qualified":False,"engine_qualified":False})
    (a.output/"digital-geometry-and-export.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"three_mf_written_and_roundtrip_verified":True,"vertices":len(v),"triangles":len(f),
                      "stl_float32_max_corner_rounding_mm":maximum,"manufacturing_qualified":False}))


if __name__=="__main__":
    main()
