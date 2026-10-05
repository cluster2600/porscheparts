#!/usr/bin/env python3
"""Read-only indexed topology and stored-curve audit of a shape-screened mesh.

No coordinate welding, triangle deletion, native relabelling or volume release.
Geometric intersections require a separate, exact-array-bound audit.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import signal
import sys
import time

import numpy as np
from run_parallel_cad_trials import BODY_SHA, native
from run_bounded_chamfer import surface_arrays
from trial_compound_junction_mesh import surface_edges
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'picogk-local-junction'))
from audit_surface_topology import link_type


def indexed_topology(points, triangles):
    if len(points) > 2_000_000 or len(triangles) > 2_000_000:
        raise ValueError('bounded_surface_required')
    p, f = surface_arrays(points, triangles)
    edges = np.concatenate([f[:, pair] for pair in ((0, 1), (1, 2), (2, 0))])
    _, inverse, counts = np.unique(np.sort(edges, axis=1), axis=0, return_inverse=True, return_counts=True)
    signs = np.where(edges[:, 0] < edges[:, 1], 1, -1)
    conflicts = int(((counts == 2) & (np.bincount(inverse, weights=signs) != 0)).sum())
    links = np.concatenate([f, f[:, [1, 2, 0]], f[:, [2, 0, 1]]])
    links = links[np.argsort(links[:, 0], kind='stable')]
    starts = np.r_[0, np.flatnonzero(np.diff(links[:, 0]))+1, len(links)]
    kinds = Counter(link_type(links[a:b, 1:].tolist()) for a, b in zip(starts[:-1], starts[1:]))
    result = surface_edges(f)
    result.update(vertex_links_checked=True, vertex_link_classification=dict(kinds),
        used_vertices=len(p), unreferenced_stored_nodes=len(points)-len(p),
        exact_duplicate_used_coordinates=len(p)-len(np.unique(p, axis=0)),
        two_incidence_orientation_conflicts=conflicts, coordinates_merged=False,
        triangles_removed=0)
    result['indexed_closed_oriented_manifold_screen_passed'] = bool(
        not result['not_incident_twice'] and not result['duplicate_triangles'] and not conflicts
        and kinds.get('circle', 0) == len(p) and not result['exact_duplicate_used_coordinates'])
    return result


def stored_curve_edges(triangles, lines):
    triangles, lines = np.asarray(triangles), np.asarray(lines)
    if (triangles.ndim != 2 or triangles.shape[1] != 3 or lines.ndim != 2 or lines.shape[1] != 2
            or not np.issubdtype(triangles.dtype, np.integer) or not np.issubdtype(lines.dtype, np.integer)
            or not len(triangles) or not len(lines) or len(lines) > 2_000_000):
        raise ValueError('bounded_triangle_and_line_tags_required')
    skin = np.unique(np.sort(np.concatenate([triangles[:, p] for p in ((0, 1), (1, 2), (2, 0))]), axis=1), axis=0)
    all_edges = np.vstack([skin, np.sort(lines, axis=1)])
    _, ids = np.unique(all_edges, axis=0, return_inverse=True)
    missing = ~np.isin(ids[len(skin):], ids[:len(skin)])
    return dict(stored_lines=len(lines), lines_not_direct_surface_edges=int(missing.sum()),
                missing_line_indices_private=np.flatnonzero(missing).tolist(),
                subdivided_curve_chain_or_native_curve_distance_checked=False)


def orient_entities(points, triangles, labels):
    """One connected closed shell, whole-entity permutations, positive flux."""
    points, triangles, labels = map(np.asarray, (points, triangles, labels))
    surface_arrays(points, triangles)
    if (len(triangles) > 2_000_000 or labels.shape != (len(triangles),)
            or labels.dtype.kind not in 'iu' or labels.min() <= 0):
        raise ValueError('bounded_triangle_entity_labels_required')
    edges = np.concatenate([triangles[:, p] for p in ((0, 1), (1, 2), (2, 0))])
    _, inv, counts = np.unique(np.sort(edges, axis=1), axis=0, return_inverse=True, return_counts=True)
    if (counts != 2).any(): raise ValueError('closed_two_incidence_surface_required')
    order = np.argsort(inv, kind='stable').reshape(-1, 2)
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    pairs = np.tile(np.arange(len(triangles)), 3)[order]
    graph = coo_matrix((np.ones(len(pairs), dtype=np.int8), (pairs[:, 0], pairs[:, 1])),
                       shape=(len(triangles), len(triangles))).tocsr()
    if connected_components(graph, directed=False, return_labels=False) != 1:
        raise ValueError('single_connected_entity_shell_required')
    owners = np.tile(labels, 3); direction = np.where(edges[:, 0] < edges[:, 1], 1, -1)
    relations = np.unique(np.c_[owners[order], -direction[order].prod(axis=1)], axis=0)
    neighbours = defaultdict(list)
    for a, b, relation in relations:
        neighbours[a].append((b, relation)); neighbours[b].append((a, relation))
    signs = {int(labels.min()): 1}; pending = list(signs)
    while pending:
        a = pending.pop()
        for b, relation in neighbours[a]:
            expected = signs[a]*relation
            if b in signs:
                if signs[b] != expected: raise ValueError('inconsistent_entity_orientation_constraints')
            else:
                signs[b] = expected; pending.append(b)
    if len(signs) != len(np.unique(labels)): raise ValueError('single_connected_entity_shell_required')
    result = triangles.copy(); reverse = np.isin(labels, [tag for tag, sign in signs.items() if sign < 0])
    result[reverse] = result[reverse, ::-1]
    xyz = points[result]-points[np.unique(result)].mean(axis=0)
    import math
    flux = math.fsum(map(float, np.einsum('ij,ij->i', xyz[:, 0], np.cross(xyz[:, 1], xyz[:, 2]))/6))
    if not np.isfinite(flux) or flux == 0: raise ValueError('nonzero_finite_signed_shell_volume_required')
    if flux < 0: result = result[:, ::-1].copy(); reverse = ~reverse
    if not np.array_equal(np.sort(result, axis=1), np.sort(triangles, axis=1)):
        raise ValueError('triangle_geometry_changed')
    return result, dict(reversed_triangles=int(reverse.sum()), reversed_face_tags_private=np.unique(labels[reverse]).tolist(),
        edge_connected_triangle_components=1,
        positive_signed_flux_scan_units_cubed=abs(flux), coordinate_changes=0,
        unordered_triangles_unchanged=True, material_or_native_face_orientation_certified=False)


def run(args):
    import gmsh
    start = time.monotonic()
    sources = [Path(__file__), Path(native.__file__), Path(sys.modules[link_type.__module__].__file__),
               Path(sys.modules[surface_arrays.__module__].__file__), Path(sys.modules[surface_edges.__module__].__file__)]
    pins = {p: native.sha256(p) for p in [args.body, args.mesh, args.receipt, args.shape_audit, *sources]}
    receipt = json.loads(args.receipt.read_text()); shape = json.loads(args.shape_audit.read_text())
    if (args.output.exists() or args.output.is_symlink() or any(p.is_symlink() for p in pins)
            or gmsh.__version__ != '4.15.2' or pins[args.body] != BODY_SHA
            or receipt.get('schema') != 'm64-projected-compound-screen/v1'
            or receipt.get('status') != 'completed_diagnostic_only'
            or receipt.get('input_sha256') != BODY_SHA or receipt.get('surface_sha256') != pins[args.mesh]
            or receipt.get('necessary_surface_checks_passed') is not True or receipt.get('inputs_unchanged') is not True
            or shape.get('schema') != 'm64-compound-native-shape-samples/v1'
            or shape.get('status') != 'completed_diagnostic_only' or shape.get('sampled_screen_passed') is not True
            or shape.get('inputs_unchanged') is not True
            or any(shape.get('source_hashes', {}).get(p.name) != pins[p] for p in (args.body, args.mesh, args.receipt))):
        raise ValueError('fresh_output_and_hash_bound_screened_surface_required')
    args.output.mkdir(mode=0o700)
    report = dict(schema='m64-projected-surface-topology/v1', status='incomplete',
        source_hashes={str(p): h for p, h in pins.items()}, CAE_authorized=False, manufacturing_authorized=False)
    native.save(args.output/'report.json', report)
    gmsh.initialize(['surface-topology', '-nopopup'], readConfigFiles=False, run=False)
    gmsh.option.setNumber('General.Terminal', 0)
    try:
        gmsh.open(str(args.mesh))
        if len(gmsh.model.mesh.getElements(3)[0]): raise ValueError('surface_only_input_required')
        tags, xyz, _ = gmsh.model.mesh.getNodes(); order = np.argsort(tags)
        tags = tags[order]; points = np.asarray(xyz).reshape(-1, 3)[order]
        types, elements, nodes = gmsh.model.mesh.getElements(2)
        if list(types) != [2]: raise ValueError('linear_surface_required')
        triangles = np.asarray(nodes[0]).reshape(-1, 3); indices = np.searchsorted(tags, triangles)
        if indices.max() >= len(tags) or not np.array_equal(tags[indices], triangles): raise ValueError('known_node_tags_required')
        report['topology'] = indexed_topology(points, indices)
        if args.orient_entities:
            topology = report['topology']
            if (topology['not_incident_twice'] or topology['duplicate_triangles']
                    or topology['exact_duplicate_used_coordinates']
                    or topology['vertex_link_classification'] != {'circle': topology['used_vertices']}):
                raise ValueError('closed_vertex_manifold_before_orientation_required')
            labels = np.zeros(len(indices), dtype=np.int64)
            element_order = np.argsort(elements[0]); sorted_elements = elements[0][element_order]
            for _, tag in gmsh.model.getEntities(2):
                t, e, _ = gmsh.model.mesh.getElements(2, tag)
                if len(t): labels[element_order[np.searchsorted(sorted_elements, e[0])]] = tag
            indices, report['orientation_permutation'] = orient_entities(points, indices, labels)
            report['oriented_topology'] = indexed_topology(points, indices)
            if not report['oriented_topology']['indexed_closed_oriented_manifold_screen_passed']:
                raise ValueError('orientation_result_failed_topology')
        types, _, nodes = gmsh.model.mesh.getElements(1)
        if list(types) != [1]: raise ValueError('linear_stored_curve_mesh_required')
        report['stored_curves'] = stored_curve_edges(triangles, np.asarray(nodes[0]).reshape(-1, 2))
        # Binary arrays preserve doubles and indices; never round through STL.
        path = args.output/'surface-private.npz'
        with path.open('xb') as stream: np.savez(stream, points=points, triangles=indices)
        path.chmod(0o600)
        with np.load(path, allow_pickle=False) as data:
            exact = np.array_equal(data['points'], points) and np.array_equal(data['triangles'], indices)
        report.update(array_export_sha256=native.sha256(path), array_readback_exact=exact,
            array_export_orientation='consistent_entity_positive_flux' if args.orient_entities else 'original_stored_order',
            geometric_intersections_checked=False, native_1d_mesh_rebuilt=False,
            status='completed_diagnostic_only')
    except Exception as error:
        report.update(status='failed', error=type(error).__name__+': '+str(error))
    finally:
        gmsh.finalize()
        report.update(inputs_unchanged=all(native.sha256(p) == h for p, h in pins.items()), seconds=time.monotonic()-start)
        native.save(args.output/'report.json', report)
    print(json.dumps({k: report.get(k) for k in ('status', 'error', 'topology', 'inputs_unchanged', 'seconds')}))
    return 0 if report['status'] == 'completed_diagnostic_only' and report['inputs_unchanged'] else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('body', 'mesh', 'receipt', 'shape-audit', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--orient-entities', action='store_true', help='Export only whole-face winding permutations; keep the mesh/CAD untouched.')
    signal.alarm(300)
    raise SystemExit(run(parser.parse_args()))
