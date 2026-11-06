"""Attribute whole-candidate intersection/topology conflicts to entire inferred acquisition patches."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):
    with np.load(path,allow_pickle=False) as data:return {key:data[key] for key in data.files}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job','mesh','intersection-proof','output'):parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args();job = json.loads(args.job.read_text());started = time.monotonic()
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    before = sha(args.mesh);proof = json.loads(args.intersection_proof.read_text())
    assert proof['source_sha256']=='3e0b239ca4993388f32563092c78d97065cc1fb0753c68a2def3d631feda7976'
    assert proof['mesh_sha256']==before and proof['job_sha256']==sha(Path(job['predicate_job']))
    args.output.mkdir(mode=0o700,exist_ok=False);base = load(job['retained']);data = load(args.mesh)
    n = len(base['triangles']);faces = data['triangles'];labels = data['source_acquisition_curve_ids'];vertices = len(data['points'])
    assert np.array_equal(data['points'],base['points']) and np.array_equal(faces[:n],base['triangles'])
    assert np.all(labels[:n]==-1) and np.all(labels[n:]>=0)
    rejected = set();reasons = [];pairs = np.load(args.intersection_proof.parent/'private-intersecting-face-pairs.npy',allow_pickle=False)
    excluded = np.load(args.intersection_proof.parent/'private-excluded-zero-cross-faces.npy',allow_pickle=False)
    assert len(pairs)==proof['full_mesh_intersection_pairs'] and len(excluded)==proof['predicate_excluded_zero_cross_faces']
    for a,b in pairs:
        involved = set(map(int,labels[[a,b]]))-{-1};assert involved,'Unchanged base developed an unexplained intersection'
        rejected.update(involved)
    if len(pairs):reasons.append('whole_candidate_intersection')
    for face in excluded:
        assert labels[face]>=0;rejected.add(int(labels[face]))
    if len(excluded):reasons.append('predicate_excluded_added_face')
    edges = np.stack((faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]),axis=1).reshape(-1,2)
    code = edges.min(axis=1)*vertices+edges.max(axis=1);order = np.argsort(code,kind='stable');ordered = code[order]
    first = np.r_[0,np.flatnonzero(ordered[1:]!=ordered[:-1])+1];uses = np.diff(np.r_[first,len(order)])
    bad = uses>2;twice = np.flatnonzero(uses==2)
    bad[twice] |= np.any(edges[order[first[twice]]]!=edges[order[first[twice]+1]][:,::-1],axis=1)
    for index in np.flatnonzero(bad):
        rows = order[first[index]:first[index]+uses[index]]//3;involved = set(map(int,labels[rows]))-{-1}
        assert involved,'Unchanged base has an unexplained edge conflict';rejected.update(involved)
    if bad.any():reasons.append('global_edge_incidence_or_winding')
    assert vertices**3<2**63
    canonical = np.sort(faces,axis=1);fcode = (canonical[:,0]*vertices+canonical[:,1])*vertices+canonical[:,2]
    forder = np.argsort(fcode,kind='stable');fc = fcode[forder];fstart = np.r_[0,np.flatnonzero(fc[1:]!=fc[:-1])+1];fuses = np.diff(np.r_[fstart,len(fc)])
    for index in np.flatnonzero(fuses>1):
        rows = forder[fstart[index]:fstart[index]+fuses[index]];involved = set(map(int,labels[rows]))-{-1}
        assert involved,'Unchanged base has duplicate indexed faces';rejected.update(involved)
    if np.any(fuses>1):reasons.append('duplicate_indexed_face')
    assert sha(args.mesh)==before
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    report = dict(source_sha256=sha(__file__),job_sha256=sha(args.job),mesh_sha256=before,
                  intersection_proof_sha256=sha(args.intersection_proof),full_candidate_intersection_pairs=len(pairs),
                  predicate_excluded_faces=len(excluded),global_edge_conflicts=int(bad.sum()),duplicate_face_groups=int(np.count_nonzero(fuses>1)),
                  open_boundary_edges=int(np.count_nonzero(uses==1)),rejected_acquisition_curve_ids=sorted(rejected),rejection_categories=reasons,
                  all_conflicts_attributed_to_inferred_faces=True,base_geometry_unchanged=True,
                  source_preserving_surface_checks_passed=not rejected,closed_volume=not np.any(uses==1),
                  full_bare_head_created=False,physical_acceptance=False,manufacturing_authorized=False,
                  seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k in ('full_candidate_intersection_pairs','global_edge_conflicts','duplicate_face_groups','open_boundary_edges','rejected_acquisition_curve_ids','source_preserving_surface_checks_passed')}),flush=True)


if __name__=='__main__':main()
