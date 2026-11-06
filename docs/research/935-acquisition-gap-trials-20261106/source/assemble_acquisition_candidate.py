"""Assemble checked acquired-gap patches while preserving the complete omission ancestry."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):
    with np.load(path,allow_pickle=False) as data:return {k:data[k] for k in data.files}


def compose(base,added,labels):
    n=len(base['triangles']);count=len(added);assert labels.shape==(count,)
    result={}
    for key,value in base.items():
        if key in ('points','global_node_ids'):result[key]=value
        elif key=='triangles':result[key]=np.r_[value,added]
        else:
            assert value.ndim==1 and len(value)==n,'unsupported_parent_provenance'
            extra=20000000+labels if key=='source_patch_curve_ids' else np.full(count,3 if key=='inferred_surface_kind' else -1,dtype=value.dtype)
            result[key]=np.r_[value,extra]
    assert 'source_acquisition_curve_ids' not in base and 'immediate_parent_face_rows' not in base
    result['source_acquisition_curve_ids']=np.r_[np.full(n,-1,dtype=np.int64),labels]
    result['immediate_parent_face_rows']=np.r_[np.arange(n,dtype=np.int64),np.full(count,-1,dtype=np.int64)]
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('job','local-proof','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--mode',choices=('build','check'),required=True);parser.add_argument('--built',type=Path)
    parser.add_argument('--reject-report',type=Path,action='append',default=[]);parser.add_argument('--initial-candidate',type=Path)
    args=parser.parse_args();job=json.loads(args.job.read_text());started=time.monotonic()
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    proof=json.loads(args.local_proof.read_text())
    assert proof['source_sha256']=='301c2474971407b2221e7f8e26d969b4de59f9f2e6957d93df97c7722e800316'
    assert proof['job_sha256']==sha(args.job) and not proof['controls_only']
    selected={row['curve']:row for row in proof['private_patch_results'] if row['accepted']};dropped=set()
    for path in args.reject_report:
        rejected=json.loads(path.read_text());assert rejected['job_sha256']==sha(args.job)
        assert args.initial_candidate is not None and rejected['mesh_sha256']==sha(args.initial_candidate)
        dropped.update(rejected['rejected_acquisition_curve_ids'])
    assert dropped<=set(selected);selected={i:row for i,row in selected.items() if i not in dropped}
    base=load(job['retained']);parts=[];labels=[]
    for curve,row in sorted(selected.items()):
        path=args.local_proof.parent/('private-patch-'+str(curve).zfill(4)+'.npz');assert sha(path)==row['private_patch_sha256']
        patch=load(path);assert int(patch['source_curve_index'])==curve
        faces=patch['source_body_vertex_triangles'];assert faces.ndim==2 and faces.shape[1]==3 and faces.min()>=0 and faces.max()<len(base['points'])
        parts.append(faces);labels.extend([curve]*len(faces))
    added=np.concatenate(parts) if parts else np.empty((0,3),dtype=np.int64);labels=np.array(labels,dtype=np.int64)
    expected=compose(base,added,labels);args.output.mkdir(mode=0o700,exist_ok=False)
    if args.mode=='build':
        target=args.output;np.savez_compressed(target/'candidate.npz',**expected)
        with (target/'candidate.obj').open('x') as stream:
            stream.write('# Open acquired-gap hypothesis; exact parent plus marked caps; project mm; NOT PRINT READY\n')
            for p in expected['points']:stream.write('v '+' '.join(format(float(x),'.17g') for x in p)+'\n')
            for f in expected['triangles']:stream.write('f '+' '.join(str(int(x)+1) for x in f)+'\n')
    else:
        assert args.built is not None;target=args.built;actual=load(target/'candidate.npz');assert set(actual)==set(expected)
        for key in expected:assert np.array_equal(actual[key],expected[key]),key
        path=Path(__file__).with_name('inspect_acquisition_patches.py');assert sha(path)=='301c2474971407b2221e7f8e26d969b4de59f9f2e6957d93df97c7722e800316'
        spec=importlib.util.spec_from_file_location('frozen_independent_native_OBJ_reader',path);reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
        points,faces=reader.read_obj(target/'candidate.obj')
        assert np.array_equal(points,expected['points']) and np.array_equal(faces,expected['triangles'])
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    result=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),local_proof_sha256=sha(args.local_proof),mode=args.mode,
                base_vertices=len(base['points']),base_faces=len(base['triangles']),added_inferred_cap_faces=len(added),total_faces=len(expected['triangles']),
                selected_acquisition_curve_ids=sorted(selected),rejected_acquisition_curve_ids=sorted(dropped),
                candidate_NPZ_sha256=sha(target/'candidate.npz'),candidate_OBJ_sha256=sha(target/'candidate.obj'),
                all_parent_coordinates_faces_and_provenance_unchanged=True,omission_ancestry_preserved=True,new_caps_marked_inferred=True,
                full_bare_head_created=False,physical_acceptance=False,manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(mode=args.mode,patches=len(selected),added_faces=len(added),parent_geometry_unchanged=True)),flush=True)


if __name__=='__main__':main()
