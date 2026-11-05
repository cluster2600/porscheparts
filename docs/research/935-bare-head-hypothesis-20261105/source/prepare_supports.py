#!/usr/bin/env python3
"""Propose supports on the new revision; no old accessibility/support claim reused."""
import argparse
import json
from pathlib import Path

import igl
import numpy as np
from scipy import ndimage
import trimesh


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mesh",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    a.output.mkdir(exist_ok=False)
    report=json.loads(a.report.read_text())
    assert report["geometry_export_gate_passed"]
    from prepare_aligned import sha
    assert report["input_sha256"]==sha(a.mesh)
    with np.load(a.mesh,allow_pickle=False) as data:
        v,f=data["vertices"],data["triangles"]
    pitch=2.
    origin=np.floor((v.min(axis=0)-4)/pitch)*pitch
    size=np.ceil((v.max(axis=0)+4-origin)/pitch).astype(int)
    indices=np.indices(size).reshape(3,-1).T
    points=origin+(indices+.5)*pitch
    winding=igl.fast_winding_number(v,f,points)
    # Treat numerically uncertain near-surface centres as occupied, conservatively.
    occupied=(winding>.25).reshape(tuple(size))
    outside=~occupied
    seed=np.zeros_like(outside)
    seed[[0,-1],:,:]=True;seed[:,[0,-1],:]=True;seed[:,:,[0,-1]]=True
    air=ndimage.binary_propagation(seed&outside,mask=outside)
    np.savez_compressed(a.output/"private-exterior-grid.npz",origin=origin,pitch=pitch,occupied=occupied,exterior=air)
    mesh=trimesh.Trimesh(v,f,process=False)
    xs=np.arange(v[:,0].min()+2.137,v[:,0].max(),6.)
    ys=np.arange(v[:,1].min()+2.419,v[:,1].max(),6.)
    xy=np.array(np.meshgrid(xs,ys,indexing="ij")).reshape(2,-1).T
    origins=np.column_stack((xy,np.full(len(xy),5.)))
    directions=np.tile([0.,0.,1.],(len(xy),1))
    loc,ray,face=mesh.ray.intersects_location(origins,directions,multiple_hits=True)
    supports=[];odd=0;inaccessible=0;short=0
    for index in np.unique(ray):
        hits=np.flatnonzero(ray==index)
        hits=hits[np.argsort(loc[hits,2])]
        hits=hits[np.r_[True,np.diff(loc[hits,2])>1e-4]]
        if len(hits)%2:
            odd+=1
            continue
        previous=5.
        for entry,exit_index in zip(hits[::2],hits[1::2]):
            z=float(loc[entry,2])
            midpoint=np.array([*xy[index],(previous+z)/2])
            cell=np.floor((midpoint-origin)/pitch).astype(int)
            accessible=bool((cell<0).any() or (cell>=size).any() or air[tuple(cell)])
            if z-previous<2:
                short+=1
            elif not accessible:
                inaccessible+=1
            elif mesh.face_normals[face[entry],2]<-np.cos(np.pi/4):
                supports.append([float(xy[index,0]),float(xy[index,1]),previous-.25,z+.25])
            previous=float(loc[exit_index,2])
    assert supports
    result={"source_sha256":sha(a.mesh),"source_triangle_count":len(f),"support_columns":supports,
            "support_grid_mm":6.,"stem_radius_mm":1.2,"contact_tip_radius_mm":.5,"contact_overlap_mm":.25,
            "base_plate_mm":[float(v[:,0].max()+40),float(v[:,1].max()+10),5.],
            "coupon_centre_mm":[float(v[:,0].max()+20),20.,5.],"coupon_radius_mm":6.,"coupon_height_mm":20.,
            "odd_intersection_rays_rejected":odd,"air_intervals_rejected_as_inaccessible":inaccessible,
            "short_intervals_skipped":short,"exterior_grid_pitch_mm":pitch,
            "uncertain_winding_centres_treated_as_occupied":int(((winding>.25)&(winding<.75)).sum()),
            "assumptions":["Hypothetical bare-head blank and planar closures, with 0.75 mm provisional stock",
                           "Support dimensions, build orientation and coarse accessibility screen are provisional",
                           "Accessibility is not support-removal or powder-evacuation qualification",
                           "No machine-specific exposure or build calibration inferred"],
            "manufacturing_qualified":False,"engine_qualified":False}
    (a.output/"build-hypotheses.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"support_columns":len(supports),"odd_rays_rejected":odd,
                      "inaccessible_air_intervals_rejected":inaccessible,"manufacturing_qualified":False}))


if __name__=="__main__":
    main()
