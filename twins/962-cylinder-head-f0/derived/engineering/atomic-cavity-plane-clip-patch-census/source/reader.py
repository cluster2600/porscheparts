"""Read-only clipped poor/incident-patch census; no coordinate or topology mutation."""
import ast
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import struct
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
HELPER = 'twins/962-cylinder-head-f0/source/audit_quality_head.py'


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576), b''):
            result.update(block)
    return result.hexdigest()


def verify(c):
    for name, expected in c['input_hashes'].items():
        relative = Path(name); path = ROOT/relative
        if relative.is_absolute() or '..' in relative.parts or path.is_symlink() or sha(path) != expected:
            raise ValueError('Bound census input drift: '+name)
    if sha(Path(sys.executable).resolve()) != c['runtime']['python_executable_sha256']:
        raise ValueError('Selected interpreter changed')


def main():
    c = json.loads((OUT/'frozen-contract.json').read_text()); contract_sha = sha(OUT/'frozen-contract.json')
    if c['readback_launch_authorized'] is not True or OUT != (ROOT/c['expected_fresh_output']).resolve():
        raise ValueError('Separate reviewed launch required')
    if (OUT/'readback-report.json').exists() or (OUT/'readback-report.json').is_symlink():
        raise ValueError('Fresh report required; prior results preserved')
    verify(c)
    spec = importlib.util.spec_from_file_location('frozen_patch_census_kernels',OUT/'patch_kernels.py')
    kernels = importlib.util.module_from_spec(spec); spec.loader.exec_module(kernels)
    face_groups, incidence, link_status, topology, vertex_contacts = (getattr(kernels,n) for n in
        ('face_groups','incidence','link_status','topology','vertex_contacts'))
    if platform.machine() != 'arm64' or np.__version__ != c['runtime']['numpy_version']:
        raise ValueError('Retained ARM NumPy version required')
    definitions = [n for n in ast.parse((ROOT/HELPER).read_text()).body if isinstance(n, ast.FunctionDef) and n.name == 'read']
    if len(definitions) != 1:
        raise ValueError('Exact retained codec definition required')
    namespace = {'np':np, 'struct':struct}
    exec(compile(ast.Module(body=definitions, type_ignores=[]), HELPER, 'exec'), namespace)
    started = time.monotonic(); p, f = namespace['read'](ROOT/c['candidate'])
    if p.shape != (869355,3) or f.shape != (1739126,3):
        raise ValueError('Bound clipped surface counts changed')
    retained = json.loads((ROOT/c['completed_census']).read_text())
    poor = sorted(i for row in retained['candidate']['plane_classes'].values() for i in row['poor_face_ids'])
    if len(poor) != 3112 or len(set(poor)) != 3112 or not all(type(i) is int and 0 <= i < len(f) for i in poor):
        raise ValueError('Complete frozen poor-face ID partition required')
    poor_set = set(poor); seeds = np.unique(f[poor]); seed_mask = np.zeros(len(p),dtype=bool); seed_mask[seeds] = True
    patch_mask = np.zeros(len(f),dtype=bool)
    for start in range(0,len(f),65536):
        patch_mask[start:start+65536] = np.any(seed_mask[f[start:start+65536]],axis=1)
    patch_ids = np.flatnonzero(patch_mask)
    if len(seeds)!=3580 or len(patch_ids)!=9872 or hashlib.sha256(patch_mask.tobytes()).hexdigest()!=retained['candidate']['exact_incident_patch_mask_sha256']:
        raise ValueError('Frozen exact incidence does not reproduce')
    patch = {int(i):tuple(map(int,f[i])) for i in patch_ids}; bad = {i:patch[i] for i in poor}
    poor_groups, patch_groups = face_groups(bad), face_groups(patch)
    patch_edges = incidence(patch); vertices = sorted({v for t in patch.values() for v in t})
    vertex_mask = np.zeros(len(p),dtype=bool); vertex_mask[vertices] = True
    codes = np.array(sorted(a*len(p)+b for a,b in patch_edges),dtype='<u8')
    complete_edges = defaultdict(list); stars = defaultdict(list); nearby_faces = {}
    exterior_hash = hashlib.sha256(); fixed = np.zeros(len(p),dtype=bool)
    for start in range(0,len(f),65536):
        chunk = f[start:start+65536]
        exterior = chunk[~patch_mask[start:start+len(chunk)]]
        exterior_hash.update(np.ascontiguousarray(exterior,dtype='<u8').tobytes()); fixed[exterior.ravel()] = True
        aa = chunk.ravel(); bb = chunk[:,[1,2,0]].ravel()
        code = np.minimum(aa,bb)*len(p)+np.maximum(aa,bb); locations = np.searchsorted(codes,code)
        hit = locations<len(codes); hit[hit] &= codes[locations[hit]]==code[hit]
        for k in np.flatnonzero(hit):
            a,b = int(aa[k]),int(bb[k]); complete_edges[tuple(sorted((a,b)))].append((start+int(k)//3,a,b))
        for offset in np.flatnonzero(np.any(vertex_mask[chunk],axis=1)):
            fid = start+int(offset); t = tuple(map(int,chunk[offset])); nearby_faces[fid] = t
            for i,v in enumerate(t):
                if vertex_mask[v]:
                    stars[v].append((t[(i+1)%3],t[(i+2)%3]))
    fixed |= (p[:,0]==-76)|(p[:,0]==76)
    if set(complete_edges)!=set(patch_edges) or set(stars)!=set(vertices):
        raise ValueError('Incomplete selected-edge or vertex-star coverage')
    if int(fixed.sum())!=865429 or hashlib.sha256(fixed.tobytes()).hexdigest()!=retained['candidate']['fixed_mask_sha256']:
        raise ValueError('Descriptive legacy fixed mask changed')
    def face_class(fid):
        count = sum(p[v,2]==0 for v in nearby_faces[fid])
        return 'cap' if count==3 else 'mixed' if count else 'offplane'
    def records(groups, faces):
        result = []
        for gid, members in enumerate(groups):
            selected = {i:faces[i] for i in members}; top = topology(selected); member_set = set(members)
            local_vertices = sorted({v for t in selected.values() for v in t}); boundary = []
            for a,b in top['boundary_edges']:
                adjacent = complete_edges[tuple(sorted((a,b)))]
                boundary.append(dict(oriented_edge=[a,b],complete_incident_faces=[x[0] for x in adjacent],
                    complete_edge_two_opposite=len(adjacent)==2 and sum(1 if x<y else -1 for _,x,y in adjacent)==0,
                    outside_faces=[dict(face=i,plane_class=face_class(i),poor=i in poor_set) for i,_,_ in adjacent if i not in member_set]))
            selected_edges = incidence(selected)
            rims = [list(edge) for edge in selected_edges
                    if len({face_class(i)=='cap' for i,_,_ in complete_edges[edge]})>1]
            complete_edge_failures = [list(edge) for edge in selected_edges if len(complete_edges[edge])!=2
                or sum(1 if a<b else -1 for _,a,b in complete_edges[edge])!=0]
            result.append(dict(group=gid,face_ids=members,topology=top,
                plane_class_faces=dict(Counter(face_class(i) for i in members)),poor_faces=sum(i in poor_set for i in members),
                cap_noncap_rim_edges=sorted(rims),boundary_full_incidence=boundary,
                selected_edge_complete_surface_incidence_or_orientation_failures=sorted(complete_edge_failures),
                full_surface_vertex_link_cycle_failures=[v for v in local_vertices if not link_status(stars[v],False)['valid']],
                on_plane_vertex_ids=[v for v in local_vertices if p[v,2]==0],
                exact_boundary_coordinate_rows_sha256=hashlib.sha256(np.ascontiguousarray(p[top['boundary_vertices']],dtype='<f8').tobytes()).hexdigest(),
                reference_vertex_coordinate_rows_sha256=hashlib.sha256(np.ascontiguousarray(p[local_vertices],dtype='<f8').tobytes()).hexdigest()))
        return result
    report = dict(status='complete_local_combinatorial_census_only',source_candidate_sha256=c['input_hashes'][c['candidate']],
        completed_array_census_sha256=c['input_hashes'][c['completed_census']],
        poor_face_components=records(poor_groups,bad),exact_seed_incident_patch_components=records(patch_groups,patch),
        poor_component_vertex_contacts=vertex_contacts(poor_groups,bad),patch_component_vertex_contacts=vertex_contacts(patch_groups,patch),
        strict_poor_faces=3112,seed_vertices=3580,exact_incident_faces=9872,
        exact_incident_mask_sha256=retained['candidate']['exact_incident_patch_mask_sha256'],
        descriptive_legacy_fixed_vertices=865429,descriptive_legacy_mask_is_approved_repair_constraint=False,
        exterior_oriented_index_rows_sha256=exterior_hash.hexdigest(),
        selected_complete_edge_incidence_histogram=dict(Counter(len(rows) for rows in complete_edges.values())),
        selected_complete_edge_incidence_sha256=hashlib.sha256(np.array(
            [(a,b,*row) for (a,b),rows in sorted(complete_edges.items()) for row in sorted(rows)],dtype='<u8').tobytes()).hexdigest(),
        global_incidence_only_for_selected_patch_edges=True,full_vertex_links_only_for_patch_vertices=True,
        proposed_later_repair_preservation=['Exact oriented boundary and all exterior faces/coordinates; no automatic permission from this census.',
            'New finishing-datum cap survives at exact z0 with outward negative-Z winding; cap holes/rim continuity require separate proof.',
            'Any chosen component must preserve its actual manifold/Euler/boundary-link status; non-disk status is not converted to an assumed disk.',
            'Complete new global intersections/topology/features and both distances <=0.0625mm against original894; strict zero faces below2/29 before volume SICN>=0.1.'],
        repair_or_geometry_export_calls=0,global_topology_intersections_distance_or_feature_admission=False,
        old135_edges_228_disks_or_subset_origin_maps_inherited=False,head_or_physics_or_manufacturing_admitted=False,
        runtime=dict(python_executable_sha256=c['runtime']['python_executable_sha256'],numpy=np.__version__,machine=platform.machine()),
        readback_wall_seconds=time.monotonic()-started)
    verify(c)
    if sha(OUT/'frozen-contract.json')!=contract_sha:
        raise ValueError('Census contract changed')
    report['all_bound_inputs_unchanged'] = True
    with (OUT/'readback-report.json').open('x') as stream:
        json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(status=report['status'],poor_components=len(poor_groups),incident_components=len(patch_groups))))


if __name__=='__main__':
    main()
