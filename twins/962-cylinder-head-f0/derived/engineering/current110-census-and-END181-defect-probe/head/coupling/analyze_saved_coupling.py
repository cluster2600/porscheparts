"""Derive the complete movable-node coupling graph from one saved census JSON."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import hashlib
import itertools
import json
import sys
import time

started = time.monotonic()
deadline = started + 10.0
root = Path(__file__).resolve().parents[3]
output = Path(__file__).parent
source_input = root / 'work/962-engineering/head-star-current110-full-stars-001/readback-report.json'
expected_sha = '657fbb0ce1c89dbf691f5a07c62feedf0fd91f7bc78f21d2aa14a3e01a9566da'
expected_bytes = 1691746
hash_bytes = lambda raw: hashlib.sha256(raw).hexdigest()
raw = source_input.read_bytes()
assert len(raw) == expected_bytes and hash_bytes(raw) == expected_sha
census = json.loads(raw)
stars = census['complete_seed_star_census']
movable = stars['movable_node_tags']
cells = stars['complete_incident_tetrahedra']
context_rows = stars['unique_incident_nodes']
poor = stars['positive_poor_tetrahedron_tags']
assert movable == sorted(set(movable)) and len(movable) == stars['movable_count'] == 82
assert len(cells) == stars['complete_incident_tetrahedron_count'] == 2482
assert len(poor) == stars['initially_positive_poor_incident_tetrahedra'] == 110
assert stars['all_seed_stars_complete_including_initially_good_and_shared_cells'] is True
assert stars['all_positive_poor_rows_covered_by_movable_stars'] is True
assert stars['unseedable_positive_poor_tetrahedron_tags'] == []
assert census['status'] == 'direct_saved_file_readback_completed'
assert census['SICN_point1_gate_passed'] is False
nodes = {r['node_tag']: r for r in context_rows}
assert len(nodes) == len(context_rows) == stars['unique_incident_node_count'] == 1439
variables = set(movable)
assert {n for n, r in nodes.items() if r['in_movable_seed_set']} == variables
assert sorted(poor) == sorted(r['tetrahedron_tag'] for r in census['positive_poor_SICN_cells']['complete_tagged_cells'])
by_tag = {r['tetrahedron_tag']: r for r in cells}
assert len(by_tag) == 2482 and [r['tetrahedron_tag'] for r in cells] == sorted(by_tag)
assert {r['tetrahedron_tag'] for r in cells if r['initially_positive_poor']} == set(poor)
assert sum(not r['initially_positive_poor'] for r in cells) == stars['initially_good_incident_tetrahedra'] == 2372
assert sum(len(r['movable_node_tags']) > 1 for r in cells) == stars['shared_by_multiple_movable_nodes_tetrahedra'] == 58
adjacency = {n: set() for n in movable}
supports = {}
for cell in cells:
    if time.monotonic() > deadline:
        raise TimeoutError('Ten-second saved-metadata graph budget exceeded')
    tags = cell['node_tags']
    touches = sorted(variables.intersection(tags))
    assert len(tags) == 4 and len(set(tags)) == 4 and touches
    assert touches == cell['movable_node_tags']
    assert set(tags) <= set(nodes)
    assert cell['initially_positive_poor'] is (0.0 < cell['initial_native_SICN'] < 0.1)
    for a, b in itertools.combinations(touches, 2):
        adjacency[a].add(b)
        adjacency[b].add(a)
        supports.setdefault((a, b), []).append(cell['tetrahedron_tag'])
assert {n for cell in cells for n in cell['node_tags']} == set(nodes)
components = []
unassigned = set(movable)
while unassigned:
    if time.monotonic() > deadline:
        raise TimeoutError('Ten-second saved-metadata graph budget exceeded')
    seed = min(unassigned)
    stack = [seed]
    found = set()
    while stack:
        n = stack.pop()
        if n in found:
            continue
        found.add(n)
        stack.extend(sorted(adjacency[n] - found, reverse=True))
    assert found <= unassigned
    unassigned.difference_update(found)
    components.append(sorted(found))
owner = {n: i + 1 for i, members in enumerate(components) for n in members}
component_cells = {i + 1: [] for i in range(len(components))}
for cell in cells:
    owners = {owner[n] for n in cell['movable_node_tags']}
    assert len(owners) == 1
    component_cells[owners.pop()].append(cell['tetrahedron_tag'])
edge_rows = []
for (a, b), witnesses in sorted(supports.items()):
    assert owner[a] == owner[b] and witnesses == sorted(set(witnesses))
    edge_rows.append({
        'movable_node_pair': [a, b],
        'component_ID': owner[a],
        'supporting_tetrahedron_tags': witnesses,
        'initially_positive_poor_supporting_tetrahedron_tags': [t for t in witnesses if by_tag[t]['initially_positive_poor']],
        'initially_good_supporting_tetrahedron_tags': [t for t in witnesses if not by_tag[t]['initially_positive_poor']],
    })
records = []
fixed_owners = {}
for component_id, members in enumerate(components, 1):
    ts = component_cells[component_id]
    all_nodes = sorted({n for t in ts for n in by_tag[t]['node_tags']})
    fixed = sorted(set(all_nodes) - set(members))
    assert not variables.intersection(fixed)
    for n in fixed:
        fixed_owners.setdefault(n, []).append(component_id)
    poor_tags = [t for t in ts if by_tag[t]['initially_positive_poor']]
    good_tags = [t for t in ts if not by_tag[t]['initially_positive_poor']]
    shared_tags = [t for t in ts if len(by_tag[t]['movable_node_tags']) > 1]
    es = [r['movable_node_pair'] for r in edge_rows if r['component_ID'] == component_id]
    boundary = [n for n in fixed if nodes[n]['source_boundary_tag']]
    fixed_interior = [n for n in fixed if not nodes[n]['source_boundary_tag']]
    records.append({
        'component_ID': component_id,
        'movable_node_tags': members,
        'coordinate_variable_count': 3 * len(members),
        'tetrahedron_tags': ts,
        'initially_positive_poor_tetrahedron_tags': poor_tags,
        'initially_good_tetrahedron_tags': good_tags,
        'shared_by_multiple_movable_nodes_tetrahedron_tags': shared_tags,
        'graph_edges': es,
        'all_incident_node_tags': all_nodes,
        'fixed_context_node_tags': fixed,
        'fixed_source_boundary_node_tags': boundary,
        'fixed_other_interior_node_tags': fixed_interior,
        'counts': {'movable_nodes': len(members), 'coordinate_variables': 3 * len(members), 'TET4': len(ts), 'poor': len(poor_tags), 'good': len(good_tags), 'shared': len(shared_tags), 'edges': len(es), 'all_incident_nodes': len(all_nodes), 'fixed_boundary_nodes': len(boundary), 'fixed_interior_nodes': len(fixed_interior)},
    })
vertex_occurrences = Counter(n for c in records for n in c['movable_node_tags'])
tet_occurrences = Counter(t for c in records for t in c['tetrahedron_tags'])
poor_occurrences = Counter(t for c in records for t in c['initially_positive_poor_tetrahedron_tags'])
assert vertex_occurrences == Counter(movable)
assert tet_occurrences == Counter(sorted(by_tag))
assert poor_occurrences == Counter(poor)
assert sum(c['counts']['good'] for c in records) == 2372
assert sum(c['counts']['shared'] for c in records) == 58
assert sum(c['counts']['edges'] for c in records) == len(edge_rows)
assert all(adjacency[n] == {m for edge in supports for m in edge if n in edge and m != n} for n in movable)
assert set(fixed_owners) == set(nodes) - variables
assert sum(nodes[n]['source_boundary_tag'] for n in fixed_owners) == 889
assert sum(not nodes[n]['source_boundary_tag'] for n in fixed_owners) == 468
input_after = source_input.read_bytes()
assert input_after == raw
assert time.monotonic() <= deadline
analysis = {
    'schema': '962-current110-complete-saved-census-coupling-graph/v1',
    'status': 'DERIVED_SAVED_METADATA_ANALYSIS_CENSUS_ROOT_ACCEPTANCE_PENDING',
    'created_UTC': datetime.now(timezone.utc).isoformat(),
    'input': {'path': str(source_input.relative_to(root)), 'sha256': expected_sha, 'bytes': expected_bytes},
    'graph_definition': 'Vertices are all 82 saved movable node IDs. An undirected edge exists iff both movable nodes occur in the same saved incident TET4, including initially good and shared cells. Each vertex represents three coordinate variables; fixed context coordinates are not graph vertices.',
    'component_order': 'Increasing minimum movable node ID; all memberships and edges sorted by stable tags.',
    'summary': {
        'movable_nodes': 82, 'coordinate_variables': 246, 'incident_TET4': 2482, 'poor_TET4': 110, 'good_TET4': 2372, 'shared_TET4': 58,
        'context_nodes': 1439, 'fixed_source_boundary_nodes': 889, 'fixed_other_interior_nodes': 468,
        'graph_edges': len(edge_rows), 'connected_components': len(records),
        'isolated_movable_nodes': sum(not adjacency[n] for n in movable),
        'maximum_component_movable_nodes': max(c['counts']['movable_nodes'] for c in records),
        'maximum_component_coordinate_variables': max(c['counts']['coordinate_variables'] for c in records),
        'maximum_component_TET4': max(c['counts']['TET4'] for c in records),
        'maximum_component_poor_TET4': max(c['counts']['poor'] for c in records),
        'maximum_component_good_TET4': max(c['counts']['good'] for c in records),
        'maximum_component_shared_TET4': max(c['counts']['shared'] for c in records),
        'fixed_context_nodes_shared_between_components': sum(len(v) > 1 for v in fixed_owners.values()),
    },
    'components': records,
    'all_graph_edges_with_complete_cell_supports': edge_rows,
    'all82_vertex_adjacency_lists': [{'node_tag': n, 'adjacent_movable_node_tags': sorted(adjacency[n]), 'component_ID': owner[n]} for n in movable],
    'all2482_source_incident_cell_records_preserved': cells,
    'all110_source_positive_poor_tetrahedron_tags': poor,
    'fixed_context_node_component_memberships': [{'node_tag': n, 'component_IDs': ids, 'source_boundary_tag': nodes[n]['source_boundary_tag']} for n, ids in sorted(fixed_owners.items())],
    'coverage': {
        'all82_movable_nodes_exactly_once': True, 'all2482_incident_cells_exactly_once': True, 'all110_poor_cells_exactly_once': True,
        'all2372_good_cells_and58_shared_cells_preserved': True, 'no_incident_cell_spans_two_variable_components': True,
        'all_edges_exactly_cell_cooccurrences_with_full_witness_lists': True,
        'movable_node_and_tetrahedron_component_memberships_pairwise_disjoint': True,
        'fixed_context_node_memberships_may_overlap': True,
        'input_bytes_unchanged': True,
    },
    'limits': [
        'The saved census root acceptance is pending and is not consumed as authority by this analysis.',
        'Components describe local cell-quality coupling with other coordinates fixed. Shared fixed context nodes are reported separately; they do not merge variable components.',
        'This graph does not prove global embedding, outside nonoverlap, containment, repair feasibility, strength, thermal resolution or physical performance.',
        'All initial SICN values and complete-star membership remain saved-census/native-worker observations; no metric or geometry calculation is replayed.',
        'No coordinates are proposed or changed. No optimization, native meshing, PDE solve, material/LPBF calibration, surrogate training or manufacturing release is performed.',
    ],
    'native_output_modified': False, 'geometry_proposal_or_optimization': False,
    'global_embedding_or_nonoverlap_proved': False, 'repair_feasibility_proved': False,
    'head_PDE_authorized': False, 'material_qualified': False, 'physics_qualified': False, 'training_authorized': False,
    'engineering_accepted': False, 'manufacturing_authorized': False,
}
analysis_bytes = (json.dumps(analysis, indent=2, allow_nan=False) + '\n').encode()
assert time.monotonic() <= deadline
target = output / 'coupling-graph.json'
with target.open('xb') as stream:
    stream.write(analysis_bytes)
target.chmod(0o444)
source_bytes = Path(__file__).read_bytes()
receipt = {
    'schema': '962-current110-saved-coupling-graph-execution/v1',
    'status': 'COMPLETED_ONE_STDLIB_ONLY_SAVED_METADATA_ANALYSIS',
    'invocation_count': 1,
    'source': {'path': str(Path(__file__).relative_to(root)), 'sha256': hash_bytes(source_bytes), 'bytes': len(source_bytes)},
    'input_before_and_after': analysis['input'],
    'input_bytes_before_after_exact': True,
    'output': {'path': str(target.relative_to(root)), 'sha256': hash_bytes(analysis_bytes), 'bytes': len(analysis_bytes)},
    'ordinary_internal_deadline_seconds': 10,
    'wall_seconds_before_receipt': time.monotonic() - started,
    'python_version': sys.version.split()[0],
    'imports': ['pathlib', 'collections', 'datetime', 'hashlib', 'itertools', 'json', 'sys', 'time'],
    'raw_geometry_native_or_scientific_module_access': False,
    'native_output_modified': False,
    'geometry_proposals_optimization_or_solver_execution': False,
    'root_census_acceptance_consumed': False,
    'material_or_physical_PDE_training_manufacturing_authority': False,
    'automatic_retry': False,
}
receipt_target = output / 'execution-receipt.json'
with receipt_target.open('x') as stream:
    json.dump(receipt, stream, indent=2, allow_nan=False)
    stream.write('\n')
receipt_target.chmod(0o444)
print(json.dumps({'summary': analysis['summary'], 'output': receipt['output'], 'wall_seconds': receipt['wall_seconds_before_receipt']}))
