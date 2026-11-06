"""Assemble/read back a source-preserving surface trial with explicitly inferred quarantine patches."""
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
    for name in ('job','local-proof','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--mode',choices=('build','check'),required=True);parser.add_argument('--built',type=Path)
    parser.add_argument('--global-rejections',type=Path);parser.add_argument('--initial-candidate',type=Path)
    args = parser.parse_args();job = json.loads(args.job.read_text());started = time.monotonic()
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    proof = json.loads(args.local_proof.read_text())
    assert proof['source_sha256']=='2b5835ea1e4d53e5dfb4b8c499b0b02e858f3d495667c038b9203c2f1fb2d945'
    assert proof['job_sha256']==sha(args.job) and not proof['controls_only']
    selected = {row['curve']:row for row in proof['private_patch_results'] if row['accepted']};dropped = []
    if args.global_rejections:
        report = json.loads(args.global_rejections.read_text())
        assert args.initial_candidate is not None and sha(args.initial_candidate)==report['mesh_sha256']
        assert report['job_sha256']==sha(args.job)
        dropped = sorted(report['rejected_patch_curve_ids']);assert set(dropped)<=set(selected)
        selected = {key:row for key,row in selected.items() if key not in dropped}
    args.output.mkdir(mode=0o700,exist_ok=False)
    base = load(job['retained']);parts = [];labels = []
    for curve,row in sorted(selected.items()):
        path = args.local_proof.parent/('private-patch-'+str(curve).zfill(4)+'.npz');assert sha(path)==row['private_patch_sha256']
        patch = load(path);faces = patch['source_body_vertex_triangles']
        assert int(patch['source_curve_index'])==curve and faces.min()>=0 and faces.max()<len(base['points'])
        parts.append(faces);labels.extend([curve]*len(faces))
    added = np.concatenate(parts) if parts else np.empty((0,3),dtype=np.int64)
    faces = np.r_[base['triangles'],added];origin = np.r_[np.full(len(base['triangles']),-1,dtype=np.int32),np.array(labels,dtype=np.int32)]
    if args.mode=='build':
        np.savez_compressed(args.output/'candidate.npz',points=base['points'],triangles=faces,global_node_ids=base['global_node_ids'],
                            original_face_ids=np.r_[base['original_face_ids'],np.full(len(added),-1,dtype=np.int64)],
                            source_fragment_indices=np.r_[base['source_fragment_indices'],np.full(len(added),-1,dtype=np.int64)],
                            source_patch_curve_ids=origin)
        with (args.output/'candidate.obj').open('x') as stream:
            stream.write('# Open source surface with masked inferred quarantine patches; unqualified.\n')
            stream.write('# Owner nominal millimetres; no engine or manufacturing release.\n')
            for p in base['points']:stream.write('v '+' '.join(format(float(x),'.17g') for x in p)+'\n')
            for f in faces:stream.write('f '+' '.join(str(int(x)+1) for x in f)+'\n')
        target = args.output
    else:
        assert args.built is not None;target = args.built;stored = load(target/'candidate.npz')
        assert np.array_equal(stored['points'],base['points']) and np.array_equal(stored['triangles'],faces)
        assert np.array_equal(stored['global_node_ids'],base['global_node_ids']) and np.array_equal(stored['source_patch_curve_ids'],origin)
        assert np.array_equal(stored['original_face_ids'][:len(base['triangles'])],base['original_face_ids'])
        assert np.array_equal(stored['source_fragment_indices'][:len(base['triangles'])],base['source_fragment_indices'])
        assert np.all(stored['original_face_ids'][len(base['triangles']):]==-1) and np.all(stored['source_fragment_indices'][len(base['triangles']):]==-1)
        vertex_count = face_count = 0
        with (target/'candidate.obj').open() as stream:
            for line in stream:
                words = line.split()
                if not words or words[0].startswith('#'):continue
                assert len(words)==4
                if words[0]=='v':
                    assert np.array_equal(np.array(list(map(float,words[1:]))),base['points'][vertex_count]);vertex_count+=1
                else:
                    assert words[0]=='f' and np.array_equal(np.array([int(x)-1 for x in words[1:]]),faces[face_count]);face_count+=1
        assert vertex_count==len(base['points']) and face_count==len(faces)
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    report = dict(source_sha256=sha(__file__),job_sha256=sha(args.job),local_proof_sha256=sha(args.local_proof),mode=args.mode,
                  base_vertices=len(base['points']),base_faces=len(base['triangles']),added_hypothesis_faces=len(added),
                  total_faces=len(faces),selected_patch_curve_ids=sorted(selected),globally_rejected_curve_ids=dropped,
                  candidate_NPZ_sha256=sha(target/'candidate.npz'),candidate_OBJ_sha256=sha(target/'candidate.obj'),
                  base_points_faces_and_provenance_unchanged=True,added_faces_marked_as_inferred=True,
                  original_acquisition_contours_intentionally_filled=False,full_bare_head_created=False,
                  physical_acceptance=False,manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(mode=args.mode,patches=len(selected),added_faces=len(added),base_observations_unchanged=True)),flush=True)


if __name__=='__main__':main()
