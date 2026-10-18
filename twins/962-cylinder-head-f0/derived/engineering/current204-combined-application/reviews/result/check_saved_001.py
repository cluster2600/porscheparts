"""Independent stopped JSON/word associations only; no native, MSH, or geometry replay."""
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / 'work/962-engineering'
HERE = Path(__file__).resolve().parent
OUT = WORK / 'head-star-current204-combined-application-001'
RUN = WORK / 'head-star-current204-combined-application-root-execution-001'
ACTUAL = WORK / 'head-star-current204-combined-application-execution-prep-001/actual-contract.json'
MANIFEST = WORK / 'head-star-current204-combined-application-prep-001/admitted-manifest.json'


def digest(path):
    assert path.suffix != '.msh', 'MSH bodies excluded'
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def serialized(value):
    return hashlib.sha256((json.dumps(value, indent=2, allow_nan=False) + '\n').encode()).hexdigest()


def words(values):
    assert all(type(x) in (int, float) and math.isfinite(x) for x in values)
    return struct.pack('<' + 'd' * len(values), *values)


actual = load(ACTUAL)
closed = load(RUN / 'closed-result.json')
manifest = load(MANIFEST)
assert digest(ACTUAL) == '98949f822fafd53199204eb812e5eec85b93516873743637de5b1baab5a2b600'
assert digest(RUN / 'closed-result.json') == '36f4cfbde50c83680fd617dcc7536ddaba3c7d57ccb8cbf3b4263629df9f7684'
assert digest(RUN / 'result-review.json') == '324fac82ca823c3cd378b8fd89a2f026f15e742a8647021d018ded49067a1133'
assert len(actual['input_hashes']) == actual['input_count'] == 420
deferred = {p: h for p, h in actual['input_hashes'].items() if Path(p).suffix == '.msh'}
assert deferred == {actual['MSH']: actual['MSH_sha256']}
selected = {ROOT / p: h for p, h in actual['input_hashes'].items() if p not in deferred}
for p in [ACTUAL, RUN / 'closed-result.json', RUN / 'launch.json', RUN / 'result-review.json',
          RUN / 'controller.stdout.log', RUN / 'controller.stderr.log']:
    selected[p] = digest(p)
assert set(p.name for p in OUT.iterdir()) == set(closed['output_files'])
assert len(closed['output_files']) == 7
for name, row in closed['output_files'].items():
    p = OUT / name
    assert p.is_file() and not p.is_symlink() and p.stat().st_size == row['bytes']
    if p.suffix != '.msh':
        selected[p] = row['sha256']
before = {str(p.relative_to(ROOT)): {'sha256': digest(p), 'bytes': p.stat().st_size} for p in selected}
assert all(before[str(p.relative_to(ROOT))]['sha256'] == h for p, h in selected.items())
report = load(OUT / 'readback-report.json')
receipt = load(OUT / 'execution-receipt.json')
parent = load(WORK / 'apex1474426-head-application-001/readback-report.json')
context = load(WORK / 'head-star-current204-union-context-001/readback-report.json')
batch = load(WORK / 'head-star-current204-batch-shells-001/report.json')
source_rows = {r['apex']: r for r in batch['all_candidate_star_records']}
context_nodes = {r['node_tag']: r for r in context['selected_original_native_node_rows']}
apices = manifest['accepted_apices']
assert len(apices) == len(set(apices)) == len(manifest['cases']) == 47
assert report['admitted_apices'] == apices
assert report['before'] == parent['after'] == parent['saved_reopen']
assert report['after'] == report['saved_reopen']
assert report['runtime_sha256s'] == actual['runtime_sha256s']
assert report['original_parent_MSH_sha256'] == actual['MSH_sha256']
assert report['admitted_manifest_sha256'] == digest(MANIFEST)
assert report['context_sha256'] == digest(WORK / 'head-star-current204-union-context-001/readback-report.json')
all_vertices, all_old_cells, replacements, mapped_words = set(), set(), {}, []
metrics = {k: [] for k in ('SICN', 'Jacobian', 'native_volume_mm3')}
case_checks = []
nmax, emax, total_poor, total_fresh, noncontiguous = 1613812, 32158167, 0, 0, 0
for index, item in enumerate(manifest['cases']):
    row = item['local_case']
    apex = row['apex']
    assert apex == apices[index]
    original = source_rows[apex]
    shell, observation = original['shell'], original['observation']
    assert serialized(original) == row['source_record_sha256']
    assert serialized(shell) == row['shell_serialized_sha256']
    assert serialized(observation) == row['observation_serialized_sha256']
    vertices = set(original['all_vertex_tags'])
    old = sorted(r['tetrahedron_tag'] for r in observation['native_ordered_cell_rows'])
    assert sorted(vertices) == row['old_vertex_tags'] and old == row['old_tetrahedron_tags']
    assert len(old) == row['K'] and len(vertices) == row['NV'] + 1
    assert not vertices & all_vertices and not set(old) & all_old_cells
    all_vertices.update(vertices)
    all_old_cells.update(old)
    old_poor = sum(r['initial_native_SICN'] < .1 for r in observation['native_ordered_cell_rows'])
    assert all(r['initially_positive_poor'] == (0 < r['initial_native_SICN'] < .1) for r in observation['native_ordered_cell_rows'])
    total_poor += old_poor
    original_nodes = {r['node_tag']: r for r in observation['selected_node_rows']}
    for tag in vertices:
        node, native = original_nodes[tag], context_nodes[tag]
        assert words(node['coordinates_mm']) == words(native['coordinates_mm'])
        assert [x.hex() for x in node['coordinates_mm']] == node['binary64_hex'] == native['binary64_hex']
        assert words(node['coordinates_mm']).hex() == node['binary64_little_endian_bytes_hex']
    arrays = load(ROOT / row['records']['arrays']['path'])
    assert arrays['after'] == arrays['saved_reopen']
    saved = arrays['saved_reopen']
    assert len(saved['node_tags']) == row['N'] and len(saved['tetra_tags']) == row['M']
    assert saved['node_tags'] == sorted(set(saved['node_tags']))
    assert saved['tetra_tags'] == sorted(set(saved['tetra_tags']))
    coords = dict(zip(saved['node_tags'], saved['coordinates_mm'], strict=True))
    assert all(len(c) == 3 for c in coords.values())
    node_map = {i: tag for i, tag in enumerate(shell['local_to_global_node_tags'], 1)}
    assert len(node_map) == row['NV'] and apex not in node_map.values()
    for vertex in shell['vertex_rows']:
        local, global_tag = vertex['local_node_tag'], vertex['source_global_node_tag']
        assert node_map[local] == global_tag
        assert words(coords[local]) == words(vertex['coordinates_mm']) == words(context_nodes[global_tag]['coordinates_mm'])
        assert words(coords[local]).hex() == vertex['binary64_little_endian_bytes_hex']
    interiors = sorted(set(saved['node_tags']) - set(node_map))
    assert interiors == row['candidate_interior_node_tags'] and len(interiors) == row['I'] >= 1
    noncontiguous += interiors != list(range(row['NV'] + 1, row['NV'] + 1 + row['I']))
    fresh = list(range(nmax + 1, nmax + row['I']))
    node_map.update(zip(interiors, [apex] + fresh, strict=True))
    slots = old + list(range(emax + 1, emax + 1 + row['M'] - row['K']))
    assert len(slots) == row['M'] and row['M'] >= row['K']
    case_replacement = {str(tag): [node_map[n] for n in cell] for tag, cell in zip(slots, saved['tetra_node_tags'], strict=True)}
    expected = {'apex': apex, 'node_map': {str(k): v for k, v in node_map.items()}, 'fresh_nodes': fresh,
                'element_slots': slots, 'replacement': case_replacement, 'local_tetra_tags': saved['tetra_tags'],
                'interior_node_tags': interiors}
    assert report['per_case_mappings'][index] == expected
    assert not set(replacements) & set(case_replacement)
    replacements.update(case_replacement)
    coordinate_payload = b''.join(struct.pack('<Q', node_map[tag]) + words(coords[tag]) for tag in saved['node_tags'])
    mapped_words.append(coordinate_payload)
    for metric in metrics:
        values = saved['native_qualities'][metric]
        assert len(values) == row['M'] and all(math.isfinite(q) and q > 0 for q in values)
        assert metric != 'SICN' or min(values) >= .1
        metrics[metric].extend(values)
    case_checks.append({'apex': apex, 'old_cells': row['K'], 'replacement_cells': row['M'], 'fresh_nodes': len(fresh),
                        'raw_candidate_to_global_coordinate_words_sha256': hashlib.sha256(coordinate_payload).hexdigest(),
                        'ordered_replacements_sha256': serialized(case_replacement), 'local_metric_words_exact': True})
    nmax += row['I'] - 1
    emax += row['M'] - row['K']
    total_fresh += len(fresh)
assert len(all_old_cells) == 2078 and len(replacements) == 2972 and total_fresh == 162 and total_poor == 75
assert list(report['replacement_ordered_rows'].items()) == list(replacements.items())
assert {'node': nmax, 'element_all_dimensions': emax} == report['expected_maxima'] == actual['expected_global_maxima']
for key, values in metrics.items():
    assert words(values) == words(report['replacement_native_metrics'][key])
assert sum(len(v) for v in metrics.values()) == 8916
before_pres = report['before_preservation']
parameter_keys = ('dimension', 'entity_tag', 'count', 'parameter_width', 'node_tags_u64_sha256', 'available_parameter_words_f64_sha256')
parameters = [{k: r[k] for k in parameter_keys} for r in context['full_entity_node_parameter_inventory']]
for stage in ('before_preservation', 'after_preservation', 'saved_preservation'):
    proof = report[stage]
    assert proof['preservation'] == before_pres['preservation']
    assert proof['preservation']['outside_nodes'] == 1097057 - 47
    assert proof['preservation']['outside_TET4'] == 3620861 - 2078
    assert proof['original_parameter_projection'] == parameters
    assert proof['original_classification_projection_exact'] is True and proof['expected_new_nodes'] == 162
    assert proof['new_nodes_on_volume1'] == (0 if stage == 'before_preservation' else 162)
    assert proof['metadata_sha256s'] == before_pres['metadata_sha256s']
    for key, value in proof['metadata_sha256s'].items():
        canonical = json.dumps(context[key], sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        assert hashlib.sha256(canonical).hexdigest() == value
assert report['after_preservation'] == report['saved_preservation']
for stage in ('before', 'after', 'saved_reopen'):
    audit = report[stage]
    assert audit['source_boundary_identity'] == report['before']['source_boundary_identity']
    assert audit['unreferenced_mesh_nodes'] == 0
    for key in ('minimum_jacobian', 'native_volume_mm3', 'minimum_SICN', 'independent_signed_volume_mm3'):
        q = audit['quality'][key]
        assert q['count'] == audit['tetrahedra'] and q['nonpositive_count'] == 0 and q['minimum'] > 0
assert report['after']['total_mesh_nodes'] == 1097219 and report['after']['tetrahedra'] == 3621755
assert report['after']['tetra_referenced_interior_nodes'] == 225488
assert report['before']['quality']['minimum_SICN']['below_point1_count'] == 204
assert report['after']['quality']['minimum_SICN']['below_point1_count'] == report['actual_whole_head_positive_poor_count'] == 129
assert report['after']['quality']['minimum_SICN']['minimum'] == .039074265058645995
assert report['actual_replacement_SICN_gate_passed'] is True and report['actual_whole_head_SICN_gate_passed'] is False
assert report['procedural_checks_passed'] and report['partial_replacement_attempted'] and report['partial_replacement_completed']
assert report['saved_mesh_identity_exact'] and report['bound_inputs_unchanged'] and report['gmsh_warnings_errors'] == []
counts = {'removeElements': 1, 'setNode': 47, 'addNodes': 1, 'addElementsByType': 1, 'rebuildNodeCache': 1,
          'rebuildElementCache': 1, 'write_mesh': 1, 'generate': 0, 'optimize': 0, 'createGeometry': 0, 'reclassifyNodes': 0, 'solve': 0}
assert report['native_operation_counts'] == counts and report['call_counts_are_attempts'] is True
for key in ('global_embedding_or_containment_proved', 'stronger_Mesh2_criterion_passed', 'engineering_accepted', 'physics_qualified', 'material_qualified', 'process_calibrated', 'manufacturing_authorized'):
    assert report[key] is False
assert receipt['returncode'] == closed['controller_returncode'] == 2 and receipt['stop_reason'] is None
for key, name in [('reader_sha256', 'reader.py'), ('runner_sha256', 'run_readback.py'), ('contract_sha256', 'frozen-contract.json'), ('native_log_sha256', 'native.log'), ('readback_report_sha256', 'readback-report.json')]:
    assert receipt[key] == digest(OUT / name)
assert receipt['hard_wall_seconds'] == 1200 and receipt['sampled_RSS_stop_bytes'] == 8 * 1024**3
assert receipt['sampled_output_stop_bytes'] == 1024**3 and receipt['threads'] == 2
assert receipt['max_observed_RSS_bytes'] == max(r['RSS_bytes'] for r in receipt['RSS_samples']) == 6093012992
assert receipt['hard_OS_CPU_quota_applied'] is False and receipt['hard_address_space_limit_applied'] is False
assert receipt['native_generate_optimize_solve_calls_declared'] == 0 and receipt['mesh_write_calls_declared'] == 1 and receipt['counters_are_declarations']
assert receipt['final_output_bytes_before_receipt'] == sum(r['bytes'] for n, r in closed['output_files'].items() if n != 'execution-receipt.json')
assert closed['controller_wait_reaped'] and closed['observed_owned_controller_leader_absent']
assert closed['native_PID_directly_observed'] is False and closed['native_cleanup_attributed_to_frozen5ab38_finally_and_receipt'] is True
assert closed['universal_descendant_absence_claimed'] is False and closed['all420_input_actual_selected_runtime_python_unchanged'] is True
assert closed['root_stop_reason'] is None and closed['root_error'] is None and closed['pin_error'] is None and closed['root_fallback_SIGKILL'] is False
assert closed['partial_procedural_checks_passed'] and closed['actual_whole_head_quality_gate_passed'] is False and closed['observed_whole_head_poor_count'] == 129
assert closed['actual_sha256'] == digest(ACTUAL)
assert closed['root_launch_sha256'] == digest(RUN / 'launch.json')
launch = load(RUN / 'launch.json')
assert launch['controller_pid'] == closed['controller_pid']
assert digest(RUN / 'controller.stdout.log') == closed['stdout_sha256'] and digest(RUN / 'controller.stderr.log') == closed['stderr_sha256']
assert report['mesh_sha256'] == closed['output_files']['head-volume.msh']['sha256'] and report['mesh_bytes'] == 235785726
after = {str(p.relative_to(ROOT)): {'sha256': digest(p), 'bytes': p.stat().st_size} for p in selected}
assert before == after
result = {'decision': 'CLEAR_SAVED_ASSOCIATIONS_PARTIAL_PROCEDURE_WHOLE_HEAD_REJECTED',
          'small_body_count': len(selected), 'actual_inputs': 420, 'independently_hashed_actual_small_inputs': 419,
          'deferred_parent_MSH_root_identity': deferred, 'output_inventory': closed['output_files'],
          'independently_hashed_outputs': 6, 'output_MSH_identity_scope': 'root inventory and saved report only; stat size, no body read/hash/decode',
          'case_count': 47, 'removed_cells': 2078, 'replacement_cells': 2972, 'fresh_nodes': 162,
          'noncontiguous_interior_tag_cases': noncontiguous, 'removed_original_poor_cells': 75,
          'candidate_to_global_raw_words_sha256': hashlib.sha256(b''.join(mapped_words)).hexdigest(),
          'native_metric_doublewords_bit_exact': 8916, 'maximum_metric_word_difference': 0,
          'observed_global_poor_before': 204, 'observed_global_poor_after': 129,
          'observed_global_minimum_SICN': .039074265058645995, 'replacement_minimum_SICN': min(metrics['SICN']),
          'full_before_parent_association': True, 'full_after_saved_association': True,
          'outside_and_original_metadata_saved_associations': True, 'operation_attempts': counts,
          'native_global_metrics_and_preservation_execution_attribution': 'frozen worker plus root; no native/global-array replay or MSH decode',
          'root_controller_wait_and_absence': True, 'native_PID_directly_observed_by_root': False,
          'native_cleanup_scope': 'inner frozen 5ab38 controller finally/receipt; no universal descendant absence claim',
          'sampled_worker_RSS_max_bytes': receipt['max_observed_RSS_bytes'], 'sampled_RSS_is_true_peak': False,
          'pair_or_geometry_predicates_reexecuted': False, 'native_or_scientific_imports': False,
          'engineering_accepted': False, 'physics_qualified': False, 'manufacturing_authorized': False,
          'case_checks': case_checks, 'small_hashes_before': before, 'small_hashes_after': after}
(HERE / 'independent-saved-check.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
print(json.dumps({k: result[k] for k in ('decision', 'case_count', 'replacement_cells', 'fresh_nodes', 'native_metric_doublewords_bit_exact', 'observed_global_poor_after', 'small_body_count')}))
