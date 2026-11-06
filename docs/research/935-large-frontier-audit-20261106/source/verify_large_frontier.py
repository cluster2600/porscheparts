"""Replay large-walk provenance and scalar diagnostics without importing the producer."""
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


def inferred_signature(mesh, owner, edge, raw, refs, kind, pair):
    assert mesh['inferred_surface_kind'][owner] == kind and mesh['original_face_ids'][owner] == -1
    nodes = [int(refs[0, 1]), int(refs[0, 2]), int(refs[1, 1]), int(refs[1, 2])]
    quad = raw['vertices'][nodes]
    assert len(set(map(tuple, quad))) == 4
    local = []
    for p in mesh['points'][mesh['triangles'][owner]]:
        matches = [i for i in range(4) if np.array_equal(quad[i], p)]
        assert len(matches) == 1
        local.append(matches[0])
    cyclic = min(tuple(local[i:]+local[:i]) for i in range(3))
    allowed = ((1, 0, 3), (1, 3, 2), (1, 0, 2), (0, 3, 2))
    assert cyclic in {min(tuple(t[i:]+t[:i]) for i in range(3)) for t in allowed}
    ends = []
    for node in edge:
        matches = [i for i in range(4) if np.array_equal(quad[i], mesh['points'][node])]
        assert len(matches) == 1
        ends.append(matches[0])
    assert tuple(ends) in ((0, 3), (2, 1))
    return [kind, pair, int(refs[0, 0]), int(refs[1, 0]), -1, nodes[ends[0]], nodes[ends[1]]]


def scalar_diagnostics(points, positions, normals, owners, limits, legacy):
    reasons = legacy.inspect(points, positions, normals, owners, limits)
    local = points-np.mean(points, axis=0)
    covariance = sum((np.outer(p, p) for p in local), start=np.zeros((3, 3)))
    values, axes = np.linalg.eigh(covariance)
    values = values[::-1]; basis = axes[:, ::-1].T
    scale = float(values.sum())
    plane_unique = bool(values[1]-values[2] > 1e-10*scale)
    frame_unique = bool(plane_unique and values[0]-values[1] > 1e-10*scale)
    crosses = [np.cross(local[i], local[(i+1) % len(local)]) for i in range(len(local))]
    area = sum(crosses, start=np.zeros(3))
    normal = basis[-1].copy()
    if np.dot(normal, area) > 0:
        normal = -normal
    strength = abs(float(np.dot(normal, area)))/max(sum(float(np.linalg.norm(c)) for c in crosses), np.finfo(float).tiny)
    reliable = plane_unique and strength > 1e-10
    dots = []
    for i, source_normal in zip(positions, normals):
        tangent = points[(int(i)+1) % len(points)]-points[int(i)]
        length = np.linalg.norm(tangent)
        if length == 0:
            continue
        tangent /= length
        binormal = np.cross(tangent, source_normal)
        magnitude = np.linalg.norm(binormal)
        if magnitude == 0:
            continue
        binormal /= magnitude
        dots.append(float(np.dot(binormal, normal)))
    return dict(reasons=set(reasons), squared_singular_values=values,
        principal_spans=np.ptp(local@basis.T, axis=0), plane_unique=plane_unique,
        frame_unique=frame_unique, orientation_reliable=reliable, orientation_strength=strength,
        signed_minimum=min(dots) if dots else None, signed_p10=float(np.quantile(dots, .1)) if dots else None,
        plane_residual=float(max(abs(local@normal))),
        compatible=not set(reasons)-{'edge_count', 'diagonal'} and reliable)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'audit', 'output'):
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args(); began = time.monotonic()
    job = json.loads(args.job.read_text())
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    peer = json.loads((args.audit/'report.json').read_text())
    assert peer['source_sha256'] == sha(job['producer_source'])
    assert peer['job_sha256'] == sha(args.job) and peer['mesh_sha256'] == sha(job['mesh'])
    assert peer['ancestry_sha256'] == sha(args.audit/'private-large-walk-ancestry.npz')
    assert peer['descriptors_sha256'] == sha(args.audit/'private-large-walk-descriptors.json')
    mesh, border, raw, registry, saved = map(load, (job['mesh'], job['boundaries'], job['source_arrays'],
        job['registry'], args.audit/'private-large-walk-ancestry.npz'))
    rows = json.loads((args.audit/'private-large-walk-descriptors.json').read_text())
    surface = json.loads(Path(job['surface_proof']).read_text())
    assert surface['surface_study_checks_passed'] and surface['mesh_sha256'] == sha(job['mesh'])
    assert surface['source_sha256'] == sha(job['surface_inspector'])
    registry_proof = json.loads(Path(job['registry_proof']).read_text())
    assert registry_proof['registry_independently_verified'] and registry_proof['registry_sha256'] == sha(job['registry'])
    assert registry_proof['source_sha256'] == sha(job['registry_inspector'])
    identity = module(job['raw_identity_inspector'], 'scalar_large_identity')
    old_scalar = module(job['legacy_inspector_source'], 'scalar_unchanged_signed_screen')
    topology = module(job['boundary_helper'], 'scalar_large_edge_table')
    dual = module(job['dual_component_source'], 'scalar_large_dual_components')
    labels, certificate = dual.surface_components(mesh['triangles'], len(mesh['points']), border, topology)
    assert np.array_equal(labels, saved['face_component_ids'])
    assert np.array_equal(certificate, saved['component_V_E_F_B_chi_genus'])
    source_data = {}
    for source in job['birth_sources']:
        proof = json.loads(Path(source['proof']).read_text())
        assert proof['census_independently_verified'] and proof['census_sha256'] == sha(source['census'])
        assert proof['source_sha256'] == sha(source['inspector'])
        source_data[sha(source['census'])] = (load(source['census']), sha(source['proof']), source['class_policy'], source['birth_round'])
    assert np.array_equal(registry['global_pair_ids'], np.arange(len(registry['raw_pair_keys'])))
    born = {}
    for i in range(len(registry['global_pair_ids'])):
        census, proof_sha, class_policy, birth_round = source_data[str(registry['birth_census_sha256'][i])]
        assert registry['birth_rounds'][i] == birth_round
        assert registry['birth_census_proof_sha256'][i] == proof_sha
        local = int(registry['birth_local_pair_ids'][i])
        refs = census['source_edge_keys'][census['selected_pair_edge_ids'][local]]
        canonical = sorted(tuple(map(int, key)) for key in refs)
        assert tuple(registry['raw_pair_keys'][i]) == canonical[0]+canonical[1]
        assert 'selected_pair_classes' in census or class_policy == 'opposed_only'
        expected_class = int(census['selected_pair_classes'][local]) if 'selected_pair_classes' in census else 1
        assert registry['geometry_classes'][i] == expected_class
        born[i] = refs
    frontier, untried, opposed, old_mesh, old_border = map(load, (job['frontier_census'], job['untried_census'],
        job['opposed_census'], job['frontier_parent_mesh'], job['frontier_parent_boundaries']))
    walks, flat, offsets = [], [], [0]
    for curve in range(len(border['offsets'])-1):
        a, b = border['offsets'][curve:curve+2]; ids = border['cycle_edges'][a:b]
        origins = {int(border['edge_origin_kind'][i]) for i in ids}
        if len(ids) > 128 and 1 in origins and not origins-{1, 6, 7, 8, 9}:
            walks.append(curve); flat.extend(map(int, ids)); offsets.append(len(flat))
    assert np.array_equal(walks, saved['walk_ids']) and np.array_equal(flat, saved['flat_edge_ids'])
    assert np.array_equal(offsets, saved['walk_offsets']) and len(rows) == len(walks)
    signatures, normals, references, reference_offsets = [], [], [], [0]
    counts, cache = Counter(), {}
    for edge in flat:
        nodes, owner, origin = border['boundary'][edge], int(border['owners'][edge]), int(border['edge_origin_kind'][edge])
        face = mesh['triangles'][owner]
        assert tuple(nodes) in list(zip(face, np.roll(face, -1)))
        if origin == 1:
            key, normal = identity.original_key(mesh, nodes, owner, raw)
            refs = np.asarray([key]); signature = [0, key[0], key[0], -1, -1, key[1], key[2]]
        else:
            normal = np.zeros(3)
            kind, field, census = {6: (4, 'source_frontier_pair_ids', frontier),
                7: (6, 'source_untried_pair_ids', untried), 8: (7, 'source_opposed_wall_pair_ids', opposed),
                9: (9, 'source_continuation_pair_ids', None)}[origin]
            pair = int(mesh[field][owner]); assert pair >= 0
            if (kind, pair) not in cache:
                if kind == 9:
                    refs = born[pair]
                elif kind == 4:
                    ids = census['selected_pair_edge_ids'][pair]
                    refs = np.asarray([identity.original_key(old_mesh, old_border['boundary_local_nodes'][e],
                        old_border['boundary_face_rows'][e], raw)[0] for e in ids])
                else:
                    refs = census['source_edge_keys'][census['selected_pair_edge_ids'][pair]]
                for key in refs:
                    tri = list(map(int, raw['triangles'][int(key[0])]))
                    assert (int(key[1]), int(key[2])) in list(zip(tri, tri[1:]+tri[:1]))
                    p = raw['vertices'][tri]
                    assert np.linalg.norm(np.cross(p[1]-p[0], p[2]-p[0])) > 0
                cache[kind, pair] = refs
            refs = cache[kind, pair]
            signature = inferred_signature(mesh, owner, nodes, raw, refs, kind, pair)
        signatures.append(signature); normals.append(normal); references.extend(refs)
        reference_offsets.append(len(references)); counts[str(origin)] += 1
    assert np.array_equal(signatures, saved['edge_signatures'])
    assert np.allclose(normals, saved['actual_acquired_normals'], rtol=0, atol=1e-14)
    assert np.array_equal(reference_offsets, saved['reference_offsets'])
    assert np.array_equal(references, saved['raw_owner_edge_keys'])
    compatible, compatible_edges, thin = 0, 0, 0
    for i, (curve, row) in enumerate(zip(walks, rows)):
        a, b = offsets[i:i+2]; ids = np.asarray(flat[a:b]); nodes = border['boundary'][ids, 0]
        assert np.array_equal(border['boundary'][ids, 1], np.roll(nodes, -1))
        assert row['curve'] == curve and row['edges'] == len(ids)
        comps = set(map(int, labels[border['owners'][ids]])); assert comps == {row['component']}
        sequence = [tuple(map(int, x)) for x in signatures[a:b]]
        assert len(set(sequence)) == len(sequence)
        minimum = min(sequence); first = sequence.index(minimum)
        digest = hashlib.sha256(json.dumps(sequence[first:]+sequence[:first], separators=(',', ':')).encode()).hexdigest()
        assert digest == row['directed_source_cycle_sha256']
        positions = np.flatnonzero(border['edge_origin_kind'][ids] == 1)
        own = mesh['original_face_ids'][border['owners'][ids[positions]]]
        result = scalar_diagnostics(mesh['points'][nodes], positions, np.asarray(normals[a:b])[positions], own,
                                    job['legacy_limits'], old_scalar)
        assert result['reasons'] == set(row['legacy_scope_refusals'])
        assert result['plane_unique'] == row['principal_plane_unique']
        assert result['frame_unique'] == row['principal_frame_unique']
        assert result['orientation_reliable'] == row['projected_orientation_reliable']
        assert np.allclose(result['squared_singular_values'], row['principal_squared_singular_values'], rtol=1e-8, atol=1e-9)
        assert np.isclose(result['plane_residual'], row['plane_residual_nominal_mm'], rtol=1e-7, atol=1e-8)
        if result['orientation_reliable']:
            assert np.isclose(result['signed_minimum'], row['minimum_acquired_binormal_signed_dot'], rtol=1e-7, atol=1e-7)
            assert np.isclose(result['signed_p10'], row['acquired_binormal_signed_p10'], rtol=1e-7, atol=1e-7)
        if result['frame_unique']:
            assert np.allclose(result['principal_spans'], row['principal_spans_nominal_mm'], rtol=1e-7, atol=1e-7)
        assert result['compatible'] == row['fixed_planar_acquired_binormal_diagnostic_compatible']
        assert row['physical_classification'] == 'unreviewed' and row['reconstruction_admitted'] is False
        compatible += bool(result['compatible']); compatible_edges += len(ids) if result['compatible'] else 0
        thin += result['frame_unique'] and result['principal_spans'][1] <= .5
    assert compatible == peer['fixed_planar_binormal_diagnostic_compatible_walks']
    assert compatible_edges == peer['fixed_planar_binormal_diagnostic_compatible_edges']
    assert thin == peer['principal_thin_diagnostic_walks']
    args.output.mkdir(mode=0o700, exist_ok=False)
    result = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), mesh_sha256=sha(job['mesh']),
        ancestry_sha256=sha(args.audit/'private-large-walk-ancestry.npz'),
        descriptors_sha256=sha(args.audit/'private-large-walk-descriptors.json'),
        independently_verified_large_walks=len(walks), independently_verified_large_edges=len(flat),
        scoped_origin_counts=dict(counts), scalar_raw_identity_controls_passed=identity.identity_controls(),
        all_registry_births_verified=len(born), dual_and_primal_components_agree=True,
        all_source_references_and_directed_cycle_hashes_verified=True,
        independent_covariance_eigen_and_scalar_diagnostics_verified=True,
        fixed_planar_binormal_diagnostic_compatible_walks=compatible,
        fixed_planar_binormal_diagnostic_compatible_edges=compatible_edges,
        principal_thin_diagnostic_walks=int(thin), producer_imported=False,
        large_frontier_audit_independently_verified=True, construction_admitted=False,
        projection_or_contact_audit_performed=False, inferred_normals_used_as_acquired_evidence=False,
        geometry_modified=False, physical_acceptance=False, manufacturing_authorized=False,
        seconds=time.monotonic()-began)
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    (args.output/'report.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
