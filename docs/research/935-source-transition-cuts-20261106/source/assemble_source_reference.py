"""Assemble and independently inspect source-faithful open references after local cuts."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    return hashlib.file_digest(Path(path).open('rb'),'sha256').hexdigest()


def arrays(path):
    with np.load(path,allow_pickle=False) as data:return {key:data[key] for key in data.files}


def write_reference(target,full_points,global_triangles,original_ids,fragment_ids):
    used,inverse = np.unique(global_triangles,return_inverse=True)
    points = full_points[used];triangles = inverse.reshape(-1,3)
    np.savez_compressed(target.with_suffix('.npz'),points=points,triangles=triangles,
                        global_node_ids=used,original_face_ids=original_ids,source_fragment_indices=fragment_ids)
    with target.with_suffix('.obj').open('x') as stream:
        stream.write('# Open source reference with explicit hypothetical local component cuts; no caps.\n')
        stream.write('# Owner nominal units; anatomy, physical metrology and manufacturing unqualified.\n')
        stream.write('o '+target.name+'\n')
        for p in points:stream.write('v '+' '.join(format(float(x),'.17g') for x in p)+'\n')
        for tri in triangles:stream.write('f '+' '.join(str(int(i)+1) for i in tri)+'\n')
    return dict(name=target.name,triangles=len(triangles),vertices=len(points),
                OBJ_sha256=sha(target.with_suffix('.obj')),NPZ_sha256=sha(target.with_suffix('.npz')))


def edge_inventory(triangles,vertex_count):
    edges = np.stack((triangles[:,[0,1]],triangles[:,[1,2]],triangles[:,[2,0]]),axis=1).reshape(-1,2)
    code = edges.min(axis=1)*vertex_count+edges.max(axis=1)
    order = np.argsort(code,kind='stable');ordered = code[order]
    first = np.r_[0,np.flatnonzero(ordered[1:]!=ordered[:-1])+1]
    uses = np.diff(np.r_[first,len(order)])
    assert np.all((uses==1)|(uses==2))
    twice = first[uses==2]
    assert np.array_equal(edges[order[twice]],edges[order[twice+1]][:,::-1]),'Source edge winding mismatch'
    return ordered[first],uses,edges[order[first]]


def inspect_reference(target,region,vertices,faces,roles,fragments,node_map,full_points,expected_sections):
    data = arrays(target.with_suffix('.npz'));nodes = data['global_node_ids']
    tri = data['triangles'];original = data['original_face_ids'];indices = data['source_fragment_indices']
    assert nodes.ndim==1 and len(set(map(int,nodes)))==len(nodes)
    assert nodes.min()>=0 and nodes.max()<len(full_points)
    assert np.array_equal(data['points'],full_points[nodes])
    actual = nodes[tri]
    assert np.array_equal(np.unique(actual),np.sort(nodes)) and len(original)==len(indices)==len(tri)
    plain = indices==-1;clipped = ~plain
    expected_plain = np.flatnonzero(roles==region)
    assert Counter(map(int,original[plain]))==Counter(map(int,expected_plain))
    assert np.array_equal(actual[plain],faces[original[plain]])
    wanted_fragment = np.flatnonzero(fragments['triangle_halfspaces']<0) if region==0 else np.flatnonzero(
        (fragments['triangle_halfspaces']>0)&(fragments['triangle_regions']==region))
    assert Counter(map(int,indices[clipped]))==Counter(map(int,wanted_fragment))
    assert np.array_equal(original[clipped],fragments['parent_source_face_ids'][indices[clipped]])
    assert np.array_equal(actual[clipped],node_map[fragments['triangles'][indices[clipped]]])
    # Actual OBJ values are parsed independently after NPZ/source coverage is established.
    before = sha(target.with_suffix('.obj'));vcount = fcount = 0
    with target.with_suffix('.obj').open() as stream:
        for line in stream:
            words = line.split()
            if not words or words[0].startswith('#') or words[0]=='o':continue
            assert len(words)==4
            if words[0]=='v':
                assert vcount<len(nodes) and np.array_equal(np.array(list(map(float,words[1:]))),full_points[nodes[vcount]])
                vcount+=1
            else:
                assert words[0]=='f' and fcount<len(tri)
                numbers = np.array([int(x)-1 for x in words[1:]])
                assert np.all(numbers>=0) and np.all(numbers<len(nodes))
                assert np.array_equal(nodes[numbers],actual[fcount]);fcount+=1
    assert vcount==len(nodes) and fcount==len(tri) and sha(target.with_suffix('.obj'))==before
    edge_codes,uses,direction = edge_inventory(actual,len(full_points))
    expected = expected_sections[region]
    locations = np.searchsorted(edge_codes,expected)
    assert np.all(locations<len(edge_codes)) and np.array_equal(edge_codes[locations],expected)
    assert np.all(uses[locations]==1),'Constructed section is not a one-use interface'
    return dict(region=region,original_whole_triangles=len(expected_plain),clipped_transition_fragments=len(wanted_fragment),
                actual_OBJ_vertices=vcount,actual_OBJ_triangles=fcount,edges=len(edge_codes),boundary_edges=int(np.count_nonzero(uses==1)),
                original_triangle_coverage_and_coordinates_exact=True,actual_OBJ_readback_exact=True,
                expected_cut_section_edges_are_one_use=True,source_edge_winding_preserved=True,
                OBJ_sha256=before,NPZ_sha256=sha(target.with_suffix('.npz'))),direction[locations]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job','fragments','proof','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--built',type=Path);parser.add_argument('--mode',choices=('build','check'),required=True)
    args = parser.parse_args();job = json.loads(args.job.read_text());started = time.monotonic()
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    assert job['schema']=='935-source-transition-cuts-1'
    proof = json.loads(args.proof.read_text())
    assert proof['source_sha256']=='06bc7701651dcaef4ee632783fe8d715ecd2110f214ef833a7352f84ce858f54'
    assert proof['job_sha256']==sha(args.job) and proof['fragments_sha256']==sha(args.fragments)
    assert proof['each_original_triangle_exactly_tiled_by_two_opposite_halves']
    args.output.mkdir(mode=0o700,exist_ok=False)
    source = arrays(job['arrays']);vertices,faces = source['vertices'],source['triangles']
    roles = arrays(job['source_partition'])['original_face_roles']
    admission = arrays(job['admission']);admitted = admission['admitted_source_face_ids'];quarantine = admission['quarantined_source_face_ids']
    assert np.all(roles[quarantine]==-2) and np.array_equal(np.flatnonzero(roles!=-2),admitted)
    fragments = arrays(args.fragments);parents = fragments['parent_source_face_ids']
    assert np.array_equal(np.flatnonzero(roles==-1),np.unique(parents))
    source_nodes = fragments['source_vertex_ids'];new = np.flatnonzero(source_nodes==-1)
    node_map = source_nodes.copy();node_map[new] = len(vertices)+np.arange(len(new))
    full_points = np.r_[vertices,fragments['points'][new]]
    original = source_nodes>=0;assert np.array_equal(fragments['points'][original],vertices[source_nodes[original]])
    rows = [];directions = {};section_codes = {};region_rows = json.loads(Path(job['admitted_regions']).read_text())['regions']
    for row in region_rows:
        path = Path(job['admitted_regions']).parent/('private-region-'+str(row['region'])+'.npz')
        assert sha(path)==row['private_region_sha256'];data = arrays(path);plane = row['plane']
        lookup = {(int(fragments['node_plane_indices'][i]),int(fragments['source_edge_codes'][i])):int(node_map[i]) for i in new}
        nodes = np.array([lookup[(plane,int(code))] for code in data['section_edge_codes']])
        section_codes[row['region']] = np.sort(np.minimum(nodes,np.roll(nodes,-1))*len(full_points)+np.maximum(nodes,np.roll(nodes,-1)))
    section_codes[0] = np.sort(np.concatenate([section_codes[i] for i in range(1,6)]))
    assert len(np.unique(section_codes[0]))==726
    for region in range(6):
        name = 'retained-source-after-local-cuts' if region==0 else 'provisional-source-region-'+str(region)
        if args.mode=='build':
            plain = np.flatnonzero(roles==region)
            pieces = np.flatnonzero(fragments['triangle_halfspaces']<0) if region==0 else np.flatnonzero(
                (fragments['triangle_halfspaces']>0)&(fragments['triangle_regions']==region))
            all_faces = np.r_[faces[plain],node_map[fragments['triangles'][pieces]]]
            rows.append(write_reference(args.output/name,full_points,all_faces,np.r_[plain,parents[pieces]],np.r_[np.full(len(plain),-1,dtype=np.int64),pieces]))
        else:
            assert args.built is not None
            result,direction = inspect_reference(args.built/name,region,vertices,faces,roles,fragments,node_map,full_points,section_codes)
            rows.append(result);directions[region] = direction
        print(json.dumps(dict(mode=args.mode,region=region,complete=True)),flush=True)
    reconciliation = None
    if args.mode=='check':
        for region in range(1,6):
            positions = np.searchsorted(section_codes[0],section_codes[region])
            assert np.array_equal(directions[0][positions],directions[region][:,::-1])
        original_codes,original_uses,_ = edge_inventory(faces[admitted],len(full_points))
        boundary = int(np.count_nonzero(original_uses==1));edge_sum = sum(row['edges'] for row in rows)
        boundary_sum = sum(row['boundary_edges'] for row in rows)
        assert edge_sum==len(original_codes)+3*726+726
        assert boundary_sum==boundary+2*726
        assert sum(row['actual_OBJ_triangles'] for row in rows)==len(admitted)+2*726
        reconciliation = dict(admitted_original_edges=len(original_codes),original_boundary_edges=boundary,
                              new_shared_section_nodes=726,source_edge_subdivisions=726,quad_fan_diagonals=726,
                              section_segments=726,separate_mesh_edge_sum=edge_sum,separate_mesh_boundary_sum=boundary_sum,
                              exact_edge_and_boundary_reconciliation=True,body_and_outward_interfaces_oppositely_oriented=True)
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    assert sha(args.fragments)==proof['fragments_sha256']
    report = dict(source_sha256=sha(__file__),job_sha256=sha(args.job),mode=args.mode,references=rows,
                  reconciliation=reconciliation,unresolved_original_holes_filled=False,
                  caps_or_hidden_surfaces_added=False,original_scan_modified=False,full_bare_head_created=False,
                  physical_acceptance=False,manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
