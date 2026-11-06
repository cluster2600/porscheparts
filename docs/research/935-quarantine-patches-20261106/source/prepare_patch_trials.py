"""Prepare explicit quarantine-only local source masks and immutable CGAL halo inputs."""
import argparse
from collections import defaultdict
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


def module(path,name,expected):
    assert sha(path)==expected
    spec = importlib.util.spec_from_file_location(name,path)
    result = importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def projection(points):
    exact = [tuple(F.from_float(float(x)) for x in point) for point in points]
    vector = [sum(a[(j+1)%3]*b[(j+2)%3]-a[(j+2)%3]*b[(j+1)%3]
                  for a,b in zip(exact,exact[1:]+exact[:1])) for j in range(3)]
    if not any(vector):return None,None
    drop = max(range(3),key=lambda j:abs(vector[j]));axes = [j for j in range(3) if j!=drop]
    return drop,[tuple(p[j] for j in axes) for p in exact]


def quarantine_groups(raw_faces,quarantine,pairs):
    parent = {int(i):int(i) for i in quarantine};edges = defaultdict(list)
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    def join(a,b):
        a,b = root(int(a)),root(int(b))
        if a!=b:parent[max(a,b)]=min(a,b)
    for identity in quarantine:
        tri = list(map(int,raw_faces[identity]))
        for a,b in zip(tri,tri[1:]+tri[:1]):edges[tuple(sorted((a,b)))].append(int(identity))
    for uses in edges.values():
        for b in uses[1:]:join(uses[0],b)
    for a,b in pairs:
        assert int(a) in parent and int(b) in parent;join(a,b)
    return {i:root(i) for i in parent},edges


def write_obj(path,points,faces):
    with path.open('x') as stream:
        for point in points:stream.write('v '+' '.join(format(float(x),'.17g') for x in point)+'\n')
        for face in faces:stream.write('f '+' '.join(str(int(x)+1) for x in face)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job','baseline','output','builder','polygon-checker'):parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args();job = json.loads(args.job.read_text());started = time.monotonic()
    assert job['schema']=='935-quarantine-patch-trials-1'
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    proof = json.loads(args.baseline.read_text())
    assert proof['source_sha256']=='3e0b239ca4993388f32563092c78d97065cc1fb0753c68a2def3d631feda7976'
    assert proof['mesh_sha256']==job['retained_sha256'] and proof['admissible_for_masked_local_patch_trials']
    boundary_proof = json.loads(Path(job['boundary_proof']).read_text())
    assert boundary_proof['source_sha256']=='68c0d319a02417bb12a52135c4f38d979ab1814688ec47d9c53ab39dd0be4d94'
    assert boundary_proof['all_surface_vertex_fans_independently_rejoined']
    args.output.mkdir(mode=0o700,exist_ok=False)
    builder = module(args.builder,'frozen_source_fan_splitter','fca5259ef3b3412a72e441fea39816e14fea4e375095e1c83def2e4117f6ae8e')
    polygon_checker = module(args.polygon_checker,'frozen_exact_section_checker','5a657fb1095d0c87231c890b92bc40bd5bf2e85e8e51cab2cbca4fccf832f54f')
    body = load(job['retained']);raw = load(job['arrays']);role = load(job['roles'])['original_face_roles']
    boundary = load(job['boundaries']);review = json.loads(Path(job['review']).read_text())
    q = np.flatnonzero(role==-2);pairs = np.load(job['intersection_pairs'],allow_pickle=False)
    groups,qedges = quarantine_groups(raw['triangles'],q,pairs)
    targets = [row for row in review if set(row['edge_origin_counts'])=={'2'}];assert len(targets)==59
    body_nodes = body['global_node_ids'];assert np.array_equal(body_nodes,np.sort(body_nodes))
    all_target = np.unique(np.concatenate([boundary['boundary_global_nodes'][
        boundary['cycle_boundary_edge_ids'][boundary['cycle_offsets'][row['curve']]:boundary['cycle_offsets'][row['curve']+1]],0] for row in targets]))
    compact_target = np.searchsorted(body_nodes,all_target);assert np.array_equal(body_nodes[compact_target],all_target)
    flags = np.zeros(len(body_nodes),dtype=bool);flags[compact_target]=True
    incident = defaultdict(list)
    for face in np.flatnonzero(flags[body['triangles']].any(axis=1)):
        for v in body['triangles'][face]:
            if flags[v]:incident[int(v)].append(int(face))
    rows = []
    for target in targets:
        index = target['curve'];a,b = boundary['cycle_offsets'][index:index+2]
        edge_ids = boundary['cycle_boundary_edge_ids'][a:b];global_edges = boundary['boundary_global_nodes'][edge_ids]
        nodes = global_edges[:,0];compact = np.searchsorted(body_nodes,nodes);points = body['points'][compact]
        assert np.array_equal(body_nodes[compact],nodes) and np.all(boundary['edge_origin_kind'][edge_ids]==2)
        qfaces = sorted({i for edge in global_edges for i in qedges[tuple(sorted(map(int,edge)))]})
        assert qfaces and all(role[i]==-2 for i in qfaces)
        row = dict(curve=index,boundary_edges=len(edge_ids),raw_quarantine_facets=qfaces,
                   original_defect_coupling_groups=sorted({groups[i] for i in qfaces}),
                   source_acquisition_edges_in_target=0,physical_role_accepted=False)
        if len(np.unique(points,axis=0))!=len(points):
            row.update(admitted=False,reason='self_contact_source_boundary');rows.append(row);continue
        drop,polygon = projection(points)
        if drop is None or not polygon_checker.simple(polygon):
            row.update(admitted=False,reason='non_simple_or_zero_exact_projection');rows.append(row);continue
        halo = np.array(sorted({i for v in compact for i in incident[int(v)]}),dtype=np.int64)
        used,inverse = np.unique(body['triangles'][halo],return_inverse=True)
        v,f,mapping,components,counts = builder.atlas(body['points'][used],inverse.reshape(-1,3))
        assert np.array_equal(used[mapping[f]],body['triangles'][halo])
        wanted = []
        for edge,owner in zip(global_edges,boundary['boundary_face_rows'][edge_ids]):
            local_face = int(np.searchsorted(halo,owner));assert halo[local_face]==owner
            original_face = body_nodes[body['triangles'][owner]].tolist();pairs_in_face = list(zip(original_face,original_face[1:]+original_face[:1]))
            corner = pairs_in_face.index(tuple(map(int,edge)))
            wanted.append((int(f[local_face,corner]),int(f[local_face,(corner+1)%3])))
        wanted = np.array(wanted,dtype=np.int64);assert np.array_equal(wanted[:,1],np.roll(wanted[:,0],-1))
        assert len(np.unique(wanted[:,0]))==len(points)
        path = args.output/('curve-'+str(index).zfill(4));path.mkdir(mode=0o700,exist_ok=False)
        write_obj(path/'input.obj',v,f)
        (path/'target-edges.txt').write_text(str(index)+' '+str(wanted[0,0])+' '+str(wanted[0,1])+'\n')
        np.savez_compressed(path/'private-halo-map.npz',points=v,triangles=f,source_body_vertex_ids=used[mapping],
                            body_face_rows=halo,ordered_hole_nodes=wanted[:,0],expected_source_boundary_edges=wanted,
                            original_global_hole_nodes=nodes,raw_quarantine_facets=np.array(qfaces,dtype=np.int64))
        centred = points-points.mean(axis=0);_,_,axes = np.linalg.svd(centred,full_matrices=False)
        normal = axes[-1];plane_residual = float(np.abs(centred@normal).max())
        adjacent = body['points'][body['triangles'][boundary['boundary_face_rows'][edge_ids]]]
        normals = np.cross(adjacent[:,1]-adjacent[:,0],adjacent[:,2]-adjacent[:,0]);normals/=np.linalg.norm(normals,axis=1)[:,None]
        row.update(admitted=True,reason='quarantine_only_simple_exact_projection_local_surface_trial',
                   dropped_projection_axis=drop,halo_faces=len(f),halo_vertex_objects=len(v),halo_source_body_vertices=len(used),
                   local_point_contact_fan_splits=len(v)-len(used),native_source_topology=counts,
                   diagnostic_fitted_plane_maximum_nominal_mm=plane_residual,
                   diagnostic_adjacent_normal_absolute_alignment_p10=float(np.quantile(np.abs(normals@normal),.1)),
                   diagnostics_are_not_physical_tolerances=True,input_OBJ_sha256=sha(path/'input.obj'),
                   target_sha256=sha(path/'target-edges.txt'),halo_map_sha256=sha(path/'private-halo-map.npz'))
        rows.append(row)
    report = dict(source_sha256=sha(__file__),job_sha256=sha(args.job),baseline_report_sha256=sha(args.baseline),
                  complete_target_denominator=59,admitted_local_trials=sum(row['admitted'] for row in rows),
                  rejected_targets=sum(not row['admitted'] for row in rows),quarantined_raw_facets=len(q),
                  raw_intersection_pairs_rejoined=len(pairs),original_defect_coupling_groups=len(set(groups.values())),
                  private_targets=rows,source_points_or_base_faces_changed=False,physical_classifications_accepted=0,
                  manufacturing_authorized=False,seconds=time.monotonic()-started)
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('private_targets',)}),flush=True)


if __name__=='__main__':main()
