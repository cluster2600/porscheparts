"""Independently inspect an entire source-derived candidate with isolated libigl predicates."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def detect(vertices,faces):
    import igl.predicates
    assert vertices.ndim==2 and vertices.shape[1]==3 and np.isfinite(vertices).all()
    assert faces.ndim==2 and faces.shape[1]==3 and faces.dtype.kind in 'iu'
    assert not len(faces) or (faces.min()>=0 and faces.max()<len(vertices))
    cross = np.cross(vertices[faces[:,1]]-vertices[faces[:,0]],vertices[faces[:,2]]-vertices[faces[:,0]])
    keep = np.any(cross!=0,axis=1);source = np.flatnonzero(keep)
    if len(source):
        found,pairs,coplanar = igl.predicates.find_self_intersections(
            np.ascontiguousarray(vertices,dtype=np.float64),np.ascontiguousarray(faces[keep],dtype=np.int64),False)
        pairs = np.asarray(pairs,dtype=np.int64).reshape(-1,2);coplanar = np.asarray(coplanar,dtype=bool).reshape(-1)
        assert bool(found)==bool(len(pairs)) and len(coplanar)==len(pairs)
        assert not len(pairs) or (pairs.min()>=0 and pairs.max()<len(source))
        return source[pairs],coplanar,np.flatnonzero(~keep)
    return np.empty((0,2),dtype=np.int64),np.empty(0,dtype=bool),np.flatnonzero(~keep)


def controls():
    a = np.array([[-1.,-1.,0.],[1.,-1.,0.],[0.,1.,0.]])
    b = np.array([[0.,-.5,-1.],[0.,-.5,1.],[0.,.5,0.]])
    f = np.array([[0,1,2],[3,4,5]])
    rows = {}
    for name,v,faces,expected in [
        ('separated',np.r_[a,a+[4.,0.,0.]],f,False),
        ('crossing',np.r_[a,b],f,True),
        ('coplanar_overlap',np.r_[a,a+[.2,0.,0.]],f,True),
        ('shared_edge',np.array([[0.,0.,0.],[1.,0.,0.],[1.,1.,0.],[0.,1.,0.]]),np.array([[0,1,2],[0,2,3]]),False),
        ('shared_source_point',np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[-1.,0.,0.],[0.,-1.,0.]]),np.array([[0,1,2],[0,3,4]]),False)]:
        pairs,cp,excluded = detect(v,faces)
        assert bool(len(pairs))==expected and not len(excluded),name
        if name=='coplanar_overlap':assert cp.all()
        rows[name] = dict(pairs=len(pairs),coplanar_pairs=int(cp.sum()))
    pairs,_,excluded = detect(np.r_[a,b],np.r_[[[0,0,0]],f])
    assert excluded.tolist()==[0] and {tuple(sorted(p)) for p in pairs.tolist()}=={(1,2)}
    rows['degenerate_face_original_index_mapping_verified'] = True
    try:detect(a,np.array([[0,1,99]]))
    except AssertionError:pass
    else:raise AssertionError('Invalid source index admitted')
    rows['invalid_index_refused'] = True
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--controls-only',action='store_true')
    parser.add_argument('--mesh',type=Path);parser.add_argument('--expected-mesh-sha256')
    args = parser.parse_args();job = json.loads(args.job.read_text());started = time.monotonic()
    assert job['schema']=='935-quarantine-patch-trials-1'
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    addon = Path(job['igl_addon']).resolve();manifest = addon/'manifest.json'
    assert sha(manifest)==job['igl_addon_manifest_sha256']
    for row in json.loads(manifest.read_text())['files']:assert sha(addon/row['path'])==row['sha256']
    import igl
    import igl.predicates
    assert Path(igl.__file__).resolve().is_relative_to(addon)
    assert Path(igl.predicates.__file__).resolve().is_relative_to(addon)
    assert importlib.metadata.version('libigl')=='2.6.3'
    args.output.mkdir(mode=0o700,exist_ok=False);control = controls()
    runtime = dict(python=sys.version.split()[0],numpy=np.__version__,libigl=importlib.metadata.version('libigl'),
                   private_addon_origin_verified=True,addon_manifest_sha256=sha(manifest))
    result = dict(source_sha256=sha(__file__),job_sha256=sha(args.job),controls=control,runtime=runtime,
                  controls_only=args.controls_only,full_bare_head_created=False,physical_acceptance=False,manufacturing_authorized=False)
    if not args.controls_only:
        mesh = args.mesh or Path(job['retained'])
        expected = args.expected_mesh_sha256 if args.mesh else job['retained_sha256']
        assert expected and sha(mesh)==expected
        with np.load(mesh,allow_pickle=False) as data:vertices,faces = data['points'],data['triangles']
        if not args.mesh:assert len(faces)==2401740
        pairs,coplanar,excluded = detect(vertices,faces)
        np.save(args.output/'private-intersecting-face-pairs.npy',pairs)
        np.save(args.output/'private-coplanar-pair-flags.npy',coplanar)
        np.save(args.output/'private-excluded-zero-cross-faces.npy',excluded)
        assert sha(mesh)==expected
        result.update(mesh_sha256=expected,vertices=len(vertices),triangles=len(faces),
                      full_mesh_intersection_pairs=len(pairs),coplanar_pairs=int(coplanar.sum()),
                      predicate_excluded_zero_cross_faces=len(excluded),
                      admissible_for_masked_local_patch_trials=not len(pairs) and not len(excluded),
                      independent_intersection_engine='libigl predicates.find_self_intersections; all faces; original-index mapping retained')
    for row in json.loads(manifest.read_text())['files']:assert sha(addon/row['path'])==row['sha256']
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    result['seconds'] = time.monotonic()-started
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:value for key,value in result.items() if key in ('controls_only','vertices','triangles','full_mesh_intersection_pairs','predicate_excluded_zero_cross_faces','admissible_for_masked_local_patch_trials','seconds')}),flush=True)


if __name__=='__main__':main()
