"""Attribute every retained boundary edge and separate surface vertex fans for review."""
import argparse
from collections import Counter
import csv
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


def table(triangles,vertex_count):
    edges = np.stack((triangles[:,[0,1]],triangles[:,[1,2]],triangles[:,[2,0]]),axis=1).reshape(-1,2)
    codes = edges.min(axis=1)*vertex_count+edges.max(axis=1)
    order = np.argsort(codes,kind='stable');ordered = codes[order]
    first = np.r_[0,np.flatnonzero(ordered[1:]!=ordered[:-1])+1]
    uses = np.diff(np.r_[first,len(order)])
    return edges,order,first,ordered[first],uses


def fans_and_cycles(triangles,vertex_count):
    edges,order,first,codes,uses = table(triangles,vertex_count)
    assert np.all((uses==1)|(uses==2))
    paired = first[uses==2]
    assert np.array_equal(edges[order[paired]],edges[order[paired+1]][:,::-1])
    single = order[first[uses==1]];boundary = edges[single];owners = single//3
    if not len(boundary):
        return dict(boundary=boundary,owners=owners,from_fans=np.array([],dtype=np.int64),
                    to_fans=np.array([],dtype=np.int64),offsets=np.array([0]),cycle_edges=np.array([],dtype=np.int64))
    boundary_vertices = np.unique(boundary);selected = np.zeros(vertex_count,dtype=bool)
    selected[boundary_vertices] = True;face_count = len(triangles)
    row,column = np.nonzero(selected[triangles])
    corner = np.sort(triangles[row,column]*face_count+row)
    assert len(np.unique(corner))==len(corner)
    left = [];right = []
    for endpoint in (0,1):
        v = edges[order[paired],endpoint];keep = selected[v];v = v[keep]
        a = v*face_count+order[paired[keep]]//3
        b = v*face_count+order[paired[keep]+1]//3
        ia,ib = np.searchsorted(corner,a),np.searchsorted(corner,b)
        assert np.array_equal(corner[ia],a) and np.array_equal(corner[ib],b)
        left.extend((ia,ib));right.extend((ib,ia))
    a,b = np.concatenate(left),np.concatenate(right)
    graph = coo_matrix((np.ones(len(a),dtype=np.int8),(a,b)),shape=(len(corner),len(corner))).tocsr()
    _,labels = connected_components(graph,directed=False)
    from_fans,to_fans = [labels[np.searchsorted(corner,boundary[:,i]*face_count+owners)] for i in (0,1)]
    assert Counter(map(int,from_fans))==Counter(map(int,to_fans))
    assert len(set(map(int,from_fans)))==len(boundary),'Unresolved branching within a surface fan'
    outgoing = {int(fan):i for i,fan in enumerate(from_fans)}
    remaining = set(range(len(boundary)));cycles = []
    while remaining:
        start = min(remaining);current = start;cycle = []
        while current in remaining:
            remaining.remove(current);cycle.append(current);current = outgoing[int(to_fans[current])]
        assert current==start and len(cycle)>=3
        cycles.append(cycle)
    return dict(boundary=boundary,owners=owners,from_fans=from_fans,to_fans=to_fans,
                offsets=np.r_[0,np.cumsum([len(c) for c in cycles])],cycle_edges=np.concatenate(cycles))


def attribute(boundary,owners,parent_ids,raw_faces,roles,vertex_count,original_vertex_count,cut_regions):
    edges,order,first,codes,uses = table(raw_faces,vertex_count)
    raw_open = uses==1;raw_edges = edges[order[first[raw_open]]]
    used,inverse = np.unique(raw_edges,return_inverse=True);local = inverse.reshape(-1,2)
    graph = coo_matrix((np.ones(len(local)),(local[:,0],local[:,1])),shape=(len(used),len(used)))
    raw_count,labels = connected_components(graph,directed=False)
    raw_curve = np.full(len(codes),-1,dtype=np.int32);raw_curve[raw_open] = labels[local[:,0]]
    assert np.all(np.bincount(local.ravel(),minlength=len(used))==2)
    kind = np.zeros(len(boundary),dtype=np.int8);curve = np.full(len(boundary),-1,dtype=np.int32)
    declared = np.zeros(len(boundary),dtype=np.int16)
    for i,(a,b) in enumerate(boundary):
        a,b = int(a),int(b);code = min(a,b)*vertex_count+max(a,b)
        if a>=original_vertex_count and b>=original_vertex_count:
            assert code in cut_regions,'Unexplained constructed boundary edge'
            kind[i]=3;declared[i]=cut_regions[code];continue
        assert a<original_vertex_count and b<original_vertex_count,'Unexpected split original boundary'
        location = int(np.searchsorted(codes,code))
        assert location<len(codes) and codes[location]==code,'Boundary edge absent from acquisition'
        raw_parents = order[first[location]:first[location]+uses[location]]//3
        parent = int(parent_ids[owners[i]])
        assert np.count_nonzero(raw_parents==parent)==1,'Retained boundary parent not rejoined to source'
        others = raw_parents[raw_parents!=parent]
        if not len(others):
            kind[i]=1;curve[i]=raw_curve[location]
        else:
            assert np.all(roles[others]==-2),'Unexplained removal of acquired nonquarantine surface'
            kind[i]=2
    assert set(cut_regions)=={min(map(int,e))*vertex_count+max(map(int,e)) for e,k in zip(boundary,kind) if k==3}
    return kind,curve,declared,dict(raw_original_open_edges=int(np.count_nonzero(raw_open)),raw_original_boundary_curves=int(raw_count))


def geometry(points):
    centre = points.mean(axis=0);_,singular,axes = np.linalg.svd(points-centre,full_matrices=False)
    tolerance = singular.max()*max(points.shape)*np.finfo(float).eps
    rank = int(np.count_nonzero(singular>tolerance));normal = axes[-1]
    distance = np.abs((points-centre)@normal)
    perimeter = float(np.linalg.norm(np.roll(points,-1,axis=0)-points,axis=1).sum())
    return dict(vertices=len(points),perimeter_nominal_mm=perimeter,affine_rank=rank,
                plane_maximum_residual_nominal_mm=float(distance.max()) if rank>=2 else None,
                plane_RMS_residual_nominal_mm=float(np.sqrt(np.mean(distance**2))) if rank>=2 else None,
                bounds_diagonal_nominal_mm=float(np.linalg.norm(np.ptp(points,axis=0))),
                repeated_coordinate_visits=len(points)-len(np.unique(points,axis=0))),centre,normal


def controls():
    square = np.array([[0,1,2],[0,2,3]])
    one = fans_and_cycles(square,4);assert len(one['offsets'])-1==1 and len(one['boundary'])==4
    contact = fans_and_cycles(np.array([[0,1,2],[0,3,4]]),5)
    assert len(contact['offsets'])-1==2 and len(contact['boundary'])==6
    assert len(set(contact['from_fans'][contact['boundary'][:,0]==0]))==2
    boundary = np.array([[0,1],[1,2],[2,0]]);owner = np.zeros(3,dtype=int)
    kind,_,_,_ = attribute(boundary,owner,np.array([0]),square,np.array([0,-2]),4,4,{})
    assert Counter(kind)==Counter({1:2,2:1})
    try:attribute(boundary,owner,np.array([0]),square,np.array([0,0]),4,4,{})
    except AssertionError as error:assert 'Unexplained removal' in str(error)
    else:raise AssertionError('Unexplained source loss accepted')
    return dict(shared_square_cycle=True,point_contact_fans_not_joined=True,
                acquisition_and_quarantine_edges_distinguished=True,unexplained_source_loss_refused=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--controls-only',action='store_true')
    args = parser.parse_args();job = json.loads(args.job.read_text());started = time.monotonic()
    assert job['schema']=='935-retained-boundary-origin-1'
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    args.output.mkdir(mode=0o700,exist_ok=False);control = controls()
    if args.controls_only:
        (args.output/'report.json').write_text(json.dumps(dict(controls=control,source_sha256=sha(__file__)))+'\n');return
    original = load(job['arrays']);vertices,raw_faces = original['vertices'],original['triangles']
    body = load(job['retained']);fragments = load(job['fragments']);roles = load(job['roles'])['original_face_roles']
    cuts = np.flatnonzero(fragments['source_vertex_ids']==-1);full_points = np.r_[vertices,fragments['points'][cuts]]
    lookup = {(int(fragments['node_plane_indices'][i]),int(fragments['source_edge_codes'][i])):len(vertices)+j for j,i in enumerate(cuts)}
    cut_regions = {};expected_cut_sets = {}
    region_rows = json.loads(Path(job['source_regions']).read_text())['regions']
    for row in region_rows:
        p = Path(job['source_regions']).parent/('private-region-'+str(row['region'])+'.npz')
        assert sha(p)==row['private_region_sha256'];codes = load(p)['section_edge_codes']
        nodes = [lookup[(row['plane'],int(code))] for code in codes]
        expected_cut_sets[row['region']] = set()
        for a,b in zip(nodes,nodes[1:]+nodes[:1]):
            code = min(a,b)*len(full_points)+max(a,b);assert code not in cut_regions
            cut_regions[code]=row['region'];expected_cut_sets[row['region']].add(code)
    assert np.array_equal(body['points'],full_points[body['global_node_ids']])
    triangles = body['global_node_ids'][body['triangles']];result = fans_and_cycles(triangles,len(full_points))
    boundary,owners = result['boundary'],result['owners'];assert len(boundary)==98874
    kind,raw_curve,declared,raw_summary = attribute(boundary,owners,body['original_face_ids'],raw_faces,roles,len(full_points),len(vertices),cut_regions)
    assert raw_summary==dict(raw_original_open_edges=99876,raw_original_boundary_curves=928)
    atlas = load(job['atlas'])['source_chunk_owner'];rows = [];centres = [];normals = [];seen_cuts = set()
    for i,(start,end) in enumerate(zip(result['offsets'][:-1],result['offsets'][1:])):
        indices = result['cycle_edges'][start:end];ordered = boundary[indices]
        assert np.array_equal(ordered[:,1],np.roll(ordered[:,0],-1))
        stats,centre,normal = geometry(full_points[ordered[:,0]]);centres.append(centre);normals.append(normal)
        counts = dict(Counter(map(int,kind[indices])));region = 0
        if 3 in counts:
            assert set(counts)=={3} and len(set(map(int,declared[indices])))==1
            region = int(declared[indices[0]]);actual = {min(map(int,e))*len(full_points)+max(map(int,e)) for e in ordered}
            assert actual==expected_cut_sets[region];seen_cuts.add(region)
        chunks = np.unique(atlas[body['original_face_ids'][owners[indices]]]);assert chunks.min()>=0
        rows.append(dict(curve=i,edges=len(indices),**stats,edge_origin_counts=counts,
                         source_raw_curve_ids=sorted(set(map(int,raw_curve[indices]))-{-1}),
                         original_atlas_chart_indices=chunks.tolist(),declared_cut_region=region,
                         repeated_original_node_visits=len(ordered)-len(np.unique(ordered[:,0])),
                         physical_classification='unreviewed',closure_authorized=False))
    assert seen_cuts==set(range(1,6))
    np.savez_compressed(args.output/'private-boundary-origins-and-fans.npz',boundary_global_nodes=boundary,
                        boundary_face_rows=owners,from_fan_labels=result['from_fans'],to_fan_labels=result['to_fans'],
                        cycle_offsets=result['offsets'],cycle_boundary_edge_ids=result['cycle_edges'],
                        edge_origin_kind=kind,raw_original_curve_ids=raw_curve,declared_cut_regions=declared,
                        fitted_centres=np.array(centres),fitted_normals=np.array(normals))
    (args.output/'private-curve-review.json').write_text(json.dumps(rows,indent=2)+'\n')
    fields=['curve','edges','perimeter_nominal_mm','affine_rank','plane_maximum_residual_nominal_mm','declared_cut_region','physical_classification','closure_authorized']
    with (args.output/'private-review.csv').open('x',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows({k:r[k] for k in fields} for r in rows)
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    report = dict(source_sha256=sha(__file__),job_sha256=sha(args.job),controls=control,**raw_summary,
                  retained_boundary_edges=len(boundary),retained_boundary_curves=len(rows),
                  indexed_boundary_vertices=len(np.unique(boundary)),surface_fan_boundary_vertices=len(set(map(int,result['from_fans']))),
                  edge_origin_counts=dict(Counter(map(int,kind))),declared_cut_curves=sum(r['declared_cut_region']>0 for r in rows),
                  repeated_node_curves=sum(r['repeated_original_node_visits']>0 for r in rows),
                  repeated_coordinate_curves=sum(r['repeated_coordinate_visits']>0 for r in rows),
                  private_boundary_sha256=sha(args.output/'private-boundary-origins-and-fans.npz'),
                  private_review_sha256=sha(args.output/'private-curve-review.json'),
                  source_geometry_changed=False,any_curve_filled=False,physical_classifications_accepted=0,
                  full_bare_head_created=False,physical_acceptance=False,manufacturing_authorized=False,
                  seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k.endswith('curves') or k.endswith('edges') or k=='edge_origin_counts'}),flush=True)


if __name__=='__main__':main()
