"""Prepare all admitted acquisition-only native halos with exact source correspondence."""
import argparse
from collections import defaultdict
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


def write_obj(path,points,faces):
    with path.open('w') as stream:
        for point in points:stream.write('v '+' '.join(format(float(x),'.17g') for x in point)+'\n')
        for face in faces:stream.write('f '+' '.join(str(int(x)+1) for x in face)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('job','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();job=json.loads(args.job.read_text());started=time.monotonic()
    assert job['schema']=='935-acquisition-gap-trials-1'
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    admission=json.loads(Path(job['admission_report']).read_text());assert admission['candidate_sha256']==sha(job['retained'])
    assert admission['source_sha256']=='30129c9eb68cd571d2f674562bd0dc7de73cb68046760f9ccca0d1f113521ecf'
    assert admission['whole_topology_and_omission_deviations_checked_before_admission']
    selected=np.load(job['admission_ids'],allow_pickle=False);decisions=json.loads(Path(job['admission_decisions']).read_text())
    assert selected.tolist()==[row['curve'] for row in decisions if row['experimental_trial_admitted']]
    assert len(selected)==admission['experimental_trials_admitted']==286
    assert sha(job['builder_source'])=='fca5259ef3b3412a72e441fea39816e14fea4e375095e1c83def2e4117f6ae8e'
    spec=importlib.util.spec_from_file_location('frozen_source_atlas_builder',job['builder_source']);builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    body=load(job['retained']);boundary=load(job['boundaries']);body_nodes=body['global_node_ids'];assert np.all(np.diff(body_nodes)>0)
    flags=np.zeros(len(body_nodes),dtype=bool)
    for curve in selected:
        a,b=boundary['cycle_offsets'][curve:curve+2];ids=boundary['cycle_boundary_edge_ids'][a:b]
        assert np.all(boundary['edge_origin_kind'][ids]==1)
        flags[boundary['boundary_local_nodes'][ids,0]]=True
    incident=defaultdict(list)
    for row in np.flatnonzero(flags[body['triangles']].any(axis=1)):
        for v in body['triangles'][row]:
            if flags[v]:incident[int(v)].append(int(row))
    args.output.mkdir(mode=0o700,exist_ok=False);records=[]
    for curve in selected:
        index=int(curve);a,b=boundary['cycle_offsets'][index:index+2];edge_ids=boundary['cycle_boundary_edge_ids'][a:b]
        local_edges=boundary['boundary_local_nodes'][edge_ids];nodes=local_edges[:,0]
        assert np.array_equal(local_edges[:,1],np.roll(nodes,-1)) and len(np.unique(nodes))==len(nodes)
        halo=np.array(sorted({row for v in nodes for row in incident[int(v)]}),dtype=np.int64)
        used,inverse=np.unique(body['triangles'][halo],return_inverse=True)
        points,faces,mapping,_,topology=builder.atlas(body['points'][used],inverse.reshape(-1,3))
        assert np.array_equal(used[mapping[faces]],body['triangles'][halo])
        wanted=[]
        for edge,owner in zip(local_edges,boundary['boundary_face_rows'][edge_ids]):
            row=int(np.searchsorted(halo,owner));assert halo[row]==owner
            original=body['triangles'][owner].tolist();pairs=list(zip(original,original[1:]+original[:1]));corner=pairs.index(tuple(map(int,edge)))
            wanted.append((int(faces[row,corner]),int(faces[row,(corner+1)%3])))
        wanted=np.array(wanted,dtype=np.int64)
        assert np.array_equal(wanted[:,1],np.roll(wanted[:,0],-1)) and len(np.unique(wanted[:,0]))==len(nodes)
        raw_curves=np.unique(boundary['raw_original_curve_ids'][edge_ids]);assert np.all(raw_curves>=0)
        path=args.output/('curve-'+str(index).zfill(4));path.mkdir(mode=0o700,exist_ok=False)
        write_obj(path/'input.obj',points,faces)
        (path/'target-edges.txt').write_text(str(index)+' '+str(wanted[0,0])+' '+str(wanted[0,1])+'\n')
        np.savez_compressed(path/'private-halo-map.npz',points=points,triangles=faces,source_body_vertex_ids=used[mapping],body_face_rows=halo,
                            ordered_hole_nodes=wanted[:,0],expected_source_boundary_edges=wanted,original_global_hole_nodes=body_nodes[nodes],acquisition_raw_curve_ids=raw_curves)
        records.append(dict(curve=index,admitted=True,reason='independently_admitted_acquired_source_gap_experiment',boundary_edges=len(nodes),
                            halo_faces=len(faces),halo_vertex_objects=len(points),halo_source_body_vertices=len(used),local_point_contact_fan_splits=len(points)-len(used),
                            native_source_topology=topology,input_OBJ_sha256=sha(path/'input.obj'),target_sha256=sha(path/'target-edges.txt'),halo_map_sha256=sha(path/'private-halo-map.npz'),
                            physical_role_accepted=False))
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    report=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),retained_sha256=sha(job['retained']),admission_report_sha256=sha(job['admission_report']),
                complete_target_denominator=len(selected),admitted_local_trials=len(records),private_targets=records,
                source_points_or_base_faces_changed=False,physical_classifications_accepted=0,manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='private_targets'}),flush=True)


if __name__=='__main__':main()
