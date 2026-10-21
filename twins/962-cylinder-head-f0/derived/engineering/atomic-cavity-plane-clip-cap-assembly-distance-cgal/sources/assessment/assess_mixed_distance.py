"""Join one retained CUB forward and two CGAL reverse intervals; saved bytes only."""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT/'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-distance-cap-split-assessment-prep-001/assess_split_distance.py'
import hashlib
if hashlib.sha256(BASE.read_bytes()).hexdigest() != '19abf66ab6aa06da97408c0d04c3d5cd0265415418156d56ad81f1dd589012f5':
    raise ValueError('Frozen stdlib helper changed')
SPEC = importlib.util.spec_from_file_location('frozen_distance_helpers', BASE)
H = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(H)
need, digest, number = H.need, H.digest, H.number
PREFIX = H.W+H.P
CPP = '26297ed13e6c95588d94abf8a320e7aaea2c8e4d12cec125b189cfd58ae7d408'
ELF = '6a173c3af29e462fa300a2663d4c02c578ce68faea19b0e761654e0845dffdca'
CLI = 'c51fc33575062b35d38d8f9d2920d3e3ef140707426e3d50b0f3b2f57a9fbaf5'
CORE = 'f46c09cb7b9a53ce0470d103932bce8e6e6682c84bf2771c0827fd9f29996e43'
META = 'bb1d006e6146918df8b566aea4d244c0c00b143587d30dc41dfb1da361a5e215'
IMAGE = 'sha256:57c6b17ed0bd093a61a3d3cecb7563e912caeb3832fd59e8cec2d4d9d4d1e2f8'
CHILDREN = {'cap':'2a369d8d28688800528b2305b89c690a8da4bfd35ca3f6741d5318994e1ee985',
            'noncap':'6de730a3cfd921e4223244c81b9e4e16c7da18770f990bbf05a3211b57514a04'}
COUNTS = {'cap':8976, 'noncap':5426}
EPSILON = H.GAP/4


def roles(parts):
    need(set(parts) == {'cap','noncap'} and len(set(parts.values())) == 2, 'Both distinct reverse parts required')


def query_identity(q, role, ids):
    need((q['source_path'],q['source_sha256'],q['full_source_vertices'],q['full_source_faces'])
         == (H.CANDIDATE,H.CANDIDATE_SHA,871731,1743878), 'Exact assembled source required')
    need((q['target_path'],q['target_sha256'],q['complete_target_vertices'],q['complete_target_faces'])
         == (H.ORIGINAL,H.ORIGINAL_SHA,902145,1804706), 'Complete original target required')
    need(type(q['selected_faces']) is int and q['selected_faces'] == len(ids) == COUNTS[role]
         and q['constructed_source_disjoint_vertices'] == 3*len(ids)
         and (q['epsilon_mm'],q['unchanged_interval_gap_mm'],q['unchanged_polygon_budget_mm']) == (EPSILON,H.GAP,H.BUDGET)
         and q['query_completion_distinct_from_polygon_budget'] is True and q['inner_roundoff_certificate'] is False,
         'Frozen source selection/counts/error policy required')


def cgal_interval(d, role, ids):
    need(d['schema'] == '962-CGAL-directed-bounded-distance/v1' and d['status'] == 'completed_interval'
         and d['stage'] == 'completed' and d['error'] == '' and d['query_completed'] is True
         and d['CGAL'] == '5.6' and d['point_and_oriented_face_snapshots_unchanged'] is True,
         'Completed unchanged CGAL interval required')
    need((d['source_full_vertices'],d['source_full_faces'],d['source_selected_faces'],d['source_constructed_disjoint_vertices'],
          d['target_full_vertices'],d['target_full_faces']) == (871731,1743878,COUNTS[role],3*COUNTS[role],902145,1804706)
         and all(type(v) is int for v in d['selected_original_face_IDs'])
         and tuple(d['selected_original_face_IDs']) == ids, 'Exact full source/complete target/selected IDs required')
    need(d['epsilon_mm'] == EPSILON and d['required_interval_gap_mm'] == H.GAP and d['polygon_budget_mm'] == H.BUDGET
         and d['concurrency'] == 'Sequential_tag' and d['match_faces_source'] is False and d['match_faces_target'] is False
         and d['normalization'] is False and d['complete_target_required'] is True and d['source_closedness_required'] is False
         and d['roundoff_certificate'] is False and d['mesh_exported'] is False and d['input_files_written'] is False,
         'Unchanged absolute algorithm and immutability scope required')
    s, low, high = d['scalar_mm'],d['lower_mm'],d['upper_mm']
    need(all(number(v) for v in (s,low,high)) and s >= 0, 'Finite nonnegative scalar and endpoints required')
    need(low == max(0.,math.nextafter(s-EPSILON,-math.inf)) and high == math.nextafter(s+EPSILON,math.inf)
         and 0 <= low <= high and high-low <= H.GAP and d['actual_interval_gap_mm'] == high-low
         and d['polygon_budget_passed'] is (high <= H.BUDGET), 'Exact outward closed interval/gap/budget flag required')
    return low, high


def split_coverage(child, bound, load):
    proof = load(child['split_proof'])
    need(proof['schema'] == '962-exact-cap-noncap-reverse-source-split/v1'
         and all(proof[k] is True for k in ['disjoint_complete_union_verified','complete_original_target_required',
             'deferred_other_piece_faces_are_not_zero_distance_cancellation']), 'Exact split proof required')
    for n,h in proof['input_sha256'].items(): need(digest(bound(n)) == h, 'Split proof input changed')
    need(proof['source'] == dict(path=H.CANDIDATE,sha256=H.CANDIDATE_SHA,vertices=871731,faces=1743878)
         and proof['complete_target'] == dict(path=H.ORIGINAL,sha256=H.ORIGINAL_SHA,vertices=902145,faces=1804706), 'Frozen geometry identity required')
    masks = {}
    for key,item,count in [('old',proof['old_partition'],14402),('cap',proof['parts']['cap'],8976),('noncap',proof['parts']['noncap'],5426)]:
        need(item['source_faces'] == 1743878 and digest(bound(item['path'])) == item['sha256'], 'Frozen partition identity required')
        ids,ms,ss = H.partition(bound(item['path']),1743878,count)
        need(ms == item['raw_shared_face_mask_sha256'] and ss == item['raw_changed_face_indices_sha256'], 'Complete mask/ID bytes required')
        masks[key] = ids
    cap = proof['cap_authority']; raw = bound(cap['cap_map_path']).read_bytes()
    need(digest(bound(cap['cap_map_path'])) == cap['cap_map_sha256'] and cap['cap_rows'] == 8976
         and digest(bound(cap['index_census_path'])) == cap['index_census_sha256'], 'Complete cap-map authority required')
    H.coverage(masks['old'],masks['cap'],masks['noncap'],tuple(v[0] for v in struct.iter_unpack('<Q',raw)))
    need(proof['contract_sha256'] == digest(bound(child['split_producer_contract'])), 'Actual split producer required')
    cp = child['cancellation_proof']; cancellation = load(cp)
    need(digest(bound(cp)) == 'c97ed3d65639e8769226e8efb92c1a746d68d7c777c3f43bceb0a76e6634365e'
         and cancellation['shared_faces'] == 1729476 and cancellation['each_shared_key_occurs_once_in_each_complete_surface'] is True
         and cancellation['complete_opposite_targets_required'] is True and cancellation['coordinate_tolerance_mm'] == 0,
         'Frozen exact shared-facet cancellation proof required; no geometry replay')
    for n,h in cancellation['input_sha256'].items(): need(digest(bound(n)) == h, 'Cancellation proof input changed')
    return masks, cancellation


def forward(bound, load, cancellation):
    directory = H.OLD; cp = directory+'/frozen-execution-contract.json'; c = load(cp)
    need(digest(bound(cp)) == H.OLD_CHILD_SHA and c['selected_worker']['sha256'] == H.WORKER_SHA
         and c['selected_runner']['sha256'] == '637678b134c30af34ad56118945b820985e046c4682d8ea00c10b48477030ac5'
         and c['absolute_gap_tolerance_mm'] == H.GAP and c['envelope_limit_mm'] == H.BUDGET, 'Preserved CUB child/worker/runner required')
    for n,h in dict(c['input_hashes'],**c['query_config_hashes']).items(): need(digest(bound(n)) == h, 'CUB source/runtime/config changed')
    for name,known in [('controller-executed.py',c['selected_runner']['sha256']),('worker-executed.py',H.WORKER_SHA)]:
        need(digest(bound(directory+'/'+name)) == known, 'CUB executed source snapshot mismatch')
    files = {'controller-executed.py','worker-executed.py','frozen-execution-contract.json','execution-summary.json'}
    for config_path in c['queries']:
        files.update(load(config_path)['id']+'/'+n for n in ['execution-receipt.json','running-receipt.json','worker-report.json','native.log'])
    need(len(files) == 12 and {str(p.relative_to(ROOT/directory)) for p in (ROOT/directory).rglob('*') if p.is_file()} == files,
         'Preserved complete twelve-file CUB set required; failed reverse is not credited')
    for n in files: bound(directory+'/'+n)
    summary = load(directory+'/execution-summary.json'); config_path = c['queries'][0]; config = load(config_path)
    need(summary['contract_sha256'] == H.OLD_CHILD_SHA and summary['all_bound_inputs_unchanged'] is True
         and config['source'] == H.ORIGINAL and config['target'] == H.CANDIDATE, 'Only preserved valid forward direction required')
    item = cancellation['partitions']['original']; ids,ms,ss = H.partition(bound(config['partition']),1804706,75230)
    need(config['partition'] == item['path'] and digest(bound(item['path'])) == item['sha256']
         and ms == item['shared_mask_sha256'] and ss == item['changed_indices_sha256'], 'Complete original forward source mask required')
    folder = directory+'/'+config['id']; ep = folder+'/execution-receipt.json'; e = load(ep); report = load(folder+'/worker-report.json')
    need(digest(bound(ep)) == summary['execution_receipt_sha256'][config['id']+'/execution-receipt.json']
         and e['contract_sha256'] == H.OLD_CHILD_SHA and e['config_sha256'] == digest(bound(config_path)), 'Forward execution association required')
    H.controls(e,c['resources'])
    need(set(e['artifact_sha256']) == {'running-receipt.json','worker-report.json','native.log'}
         and {p.name for p in (ROOT/folder).iterdir()} == set(e['artifact_sha256'])|{'execution-receipt.json'}, 'Forward complete four-file closure required')
    for n,h in e['artifact_sha256'].items(): need(digest(bound(folder+'/'+n)) == h, 'Forward artifact changed')
    need(digest(bound(folder+'/worker-report.json')) == H.OLD_FORWARD_SHA and report['status'] == 'completed'
         and report.get('error') is None and report['all_bound_inputs_unchanged'] is True
         and report['contract_sha256'] == H.OLD_CHILD_SHA and report['config_sha256'] == digest(bound(config_path))
         and report['assessor_sha256'] == H.WORKER_SHA and report['full_source_faces'] == 1804706
         and report['complete_target_faces'] == 1743878 and all(report['runtime'][k] == v for k,v in c['runtime'].items()), 'Known completed forward report required')
    return H.interval(report['distance'],75230,1743878,871731), digest(bound(folder+'/worker-report.json'))


def reverse(role, directory, ids, bound, load):
    label = 'assembled-'+role+'-to-complete-original'; cp = directory+'/frozen-execution-contract.json'; c = load(cp)
    need(digest(bound(cp)) == CHILDREN[role] and c['phase'] == 'head' and c['image_id'] == IMAGE
         and c['selected_cpp_sha256'] == CPP and c['compiled_binary']['sha256'] == ELF
         and c['selected_controller']['sha256'] == CLI and c['automatic_retry'] is False
         and c['limits'] == dict(cpus=2,memory_bytes=4294967296,swap_bytes=0,hard_wall_seconds_each=300,tmpfs_bytes=0,network='none'), 'Exact CGAL child/source/binary/controller/controls required')
    for n,h in c['input_sha256'].items(): need(digest(bound(n)) == h, 'CGAL child input changed')
    summary = load(directory+'/phase-summary.json')
    need(summary['actual_before_sha256'] == summary['actual_after_sha256'] == c['input_sha256']
         and summary['execution_contract_sha256'] == CHILDREN[role] and summary['procedural_phase_finished'] is True
         and summary['all_inputs_unchanged'] is True and summary['error'] is None
         and summary['jobs'] == [dict(label=label,execution_passed=True,previous_artifacts_unchanged=True,returncode=0)], 'Completed unchanged one-job CGAL phase required')
    files = {'run_cgal_phase.py','run_finest_endpoint_metadata.py','run_finest_endpoint_preflight.py','frozen-execution-contract.json',
             'phase-summary.json',label+'.execution.json',label+'.native.log',label+'/report.json'}
    need({str(p.relative_to(ROOT/directory)) for p in (ROOT/directory).rglob('*') if p.is_file()} == files
         and set(summary['artifact_sha256']) == files-{'phase-summary.json'}, 'Exact eight-file CGAL closure required')
    for n,h in summary['artifact_sha256'].items(): need(digest(bound(directory+'/'+n)) == h, 'CGAL artifact changed')
    for name,h in [('run_cgal_phase.py',CLI),('run_finest_endpoint_metadata.py',META),('run_finest_endpoint_preflight.py',CORE)]:
        need(digest(bound(directory+'/'+name)) == h, 'Known executed CGAL sources required')
    q = c['directed_query']; query_identity(q,role,ids)
    need(tuple(v[0] for v in struct.iter_unpack('<Q',bound(q['source_ids_path']).read_bytes())) == ids
         and digest(bound(q['source_ids_path'])) == q['source_ids_sha256'], 'Exact selected raw u64 source IDs required')
    e = load(directory+'/'+label+'.execution.json'); controls = dict(NanoCpus=2000000000,Memory=4294967296,MemorySwap=4294967296,NetworkMode='none',ReadonlyRootfs=True,Tmpfs=None)
    need(e['error'] is None and not e['cleanup_errors'] and e['attach_returncode'] == 0 and e['attach_reaped'] is True
         and e['attach_process_started'] is True and e['owned_container_removed'] is True
         and number(e['wall_seconds']) and 0 <= e['wall_seconds'] < 300, 'Reaped successful CGAL execution within absolute budget required')
    initial,final = e['initial_metadata'],e['final_metadata']; owner = initial['Owner']; container = initial['Id']
    need(re.fullmatch('[0-9a-f]{64}',container) and initial['Image'] == final['Image'] == IMAGE
         and final['Id'] == container and final['Owner'] == owner and initial['Controls'] == final['Controls'] == controls
         and initial['State']['Running'] is False and initial['State']['Pid'] == 0
         and final['State']['Running'] is False and final['State']['Pid'] == 0
         and final['State']['ExitCode'] == 0 and final['State']['OOMKilled'] is False, 'Exact owned created/stopped Docker metadata required')
    mounts = {(str((ROOT/directory).resolve()),'/out',True,'bind')}|{(str(bound(n).resolve()),t,False,'bind') for n,t in c['jobs'][0]['read_only_mounts'].items()}
    for metadata in (initial,final): need({(m['Source'],m['Destination'],m['RW'],m['Type']) for m in metadata['Mounts']} == mounts, 'Exact read-only inputs and owned output required')
    command = ['docker','create','--name',e['command'][3],'--label','io.962-finest.owner='+owner,'--network','none','--read-only','--cpus','2','--memory','4294967296','--memory-swap','4294967296']
    command += ['--mount','type=bind,src='+str((ROOT/directory).resolve())+',dst=/out']
    for n,t in c['jobs'][0]['read_only_mounts'].items(): command += ['--mount','type=bind,src='+str(bound(n).resolve())+',dst='+t+',readonly']
    command += ['--entrypoint','/bounded-distance',IMAGE]+c['jobs'][0]['arguments']
    need(e['command'] == command and [v['operation'] for v in e['control_calls']] == ['create','inspect','inspect','inspect','remove_stopped_owned']
         and all(v['returncode'] == 0 for v in e['control_calls']) and e['control_calls'][0]['stdout'].strip() == container
         and e['native_log_sha256'] == digest(bound(directory+'/'+label+'.native.log')), 'Exact native argv/control calls/log binding required')
    inspections = [json.loads(v['stdout']) for v in e['control_calls'] if v['operation'] == 'inspect']
    need(inspections[0] == initial and inspections[-1] == final and all(v['Id'] == container and v['Owner'] == owner
         and v['Image'] == IMAGE and v['Controls'] == controls for v in inspections), 'Inspect readbacks must match embedded lifecycle metadata')
    return cgal_interval(load(directory+'/'+label+'/report.json'),role,ids), digest(bound(directory+'/'+label+'/report.json'))


def assess(path, expected):
    need(digest(path) == expected, 'Exact separately reviewed actual assessment child required')
    child = json.loads(path.read_text()); pins = child['input_sha256']
    need(child['schema'] == '962-CUB-CGAL-combined-distance-assessment-contract/v1'
         and child['root_authorized_assessment'] is True and child['root_and_peer_review_complete'] is True, 'Actual root/peer assessment authority required')
    def bound(n):
        p = ROOT/n; need(n in pins and p.is_file() and digest(p) == pins[n] and (Path(n).is_absolute() or not p.is_symlink()), 'Bound input missing or changed');return p
    def load(n): return json.loads(bound(n).read_text())
    bound(str(Path(__file__).resolve().relative_to(ROOT)));bound(str(BASE.relative_to(ROOT)))
    for n in pins: bound(n)
    roles(child['cgal_directories']); masks,cancellation = split_coverage(child,bound,load)
    rows = []; b,h = forward(bound,load,cancellation);rows.append(dict(role='forward_CUB',lower_mm=b[0],upper_mm=b[1],report_sha256=h))
    for role in ('cap','noncap'):
        need(child['cgal_directories'][role] == PREFIX+'distance-cgal-'+role+'-001', 'Exact stopped CGAL directory required')
        b,h = reverse(role,child['cgal_directories'][role],masks[role],bound,load)
        rows.append(dict(role=role+'_CGAL',lower_mm=b[0],upper_mm=b[1],report_sha256=h))
    low,high = H.combine([(x['lower_mm'],x['upper_mm']) for x in rows]); reverse_bounds = [max(x['lower_mm'] for x in rows[1:]),max(x['upper_mm'] for x in rows[1:])]
    need(high-low <= H.GAP and reverse_bounds[1]-reverse_bounds[0] <= H.GAP, 'Combined/reverse closed gaps required')
    for n in pins: bound(n)
    return dict(schema='962-CUB-CGAL-combined-polygon-distance-assessment/v1',directions=rows,reverse_interval_mm=reverse_bounds,
        combined_two_way_interval_mm=[low,high],absolute_gap_tolerance_mm=H.GAP,envelope_limit_mm=H.BUDGET,
        independent_polygon_distance_gate_passed=high<=H.BUDGET,old_CUB_failures_preserved_not_credited=True,
        assessment_contract_sha256=expected,assessor_sha256=digest(__file__),all_bound_inputs_unchanged=True,
        roundoff_certificate=False,native_CAD_deviation_certified=False,stronger_Mesh2_admission=False,
        head_volume_or_PDE_admitted=False,engineering_accepted=False,manufacturing_authorized=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('contract',type=Path)
    parser.add_argument('--contract-sha256',required=True);parser.add_argument('--report',type=Path,required=True);args=parser.parse_args()
    need(not args.report.exists() and not args.report.is_symlink(), 'Existing assessment preserved')
    result=assess(args.contract,args.contract_sha256)
    with args.report.open('x') as stream: json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
