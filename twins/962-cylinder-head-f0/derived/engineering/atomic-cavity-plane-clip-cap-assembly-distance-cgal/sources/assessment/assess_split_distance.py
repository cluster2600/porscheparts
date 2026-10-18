"""Assess one preserved forward and two new reverse parts; saved bytes only."""
import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[3]
W = 'work/962-engineering/'
P = 'atomic-cavity-plane-clip-cap-assembly-'
OLD = W + P + 'distance-001'
ORIGINAL = 'work/962-engineering/analysis-envelope-025-003/exact-input.bin'
CANDIDATE = W + P + '001/candidate.bin'
ORIGINAL_SHA = '894ece6e63d99684fd7c8710caf73132cd73731ac8bc667548c21c85962d4c95'
CANDIDATE_SHA = '9d62eac6e2cd7b6a9ecb4a7ea5b632685820369b5c4ede379acc34238f50d7b4'
OLD_CHILD_SHA = '7bd2dcc60f81d8e9d8b1f19923a887acf53609a9c151e29282df758692b2f2ac'
OLD_FORWARD_SHA = 'd89d132bc66889456aee27b399314ad3ac25bf862669272b8fd27c2b0b56cf77'
WORKER_SHA = '58a23c788cd0d9053b64c0bab3acff68a5ea33427e79a19f56516d05cb090f0d'
GAP, BUDGET = .0001, .0625


def need(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            value.update(block)
    return value.hexdigest()


def number(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def interval(d, source_faces, target_faces, target_vertices):
    low, high = d['lower'], d['upper']
    need(number(low) and number(high) and 0 <= low <= high and high-low <= GAP,
         'Finite ordered closed interval within unchanged gap required')
    need(d['interval_closed'] is True and d['target_is_complete'] is True
         and d['source_faces'] == source_faces and d['target_faces'] == target_faces
         and d['target_vertices'] == target_vertices and d['native_called'] is True
         and d['query_arrays_unchanged'] is True and d['normalize'] is False,
         'Exact selected source and complete unchanged target required')
    nv = d['source_vertices']
    need(type(nv) is int and 0 < nv <= 3*source_faces
         and d['allocation_factor'] == max(1.,min(1e6,2000000/max(nv,source_faces)))
         and all(number(d[k]) and d[k] >= 0 for k in ['diagonal','bvh_ms','bounds_ms']),
         'Unchanged source-size allocation formula and finite native metadata required')
    return low, high


def controls(execution, resources):
    need(execution['returncode'] == 0 and not isinstance(execution['returncode'], bool)
         and execution['status'] == 'finished' and execution['worker_reaped'] is True
         and execution['worker_running_after_monitor'] is False
         and execution['all_bound_inputs_unchanged'] is True
         and all(execution[k] is None for k in ['stopped_by_watchdog','monitor_error','cleanup_error'])
         and execution['SIGTERM_requested'] is False and execution['SIGTERM_handler_restored'] is True,
         'Completed reaped unchanged process and successful cleanup required')
    need(resources == dict(rss_stop_bytes=4294967296, rss_poll_seconds=.1,
         process_group_deadline_seconds=300, native_library_serial=True,
         thread_environment_limit=2, hard_address_space_quota=False, OS_CPU_quota=False)
         and execution['resources'] == resources
         and execution['hard_address_space_quota_established'] is False
         and execution['OS_CPU_quota_established'] is False,
         'Unchanged sampled RSS/wall/thread controls required')
    rss, wall = execution['maximum_observed_worker_RSS_bytes'], execution['wall_seconds']
    need(type(rss) is int and 0 <= rss < resources['rss_stop_bytes']
         and number(wall) and 0 <= wall < resources['process_group_deadline_seconds'],
         'Recorded RSS and synchronous elapsed refusal bounds required')
    need(all(execution['environment'][k] == '2' for k in ['OMP_NUM_THREADS',
         'OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS']),
         'Two-thread environment required; not an OS CPU quota')


def npy(raw, dtype, count):
    need(raw[:6] == b'\x93NUMPY' and raw[6:8] in (b'\x01\x00',b'\x02\x00'), 'Known NPY encoding required')
    width = 2 if raw[6] == 1 else 4
    n = int.from_bytes(raw[8:8+width], 'little'); start = 8+width
    need(0 < n <= 65536, 'Bounded NPY header required')
    header = ast.literal_eval(raw[start:start+n].decode('latin1'))
    need(header == dict(descr=dtype, fortran_order=False, shape=(count,)), 'Exact NPY dtype/order/shape required')
    body = raw[start+n:]
    need(len(body) == count*(1 if dtype == '|b1' else 8), 'Exact NPY payload length required')
    return body


def partition(path, faces, selected):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        need(len(names) == 2 and set(names) == {'shared_face_mask.npy','changed_face_indices.npy'}, 'Exact NPZ members required')
        mask = npy(archive.read('shared_face_mask.npy'), '|b1', faces)
        raw_ids = npy(archive.read('changed_face_indices.npy'), '<u8', selected)
    ids = tuple(v[0] for v in struct.iter_unpack('<Q', raw_ids))
    need(all(v in (0,1) for v in mask) and ids == tuple(i for i,v in enumerate(mask) if v == 0),
         'Every mask row must equal its ordered selected complement')
    return ids, hashlib.sha256(mask).hexdigest(), hashlib.sha256(raw_ids).hexdigest()


def coverage(old, cap, noncap, cap_authority):
    need(all(tuple(sorted(set(v))) == v for v in (old,cap,noncap,cap_authority)), 'Sorted unique source IDs required')
    cap_set = set(cap_authority)
    need(not set(cap).intersection(noncap) and tuple(sorted(cap+noncap)) == old
         and cap == tuple(v for v in old if v in cap_set),
         'Exact disjoint complete union and cap authority required')


def combine(bounds):
    need(len(bounds) == 3 and all(number(a) and number(b) and 0 <= a <= b and b-a <= GAP for a,b in bounds),
         'Exactly three valid directed intervals required')
    return max(a for a,b in bounds),max(b for a,b in bounds)


def assess(path):
    child = json.loads(path.read_text()); pins = child['input_sha256']
    need(child['schema'] == '962-cap-split-combined-assessment-contract/v1'
         and child['root_authorized_assessment'] is True and child['root_and_peer_review_complete'] is True,
         'Separately reviewed actual assessment contract required')
    def bound(relative):
        p = ROOT/relative
        need(relative in pins and p.is_file() and digest(p) == pins[relative], 'Frozen assessment input changed or missing')
        return p
    def load(relative):
        return json.loads(bound(relative).read_text())
    bound(str(Path(__file__).resolve().relative_to(ROOT)))
    for name in pins:
        bound(name)
    proof_path = child['split_proof']; proof = load(proof_path)
    need(proof['schema'] == '962-exact-cap-noncap-reverse-source-split/v1'
         and proof['disjoint_complete_union_verified'] is True
         and proof['complete_original_target_required'] is True
         and proof['deferred_other_piece_faces_are_not_zero_distance_cancellation'] is True,
         'Exact source-union proof required; deferred faces are not shared zero-distance faces')
    for name, sha in proof['input_sha256'].items():
        need(digest(ROOT/name) == sha, 'Split proof input changed')
    for item, expected in [(proof['source'],(CANDIDATE,CANDIDATE_SHA,871731,1743878)),
                           (proof['complete_target'],(ORIGINAL,ORIGINAL_SHA,902145,1804706))]:
        need((item['path'],item['sha256'],item['vertices'],item['faces']) == expected
             and digest(bound(item['path'])) == item['sha256'], 'Exact source/complete original target required')
    masks = {}
    for key,item,selected in [('old',proof['old_partition'],14402),('cap',proof['parts']['cap'],8976),('noncap',proof['parts']['noncap'],5426)]:
        need(item['source_faces'] == 1743878 and digest(bound(item['path'])) == item['sha256'], 'Exact full-length source mask required')
        if key != 'old':
            need(item['selected_faces'] == selected, 'Frozen selected source count required')
        ids, mask_sha, ids_sha = partition(bound(item['path']),1743878,selected)
        need(mask_sha == item['raw_shared_face_mask_sha256'] and ids_sha == item['raw_changed_face_indices_sha256'], 'Raw mask/ID hash association required')
        masks[key] = ids
    cap = proof['cap_authority']; cap_path = bound(cap['cap_map_path'])
    need(digest(cap_path) == cap['cap_map_sha256'] and cap['cap_rows'] == 8976, 'Complete cap-map authority required')
    cap_ids = tuple(v[0] for v in struct.iter_unpack('<Q', cap_path.read_bytes()))
    need(len(cap_ids) == 8976 and all(v < 1743878 for v in cap_ids), 'Complete in-range cap IDs required')
    need(digest(bound(cap['index_census_path'])) == cap['index_census_sha256'], 'Actual integer census association required')
    coverage(masks['old'],masks['cap'],masks['noncap'],cap_ids)
    need(proof['contract_sha256'] == digest(bound(child['split_producer_contract'])), 'Actual producer contract association required')
    old_path = OLD+'/frozen-execution-contract.json'; old = load(old_path)
    need(digest(bound(old_path)) == OLD_CHILD_SHA, 'Preserved original child required')
    old_summary = load(OLD+'/execution-summary.json')
    need(old_summary['contract_sha256'] == OLD_CHILD_SHA and old_summary['all_bound_inputs_unchanged'] is True,
         'Preserved old summary required; its failed reverse is not credited')
    reverse = child['reverse_directory']; new_path = reverse+'/frozen-execution-contract.json'; new = load(new_path)
    summary = load(reverse+'/execution-summary.json')
    need(summary['contract_sha256'] == digest(bound(new_path)) and summary['native_queries_completed'] is True
         and summary['all_bound_inputs_unchanged'] is True and summary['planned_queries'] == 2
         and summary['completed_queries'] == 2, 'Both new reverse parts must complete')
    need(len(new['queries']) == 2 and set(new['query_config_hashes']) == set(proof['query_config_sha256'])
         and set(new['queries']) == set(new['query_config_hashes'])
         and new['query_config_hashes'] == proof['query_config_sha256'], 'Exact two reverse config bindings required')
    for c in (old,new):
        need(c['kind'] == 'reviewed_head' and c['absolute_gap_tolerance_mm'] == GAP and c['envelope_limit_mm'] == BUDGET
             and c['selected_worker']['sha256'] == WORKER_SHA and c['runtime'] == old['runtime'], 'Unchanged worker/runtime/gap/budget required')
        for name,sha in dict(c['input_hashes'],**c['query_config_hashes']).items():
            need(digest(ROOT/name) == sha, 'Query source/runtime/config changed')
    rows = []
    jobs = [('forward',old,old_path,old_summary,OLD,old['queries'][0],75230,1743878,871731)]
    for config_path in new['queries']:
        config = load(config_path)
        role = next((k for k in ('cap','noncap') if config['partition'] == proof['parts'][k]['path']),None)
        need(role is not None, 'Each reverse query must select one exact split source')
        jobs.append((role,new,new_path,summary,reverse,config_path,8976 if role=='cap' else 5426,1804706,902145))
    need({r[0] for r in jobs} == {'forward','cap','noncap'}, 'One forward and both distinct reverse parts required')
    expected = {'controller-executed.py','worker-executed.py','frozen-execution-contract.json','execution-summary.json'}
    for job in jobs[1:]:
        config = load(job[5])
        expected.update(config['id']+'/'+n for n in ['execution-receipt.json','running-receipt.json','worker-report.json','native.log'])
    need({p.relative_to(ROOT/reverse).as_posix() for p in (ROOT/reverse).rglob('*') if p.is_file()} == expected,
         'Complete new twelve-file query set required')
    for name in expected:
        bound(reverse+'/'+name)
    for role,c,cp,s,directory,config_path,nf,tf,tv in jobs:
        config = load(config_path); folder = directory+'/'+config['id']; ep = folder+'/execution-receipt.json'
        execution = load(ep); report_path = folder+'/worker-report.json'; report = load(report_path)
        need(digest(bound(ep)) == s['execution_receipt_sha256'][config['id']+'/execution-receipt.json']
             and execution['contract_sha256'] == digest(bound(cp)) and execution['config_sha256'] == digest(bound(config_path)), 'Receipt/summary/child/config binding required')
        controls(execution,c['resources'])
        actual = {p.relative_to(ROOT/folder).as_posix() for p in (ROOT/folder).rglob('*') if p.is_file()}
        need(set(execution['artifact_sha256']) == {'running-receipt.json','worker-report.json','native.log'}
             and actual == set(execution['artifact_sha256'])|{'execution-receipt.json'}, 'Complete query artifact closure required')
        for name,sha in execution['artifact_sha256'].items():
            need(digest(bound(folder+'/'+name)) == sha, 'Query artifact changed')
        source,target = (ORIGINAL,CANDIDATE) if role=='forward' else (CANDIDATE,ORIGINAL)
        need(config['source'] == source and config['target'] == target
             and report['status'] == 'completed' and report.get('error') is None and report['all_bound_inputs_unchanged'] is True
             and report['contract_sha256'] == digest(bound(cp)) and report['config_sha256'] == digest(bound(config_path))
             and report['assessor_sha256'] == WORKER_SHA
             and report['full_source_faces'] == (1804706 if role=='forward' else 1743878)
             and report['complete_target_faces'] == tf
             and all(report['runtime'][k] == v for k,v in c['runtime'].items()), 'Completed exact direction/full target/runtime required')
        if role == 'forward':
            need(digest(bound(report_path)) == OLD_FORWARD_SHA, 'Only preserved valid old forward is reusable')
        low,high = interval(report['distance'],nf,tf,tv)
        rows.append(dict(role=role,lower_mm=low,upper_mm=high,gap_mm=high-low,query_source_faces=nf,
                         complete_target_faces=tf,report_sha256=digest(bound(report_path)),execution_sha256=digest(bound(ep))))
    need(all(digest(ROOT/name) == sha for name,sha in pins.items()), 'Assessment inputs changed while reading')
    low,high = combine([(r['lower_mm'],r['upper_mm']) for r in rows])
    need(high-low <= GAP, 'Merged closed interval must retain the absolute gap')
    return dict(schema='962-cap-split-combined-polygon-distance-assessment/v1',directions=rows,
                status='polygon_two_way_distance_gate_passed_only' if high<=BUDGET else 'polygon_two_way_distance_gate_rejected',
                reverse_interval_mm=[max(r['lower_mm'] for r in rows[1:]),max(r['upper_mm'] for r in rows[1:])],
                combined_two_way_interval_mm=[low,high],absolute_gap_tolerance_mm=GAP,envelope_limit_mm=BUDGET,
                independent_polygon_distance_gate_passed=high<=BUDGET,old_failed_reverse_preserved_not_reused=True,
                split_proof_sha256=digest(bound(proof_path)),assessment_contract_sha256=digest(path),
                assessor_sha256=digest(__file__),all_bound_artifact_hashes_verified=True,
                native_CAD_deviation_certified=False,rounding_error_certificate=False,feature_channel_BCC_review_completed=False,
                solver_admission_established=False,engineering_accepted=False,manufacturing_authorized=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('contract',type=Path)
    parser.add_argument('--report',type=Path,required=True); args = parser.parse_args()
    need(not args.report.exists() and not args.report.is_symlink(), 'Existing assessment preserved')
    result = assess(args.contract)
    with args.report.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
