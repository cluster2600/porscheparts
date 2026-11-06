"""Build, then independently parse the complete saved source-coordinate bridge candidate."""
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


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('job','local-proof','prepared','output','obj-reader'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--mode',choices=('build','check'),required=True);parser.add_argument('--built',type=Path)
    parser.add_argument('--global-rejections',type=Path)
    args=parser.parse_args();started=time.monotonic();job=json.loads(args.job.read_text())
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    proof=json.loads(args.local_proof.read_text());assert proof['job_sha256']==sha(args.job)
    assert proof['source_sha256']=='173cd6752bc88a89cca1e5356b80f252ad75be05e8fff406f3e0117e3af2aad1'
    preparation=json.loads((args.prepared/'report.json').read_text())
    assert sha(args.prepared/'report.json')==proof['prepared_report_sha256']
    base=load(job['mesh']);rows=proof['private_selected_contacts'];refused=set()
    if args.global_rejections:
        failure=json.loads(args.global_rejections.read_text());assert failure['job_sha256']==sha(args.job)
        refused=set(failure['rejected_contact_vertex_ids'])
    patches=[];labels=[]
    for row in rows:
        contact=row['contact_vertex']
        if contact in refused:continue
        patch=load(args.local_proof.parent/('private-selected-contact-'+str(contact)+'.npz'))
        assert int(patch['contact_vertex'])==contact and len(patch['new_faces'])==row['added_faces']
        assert any(x['contact_vertex']==contact and x['proposal']==row['proposal'] and x['accepted'] for x in proof['private_proposal_checks'])
        proposal=args.prepared/('private-contact-'+str(contact)+'-proposal-'+str(row['proposal'])+'.npz')
        original=next(x for x in preparation['private_contacts'] if x['contact_vertex']==contact)
        trial=next(x for x in original['trials'] if x['proposal']==row['proposal'])
        assert sha(proposal)==trial['proposal_sha256']
        assert np.array_equal(patch['new_faces'],load(proposal)['new_faces'])
        patches.append(patch['new_faces']);labels.extend([contact]*len(patch['new_faces']))
    added=np.concatenate(patches) if patches else np.empty((0,3),dtype=np.int64)
    labels=np.array(labels,dtype=np.int64);n=len(base['triangles']);count=len(added)
    expected={**base,'triangles':np.r_[base['triangles'],added],
              'original_face_ids':np.r_[base['original_face_ids'],np.full(count,-1,dtype=np.int64)],
              'source_fragment_indices':np.r_[base['source_fragment_indices'],np.full(count,-1,dtype=np.int64)],
              'source_patch_curve_ids':np.r_[base['source_patch_curve_ids'],10000000+labels],
              'source_contact_vertex_ids':np.r_[np.full(n,-1,dtype=np.int64),labels],
              'inferred_surface_kind':np.r_[np.where(base['source_patch_curve_ids']>=0,1,0),np.full(count,2,dtype=np.int64)]}
    args.output.mkdir(mode=0o700,exist_ok=False)
    if args.mode=='build':
        built=args.output;np.savez_compressed(built/'candidate.npz',**expected)
        with (built/'candidate.obj').open('w') as stream:
            stream.write('# Open source-preserving study; kind 1 quarantine patches, kind 2 contact bridges; project mm; NOT PRINT READY\n')
            for point in expected['points']:stream.write('v '+' '.join(format(float(x),'.17g') for x in point)+'\n')
            for face in expected['triangles']:stream.write('f '+' '.join(str(int(x)+1) for x in face)+'\n')
    else:
        assert args.built is not None;built=args.built;actual=load(built/'candidate.npz')
        assert set(actual)==set(expected)
        for key in expected:assert np.array_equal(actual[key],expected[key]),key
        assert sha(args.obj_reader)=='2b5835ea1e4d53e5dfb4b8c499b0b02e858f3d495667c038b9203c2f1fb2d945'
        spec=importlib.util.spec_from_file_location('frozen_saved_OBJ_reader',args.obj_reader)
        reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
        points,faces=reader.read_obj(built/'candidate.obj')
        assert np.array_equal(points,expected['points']) and np.array_equal(faces,expected['triangles'])
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    result=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),local_proof_sha256=sha(args.local_proof),mode=args.mode,
                base_vertices=len(base['points']),base_faces=n,added_contact_bridge_faces=count,total_faces=n+count,
                candidate_NPZ_sha256=sha(built/'candidate.npz'),candidate_OBJ_sha256=sha(built/'candidate.obj'),
                selected_contact_vertex_ids=sorted(set(map(int,labels))),globally_rejected_contact_vertex_ids=sorted(refused),
                all_base_coordinates_faces_and_provenance_unchanged=True,new_faces_marked_inferred=True,
                index_duplicates_created=False,base_faces_removed=False,full_bare_head_created=False,
                physical_acceptance=False,manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if not isinstance(v,(dict,list))}),flush=True)


if __name__=='__main__':main()
