"""Read-only mask/cap/exact-shortest-edge reference; no quotient or acceptance."""
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
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):
            h.update(block)
    return h.hexdigest()


def verify(c):
    for name,digest in c['input_hashes'].items():
        relative = Path(name); path = ROOT/relative
        if relative.is_absolute() or '..' in relative.parts or path.is_symlink() or sha(path) != digest:
            raise ValueError('Bound reference input drift: '+name)
    if sha(Path(sys.executable).resolve()) != c['runtime']['python_executable_sha256']:
        raise ValueError('Selected interpreter changed')


def main():
    c = json.loads((OUT/'frozen-contract.json').read_text()); contract_sha = sha(OUT/'frozen-contract.json')
    if c['readback_launch_authorized'] is not True or OUT != (ROOT/c['expected_fresh_output']).resolve():
        raise ValueError('Separate reviewed launch required')
    if (OUT/'readback-report.json').exists() or (OUT/'readback-report.json').is_symlink():
        raise ValueError('Fresh report required')
    verify(c); started = time.monotonic()
    def load(name):
        spec = importlib.util.spec_from_file_location(name,OUT/(name+'.py'))
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
    topology = load('patch_kernels'); exact = load('reference_kernels')
    if platform.machine() != 'arm64' or np.__version__ != c['runtime']['numpy_version']:
        raise ValueError('Retained ARM NumPy version required')
    definitions = [n for n in ast.parse((ROOT/HELPER).read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='read']
    if len(definitions) != 1:
        raise ValueError('Exact retained codec definition required')
    namespace = {'np':np,'struct':struct}
    exec(compile(ast.Module(body=definitions,type_ignores=[]),HELPER,'exec'),namespace)
    p,f = namespace['read'](ROOT/c['candidate'])
    if p.shape!=(869355,3) or f.shape!=(1739126,3):
        raise ValueError('Bound clipped counts changed')
    p.flags.writeable=False; f.flags.writeable=False
    retained = json.loads((ROOT/c['completed_readback']).read_text())
    census = json.loads((ROOT/c['completed_patch_census']).read_text())
    poor = sorted(i for row in retained['candidate']['plane_classes'].values() for i in row['poor_face_ids'])
    if len(poor)!=3112 or len(set(poor))!=3112 or not all(type(i) is int and 0<=i<len(f) for i in poor):
        raise ValueError('Frozen poor partition required')
    seed = np.zeros(len(p),dtype=bool); seed[np.unique(f[poor])] = True
    patch = np.zeros(len(f),dtype=bool); cap_mask = np.zeros(len(f),dtype=bool); fixed = np.zeros(len(p),dtype=bool)
    exterior_sha = hashlib.sha256()
    for start in range(0,len(f),65536):
        chunk = f[start:start+65536]; inside = np.any(seed[chunk],axis=1); patch[start:start+len(chunk)] = inside
        cap_mask[start:start+len(chunk)] = np.all(p[chunk,2]==0.0,axis=1)
        outside = chunk[~inside]; fixed[outside.ravel()] = True
        exterior_sha.update(np.ascontiguousarray(outside,dtype='<u8').tobytes())
    reference = census['exact_seed_incident_patch_components']
    if (len(reference)!=1 or np.flatnonzero(patch).tolist()!=reference[0]['face_ids']
            or sha_bytes(patch.tobytes())!=retained['candidate']['exact_incident_patch_mask_sha256']):
        raise ValueError('Completed exact incident reference changed')
    vertices = np.unique(f[patch]); boundary = reference[0]['topology']['boundary_vertices']
    legacy = fixed | (p[:,0]==-76.0) | (p[:,0]==76.0)
    if sha_bytes(legacy.tobytes())!=retained['candidate']['fixed_mask_sha256']:
        raise ValueError('Completed descriptive legacy mask changed')
    cap_ids = np.flatnonzero(cap_mask)
    if len(cap_ids)!=3508 or exterior_sha.hexdigest()!=census['exterior_oriented_index_rows_sha256']:
        raise ValueError('Complete cap or exterior association changed')
    cap = {int(i):tuple(map(int,f[i])) for i in cap_ids}; cap_edges = topology.incidence(cap)
    cap_vertices = set(v for t in cap.values() for v in t); cap_groups = topology.face_groups(cap)
    owners = {fid:gid for gid,group in enumerate(cap_groups) for fid in group}
    region_cycles = reference[0]['topology']['oriented_boundary_cycles']
    selected = {edge for edge,rows in cap_edges.items() if len(rows)==1}
    selected.update(tuple(sorted((loop[i],loop[(i+1)%len(loop)]))) for loop in region_cycles for i in range(len(loop)))
    codes = np.array(sorted(a*len(p)+b for a,b in selected),dtype='<u8'); complete = defaultdict(list)
    for start in range(0,len(f),65536):
        chunk = f[start:start+65536]; aa = chunk.ravel(); bb = chunk[:,[1,2,0]].ravel()
        values = np.minimum(aa,bb)*len(p)+np.maximum(aa,bb); positions = np.searchsorted(codes,values)
        hit = positions<len(codes); hit[hit] &= codes[positions[hit]]==values[hit]
        for k in np.flatnonzero(hit):
            a,b = int(aa[k]),int(bb[k]); complete[tuple(sorted((a,b)))].append((start+int(k)//3,a,b))
    def rim(edge):
        rows = complete[tuple(sorted(edge))]
        return dict(oriented_edge=list(edge),full_incident_faces=[dict(face_id=i,cap_component=owners.get(i),
            inside_incident_patch=bool(patch[i]),poor=i in poor_set,plane_class=plane_class(i)) for i,_,_ in rows],
            two_opposite= len(rows)==2 and sum(1 if a<b else -1 for _,a,b in rows)==0)
    def plane_class(i):
        n = int(np.count_nonzero(p[f[i],2]==0.0)); return 'cap' if n==3 else 'mixed' if n else 'offplane'
    poor_set = set(poor); cap_records = []
    for gid,group in enumerate(cap_groups):
        top = topology.topology({i:cap[i] for i in group})
        cap_records.append(dict(component=gid,face_ids=group,topology=top,
            incident_patch_face_ids=[i for i in group if patch[i]],exterior_face_ids=[i for i in group if not patch[i]],
            poor_face_ids=[i for i in group if i in poor_set],rim_full_incidence=[rim(e) for e in top['boundary_edges']]))
    points = {int(v):tuple(map(float,p[v])) for v in np.unique(f[poor])}
    shortest,all_edges,lex_edges = exact.shortest_proposals(points,{i:tuple(map(int,f[i])) for i in poor})
    fixed_ids = set(map(int,np.flatnonzero(fixed))); z = {v:point[2] for v,point in points.items()}
    def scenario(edges):
        groups = exact.component_eligibility(edges,fixed_ids,cap_vertices,z)
        return dict(unique_edge_ids=[list(e) for e in edges],unique_edges=len(edges),UF_components=len(groups),components=groups,
            component_size_histogram=dict(Counter(len(g['vertex_ids']) for g in groups)),chosen_keeper=None,
            components_with_fixed_conflicts=sum(bool(g['fixed_conflict_ids']) for g in groups))
    report = dict(status='read_only_repair_reference_observations_only',source_candidate_sha256=c['input_hashes'][c['candidate']],
        completed_global_reference_record_sha256=c['input_hashes'][c['completed_global_reference']],
        masks=dict(exterior_only_fixed_vertices=int(fixed.sum()),exterior_only_fixed_sha256=sha_bytes(fixed.tobytes()),
            legacy_fixed_vertices=int(legacy.sum()),legacy_fixed_sha256=sha_bytes(legacy.tobytes()),
            exact_masks_equal=bool(np.array_equal(fixed,legacy)),legacy_only_vertex_ids=np.flatnonzero(legacy&~fixed).tolist(),
            patch_vertices=len(vertices),boundary_vertices=len(boundary),subtraction_count=len(vertices)-len(boundary),
            patch_vertices_not_exterior_fixed=vertices[~fixed[vertices]].tolist(),
            exact_interior_equals_patch_minus_boundary=set(map(int,vertices[~fixed[vertices]]))==set(map(int,vertices))-set(boundary),
            masks_are_observed_not_approved_repair_constraints=True),
        cap=dict(faces=len(cap),all_face_ids=cap_ids.tolist(),vertices=len(cap_vertices),edge_components=len(cap_groups),
            components=cap_records,component_point_contacts=topology.vertex_contacts(cap_groups,cap),
            exact_binary64_rational_winding=exact.cap_winding({v:tuple(map(float,p[v])) for v in cap_vertices},cap),
            incident_region_cycles_with_complete_cap_ownership=[[rim((loop[i],loop[(i+1)%len(loop)])) for i in range(len(loop))] for loop in region_cycles],
            exact_z0_vertex_ids_outside_cap_complex=sorted(set(map(int,np.flatnonzero(p[:,2]==0.0)))-cap_vertices),
            negative_z_vertices=int(np.count_nonzero(p[:,2]<0.0)),geometric_void_coverage_or_feature_identity_proved=False),
        shortest_edges=dict(frozen_poor_faces=len(poor),ordered_exact_squared_lengths=shortest,
            tied_minimum_faces=sum(len(row['minimum_edges'])>1 for row in shortest),all_tied_minima=scenario(all_edges),
            exploratory_lex_first_per_face=scenario(lex_edges),lex_first_is_approved_edge_policy=False,
            keeper_eligibility_uses_only_exterior_fixed_conflicts_and_cap_z0=True,
            any_keeper_selected=False,quotient_or_geometric_guard_or_acceptance_checked=False),
        full_quality_recalculated=False,geometry_or_constraints_modified=False,repair_or_head_or_physics_admitted=False,
        runtime=dict(python_executable_sha256=c['runtime']['python_executable_sha256'],numpy=np.__version__,machine=platform.machine()),
        readback_wall_seconds=time.monotonic()-started)
    verify(c)
    if sha(OUT/'frozen-contract.json')!=contract_sha:
        raise ValueError('Reference contract changed')
    report['all_bound_inputs_unchanged'] = True
    with (OUT/'readback-report.json').open('x') as stream:
        json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(status=report['status'],cap_components=len(cap_groups),tie_faces=report['shortest_edges']['tied_minimum_faces'])))


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


if __name__=='__main__':
    main()
