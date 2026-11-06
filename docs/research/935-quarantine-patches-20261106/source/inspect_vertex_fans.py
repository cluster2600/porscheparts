"""Compare every used-vertex face fan and exact remaining source boundaries before/after patches."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):
    with np.load(path,allow_pickle=False) as data:return {key:data[key] for key in data.files}


def vertex_fans(faces,vertex_count):
    face_count = len(faces)
    edges = np.stack((faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]),axis=1).reshape(-1,2)
    codes = edges.min(axis=1)*vertex_count+edges.max(axis=1)
    order = np.argsort(codes,kind='stable');ordered = codes[order]
    first = np.r_[0,np.flatnonzero(ordered[1:]!=ordered[:-1])+1];uses = np.diff(np.r_[first,len(order)])
    assert np.all((uses==1)|(uses==2));paired = first[uses==2]
    assert np.array_equal(edges[order[paired]],edges[order[paired+1]][:,::-1])
    corners = np.sort((faces*face_count+np.arange(face_count)[:,None]).ravel())
    assert len(np.unique(corners))==len(corners)
    left = [];right = []
    for endpoint in (0,1):
        v = edges[order[paired],endpoint]
        a,b = v*face_count+order[paired]//3,v*face_count+order[paired+1]//3
        ia,ib = np.searchsorted(corners,a),np.searchsorted(corners,b)
        assert np.array_equal(corners[ia],a) and np.array_equal(corners[ib],b)
        left.extend((ia,ib));right.extend((ib,ia))
    a,b = np.concatenate(left),np.concatenate(right)
    graph = coo_matrix((np.ones(len(a),dtype=np.int8),(a,b)),shape=(len(corners),len(corners))).tocsr()
    count,labels = connected_components(graph,directed=False);source = corners//face_count
    owner = np.full(count,-1,dtype=np.int64);owner[labels]=source
    assert np.array_equal(owner[labels],source)
    fans = np.bincount(owner,minlength=vertex_count)
    return fans,edges[order[first[uses==1]]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job','mesh','assembly-proof','output'):parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args();job = json.loads(args.job.read_text());started = time.monotonic()
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    square,_ = vertex_fans(np.array([[0,1,2],[0,2,3]]),4);assert square.tolist()==[1,1,1,1]
    contact,_ = vertex_fans(np.array([[0,1,2],[0,3,4]]),5);assert contact.tolist()==[2,1,1,1,1]
    args.output.mkdir(mode=0o700,exist_ok=False);base = load(job['retained']);data = load(args.mesh)
    assembly = json.loads(args.assembly_proof.read_text());assert assembly['candidate_NPZ_sha256']==sha(args.mesh)
    assert np.array_equal(data['points'],base['points']) and np.array_equal(data['triangles'][:len(base['triangles'])],base['triangles'])
    original,before = vertex_fans(base['triangles'],len(base['points']))
    current,after = vertex_fans(data['triangles'],len(data['points']))
    assert np.array_equal(original,current),'Inferred patches changed original used-vertex face-fan partition counts'
    boundaries = load(job['boundaries']);selected = set(assembly['selected_patch_curve_ids'])
    keep = np.ones(len(boundaries['boundary_global_nodes']),dtype=bool)
    for curve in selected:
        a,b = boundaries['cycle_offsets'][curve:curve+2];ids = boundaries['cycle_boundary_edge_ids'][a:b]
        assert np.all(boundaries['edge_origin_kind'][ids]==2);keep[ids]=False
    assert np.array_equal(base['global_node_ids'][before],boundaries['boundary_global_nodes'])
    assert np.array_equal(data['global_node_ids'][after],boundaries['boundary_global_nodes'][keep]),'Unselected source boundary changed'
    np.savez_compressed(args.output/'private-used-vertex-fans-and-boundaries.npz',base_face_fans=original,candidate_face_fans=current,
                        remaining_original_boundary_edge_ids=np.flatnonzero(keep),nonmanifold_used_vertex_ids=np.flatnonzero(current>1))
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    result = dict(source_sha256=sha(__file__),job_sha256=sha(args.job),mesh_sha256=sha(args.mesh),
                  controls=dict(shared_square_vertex_fans=True,point_contact_two_fans=True),
                  base_nonmanifold_used_vertices=int(np.count_nonzero(original>1)),candidate_nonmanifold_used_vertices=int(np.count_nonzero(current>1)),
                  maximum_face_fans_at_used_vertex=int(current.max()),all_used_vertex_fan_counts_unchanged=True,
                  base_boundary_edges=len(before),candidate_boundary_edges=len(after),
                  exactly_selected_quarantine_contours_closed=len(selected),remaining_original_boundary_walks=len(boundaries['cycle_offsets'])-1-len(selected),
                  unselected_acquisition_quarantine_and_cut_edges_unchanged=True,
                  full_used_vertex_manifold=not np.any(current>1),closed_volume=False,
                  conservative_surface_workflow_fully_admitted=False,full_bare_head_created=False,
                  physical_acceptance=False,manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':main()
