#!/usr/bin/env python3
"""Recover exterior 1D bisections; retain internal compound curves as metadata.

No CAD edit, point movement, surface repair, native face-role certification or
volume generation. Internal compound lines remain explicitly unresolved.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import signal
import time

import numpy as np
from run_parallel_cad_trials import BODY_SHA, native
from trial_constrained_patch import PATCHES
from trial_project_compound_surface import split_curve_lines, update_stored_curves
from audit_projected_surface import stored_curve_edges


def recover_bisections(original, children):
    """Require exactly two existing edges per old line, no unused child edge."""
    original, children = np.asarray(original), np.asarray(children)
    split_curve_lines(original, {}); split_curve_lines(children, {})
    if len(children) != 2*len(original): raise ValueError('exact_bisection_count_required')
    adjacency = defaultdict(set)
    for a, b in children:
        adjacency[int(a)].add(int(b)); adjacency[int(b)].add(int(a))
    midpoints = {}
    for a, b in original:
        common = adjacency[int(a)] & adjacency[int(b)]
        if len(common) != 1: raise ValueError('one_shared_child_midpoint_required')
        midpoint = common.pop()
        if midpoint in original: raise ValueError('midpoint_must_not_be_an_old_curve_node')
        midpoints[tuple(sorted((int(a), int(b))))] = midpoint
    if len(set(midpoints.values())) != len(midpoints): raise ValueError('unique_midpoints_required')
    expected, _ = split_curve_lines(original, midpoints)
    canonical = lambda rows: set(map(tuple, np.sort(rows, axis=1)))
    if canonical(expected) != canonical(children): raise ValueError('child_edge_coverage_required')
    return midpoints


def curve_parameters(gmsh, tag, positions):
    """Re-invert projection coordinates: Gmsh 4.15.2 may return invalid t values."""
    positions = np.asarray(positions)
    if positions.ndim != 2 or positions.shape[1] != 3 or not len(positions) or not np.isfinite(positions).all():
        raise ValueError('finite_curve_positions_required')
    closest, _ = gmsh.model.getClosestPoint(1, tag, positions.ravel())
    closest = np.asarray(closest).reshape(-1, 3)
    if closest.shape != positions.shape or not np.isfinite(closest).all(): raise ValueError('finite_projection_required')
    distance = np.linalg.norm(closest-positions, axis=1); near = distance <= 1e-6
    if not near.any(): raise ValueError('no_surface_nodes_on_native_curve')
    # Ignore projections of distant neighbouring curves; they can lie outside the trim.
    parameters = np.full(len(positions), np.nan)
    inverse = np.asarray(gmsh.model.getParametrization(1, tag, closest[near].ravel()))
    lo, hi = gmsh.model.getParametrizationBounds(1, tag)
    if not np.isfinite([lo[0],hi[0]]).all() or lo[0]>=hi[0]: raise ValueError('bounded_curve_range_required')
    inverse = np.clip(inverse,lo[0],hi[0])
    back = np.asarray(gmsh.model.getValue(1, tag, inverse)).reshape(-1, 3)
    if (back.shape != closest[near].shape or inverse.shape != (int(near.sum()),)
            or not all(np.isfinite(a).all() for a in (inverse, back))):
        raise ValueError('native_curve_parameter_roundtrip_failed')
    # Distance to evaluated, trimmed CAD points, not the infinite supporting curve.
    distance[near] = np.linalg.norm(back-positions[near],axis=1)
    parameters[near] = inverse
    accepted = distance[near] <= 1e-6
    return parameters, distance, float(np.linalg.norm(back[accepted]-closest[near][accepted],axis=1).max(initial=0))


def run(args):
    import gmsh
    import OCP
    start = time.monotonic()
    paths = [args.body, args.mesh, args.receipt, args.topology, args.arrays, Path(__file__),
             Path(native.__file__), Path(__file__).with_name('trial_project_compound_surface.py'),
             Path(__file__).with_name('audit_projected_surface.py'), Path(__file__).with_name('trial_constrained_patch.py')]
    pins = {p: native.sha256(p) for p in paths}
    record, topology = (json.loads(p.read_text()) for p in (args.receipt, args.topology))
    if (args.output.exists() or args.output.is_symlink() or any(p.is_symlink() for p in paths)
            or pins[args.body] != BODY_SHA or gmsh.__version__ != '4.15.2' or OCP.__version__ != '7.9.3.1'
            or record.get('schema') != 'm64-projected-compound-screen/v1'
            or record.get('input_sha256') != BODY_SHA or record.get('surface_sha256') != pins[args.mesh]
            or record.get('necessary_surface_checks_passed') is not True or record.get('inputs_unchanged') is not True
            or topology.get('schema') != 'm64-projected-surface-topology/v1'
            or topology.get('status') != 'completed_diagnostic_only' or topology.get('inputs_unchanged') is not True
            or topology.get('array_export_sha256') != pins[args.arrays]
            or pins[args.mesh] not in topology.get('source_hashes', {}).values()
            or pins[args.receipt] not in topology.get('source_hashes', {}).values()
            or topology.get('oriented_topology', {}).get('indexed_closed_oriented_manifold_screen_passed') is not True):
        raise ValueError('bound_screened_surface_orientation_and_fresh_output_required')
    args.output.mkdir(mode=0o700)
    report = dict(schema='m64-exterior-curve-reconciliation/v1', status='incomplete',
        source_hashes={str(p):h for p,h in pins.items()}, geometry_changed=False,
        native_face_roles_certified=False, CAE_authorized=False, manufacturing_authorized=False)
    save = lambda: native.save(args.output/'report.json', report)
    save(); native.baseline(argparse.Namespace(input=args.body, sha256=BODY_SHA, output=args.output))
    gmsh.initialize(['reconcile-curves', '-nopopup'], readConfigFiles=False, run=False)
    gmsh.option.setNumber('General.Terminal', 0)
    try:
        gmsh.open(str(args.mesh)); mesh_name = gmsh.model.getCurrent()
        if len(gmsh.model.mesh.getElements(3)[0]): raise ValueError('surface_only_required')
        nt, xyz, _ = gmsh.model.mesh.getNodes(); order = np.argsort(nt)
        nt = nt[order]; xyz = np.asarray(xyz).reshape(-1, 3)[order]
        types, ids, nodes = gmsh.model.mesh.getElements(2)
        if list(types) != [2] or len(ids[0]) > 2_000_000: raise ValueError('bounded_linear_surface_required')
        triangles = np.asarray(nodes[0]).reshape(-1, 3); labels = np.zeros(len(triangles), dtype=int)
        index = np.argsort(ids[0])
        for _, tag in gmsh.model.getEntities(2):
            _, es, _ = gmsh.model.mesh.getElements(2, tag)
            if len(es): labels[index[np.searchsorted(ids[0][index], es[0])]] = tag
        edges0 = np.sort(np.concatenate([triangles[:, p] for p in ((0, 1), (1, 2), (2, 0))]), axis=1)
        edges, inverse, counts = np.unique(edges0, axis=0, return_inverse=True, return_counts=True)
        if (counts != 2).any(): raise ValueError('closed_surface_required')
        owners = np.tile(labels, 3)[np.argsort(inverse, kind='stable').reshape(-1, 2)]
        skin = set(map(tuple, edges)); curves = []
        for _, tag in gmsh.model.getEntities(1):
            typ, _, nd = gmsh.model.mesh.getElements(1, tag)
            if not len(typ): continue
            if list(typ) != [1]: raise ValueError('linear_curves_required')
            lines = np.asarray(nd[0]).reshape(-1, 2)
            missing = sum(tuple(sorted(e)) not in skin for e in lines)
            if missing:
                if missing != len(lines): raise ValueError('partially_split_curve_requires_separate_audit')
                curves.append((tag, lines, *gmsh.model.getAdjacencies(1, tag)))
        gmsh.model.add('unchanged-native-reference')
        for key in ('OCCFixDegenerated','OCCFixSmallEdges','OCCFixSmallFaces','OCCSewFaces','OCCMakeSolids','OCCAutoFix'):
            gmsh.option.setNumber('Geometry.'+key, 0)
        gmsh.option.setNumber('Geometry.OCCScaling', 1)
        gmsh.model.occ.importShapes(str(args.body), highestDimOnly=False); gmsh.model.occ.synchronize()
        baseline = json.loads((args.output/'native-baseline.json').read_text())
        descriptors = [dict(tag=t, area=gmsh.model.occ.getMass(2, t), centre=list(gmsh.model.occ.getCenterOfMass(2, t)))
                       for _,t in gmsh.model.getEntities(2)]
        binding = native.match_faces(baseline['face_descriptors_private'], descriptors)
        tags = {r['source_face_index']:r['gmsh_face_tag'] for r in binding['matches_private']}
        previous = {r['source_face_index']:r['gmsh_face_tag'] for r in record['native_face_binding_private']['matches_private']}
        if not binding['descriptor_bijection_verified'] or tags != previous:
            raise ValueError('fresh_native_face_binding_required')
        patch_of = {tags[i]:name for name, group in PATCHES.items() for i in group}
        splits, rows = {}, []
        report['curves_private'] = rows
        for tag, lines, mesh_up, mesh_down in curves:
            up, down = gmsh.model.getAdjacencies(1, tag)
            groups = [patch_of.get(int(t)) for t in up]
            internal = len(groups) == 2 and groups[0] is not None and groups[0] == groups[1]
            expected_extra = set() if internal else {100000+min(tags[i] for i in PATCHES[g]) for g in groups if g}
            if set(down) != set(mesh_down) or set(mesh_up) != set(up) | expected_extra:
                raise ValueError('native_curve_endpoints_and_compound_adjacency_required')
            row = dict(curve_private=tag, old_lines=len(lines), internal_compound_metadata_only=internal)
            rows.append(row)
            if internal: continue
            if len(up) != 2 or sum(g is not None for g in groups) != 1:
                raise ValueError('one_patch_and_one_native_neighbour_required')
            group = next(g for g in groups if g); patch = [tags[i] for i in PATCHES[group]]
            outside = [t for t in up if int(t) not in patch_of]
            seam = edges[(np.isin(owners, patch).sum(axis=1) == 1) & (np.isin(owners, outside).sum(axis=1) == 1)]
            candidates = np.unique(seam); positions = xyz[np.searchsorted(nt, candidates)]
            parameters, distance, residual = curve_parameters(gmsh, tag, positions)
            lo, hi = gmsh.model.getParametrizationBounds(1, tag)
            if not np.isfinite([lo[0],hi[0]]).all() or lo[0]>=hi[0]: raise ValueError('bounded_curve_range_required')
            supported = (distance <= 1e-6) & (parameters >= lo[0]-1e-10) & (parameters <= hi[0]+1e-10)
            child = seam[np.isin(seam, candidates[supported]).all(axis=1)]
            row['candidate_child_lines'] = len(child)
            mapping = recover_bisections(lines, child)
            if set(mapping) & splits.keys(): raise ValueError('unique_curve_parent_required')
            params = dict(zip(map(int, candidates), map(float, parameters)))
            for (a,b), midpoint in mapping.items():
                if not min(params[a],params[b]) < params[midpoint] < max(params[a],params[b]):
                    report['rejected_parameter_witness_private'] = dict(curve=tag, nodes=[a,midpoint,b],
                        parameters=[params[a],params[midpoint],params[b]], bounds=[float(lo[0]),float(hi[0])])
                    raise ValueError('strict_native_parameter_between_parent_endpoints_required')
            splits.update(mapping)
            row.update(recovered_child_lines=len(child), native_parameter_order_checked=True,
                maximum_node_native_distance=float(distance[supported].max()), parameter_roundtrip_residual=residual)
        report.update(curves_private=rows, internal_metadata_lines=sum(r['old_lines'] for r in rows if r['internal_compound_metadata_only']))
        gmsh.model.setCurrent(mesh_name)
        report.update(update_stored_curves(gmsh, splits))
        reversed_faces = topology['orientation_permutation']['reversed_face_tags_private']
        # Match the audited array's exact order, not an equivalent cyclic rotation.
        for tag in reversed_faces:
            _, es, ns = gmsh.model.mesh.getElements(2, tag)
            oriented = np.asarray(ns[0]).reshape(-1,3)[:,::-1].copy()
            gmsh.model.mesh.removeElements(2, tag)
            gmsh.model.mesh.addElementsByType(tag,2,es[0],oriented.ravel())
        gmsh.option.setNumber('Mesh.Binary', 1); gmsh.option.setNumber('Mesh.SaveAll', 1)
        output = args.output/'exterior-reconciled-private.msh'; gmsh.write(str(output)); output.chmod(0o600)
        gmsh.clear(); gmsh.open(str(output))
        rt, rp, _ = gmsh.model.mesh.getNodes(); ix = np.argsort(rt)
        st, se, sn = gmsh.model.mesh.getElements(2)
        restored = np.asarray(sn[0]).reshape(-1, 3)
        with np.load(args.arrays, allow_pickle=False) as data:
            exact = (np.array_equal(rt[ix], nt) and np.array_equal(np.asarray(rp).reshape(-1,3)[ix], xyz)
                and np.array_equal(xyz, data['points']) and list(st) == [2] and np.array_equal(se[0],ids[0])
                and np.array_equal(np.searchsorted(nt, restored), data['triangles']))
        if not exact: raise ValueError('exact_oriented_array_and_element_readback_required')
        typ, _, nd = gmsh.model.mesh.getElements(1)
        remaining = stored_curve_edges(restored, np.asarray(nd[0]).reshape(-1,2))
        if remaining['lines_not_direct_surface_edges'] != report['internal_metadata_lines']:
            raise ValueError('all_exterior_lines_must_match_surface_edges')
        report.update(status='exterior_reconciled_internal_compounds_pending', output_sha256=native.sha256(output),
            exact_oriented_surface_readback=True, remaining_curve_audit=remaining,
            recovered_bisections_private=[[a,b,m] for (a,b),m in sorted(splits.items())])
    except Exception as error:
        report.update(status='failed', error=type(error).__name__+': '+str(error))
    finally:
        gmsh.finalize(); report.update(seconds=time.monotonic()-start, inputs_unchanged=all(native.sha256(p)==h for p,h in pins.items())); save()
    print(json.dumps({k:report.get(k) for k in ('status','error','rebuilt_curves','subdivided_stored_lines','internal_metadata_lines','exact_oriented_surface_readback','seconds')}))
    return 0 if report['status']=='exterior_reconciled_internal_compounds_pending' and report['inputs_unchanged'] else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('body','mesh','receipt','topology','arrays','output'): parser.add_argument('--'+name,type=Path,required=True)
    signal.alarm(300)
    raise SystemExit(run(parser.parse_args()))
