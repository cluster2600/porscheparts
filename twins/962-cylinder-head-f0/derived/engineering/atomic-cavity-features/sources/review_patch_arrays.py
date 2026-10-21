"""Independent read-only NumPy association/disk readback; no VTK or solver."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import struct
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT/'work/962-engineering'
OUT = Path(__file__).with_name('review.json')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for b in iter(lambda: stream.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def array_sha(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def read(path):
    with path.open('rb') as stream:
        magic, nv, nf = struct.unpack('<8sQQ', stream.read(24))
    assert magic == b'962SURF1' and path.stat().st_size == 24+24*(nv+nf)
    return (np.memmap(path, dtype='<f8', mode='r', offset=24, shape=(nv,3)),
            np.memmap(path, dtype='<u8', mode='r', offset=24+24*nv, shape=(nf,3)))


def canonical(a):
    return np.take_along_axis(a, (np.arange(3)[None,:]+np.argmin(a,axis=1)[:,None])%3, axis=1)


def keys(a):
    return np.ascontiguousarray(canonical(a), dtype='<u8').view('V24').ravel()


def graph_components(vertices, edges):
    adjacency = {v:set() for v in vertices}
    for a,b in edges:
        adjacency[a].add(b);adjacency[b].add(a)
    unseen=set(vertices);count=0
    while unseen:
        todo=[unseen.pop()];count+=1
        while todo:
            for v in adjacency[todo.pop()] & unseen:
                unseen.remove(v);todo.append(v)
    return count


def disk(faces):
    directed=[(int(row[i]),int(row[(i+1)%3])) for row in faces for i in range(3)]
    incidence=defaultdict(list)
    for a,b in directed:incidence[tuple(sorted((a,b)))].append((a,b))
    assert all(len(rows) in (1,2) for rows in incidence.values())
    assert all(len(rows)==1 or rows[0] == rows[1][::-1] for rows in incidence.values())
    boundary=sorted(rows[0] for rows in incidence.values() if len(rows)==1)
    incoming=Counter(b for a,b in boundary);outgoing=Counter(a for a,b in boundary)
    assert incoming == outgoing and all(v==1 for v in incoming.values())
    vertices=set(map(int,faces.ravel()));links=defaultdict(list)
    for row in faces:
        for i,v in enumerate(row):links[int(v)].append((int(row[(i+1)%3]),int(row[(i+2)%3])))
    for v,edges in links.items():
        degree=Counter(x for row in edges for x in row)
        assert graph_components(set(degree),edges)==1
        assert sorted(degree.values()) == (sorted([1,1]+[2]*(len(degree)-2)) if v in incoming else [2]*len(degree))
    components=graph_components(vertices,incidence)
    loops=graph_components(set(incoming),boundary)
    result=dict(vertices=len(vertices),edges=len(incidence),faces=len(faces),
        euler_characteristic=len(vertices)-len(incidence)+len(faces),components=components,
        boundary_loops=loops,boundary_vertices=len(incoming),boundary_edges=len(boundary),vertex_link_manifold=True)
    assert components==1 and loops==1 and result['euler_characteristic']==1
    return result,np.asarray(boundary,dtype=np.int64).reshape(-1,2)


def main():
    assert not OUT.exists()
    start=time.monotonic()
    launch_path=WORK/'atomic-cavity-features-launch-001/launch.json'
    execution_path=WORK/'atomic-cavity-features-execution-001/receipt.json'
    report_path=WORK/'atomic-cavity-features-prep-001/patch-analysis.json'
    launch=json.loads(launch_path.read_text());execution=json.loads(execution_path.read_text());report=json.loads(report_path.read_text())
    assert sha(launch_path)=='c88c4f5fabf1977a288cff41f18833fbdc499bab244b9d2407c04b9659a79c34'
    assert sha(report_path)=='26309d067a92a48335ae286608b02486322f4d93d7fbd992ae1029d156fb3698'
    assert len(launch['input_sha256'])==16 and all(sha(ROOT/p)==v for p,v in launch['input_sha256'].items())
    assert launch['command']==['/usr/local/bin/python3','-B',str(ROOT/'work/962-engineering/atomic-cavity-features-prep-001/analyze_patches.py')]
    assert launch['resources']==dict(rss_stop_bytes=4294967296,rss_poll_seconds=.1,process_group_deadline_seconds=300,native_library_serial=True,thread_environment_limit=2,hard_address_space_quota=False,OS_CPU_quota=False)
    assert {p.name for p in (WORK/'atomic-cavity-features-execution-001').iterdir()}=={'analysis.log','frozen-launch.json','receipt.json'}
    assert execution['launch_sha256']==sha(launch_path) and execution['report_sha256']==sha(report_path)
    assert all(launch['input_sha256'][k]==v for k,v in report['input_sha256'].items())
    assert report['status']=='all_original_disk_and_exact_fixed_boundary_subgates_passed'
    assert report['opening_probes_executed'] is False and report['all_eight_retained_VTK_opening_probes_still_required'] is True
    assert all(report[k] is False for k in ('complete_semantic_or_OEM_interface_map','candidate_wall_clearance_qualified','conformal_metal_fluid_interface_validated','independent_distance_or_global_intersections_credited_here','volume_mesh_or_solver_admitted','thermal_strength_LPBF_or_manufacturing_qualified'))
    assert sha(WORK/'atomic-cavity-features-execution-001/frozen-launch.json')==sha(launch_path)
    assert sha(Path(launch['command'][0]))==launch['interpreter_sha256']
    assert execution['returncode']==0 and execution['all_bound_inputs_unchanged'] is True
    obs=execution['observation']
    assert obs['worker_reaped'] is True and obs['worker_running_after_monitor'] is False
    assert all(obs[x] is None for x in ('stopped_by_watchdog','monitor_error','cleanup_error'))
    p,f=read(WORK/'analysis-envelope-025-003/exact-input.bin')
    q,g=read(WORK/'atomic-cavity-head-001/head-atomic002/candidate.bin')
    assert (len(p),len(f),len(q),len(g))==(902145,1804706,901727,1803870)
    origins=np.fromfile(WORK/'atomic-cavity-head-001/head-atomic002/vertex-coordinate-origins.u64',dtype='<u8')
    patch=np.fromfile(WORK/'finest-endpoint-003-head-001/head-endpoint003/patch-reference-face-ids.u64',dtype='<u8')
    assert len(origins)==len(q) and len(np.unique(origins))==len(q) and q.tobytes()==p[origins].tobytes()
    assert len(patch)==4704 and np.array_equal(patch,np.unique(patch))
    mask=np.zeros(len(f),dtype=bool);mask[patch]=True
    fixed=np.zeros(len(p),dtype=bool);fixed[f[~mask].ravel()]=True
    fixed|=(p[:,0]==-76)|(p[:,0]==76)
    inverse=np.full(len(p),-1,dtype=np.int64);inverse[origins]=np.arange(len(q))
    assert int(fixed.sum())==900845 and np.all(inverse[fixed]>=0)
    assert q[inverse[fixed]].tobytes()==p[fixed].tobytes()
    original_ids=origins[g];exterior=keys(f[~mask]);candidate_keys=keys(original_ids)
    exterior_mask=np.isin(candidate_keys,exterior);candidate_patch=np.flatnonzero(~exterior_mask)
    assert len(exterior)==1800002 and len(np.unique(exterior))==len(exterior)
    assert np.array_equal(np.sort(candidate_keys[exterior_mask]),np.sort(exterior)) and len(candidate_patch)==3868
    assert array_sha(candidate_patch)==report['candidate_patch_face_indices_sha256']
    # Independently group original patch faces with union-find over shared edges.
    parent=list(range(len(patch)))
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]];x=parent[x]
        return x
    edge_face={}
    for i,row in enumerate(f[patch]):
        for j in range(3):
            edge=tuple(sorted((int(row[j]),int(row[(j+1)%3]))))
            if edge in edge_face:parent[find(i)]=find(edge_face[edge])
            else:edge_face[edge]=i
    groups=defaultdict(list)
    for i in range(len(patch)):groups[find(i)].append(i)
    groups=sorted(groups.values(),key=lambda group:group[0]);assert len(groups)==228
    retained=json.loads((WORK/'quality-patch-features-001/worker-report.json').read_text())
    owners=defaultdict(set)
    for i,group in enumerate(groups):
        for vertex in np.unique(f[patch[group]]):owners[int(vertex)].add(i)
    assigned=[[] for _ in groups];labels=[]
    for face_id in candidate_patch:
        row=original_ids[face_id];owner=set.intersection(*(owners[int(v)] for v in row))
        assert len(owner)==1
        selected=owner.pop();labels.append(selected);assigned[selected].append(int(face_id))
    assert array_sha(np.asarray(labels,dtype=np.int64))==report['assignment_patch_IDs_in_candidate_face_order_sha256']
    delta=Counter();changed=0
    for i,(group,ids,row) in enumerate(zip(groups,assigned,report['patches'])):
        assert ids and row['patch_id']==i
        original_selected=patch[group].astype(np.int64);current_selected=np.asarray(ids,dtype=np.int64)
        before,boundary=disk(f[original_selected]);after,candidate_boundary=disk(original_ids[current_selected])
        assert before==row['original']==retained['patches'][i]['topology'] and after==row['candidate']
        assert np.array_equal(boundary,candidate_boundary)
        assert array_sha(original_selected)==row['original_face_indices_sha256']==retained['patches'][i]['source_face_indices_sha256']
        assert array_sha(current_selected)==row['candidate_face_indices_sha256']
        assert array_sha(boundary)==row['oriented_original_ID_boundary_sha256']==retained['patches'][i]['exact_oriented_boundary_indices_sha256']
        boundary_vertices=np.unique(boundary)
        assert np.all(fixed[boundary_vertices]) and q[inverse[boundary_vertices]].tobytes()==p[boundary_vertices].tobytes()
        assert array_sha(p[boundary_vertices])==row['boundary_coordinate_bytes_sha256']==retained['patches'][i]['exact_boundary_coordinates_sha256']
        change={k:after[k]-before[k] for k in ('vertices','edges','faces')}
        assert change==row['delta_VEF'];delta.update(change);changed+=any(change.values())
        assert row['exact_fixed_boundary_unchanged'] is True and row['unique_original_group_association'] is True
    assert len(report['patches'])==228 and sum(r['original']['faces'] for r in report['patches'])==4704
    assert sum(r['candidate']['faces'] for r in report['patches'])==3868
    assert all(sha(ROOT/p)==v for p,v in launch['input_sha256'].items())
    review=dict(schema='962-atomic-patch-continuity-actual-independent-readback/v1',status='CLEAR_all228_original_disks_exact_boundaries_and_complete_assignment_only',
        launch_sha256=sha(launch_path),execution_sha256=sha(execution_path),actual_report_sha256=sha(report_path),reviewer_source_sha256=sha(Path(__file__)),
        all16_bound_inputs_current_before_and_after=True,frozen_launch_byte_exact=True,interpreter_digest_matches=True,
        complete228_rows_independently_reconstructed=True,original_disk_count=228,candidate_disk_count=228,
        independent_grouping='Union-find over original patch face shared-edge incidence; no worker/helper imports.',
        independently_checked=['All ordered original-coordinate origin bytes, unique origins and 900845 fixed vertices.','Complete 1800002 oriented exterior multiset and exact 3868-face complement.','Every candidate patch face has exactly one immutable original-group owner; all assignment/index digests.','Every original/candidate per-patch VEF/component/Euler/loop/link record from independent directed-edge and vertex-link calculations.','Every exact oriented original-ID boundary and fixed coordinate-byte digest against original arrays and retained feature record.'],
        changed_disk_count=changed,total_per_patch_delta_VEF=dict(delta),
        actual_monitored_execution=dict(returncode=0,wall_seconds=execution['wall_seconds'],**obs),
        declared_controls=launch['resources'],monitor_source_sha256=launch['input_sha256'][launch['monitor_source']],
        empty_log_verified=(sha(WORK/'atomic-cavity-features-execution-001/analysis.log')==execution['log_sha256']=='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
        metadata_and_report_file_closure_verified=True,opening_probes_executed=False,all_eight_opening_probes_still_required=True,
        complete_semantic_OEM_interface_or_clearance_qualification=False,volume_solver_physics_or_manufacturing_admission=False,
        native_or_VTK_or_CUB_or_solver_replay_calls=0,second_readonly_NumPy_full_array_association_and_topology_check=True,
        reviewer_numpy=np.__version__,review_wall_seconds=time.monotonic()-start,findings=[])
    with OUT.open('x') as stream:json.dump(review,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(review_sha256=sha(OUT),bytes=OUT.stat().st_size,changed_disks=changed,total_delta=dict(delta),wall_seconds=review['review_wall_seconds'])))


if __name__=='__main__':main()
