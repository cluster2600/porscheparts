"""Audit the complete large frontier using acquired normals and frozen ancestry."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    with np.load(path, allow_pickle=False) as arrays:
        return {name: arrays[name] for name in arrays.files}


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def birth_references(registry, sources):
    """Recover ordered observed supports; the registry stores canonical keys."""
    result = {}
    for pair in registry['global_pair_ids']:
        pair = int(pair)
        source = sources[str(registry['birth_census_sha256'][pair])]
        assert source['proof_hash'] == registry['birth_census_proof_sha256'][pair]
        assert source['birth_round'] == registry['birth_rounds'][pair]
        census = source['census']
        local = int(registry['birth_local_pair_ids'][pair])
        keys = census['source_edge_keys'][census['selected_pair_edge_ids'][local]]
        canonical = sorted(map(tuple, keys.tolist()))
        assert np.array_equal(np.r_[canonical[0], canonical[1]], registry['raw_pair_keys'][pair])
        assert 'selected_pair_classes' in census or source['class_policy'] == 'opposed_only'
        cls = int(census['selected_pair_classes'][local]) if 'selected_pair_classes' in census else 1
        assert cls == registry['geometry_classes'][pair]
        result[pair] = keys
    return result


def describe(points, acquired, normals, owners, limits, legacy, simple):
    reasons, descriptors = legacy.screen(points, acquired, normals, owners, limits, simple)
    local = points-points.mean(axis=0)
    _, singular, basis = np.linalg.svd(local, full_matrices=False)
    squares = singular**2
    scale = float(squares.sum())
    plane_unique = bool(squares[1]-squares[2] > 1e-10*scale)
    frame_unique = bool(plane_unique and squares[0]-squares[1] > 1e-10*scale)
    projected = local@basis.T
    spans = np.ptp(projected, axis=0)
    products = np.cross(local, np.roll(local, -1, axis=0))
    newell = products.sum(axis=0)
    strength = float(abs(np.dot(basis[-1], newell))/max(np.linalg.norm(products, axis=1).sum(), np.finfo(float).tiny))
    orientation_reliable = plane_unique and strength > 1e-10
    geometric = [r for r in reasons if r not in ('edge_count', 'diagonal')]
    compatible = not geometric and orientation_reliable
    descriptors.update(principal_squared_singular_values=squares.tolist(),
        principal_spans_nominal_mm=spans.tolist(), principal_plane_unique=plane_unique,
        principal_frame_unique=frame_unique, projected_area_orientation_strength=strength,
        projected_orientation_reliable=orientation_reliable,
        legacy_scope_refusals=reasons, non_size_legacy_refusals=geometric,
        fixed_planar_acquired_binormal_diagnostic_compatible=compatible,
        principal_second_span_at_most_0_5=bool(frame_unique and spans[1] <= .5),
        projection_contact_or_native_construction_admitted=False)
    return descriptors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'output'):
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args()
    job = json.loads(args.job.read_text()); began = time.monotonic()
    assert job['schema'] == '935-large-frontier-source-audit-1'
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    proof = json.loads(Path(job['surface_proof']).read_text())
    assert proof['surface_study_checks_passed'] and proof['mesh_sha256'] == sha(job['mesh'])
    assert proof['source_sha256'] == sha(job['surface_inspector'])
    mesh, border, raw, registry = map(load, (job['mesh'], job['boundaries'], job['source_arrays'], job['registry']))
    registry_proof = json.loads(Path(job['registry_proof']).read_text())
    assert registry_proof['registry_independently_verified'] and registry_proof['registry_sha256'] == sha(job['registry'])
    assert registry_proof['source_sha256'] == sha(job['registry_inspector'])
    topology = module(job['boundary_helper'], 'large_actual_boundary')
    actual = topology.fans_and_cycles(mesh['triangles'], len(mesh['points']))
    for key in actual:
        assert np.array_equal(actual[key], border[key])
    del actual
    primal = module(job['primal_component_source'], 'large_primal_components')
    component_labels, certificate = primal.vertex_components(mesh['triangles'], len(mesh['points']), border)
    identity = module(job['raw_identity_inspector'], 'large_raw_identity')
    vector = module(job['raw_identity_producer'], 'large_vector_identity')
    legacy = module(job['legacy_screen_source'], 'large_unchanged_signed_screen')
    projection = module(job['projection_helper'], 'large_projection_not_admitted')
    frontier, untried, opposed, old_mesh, old_border = map(load, (job['frontier_census'], job['untried_census'],
        job['opposed_census'], job['frontier_parent_mesh'], job['frontier_parent_boundaries']))
    sources = {}
    for source in job['birth_sources']:
        peer = json.loads(Path(source['proof']).read_text())
        assert peer['census_independently_verified'] and peer['census_sha256'] == sha(source['census'])
        assert peer['source_sha256'] == sha(source['inspector'])
        sources[sha(source['census'])] = dict(census=load(source['census']), proof_hash=sha(source['proof']),
            class_policy=source['class_policy'], birth_round=source['birth_round'])
    born = birth_references(registry, sources)
    edges, owners = border['boundary'], border['owners']
    walks, flat, offsets = [], [], [0]
    for curve, (a, b) in enumerate(zip(border['offsets'][:-1], border['offsets'][1:])):
        ids = border['cycle_edges'][a:b]
        origins = set(map(int, border['edge_origin_kind'][ids]))
        if len(ids) > 128 and 1 in origins and origins <= {1, 6, 7, 8, 9}:
            walks.append(curve); flat.extend(map(int, ids)); offsets.append(len(flat))
    flat = np.array(flat, dtype=np.int64)
    assert len(walks) == 124 and len(flat) == 69101
    keys = np.full((len(edges), 3), -1, dtype=np.int64)
    normals = np.zeros((len(edges), 3))
    acquired = flat[border['edge_origin_kind'][flat] == 1]
    keys[acquired], normals[acquired] = vector.source_edge_keys(mesh, edges, owners, raw, acquired)
    signatures = np.full((len(flat), 7), -1, dtype=np.int64)
    references, reference_offsets, cache = [], [0], {}
    counts = Counter()
    for position, edge in enumerate(flat):
        origin, owner = int(border['edge_origin_kind'][edge]), int(owners[edge])
        face = mesh['triangles'][owner]
        assert tuple(edges[edge]) in list(zip(face, np.roll(face, -1)))
        if origin == 1:
            key = keys[edge]
            signatures[position] = [0, key[0], key[0], -1, -1, key[1], key[2]]
            refs = key[None, :]
        else:
            kind, field, census = {6: (4, 'source_frontier_pair_ids', frontier),
                7: (6, 'source_untried_pair_ids', untried), 8: (7, 'source_opposed_wall_pair_ids', opposed),
                9: (9, 'source_continuation_pair_ids', None)}[origin]
            pair = int(mesh[field][owner]); assert pair >= 0
            if (kind, pair) not in cache:
                if kind == 9:
                    refs = born[pair]
                else:
                    pair_edges = census['selected_pair_edge_ids'][pair]
                    refs = np.array([identity.original_key(old_mesh, old_border['boundary_local_nodes'][e],
                        old_border['boundary_face_rows'][e], raw)[0] for e in pair_edges]) if kind == 4 else census['source_edge_keys'][pair_edges]
                cache[kind, pair] = refs
            refs = cache[kind, pair]
            signatures[position] = legacy.pair_ancestry(mesh, owner, raw, refs, pair, kind, edges[edge])
        references.extend(refs); reference_offsets.append(len(references)); counts[str(origin)] += 1
    decisions = []
    for index, curve in enumerate(walks):
        a, b = offsets[index:index+2]; ids = flat[a:b]; nodes = edges[ids, 0]
        assert np.array_equal(edges[ids, 1], np.roll(nodes, -1)) and len(np.unique(nodes)) == len(nodes)
        actual_positions = np.flatnonzero(border['edge_origin_kind'][ids] == 1)
        own = mesh['original_face_ids'][owners[ids[actual_positions]]]
        components = np.unique(component_labels[owners[ids]]); assert len(components) == 1
        descriptor = describe(mesh['points'][nodes], actual_positions, normals[ids[actual_positions]], own,
                              job['legacy_limits'], legacy, projection.simple_projection)
        decisions.append(dict(curve=curve, edges=len(ids), component=int(components[0]),
            edge_origin_counts=dict(Counter(map(str, border['edge_origin_kind'][ids]))),
            directed_source_cycle_sha256=legacy.cycle_identity(signatures[a:b]), **descriptor,
            physical_classification='unreviewed', reconstruction_admitted=False))
    args.output.mkdir(mode=0o700, exist_ok=False)
    target = args.output/'private-large-walk-ancestry.npz'
    np.savez_compressed(target, walk_ids=np.array(walks), walk_offsets=np.array(offsets),
        flat_edge_ids=flat, edge_signatures=signatures, actual_acquired_normals=normals[flat],
        reference_offsets=np.array(reference_offsets), raw_owner_edge_keys=np.asarray(references).reshape(-1, 3),
        face_component_ids=component_labels, component_V_E_F_B_chi_genus=certificate)
    details = args.output/'private-large-walk-descriptors.json'
    details.write_text(json.dumps(decisions, indent=2)+'\n')
    compatible = [row for row in decisions if row['fixed_planar_acquired_binormal_diagnostic_compatible']]
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), mesh_sha256=sha(job['mesh']),
        ancestry_sha256=sha(target), descriptors_sha256=sha(details), complete_walks=len(border['offsets'])-1,
        complete_boundary_edges=len(edges), selected_large_walks=len(walks), selected_large_edges=len(flat),
        scoped_origin_counts=dict(counts), all_boundary_cycles_recomputed=True,
        global_registry_births_checked=len(born), inferred_normals_used_as_acquired_evidence=False,
        non_size_legacy_refusal_counts=dict(Counter(reason for row in decisions for reason in row['non_size_legacy_refusals'])),
        fixed_planar_binormal_diagnostic_compatible_walks=len(compatible),
        fixed_planar_binormal_diagnostic_compatible_edges=sum(row['edges'] for row in compatible),
        principal_thin_diagnostic_walks=sum(row['principal_second_span_at_most_0_5'] for row in decisions),
        projection_or_contact_audit_performed=False, large_contours_admitted_for_construction=0,
        existing_compact_bounds_relaxed=False, geometry_modified=False,
        physical_acceptance=False, manufacturing_authorized=False, seconds=time.monotonic()-began)
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
