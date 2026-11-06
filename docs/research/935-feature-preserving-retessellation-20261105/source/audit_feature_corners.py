"""Locate acute fixed-feature sectors that force poor planar fan triangles.

The bound is conditional on retaining the existing planar sector; it is not
an impossibility claim for arbitrary three-dimensional surface changes.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("parent","features","feature-verifier","output"):
        parser.add_argument("--"+name,type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(mode=0o700,exist_ok=False);started=time.monotonic()
    assert sha(args.parent)=="7adc8f931feac78eb6298e1415c8d49b7a92bced5dde5dbcc6bc3afd2e9e947f"
    def best_quality(angle):return np.sqrt(3)*np.sin(angle)/(2-np.cos(angle))
    assert abs(best_quality(np.pi/3)-1)<1e-14
    # At fixed angle the normalized quality is maximal for equal adjacent lengths.
    for angle in (.0001,.01,.2,np.pi/3):
        ratio=np.geomspace(.01,100,401)
        actual=np.sqrt(3)*ratio*np.sin(angle)/(ratio**2+1-ratio*np.cos(angle))
        assert np.all(actual<=best_quality(angle)+1e-14)
    spec=importlib.util.spec_from_file_location("fixed_source_measures",args.feature_verifier)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    with np.load(args.parent,allow_pickle=False) as data:v,f=data["vertices"],data["triangles"]
    required=np.load(args.features,allow_pickle=False)
    q,_=helper.measure(v,f);ids=np.flatnonzero(q**(2/3)<.01);faces=f[ids]
    keys=np.sort(faces[:,[[0,1],[1,2],[2,0]]],axis=2)
    keys=keys[:,:,0]*len(v)+keys[:,:,1]
    marked=np.isin(keys,required)
    records=[]
    for i,face in enumerate(faces):
        for corner in range(3):
            # Edge corner->next has index corner; previous->corner has index corner-1.
            if not (marked[i,corner] and marked[i,(corner-1)%3]):continue
            a=v[face[(corner+1)%3]]-v[face[corner]]
            b=v[face[(corner-1)%3]]-v[face[corner]]
            angle=float(np.arctan2(np.linalg.norm(np.cross(a,b)),np.dot(a,b)))
            assert angle>0
            if angle<np.pi/3:
                maximum=best_quality(angle)**(2/3)
                if maximum<.01:records.append((int(ids[i]),int(face[corner]),angle,float(maximum)))
    records=np.asarray(records,float).reshape(-1,4)
    np.savez_compressed(args.output/"private-corner-sectors.npz",records=records)
    result={"source_sha256":sha(Path(__file__)),"parent_sha256":sha(args.parent),
            "required_feature_keys_sha256":sha(args.features),"forced_faces":len(ids),
            "required_feature_edges_per_forced_face":{str(k):int((marked.sum(axis=1)==k).sum()) for k in range(4)},
            "acute_fixed_feature_sectors_forcing_subthreshold_fan":len(records),
            "distinct_affected_faces":len(np.unique(records[:,0])),
            "distinct_corner_vertices":len(np.unique(records[:,1])),
            "minimum_sector_angle_degrees":float(np.rad2deg(records[:,2].min())) if len(records) else None,
            "minimum_best_incident_tet_mean_ratio_ceiling":float(records[:,3].min()) if len(records) else None,
            "bound":"For an acute planar sector angle alpha below 60 degrees, every triangle fan within that sector contains a corner triangle whose quality is at most sqrt(3)*sin(alpha)/(2-cos(alpha)); an incident tet has mean ratio at most q^(2/3)",
            "scope":"Existing planar sector bounded by the two required straight edges, with a fan at their unchanged common vertex. Does not rule out nonplanar surface changes or a different, separately justified solver admission criterion.",
            "controls":{"equilateral_maximum":True,"fixed_angle_length_ratio_bounds":True},
            "geometry_modified":False,"physics_admitted":False,"manufacturing_qualified":False,
            "seconds":time.monotonic()-started}
    (args.output/"report.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result),flush=True)


if __name__=="__main__":main()
