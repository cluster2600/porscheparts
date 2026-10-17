"""Independent saved-row associations only; no prepared-module or native imports."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import math
import struct

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = ROOT / 'work/962-engineering'
FACES = ((0, 2, 1), (0, 1, 3), (1, 2, 3), (2, 0, 3))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(rel):
    return json.loads((ROOT / rel).read_text())

def encoded(value):
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def same(a, b):
    assert canonical(a) == canonical(b), 'Saved JSON value/type/float-word join'

def jsha(value):
    return hashlib.sha256(canonical(value)).hexdigest()

def cyclic(a, b):
    return any(list(a) == list(b[i:]) + list(b[:i]) for i in range(3))

def coordinates(row):
    xyz = row['coordinates_mm']
    assert len(xyz) == 3 and all(type(x) is float and math.isfinite(x) for x in xyz)
    assert row['binary64_hex'] == [x.hex() for x in xyz]
    assert all(struct.pack('<d', float.fromhex(h)) == struct.pack('<d', x) for h, x in zip(row['binary64_hex'], xyz))
    return struct.pack('<3d', *xyz)

def unique(rows, key):
    answer = {row[key]: row for row in rows}
    assert len(answer) == len(rows)
    assert list(answer) == sorted(answer)
    return answer

def main():
    cfg = json.loads((HERE / 'checker-inputs.json').read_text())
    before = {rel: sha(ROOT / rel) for rel in cfg['saved_input_sha256']}
    assert before == cfg['saved_input_sha256']
    actual = load(cfg['actual'])
    report = load(cfg['report'])
    closed = load(cfg['closed'])
    launch = load(cfg['launch'])
    receipt = load(cfg['receipt'])
    parent = load(cfg['parent'])
    census = load(cfg['census'])
    batch = load(cfg['batch'])
    manifest = load(cfg['manifest'])
    child = load(cfg['child'])
    assert child['blockers'] == []
    assert actual['input_count'] == len(actual['input_hashes']) == 53
    for rel, digest in actual['input_hashes'].items():
        if rel == actual['MSH']:
            assert digest == actual['MSH_sha256'] == cfg['parent_MSH_metadata']['sha256']
        else:
            assert before[rel] == digest
    assert (ROOT / cfg['report']).parent == ROOT / actual['output_directory']
    assert {p.name for p in (ROOT / actual['output_directory']).iterdir()} == set(closed['output_files'])
    assert len(closed['output_files']) == 6
    for name, record in closed['output_files'].items():
        path = ROOT / actual['output_directory'] / name
        assert not path.is_symlink() and path.is_file()
        assert path.stat().st_size == record['bytes'] and sha(path) == record['sha256']
    assert (ROOT / actual['output_directory'] / 'frozen-contract.json').read_bytes() == (ROOT / cfg['actual']).read_bytes()
    for target, source in [('reader.py', 'reader.py'), ('run_readback.py', 'run_readback.py')]:
        assert (ROOT / actual['output_directory'] / target).read_bytes() == (WORK / 'head-star-current204-union-context-prep-002' / source).read_bytes()
    assert receipt['contract_sha256'] == closed['actual_sha256'] == launch['actual_sha256'] == before[cfg['actual']]
    assert closed['peer_sha256'] == launch['peer_sha256'] == before[cfg['child']]
    assert closed['root_launch_sha256'] == before[cfg['launch']]
    assert receipt['reader_sha256'] == actual['reader_sha256'] and receipt['runner_sha256'] == actual['runner_sha256']
    assert receipt['readback_report_sha256'] == before[cfg['report']]
    assert receipt['native_log_sha256'] == closed['output_files']['native.log']['sha256']
    assert closed['returncode'] == receipt['returncode'] == 0
    assert closed['root_stop_reason'] is None and closed['root_error'] is None and receipt['stop_reason'] is None
    assert closed['controller_wait_reaped'] is True and closed['observed_controller_absent'] is True
    assert launch['controller_pid'] == launch['controller_pgid'] == closed['controller_pid']
    assert closed['native_PID_observed'] is False and closed['controller_fallback_SIGKILL'] is False
    assert closed['native_wait_reap_attributed_to_unchanged_controller_and_valid_receipt'] is True
    assert closed['universal_descendant_absence_claimed'] is False
    assert closed['all53_inputs_parent_native3_NumPy_actual_peer_before_after_unchanged'] is True
    assert receipt['hard_wall_seconds'] == actual['controls']['hard_wall_seconds'] == 120
    assert receipt['sampled_RSS_stop_bytes'] == actual['controls']['sampled_RSS_stop_bytes'] == 8 * 1024**3
    assert receipt['sampled_output_stop_bytes'] == actual['controls']['sampled_output_stop_bytes'] == 1024**3
    assert receipt['threads'] == 2 and receipt['wall_seconds'] < 120 and closed['wall_seconds'] < 135
    samples = receipt['RSS_samples']
    assert all(a['wall_seconds'] < b['wall_seconds'] for a, b in zip(samples, samples[1:]))
    assert max(x['RSS_bytes'] for x in samples) == receipt['max_observed_RSS_bytes'] < 8 * 1024**3
    assert receipt['final_output_bytes_before_receipt'] == sum(v['bytes'] for k, v in closed['output_files'].items() if k != 'execution-receipt.json')
    assert report['status'] == 'complete_current204_selected116_union_parent_context_census'
    assert report['stage'] == 'completed' and report['complete_context_census'] is True
    for field in ['optimization_authorized', 'mesh_write_authorized', 'generation_authorized', 'head_edit_authorized', 'head_execution_authorized', 'stitching_authorized', 'engineering_accepted', 'physics_qualified', 'manufacturing_authorized']:
        assert report[field] is False and actual[field] is False
    assert report['quality_recomputed'] is False and report['native_generate_optimize_meshwrite_solve_calls'] == receipt['native_generate_optimize_meshwrite_solve_calls'] == 0
    assert report['candidate_or_MSH_written'] is False and report['selected_geometry_JSON_exported'] is True
    assert report['global_embedding_containment_or_after_edit_preservation_proved'] is False
    assert report['original_parent_MSH_sha256'] == actual['MSH_sha256'] == parent['mesh_sha256']
    assert report['original_parent_MSH_bytes'] == actual['MSH_bytes'] == parent['mesh_bytes'] == 235744782
    same(parent['after'], parent['saved_reopen'])
    same(report['full_array_sha256s'], parent['after']['array_sha256s'])
    same(report['full_native_classifications'], parent['after']['classifications'])
    same(report['current_source_boundary_identity'], parent['after']['source_boundary_identity'])
    same(report['runtime_sha256s'], actual['runtime_sha256s'])
    assert report['runtime'] == {'python': '3.10.11', 'numpy': '2.0.2', 'gmsh': '4.15.2', 'machine': 'arm64'}
    assert report['bound_inputs_unchanged'] is True
    same(report['retained_current_quality_and_global_incidence'], {k: parent['after'][k] for k in ['quality', 'actual_tetra_boundary', 'internal_tetra_face_orientation']})
    assert parent['after']['quality']['minimum_SICN']['below_point1_count'] == 204
    assert parent['actual_whole_head_SICN_gate_passed'] is False
    assert (report['full_node_count'], report['full_TET4_count']) == (1097057, 3620861)
    for key, digest in report['full_array_sha256s'].items():
        assert census[key] == digest

    cases = manifest['cases_in_increasing_apex_order']
    assert [c['apex'] for c in cases] == report['selected_apex_tags'] == sorted(set(batch['selected_apex_tags']))
    assert len(cases) == 116 and cases[0]['apex'] == 1393275
    assert manifest['source_batch_report_sha256'] == before[cfg['batch']]
    assert batch['source_census_sha256'] == before[cfg['census']]
    records = {x['apex']: x for x in batch['all_candidate_star_records']}
    star = census['complete_seed_star_census']
    cells = unique(star['complete_incident_tetrahedra'], 'tetrahedron_tag')
    nodes = unique(star['unique_incident_nodes'], 'node_tag')
    assert len(cells) == 5267 and len(nodes) == 2905
    old = {}; points = {}; expected_faces = {}; shell_nodes = set(); summaries = []
    for case in cases:
        apex = case['apex']; record = records[apex]; observation = record['observation']; shell = record['shell']
        assert record['eligible'] is True and hashlib.sha256(encoded(record)).hexdigest() == case['source_record_sha256']
        for body, field in [(shell, 'shell_serialized_sha256'), (observation, 'observation_serialized_sha256'), (record['necessary_face_screen'], 'screen_serialized_sha256')]:
            assert hashlib.sha256(encoded(body)).hexdigest() == case[field]
        expected = [r for r in cells.values() if apex in r['node_tags']]
        same(expected, observation['native_ordered_cell_rows'])
        assert len(expected) == case['old_tetrahedra']
        assert [x['tetrahedron_tag'] for x in expected] == case['old_tetrahedron_tags']
        vertices = sorted({t for x in expected for t in x['node_tags']})
        assert vertices == case['old_vertex_tags'] == record['all_vertex_tags']
        observed_nodes = unique(observation['selected_node_rows'], 'node_tag')
        assert sorted(observed_nodes) == vertices and not set(vertices) & set(points)
        for tag, row in observed_nodes.items():
            coordinates(row)
            assert set(row) == set(nodes[tag]) | {'binary64_little_endian_bytes_hex'}
            same({k: row[k] for k in nodes[tag]}, nodes[tag])
            assert row['binary64_little_endian_bytes_hex'] == coordinates(row).hex()
            points[tag] = row
        for row in expected:
            assert row['tetrahedron_tag'] not in old
            old[row['tetrahedron_tag']] = row['node_tags']
        mapping = shell['local_to_global_node_tags']
        assert mapping == sorted(set(vertices) - {apex}) and apex not in mapping
        assert mapping == sorted(mapping) and len(mapping) == case['shell_nodes']
        inverse = shell['global_to_local_node_tags']
        assert inverse == {str(t): i + 1 for i, t in enumerate(mapping)}
        shell_nodes.update(mapping)
        facekeys = []
        for face in shell['oriented_triangle_rows']:
            key = tuple(sorted(face['source_global_node_tags']))
            assert key not in expected_faces and apex not in key
            assert face['source_global_node_tags'] == [mapping[i - 1] for i in face['local_node_tags']]
            owner = cells[face['source_owner_tetrahedron_tag']]
            assert owner['native_array_index'] == face['source_native_array_index']
            assert tuple(face['native_corner_indices']) in FACES
            assert [owner['node_tags'][i] for i in face['native_corner_indices']] == face['source_global_node_tags']
            expected_faces[key] = face; facekeys.append(list(key))
        assert len(facekeys) == case['shell_faces'] == len(expected)
        summaries.append({'apex': apex, 'case_key': case['case_key'], 'case_record_sha256': case['source_record_sha256'], 'old_tetrahedra': case['old_tetrahedra'], 'shell_nodes': case['shell_nodes'], 'shell_faces': case['shell_faces'], 'original_boundary_shell_nodes': case['original_boundary_shell_nodes'], 'old_cell_tags': sorted(x['tetrahedron_tag'] for x in expected), 'shell_node_tags': mapping, 'shell_face_keys': sorted(facekeys)})
    same(summaries, report['selected_case_contexts'])
    assert (len(old), len(points), len(shell_nodes), len(expected_faces)) == (4164, 2430, 2314, 4164)
    same([{'tetrahedron_tag': t, 'node_tags': old[t]} for t in sorted(old)], report['complete_old_selected_apex_incident_rows'])

    entities = {(x['dimension'], x['entity_tag']) for x in report['full_entity_metadata']}
    selected = unique(report['selected_original_native_node_rows'], 'node_tag')
    assert set(selected) == set(points)
    for tag, row in selected.items():
        assert coordinates(row) == coordinates(points[tag])
        assert row['dimension'] == (2 if nodes[tag]['source_boundary_tag'] else 3)
        assert row['dimension'] == (2 if tag <= 871731 else 3) and (row['dimension'], row['entity_tag']) in entities
        params = row['available_parametric_coordinates']
        assert all(type(x) is float and math.isfinite(x) for x in params)
        assert row['parametric_binary64_hex'] == [x.hex() for x in params]
    faces = report['all_selected_shell_face_records']
    assert [tuple(x['shell_face_key']) for x in faces] == sorted(expected_faces)
    outside = {}; partition = Counter(); exterior = {}; owner_count = 0
    for face in faces:
        key = tuple(face['shell_face_key']); frozen = expected_faces[key]
        same(face['oriented_shell_face'], frozen['source_global_node_tags'])
        owners = face['owners']; removed = [x for x in owners if x['removed_star_owner'] is True]
        remaining = [x for x in owners if x['removed_star_owner'] is False]
        assert len(owners) == len(removed) + len(remaining) and len(removed) == 1 and len(remaining) <= 1
        first = removed[0]
        assert first['tetrahedron_tag'] == frozen['source_owner_tetrahedron_tag']
        assert first['node_tags'] == old[first['tetrahedron_tag']]
        same(first['native_corner_indices'], frozen['native_corner_indices'])
        for row in owners:
            assert len(row['node_tags']) == len(set(row['node_tags'])) == 4
            assert tuple(row['native_corner_indices']) in FACES
            assert row['oriented_face'] == [row['node_tags'][i] for i in row['native_corner_indices']]
            assert sorted(row['oriented_face']) == list(key)
            assert row['dimension'] == 3 and (3, row['entity_tag']) in entities
            owner_count += 1
        assert cyclic(first['oriented_face'], face['oriented_shell_face'])
        if remaining:
            assert face['interface_kind'] == 'internal_with_outside_owner' and face['parent_exterior_TRI_rows'] == []
            other = remaining[0]; tag = other['tetrahedron_tag']
            assert tag not in old and cyclic(other['oriented_face'], list(reversed(first['oriented_face'])))
            if tag in outside: same(outside[tag], other['node_tags'])
            outside[tag] = other['node_tags']
            if tag in cells: same(cells[tag]['node_tags'], other['node_tags'])
        else:
            assert face['interface_kind'] == 'parent_exterior' and len(face['parent_exterior_TRI_rows']) == 1
            tri = face['parent_exterior_TRI_rows'][0]
            assert tri['dimension'] == 2 and tri['element_type'] == 2 and (2, tri['entity_tag']) in entities
            assert cyclic(tri['node_tags'], face['oriented_shell_face'])
            assert tri['element_tag'] not in exterior
            exterior[tri['element_tag']] = tri
            assert all(selected[t]['dimension'] == 2 and selected[t]['entity_tag'] == tri['entity_tag'] for t in tri['node_tags'])
        partition[face['interface_kind']] += 1
    assert dict(partition) == {'parent_exterior': 1518, 'internal_with_outside_owner': 2646}
    same([{'tetrahedron_tag': t, 'node_tags': outside[t]} for t in sorted(outside)], report['complete_outside_owner_rows'])
    assert len(outside) == 2623
    outside_nodes = unique(report['complete_outside_owner_coordinate_rows'], 'node_tag')
    assert sorted(outside_nodes) == sorted({t for row in outside.values() for t in row}) and len(outside_nodes) == 3888
    overlap_census = overlap_selected = 0
    for tag, row in outside_nodes.items():
        coordinates(row)
        if tag in nodes:
            assert coordinates(row) == coordinates(nodes[tag]); overlap_census += 1
        if tag in selected:
            assert coordinates(row) == coordinates(selected[tag]); overlap_selected += 1
    maxima = report['independently_derived_global_maxima']
    same(maxima, parent['after_preservation']['maxima'])
    assert maxima == {'node': 1613812, 'element_all_dimensions': 32158167}
    assert max(int(t) for t in parent['local_to_global_node_map'].values()) == maxima['node']
    assert max(parent['replacement_element_slots']) == maxima['element_all_dimensions']
    assert max(set(outside_nodes) | set(points)) <= maxima['node']
    assert max(set(old) | set(outside) | set(exterior)) <= maxima['element_all_dimensions']
    inventory = report['full_entity_node_parameter_inventory']
    assert sum(x['count'] for x in inventory) == report['full_node_count']
    assert {(x['dimension'], x['entity_tag']) for x in inventory} == entities
    assert {(x['dimension'], x['entity_tag']): x['count'] for x in inventory} == {(2, 1): 871731, (3, 1): 225326}
    for row in inventory:
        assert row['parameter_width'] == 0 and row['available_parameter_words_f64_sha256'] == hashlib.sha256(b'').hexdigest()
        for tag, node in selected.items():
            if (node['dimension'], node['entity_tag']) == (row['dimension'], row['entity_tag']):
                assert len(node['available_parametric_coordinates']) == row['parameter_width']
    same(report['full_periodic_metadata'], [{'dimension': 2, 'entity_tag': 1, 'master_entity': 1, 'node_tags': [], 'master_node_tags': [], 'affine_transform': []}])
    assert report['full_physical_group_metadata'] == []
    lower = report['full_lower_dimensional_inventory']
    assert len(lower) == 1
    assert {k: lower[0][k] for k in ['dimension', 'entity_tag', 'element_type', 'nodes_per_element', 'count', 'minimum_tag', 'maximum_tag']} == {'dimension': 2, 'entity_tag': 1, 'element_type': 2, 'nodes_per_element': 3, 'count': 1743878, 'minimum_tag': 1, 'maximum_tag': 1743878}
    assert all(lower[0]['minimum_tag'] <= t <= lower[0]['maximum_tag'] for t in exterior)
    refs = report['future_preservation_references']
    computed = {}
    for field in ['full_lower_dimensional_inventory', 'full_entity_metadata', 'full_physical_group_metadata', 'full_periodic_metadata']:
        computed[field] = jsha(report[field])
        assert refs[field + '_sha256'] == computed[field] == parent['after_preservation']['metadata_sha256s'][field]
    assert refs['full_classification_proof_sha256'] == jsha(report['full_native_classifications'])
    param_keys = ['dimension', 'entity_tag', 'count', 'parameter_width', 'node_tags_u64_sha256', 'available_parameter_words_f64_sha256']
    assert refs['full_original_entity_parametric_metadata_sha256'] == jsha([{k: r[k] for k in param_keys} for r in inventory])
    assert refs['outside_nodes'] == report['full_node_count'] - len(cases) == 1096941
    assert refs['outside_TET4'] == report['full_TET4_count'] - len(old) == 3616697
    assert len(points) - len(cases) == len(shell_nodes)
    after = {rel: sha(ROOT / rel) for rel in before}
    assert before == after
    answer = {
        'schema': '962-independent-selected116-union-saved-association-check/v1', 'status': 'PASS',
        'saved_inputs_hashed_before_and_after': len(before), 'all_saved_inputs_unchanged': True,
        'output_files': closed['output_files'], 'original_actual_inputs': 53, 'current_small_actual_inputs_independently_hashed': 52,
        'parent_MSH_and_native3_NumPy_freshness': 'Root closed record attribution only; bodies not read by this checker.',
        'counts': {'cases': len(cases), 'old_TET4': len(old), 'selected_original_nodes': len(points), 'shell_nodes': len(shell_nodes), 'shell_faces': len(faces), 'saved_owner_rows': owner_count, 'exterior_faces': partition['parent_exterior'], 'connected_faces': partition['internal_with_outside_owner'], 'unique_outside_owner_TET4': len(outside), 'outside_owner_coordinates': len(outside_nodes), 'outside_coordinate_overlap_with_census': overlap_census, 'outside_coordinate_overlap_with_selected': overlap_selected, 'full_original_parameter_rows_native_count': sum(x['count'] for x in inventory)},
        'canonical_metadata_hashes_independently_reconstructed': computed,
        'classification_proof_hash_independently_reconstructed': jsha(report['full_native_classifications']),
        'original_parameter_metadata_projection_hash_independently_reconstructed': refs['full_original_entity_parametric_metadata_sha256'],
        'global_maxima': maxima, 'global_maxima_independent_saved_join': 'Parent allocation slots/preservation maxima; no full-parent scan by checker.',
        'controls_and_lifecycle': {'controller_returncode': receipt['returncode'], 'controller_wall_seconds': receipt['wall_seconds'], 'root_wall_seconds': closed['wall_seconds'], 'RSS_samples': len(samples), 'max_sampled_RSS_bytes_not_peak': receipt['max_observed_RSS_bytes'], 'root_controller_reaped_and_absent_record_joined': True, 'native_PID_observed_by_root': False, 'native_wait_reap_attributed_to_controller_receipt': True, 'universal_descendant_absence_claimed': False},
        'limits': ['No native/MSH/runtime body read or query/helper replay.', 'No independent global omission, full-array outside digest, quality recomputation, entity-parametric row replay or global maxima scan.', 'Saved selected-node coordinate words, classes, available parameters and all shell owner/corner/orientation/exterior associations checked in full.', 'All outside digests exclude all 116 apices and all 4164 old cells; first apex1393275 remains held. A later admitted subset requires fresh subset masks from verified parent arrays.', 'After additions, compare original entity/parameter reference only after projecting to original node tags; this report makes no after-edit preservation claim.', 'Tag-disjointness and interface ownership do not prove embedding, containment, head quality, material/process or physical acceptance.'],
        'engineering_accepted': False, 'physics_qualified': False, 'manufacturing_authorized': False,
    }
    (HERE / 'independent-saved-check.json').write_bytes(encoded(answer))
    print(json.dumps({'status': 'PASS', 'cases': len(cases), 'faces': len(faces), 'nodes': len(points)}))

if __name__ == '__main__':
    main()
