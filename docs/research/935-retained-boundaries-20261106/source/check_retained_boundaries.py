"""Rejoin complete boundaries with structured edge sorting and local face-link BFS."""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):
    with np.load(path,allow_pickle=False) as data:return {key:data[key] for key in data.files}


def complete_boundary(faces):
    n = len(faces);edges = np.concatenate((faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]))
    pairs,first,uses = np.unique(np.sort(edges,axis=1),axis=0,return_index=True,return_counts=True)
    return pairs[uses==1],edges[first[uses==1]],first[uses==1]%n


def canonical_fans(faces,boundary,owners,vertex_count):
    selected = np.zeros(vertex_count,dtype=bool);selected[np.unique(boundary)] = True
    links = defaultdict(lambda:defaultdict(list));count = len(faces)
    for row in np.flatnonzero(selected[faces].any(axis=1)):
        triangle = list(map(int,faces[row]))
        for i,v in enumerate(triangle):
            if selected[v]:
                for j in ((i+1)%3,(i+2)%3):links[v][triangle[j]].append(int(row))
    corner = {}
    for v,neighbors in links.items():
        adjacency = defaultdict(set)
        for uses in neighbors.values():
            assert len(uses) in (1,2) and len(set(uses))==len(uses)
            for row in uses:adjacency[row]
            if len(uses)==2:
                a,b = uses;adjacency[a].add(b);adjacency[b].add(a)
        remaining = set(adjacency)
        while remaining:
            pending = [min(remaining)];group = set()
            while pending:
                row = pending.pop()
                if row in group:continue
                group.add(row);pending.extend(adjacency[row]-group)
            remaining-=group;identity = v*count+min(group)
            for row in group:corner[v*count+row] = identity
    start = [corner[int(v)*count+int(row)] for v,row in zip(boundary[:,0],owners)]
    end = [corner[int(v)*count+int(row)] for v,row in zip(boundary[:,1],owners)]
    assert Counter(start)==Counter(end) and all(n==1 for n in Counter(start).values())
    return np.array(start,dtype=np.int64),np.array(end,dtype=np.int64)


def inspect_cycles(data,faces,rows,points,vertex_count,atlas,parent_ids):
    pairs,boundary,owners = complete_boundary(faces)
    assert np.array_equal(data['boundary_global_nodes'],boundary),'Incomplete or changed boundary edge inventory'
    assert np.array_equal(data['boundary_face_rows'],owners)
    start,end = canonical_fans(faces,boundary,owners,vertex_count)
    forward = {};reverse = {}
    for actual,claimed in zip(np.r_[start,end],np.r_[data['from_fan_labels'],data['to_fan_labels']]):
        actual,claimed = int(actual),int(claimed)
        assert forward.setdefault(actual,claimed)==claimed and reverse.setdefault(claimed,actual)==actual,'Incorrect vertex-fan partition'
    offsets = data['cycle_offsets'];flat = data['cycle_boundary_edge_ids']
    assert offsets[0]==0 and offsets[-1]==len(boundary) and np.all(np.diff(offsets)>=3)
    assert np.array_equal(np.sort(flat),np.arange(len(boundary))) and len(rows)==len(offsets)-1
    for index,(a,b) in enumerate(zip(offsets[:-1],offsets[1:])):
        ids = flat[a:b];edges = boundary[ids];record = rows[index]
        assert record['curve']==index and record['edges']==len(ids)
        assert np.array_equal(end[ids],np.roll(start[ids],-1)),'Boundary walk jumps between surface fans'
        assert np.array_equal(edges[:,1],np.roll(edges[:,0],-1))
        p = points[edges[:,0]];centre = np.array([math.fsum(map(float,p[:,j]))/len(p) for j in range(3)])
        assert np.linalg.norm(centre-data['fitted_centres'][index])<=1e-8
        normal = data['fitted_normals'][index];assert abs(float(normal@normal)-1)<1e-12
        distances = [abs(math.fsum(float((v-c)*n) for v,c,n in zip(point,data['fitted_centres'][index],normal))) for point in p]
        perimeter = math.fsum(math.dist(x,y) for x,y in zip(p,np.roll(p,-1,axis=0)))
        assert abs(perimeter-record['perimeter_nominal_mm'])<=1e-8
        if record['affine_rank']>=2:
            assert abs(max(distances)-record['plane_maximum_residual_nominal_mm'])<=1e-8
            assert abs(math.sqrt(math.fsum(d*d for d in distances)/len(p))-record['plane_RMS_residual_nominal_mm'])<=1e-8
        else:
            assert record['plane_maximum_residual_nominal_mm'] is None and record['plane_RMS_residual_nominal_mm'] is None
        assert record['repeated_original_node_visits']==len(p)-len(np.unique(edges[:,0]))
        assert record['repeated_coordinate_visits']==len(p)-len(np.unique(p,axis=0))
        assert record['original_atlas_chart_indices']==np.unique(atlas[parent_ids[owners[ids]]]).tolist()
        assert record['closure_authorized'] is False and record['physical_classification']=='unreviewed'
    return boundary,owners,start,end


def raw_curve_map(raw_faces):
    pairs,_,_ = complete_boundary(raw_faces)
    adjacency = defaultdict(set)
    for a,b in pairs:
        a,b = int(a),int(b);adjacency[a].add(b);adjacency[b].add(a)
    assert all(len(value)==2 for value in adjacency.values())
    remaining = set(adjacency);vertex_curve = {};count = 0
    while remaining:
        pending = [min(remaining)];group = set()
        while pending:
            v = pending.pop()
            if v in group:continue
            group.add(v);pending.extend(adjacency[v]-group)
        remaining-=group
        for v in group:vertex_curve[v]=count
        count+=1
    return {tuple(map(int,pair)):vertex_curve[int(pair[0])] for pair in pairs},count


def inspect_origins(raw_faces,roles,parent_ids,boundary,owners,data,original_vertex_count,cut_map,vertex_count):
    original_queries = {tuple(sorted(map(int,e))) for e in boundary if max(e)<original_vertex_count}
    used_vertices = np.array(sorted({v for pair in original_queries for v in pair}),dtype=np.int64)
    mask = np.zeros(original_vertex_count,dtype=bool);mask[used_vertices]=True
    incident = {pair:[] for pair in original_queries}
    for row in np.flatnonzero(mask[raw_faces].sum(axis=1)>=2):
        tri = list(map(int,raw_faces[row]))
        for a,b in zip(tri,tri[1:]+tri[:1]):
            pair = tuple(sorted((a,b)))
            if pair in incident:incident[pair].append(int(row))
    raw_curves,count = raw_curve_map(raw_faces);kinds = [];original_curve = [];cut_regions = []
    for edge,row in zip(boundary,owners):
        a,b = map(int,edge);pair = tuple(sorted((a,b)));parent = int(parent_ids[row])
        if min(a,b)>=original_vertex_count:
            code = pair[0]*vertex_count+pair[1];assert code in cut_map
            kinds.append(3);original_curve.append(-1);cut_regions.append(cut_map[code]);continue
        assert max(a,b)<original_vertex_count
        actual = incident[pair];assert actual.count(parent)==1
        others = [i for i in actual if i!=parent]
        if others:
            assert all(roles[i]==-2 for i in others),'Unexplained acquired surface loss'
            kinds.append(2);original_curve.append(-1);cut_regions.append(0)
        else:
            kinds.append(1);original_curve.append(raw_curves[pair]);cut_regions.append(0)
    assert np.array_equal(data['edge_origin_kind'],kinds)
    assert np.array_equal(data['raw_original_curve_ids'],original_curve)
    assert np.array_equal(data['declared_cut_regions'],cut_regions)
    return dict(raw_original_open_edges=len(raw_curves),raw_original_boundary_curves=count,
                independently_rejoined_retained_edge_origins=dict(Counter(kinds)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job','built','output'):parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args();job = json.loads(args.job.read_text());started = time.monotonic()
    assert job['schema']=='935-retained-boundary-origin-1'
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    args.output.mkdir(mode=0o700,exist_ok=False)
    producer = json.loads((args.built/'report.json').read_text())
    file = args.built/'private-boundary-origins-and-fans.npz';review = args.built/'private-curve-review.json'
    assert producer['job_sha256']==sha(args.job) and producer['private_boundary_sha256']==sha(file) and producer['private_review_sha256']==sha(review)
    data = load(file);rows = json.loads(review.read_text());original = load(job['arrays']);body = load(job['retained'])
    fragments = load(job['fragments']);source_vertices = original['vertices'];new = np.flatnonzero(fragments['source_vertex_ids']==-1)
    full_points = np.r_[source_vertices,fragments['points'][new]]
    assert np.array_equal(body['points'],full_points[body['global_node_ids']])
    faces = body['global_node_ids'][body['triangles']];atlas = load(job['atlas'])['source_chunk_owner']
    boundary,owners,start,end = inspect_cycles(data,faces,rows,full_points,len(full_points),atlas,body['original_face_ids'])
    lookup = {(int(fragments['node_plane_indices'][i]),int(fragments['source_edge_codes'][i])):len(source_vertices)+n for n,i in enumerate(new)}
    cut_map = {};cut_sets = {}
    for row in json.loads(Path(job['source_regions']).read_text())['regions']:
        path = Path(job['source_regions']).parent/('private-region-'+str(row['region'])+'.npz');assert sha(path)==row['private_region_sha256']
        nodes = [lookup[(row['plane'],int(code))] for code in load(path)['section_edge_codes']];cut_sets[row['region']]=set()
        for a,b in zip(nodes,nodes[1:]+nodes[:1]):
            code = min(a,b)*len(full_points)+max(a,b);cut_map[code]=row['region'];cut_sets[row['region']].add(code)
    origin = inspect_origins(original['triangles'],load(job['roles'])['original_face_roles'],body['original_face_ids'],boundary,owners,data,len(source_vertices),cut_map,len(full_points))
    seen = set()
    for row,a,b in zip(rows,data['cycle_offsets'][:-1],data['cycle_offsets'][1:]):
        indices = data['cycle_boundary_edge_ids'][a:b]
        assert row['edge_origin_counts']=={str(k):v for k,v in Counter(map(int,data['edge_origin_kind'][indices])).items()}
        assert row['source_raw_curve_ids']==sorted(set(map(int,data['raw_original_curve_ids'][indices]))-{-1})
        region = row['declared_cut_region']
        if region:
            actual = {min(map(int,e))*len(full_points)+max(map(int,e)) for e in boundary[indices]}
            assert actual==cut_sets[region] and region not in seen;seen.add(region)
    assert seen==set(range(1,6))
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    result = dict(source_sha256=sha(__file__),job_sha256=sha(args.job),producer_report_sha256=sha(args.built/'report.json'),
                  **origin,all_retained_boundary_edges_independently_enumerated=len(boundary),
                  all_surface_vertex_fans_independently_rejoined=True,all_oriented_cycles_cover_every_edge_once=True,
                  all_curve_geometry_and_source_chart_links_checked=True,declared_cut_cycles_verified=5,
                  retained_curves=len(rows),physical_classifications_accepted=0,any_curve_filled=False,
                  source_geometry_modified=False,full_bare_head_created=False,manufacturing_authorized=False,
                  seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print('COMPLETE_RETAINED_BOUNDARY_ORIGINS_AND_FANS_VERIFIED',flush=True)


if __name__=='__main__':main()
