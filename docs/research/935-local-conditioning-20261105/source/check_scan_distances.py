"""Measure full-denominator scan distances before and after numerical conditioning."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import igl
import numpy as np


def sha(path):
    with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()


def sample(vertices,faces,seed):
    area=np.empty(len(faces))
    for start in range(0,len(faces),100000):
        xyz=vertices[faces[start:start+100000]]
        area[start:start+len(xyz)]=np.linalg.norm(np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]),axis=1)/2
    rng=np.random.default_rng(seed);ids=rng.choice(len(faces),size=100000,p=area/area.sum())
    u=np.sqrt(rng.random(100000));w=rng.random(100000)
    bary=np.column_stack([1-u,u*(1-w),u*w])
    return (vertices[faces[ids]]*bary[:,:,None]).sum(axis=1),ids


def distance(points,vertices,faces):
    squared,_,_=igl.point_mesh_squared_distance(points,vertices,faces)
    return np.sqrt(np.maximum(squared,0))


def stats(values):
    return dict(zip(["p50_mm","p95_mm","p99_mm","maximum_mm"],map(float,np.quantile(values,[.5,.95,.99,1]))))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("before","after","scan","frame","preservation-report","output"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(mode=0o700,exist_ok=False);started=time.monotonic()
    assert sha(a.before)=="05159cdbf903729da5b8556d2ff2c2d29680a45c2b4bd42b34e031a122205594"
    assert sha(a.after)=="7adc8f931feac78eb6298e1415c8d49b7a92bced5dde5dbcc6bc3afd2e9e947f"
    assert sha(a.scan)=="dd94c37117a1f1277a4f2b7f0bf0023e0d1858991b943f766cf447db319a101a"
    assert sha(a.frame)=="fadd49707617c6339360009c2a279fe469bec0567f7b3dbe0191172bc9088766"
    frame=json.loads(a.frame.read_text());rotation=np.array(frame["rotation_rows"]);offset=np.array(frame["translation_after_rotation_mm"])
    assert np.max(np.abs(rotation@rotation.T-np.eye(3)))<1e-12 and abs(np.linalg.det(rotation)-1)<1e-12
    with np.load(a.before,allow_pickle=False) as d:ov,of=d["vertices"],d["triangles"]
    with np.load(a.after,allow_pickle=False) as d:nv,nf=d["vertices"],d["triangles"]
    old=(ov-offset)@rotation;new=(nv-offset)@rotation
    roundtrip=float(np.linalg.norm(new@rotation.T+offset-nv,axis=1).max());assert roundtrip<1e-9
    with np.load(a.scan,allow_pickle=False) as d:sv,sf=d["vertices"],d["triangles"]
    points,ids=sample(sv,sf,935051)
    forward_before=distance(points,old,of);forward_after=distance(points,new,nf)
    old_points,old_ids=sample(old,of,935052);new_points,new_ids=sample(new,nf,935052)
    reverse_before=distance(old_points,sv,sf);reverse_after=distance(new_points,sv,sf)
    preservation=json.loads(a.preservation_report.read_text())
    assert preservation["candidate_sha256"]==sha(a.after) and preservation["preservation_checks_passed"]
    maximum_change=float(np.abs(forward_after-forward_before).max())
    bound=preservation["composed_complete_surface_correspondence_bound_mm"]
    assert maximum_change<=bound+1e-8
    np.savez_compressed(a.output/"private-samples.npz",scan_face_ids=ids,scan_to_before_mm=forward_before,
                        scan_to_after_mm=forward_after,before_face_ids=old_ids,after_face_ids=new_ids,
                        before_to_scan_mm=reverse_before,after_to_scan_mm=reverse_after)
    result={"source_sha256":sha(Path(__file__)),"before_sha256":sha(a.before),"after_sha256":sha(a.after),
            "scan_arrays_sha256":sha(a.scan),"frame_sha256":sha(a.frame),
            "preservation_report_sha256":sha(a.preservation_report),"source_frame_roundtrip_max_mm":roundtrip,
            "samples_per_direction":100000,"sample_seed_scan":935051,"sample_seed_candidate":935052,
            "scan_to_before_all":stats(forward_before),"scan_to_after_all":stats(forward_after),
            "before_to_scan_all":stats(reverse_before),"after_to_scan_all":stats(reverse_after),
            "maximum_change_at_same_original_scan_samples_mm":maximum_change,
            "all_sampled_forward_changes_within_independent_correspondence_bound":True,
            "no_anatomical_exclusions":True,"sampling_is_not_global_distance_bound_or_metrology":True,
            "physical_acceptance":False,"manufacturing_qualified":False,"seconds":time.monotonic()-started}
    with (a.output/"report.json").open("x") as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__=="__main__":main()
