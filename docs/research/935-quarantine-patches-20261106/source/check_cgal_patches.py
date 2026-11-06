"""Independently inspect raw CGAL files against immutable local source masks."""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):
    with np.load(path,allow_pickle=False) as data:return {key:data[key] for key in data.files}


def read_obj(path):
    points = [];faces = []
    for line in Path(path).read_text().splitlines():
        words = line.split()
        if not words or words[0].startswith('#'):continue
        if words[0]=='v':assert len(words)==4;points.append(list(map(float,words[1:])))
        elif words[0]=='f':assert len(words)==4;faces.append([int(x.split('/')[0])-1 for x in words[1:]])
        else:assert words[0] in ('vn','vt','o','g','s','usemtl','mtllib')
    return np.array(points,dtype=np.float64).reshape(-1,3),np.array(faces,dtype=np.int64).reshape(-1,3)


def oriented(face):
    a,b,c = map(int,face);return min((a,b,c),(b,c,a),(c,a,b))


def simple_projection(p):
    def orient(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def on(a,b,c):return orient(a,b,c)==0 and all(min(a[j],b[j])<=c[j]<=max(a[j],b[j]) for j in (0,1))
    if len(set(p))!=len(p):return False
    for i,b in enumerate(p):
        a,c=p[i-1],p[(i+1)%len(p)]
        if orient(a,b,c)==0 and not on(a,c,b):return False
    for i in range(len(p)):
        a,b=p[i],p[(i+1)%len(p)]
        for j in range(i+1,len(p)):
            if j==i+1 or (i==0 and j==len(p)-1):continue
            c,d=p[j],p[(j+1)%len(p)]
            if orient(a,b,c)*orient(a,b,d)<0 and orient(c,d,a)*orient(c,d,b)<0:return False
            if on(a,b,c) or on(a,b,d) or on(c,d,a) or on(c,d,b):return False
    return True


def check_patch(points,source_faces,hole,source_boundary,actual_points,actual_faces):
    assert np.array_equal(source_boundary,np.c_[hole,np.roll(hole,-1)])
    source_edges = Counter((int(a),int(b)) for face in source_faces for a,b in zip(face,np.roll(face,-1)))
    assert all(source_edges[(int(a),int(b))]==1 and source_edges[(int(b),int(a))]==0 for a,b in source_boundary)
    assert np.array_equal(points,actual_points),'CGAL moved, added or reordered input vertices'
    original = Counter(oriented(face) for face in source_faces)
    assert all(n==1 for n in original.values())
    seen = Counter(oriented(face) for face in actual_faces if oriented(face) in original)
    assert seen==original,'CGAL changed original face coverage or orientation'
    added = np.array([face for face in actual_faces if oriented(face) not in original],dtype=np.int64).reshape(-1,3)
    assert len(added)==len(hole)-2 and len({oriented(f) for f in added})==len(added),'Incomplete or duplicated patch'
    assert set(map(int,added.ravel()))==set(map(int,hole)),'Patch escaped exact target vertex mask'
    uses = Counter((int(a),int(b)) for face in added for a,b in zip(face,np.roll(face,-1)))
    boundary = {};edge_count = 0
    for a,b in {tuple(sorted(e)) for e in uses}:
        n,m = uses[(a,b)],uses[(b,a)];assert n<=1 and m<=1
        edge_count+=1
        if n!=m:boundary[(a,b) if n>m else (b,a)]=1
    assert boundary=={(int(b),int(a)):1 for a,b in source_boundary},'Patch did not close only the selected source contour'
    assert len(set(map(int,added.ravel())))-edge_count+len(added)==1
    p = [tuple(F.from_float(float(x)) for x in points[i]) for i in hole]
    area_vector = [sum(a[(j+1)%3]*b[(j+2)%3]-a[(j+2)%3]*b[(j+1)%3] for a,b in zip(p,p[1:]+p[:1])) for j in range(3)]
    drop = max(range(3),key=lambda j:abs(area_vector[j]));assert area_vector[drop]!=0
    axes = [j for j in range(3) if j!=drop]
    assert simple_projection([tuple(point[j] for j in axes) for point in p]),'Source projection not a simple polygon'
    signed_original = sum(a[axes[0]]*b[axes[1]]-a[axes[1]]*b[axes[0]] for a,b in zip(p,p[1:]+p[:1]))
    total = F(0)
    for face in added:
        a,b,c = [tuple(F.from_float(float(x)) for x in points[i]) for i in face]
        i,j = axes;area = (b[i]-a[i])*(c[j]-a[j])-(b[j]-a[j])*(c[i]-a[i])
        assert area*signed_original<0,'Folded, reversed or zero projected patch triangle'
        total+=area
    assert total==-signed_original,'Exact projected patch area does not cover source contour'
    return added,dict(original_vertices_unchanged=True,original_faces_once_and_oriented=True,
                      exact_target_vertex_and_perimeter_mask=True,complete_oriented_disk=True,
                      exact_positive_projected_area_partition=True,added_faces=len(added),dropped_projection_axis=drop)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job','constructed','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--controls-only',action='store_true');parser.add_argument('--prepared',type=Path)
    args = parser.parse_args();job = json.loads(args.job.read_text());started = time.monotonic()
    assert job['schema']=='935-quarantine-patch-trials-1'
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    detector_path = next(Path(row['path']) for row in job['inputs'] if Path(row['path']).name=='inspect_intersections.py')
    assert sha(detector_path)=='3e0b239ca4993388f32563092c78d97065cc1fb0753c68a2def3d631feda7976'
    spec = importlib.util.spec_from_file_location('independent_full_predicate',detector_path)
    detector = importlib.util.module_from_spec(spec);spec.loader.exec_module(detector)
    import igl
    assert Path(igl.__file__).resolve().is_relative_to(Path(job['igl_addon']).resolve())
    raw = json.loads((args.constructed/'report.json').read_text());assert raw['job_sha256']==sha(args.job)
    assert raw['all_owned_children_reaped'] and raw['controls_only']==args.controls_only
    args.output.mkdir(mode=0o700,exist_ok=False);rows = []
    if args.controls_only:
        source = load(args.constructed/'private-control-map.npz')
        literal_points = np.array([[0.,0.,0.],[1.,0.,0.],[1.,1.,0.],[0.,1.,0.],[0.,0.,1.],[1.,0.,1.],[1.,1.,1.],[0.,1.,1.]])
        literal_faces = np.array([[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]])
        assert np.array_equal(source['points'],literal_points) and np.array_equal(source['triangles'],literal_faces)
        assert np.array_equal(source['ordered_hole_nodes'],np.arange(4))
        points,faces = read_obj(args.constructed/'positive/candidate.obj')
        added,checks = check_patch(source['points'],source['triangles'],source['ordered_hole_nodes'],source['expected_source_boundary_edges'],points,faces)
        pairs,_,excluded = detector.detect(points,faces);assert not len(pairs) and not len(excluded)
        edges = Counter(tuple(sorted((int(a),int(b)))) for face in faces for a,b in zip(face,np.roll(face,-1)))
        assert {edge for edge,n in edges.items() if n==1}=={(4,5),(5,6),(6,7),(4,7)},'Unselected second opening was closed'
        assert raw['trials'][0]['exit_code']==0 and raw['trials'][1]['exit_code']!=0
        assert not (args.constructed/'negative/candidate.obj').exists()
        result = dict(native_controls_independently_verified=True,known_selected_hole_filled_completely=True,
                      second_unselected_hole_preserved=True,nonboundary_edge_request_refused=True,
                      full_control_intersections=0,predicate_excluded_faces=0,checks=checks)
    else:
        assert args.prepared is not None
        preparation = json.loads((args.prepared/'report.json').read_text());assert preparation['job_sha256']==sha(args.job)
        body = load(job['retained']);boundary_data = load(job['boundaries'])
        metadata = {item['curve']:item for item in preparation['private_targets'] if item['admitted']}
        assert len(raw['trials'])==len(metadata)
        for trial in raw['trials']:
            index = trial['curve'];item = metadata[index];name = 'curve-'+str(index).zfill(4)
            path = args.prepared/name;mapping = load(path/'private-halo-map.npz')
            assert sha(path/'private-halo-map.npz')==item['halo_map_sha256']
            assert sha(path/'input.obj')==item['input_OBJ_sha256'] and sha(path/'target-edges.txt')==item['target_sha256']
            assert np.array_equal(mapping['points'],body['points'][mapping['source_body_vertex_ids']])
            assert np.array_equal(mapping['source_body_vertex_ids'][mapping['triangles']],body['triangles'][mapping['body_face_rows']])
            a,b = boundary_data['cycle_offsets'][index:index+2];ids = boundary_data['cycle_boundary_edge_ids'][a:b]
            assert np.all(boundary_data['edge_origin_kind'][ids]==2)
            assert np.array_equal(mapping['original_global_hole_nodes'],boundary_data['boundary_global_nodes'][ids,0])
            assert np.array_equal(body['global_node_ids'][mapping['source_body_vertex_ids'][mapping['ordered_hole_nodes']]],mapping['original_global_hole_nodes'])
            output = args.constructed/name/'candidate.obj'
            if trial['exit_code']!=0 or not output.is_file():
                rows.append(dict(curve=index,accepted=False,reason='native_constructor_refusal',native_exit_code=trial['exit_code']));continue
            assert sha(output)==trial['output_OBJ_sha256']
            try:
                source_points,source_faces = read_obj(path/'input.obj')
                assert np.array_equal(source_points,mapping['points']) and np.array_equal(source_faces,mapping['triangles'])
                points,faces = read_obj(output)
                added,checks = check_patch(mapping['points'],mapping['triangles'],mapping['ordered_hole_nodes'],mapping['expected_source_boundary_edges'],points,faces)
                global_faces = mapping['source_body_vertex_ids'][faces]
                used,inverse = np.unique(global_faces,return_inverse=True)
                pairs,_,excluded = detector.detect(body['points'][used],inverse.reshape(-1,3))
                assert not len(pairs) and not len(excluded),'Local patch intersects source halo or has excluded faces'
            except (AssertionError,ValueError) as error:
                rows.append(dict(curve=index,accepted=False,reason=str(error),native_exit_code=trial['exit_code']));continue
            patch = args.output/('private-patch-'+str(index).zfill(4)+'.npz')
            np.savez_compressed(patch,source_body_vertex_triangles=mapping['source_body_vertex_ids'][added],source_curve_index=np.array(index),
                                raw_quarantine_source_facets=mapping['raw_quarantine_facets'])
            rows.append(dict(curve=index,accepted=True,reason='masked_local_surface_hypothesis_passed',checks=checks,
                             local_intersection_pairs=0,local_predicate_excluded_faces=0,private_patch_sha256=sha(patch),
                             raw_constructor_output_sha256=sha(output),physical_role_accepted=False))
        result = dict(native_controls_independently_verified=False,complete_prepared_trial_denominator=len(metadata),
                      accepted_local_patches=sum(row['accepted'] for row in rows),rejected_local_patches=sum(not row['accepted'] for row in rows),
                      private_patch_results=rows,full_candidate_intersection_check_still_required=True)
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    result.update(source_sha256=sha(__file__),job_sha256=sha(args.job),constructor_source_sha256=raw['source_sha256'],
                  constructor_report_sha256=sha(args.constructed/'report.json'),controls_only=args.controls_only,
                  original_source_geometry_moved=False,physical_acceptance=False,manufacturing_authorized=False,
                  full_bare_head_created=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k in ('native_controls_independently_verified','complete_prepared_trial_denominator','accepted_local_patches','rejected_local_patches','seconds')}),flush=True)


if __name__=='__main__':main()
