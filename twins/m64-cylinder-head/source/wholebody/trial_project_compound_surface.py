#!/usr/bin/env python3
"""Project compound interiors and optionally refine shared native boundaries.

Private diagnostic, not editable CAD reconstruction or a manufacturing release.
No triangle deletion, welding, smoothing or quality-threshold relaxation.
"""
import argparse
import json
from pathlib import Path
import signal
import time

import numpy as np
from run_parallel_cad_trials import BODY_SHA, native
from trial_constrained_patch import PATCHES, compound, indexed, read_native
from trial_compound_junction_mesh import surface_edges


def project_points(points, target, movable):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.gp import gp_Pnt
    points, movable = np.asarray(points), np.asarray(movable)
    if (points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all()
            or movable.dtype != np.bool_ or movable.shape != (len(points),)
            or not movable.any()):
        raise ValueError('finite_points_and_nonempty_boolean_mask_required')
    result = points.astype(float, copy=True)
    op = BRepExtrema_DistShapeShape(); op.LoadS2(target)
    for i in np.flatnonzero(movable):
        op.LoadS1(BRepBuilderAPI_MakeVertex(gp_Pnt(*map(float, points[i]))).Vertex()); op.Perform()
        if not op.IsDone() or not np.isfinite(op.Value()) or not 0 <= op.Value() <= .1:
            raise ValueError('bounded_native_projection_required')
        result[i] = op.PointOnShape2(1).Coord()
    if not np.isfinite(result).all() or not np.array_equal(result[~movable], points[~movable]):
        raise ValueError('finite_projection_and_fixed_boundary_required')
    return result


def refine_patch(points, triangles, target):
    """Split interior edges once, preserving the exterior polygon exactly."""
    points, triangles = np.asarray(points), np.asarray(triangles)
    from run_bounded_chamfer import surface_arrays
    surface_arrays(points, triangles)  # Validate, but retain the caller's indices.
    edges, counts = np.unique(np.sort(np.concatenate([triangles[:, p] for p in
        ((0, 1), (1, 2), (2, 0))]), axis=1), axis=0, return_counts=True)
    if (counts > 2).any(): raise ValueError('manifold_patch_edges_required')
    interior = edges[counts == 2]
    if not len(interior): raise ValueError('interior_edges_required')
    mids = project_points(points[interior].mean(axis=1), target, np.ones(len(interior), dtype=bool))
    result = np.vstack([points, mids])
    refined, parents = split_edges(triangles, interior, len(points), result)
    return result, refined, parents


def split_edges(triangles, edges, first_node, points):
    """Use one midpoint index per selected edge on every incident triangle."""
    ids = {tuple(edge): first_node+i for i, edge in enumerate(edges)}
    refined, parents = [], []
    for index, row in enumerate(triangles):
        m = [ids.get(tuple(sorted(edge))) for edge in (row[[0, 1]], row[[1, 2]], row[[2, 0]])]
        count = sum(i is not None for i in m)
        if count == 0: children = [row.tolist()]
        elif count == 3:
            a, b, c = row; x, y, z = m
            children = [[a, x, z], [x, b, y], [z, y, c], [x, y, z]]
        else:
            # Rotate, never reverse: one split is AB; two splits are AB and BC.
            k = next(i for i in range(3) if m[i] is not None) if count == 1 else (m.index(None)+1) % 3
            a, b, c = np.roll(row, -k); x, y, _ = m[k:]+m[:k]
            children = [[a, x, c], [x, b, c]] if count == 1 else [[b, y, x], [a, x, c], [x, y, c]]
            if count == 2:
                normal = np.cross(points[b]-points[a], points[c]-points[a])
                def positive(cells):
                    p = points[cells]
                    return (np.cross(p[:, 1]-p[:, 0], p[:, 2]-p[:, 0])@normal > 0).all()
                alternative = [[b, y, x], [a, x, y], [a, y, c]]
                if not positive(children) and positive(alternative):
                    children = alternative
        refined.extend(children); parents.extend([index]*len(children))
    return np.asarray(refined, dtype=np.int64), np.asarray(parents)


def witness_region(points, triangles, witnesses):
    witnesses = np.asarray(witnesses, dtype=float)
    if witnesses.shape != (2, 3) or not np.isfinite(witnesses).all():
        raise ValueError('two_finite_directional_shape_witnesses_required')
    # Two original 0.2-size edge lengths around each measured worst sample.
    return np.any(np.linalg.norm(points[triangles, None, :]-witnesses, axis=3) <= .4, axis=(1, 2))


def refine_shared_boundaries(points, triangles, labels, faces, groups):
    """Project new shared midpoints to common CAD edges, never to face interiors."""
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopoDS import TopoDS
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GeomAbs import GeomAbs_Line
    from run_bounded_chamfer import surface_arrays
    points, triangles, labels = map(np.asarray, (points, triangles, labels))
    surface_arrays(points, triangles)
    chosen = [tag for group in groups.values() for tag in group]
    if (labels.shape != (len(triangles),) or not np.issubdtype(labels.dtype, np.integer)
            or not chosen or len(chosen) != len(set(chosen))
            or not set(chosen).issubset(faces) or not set(labels).issubset(faces)):
        raise ValueError('disjoint_bound_native_face_groups_required')
    edges, inverse, counts = np.unique(np.sort(np.concatenate([triangles[:, p] for p in
        ((0, 1), (1, 2), (2, 0))]), axis=1), axis=0, return_inverse=True, return_counts=True)
    if (counts > 2).any(): raise ValueError('manifold_patch_edges_required')
    use_order = np.argsort(inverse, kind='stable')
    first = np.r_[0, counts.cumsum()[:-1]]
    triangle_uses = np.tile(np.arange(len(triangles)), 3)
    selected, midpoints, neighbours = [], [], set()
    max_endpoint_error = 0.; skipped_straight_edges = 0
    for name, group in groups.items():
        inside = np.isin(labels, group)
        uses_inside = np.bincount(inverse, weights=np.tile(inside, 3), minlength=len(edges))
        shared = np.flatnonzero((counts == 2) & (uses_inside == 1))
        if not len(shared): raise ValueError('nonempty_shared_patch_boundary_required')
        a = triangle_uses[use_order[first[shared]]]
        b = triangle_uses[use_order[first[shared]+1]]
        outside = labels[np.where(inside[a], b, a)]
        group_edges = indexed(compound([faces[t] for t in group]), TopAbs_EDGE)
        for tag in np.unique(outside):
            if int(tag) in chosen: raise ValueError('distinct_nonoverlapping_neighbours_required')
            common = [e for e in indexed(faces[int(tag)], TopAbs_EDGE)
                      if any(e.IsSame(g) for g in group_edges)]
            if not common: raise ValueError(f'native_common_curve_required:{name}:{tag}')
            target = compound(common); e = edges[shared[outside == tag]]
            endpoints = points[np.unique(e)]
            projected = project_points(endpoints, target, np.ones(len(endpoints), dtype=bool))
            error = float(np.linalg.norm(projected-endpoints, axis=1).max())
            if error > 1e-6: raise ValueError(f'boundary_nodes_off_common_native_curve:{name}:{tag}:{error}')
            max_endpoint_error = max(max_endpoint_error, error)
            # Exact single lines need no chord correction; do not degrade their neighbours.
            if len(common) == 1 and BRepAdaptor_Curve(TopoDS.Edge_s(common[0])).GetType() == GeomAbs_Line:
                skipped_straight_edges += len(e)
                continue
            midpoints.append(project_points(points[e].mean(axis=1), target, np.ones(len(e), dtype=bool)))
            selected.append(e); neighbours.add(int(tag))
    selected = np.vstack(selected) if selected else np.empty((0, 2), dtype=np.int64)
    midpoints = np.vstack(midpoints) if midpoints else np.empty((0, 3))
    if len(np.unique(selected, axis=0)) != len(selected): raise ValueError('unique_shared_edges_required')
    result = np.vstack([points, midpoints])
    refined, parents = split_edges(triangles, selected, len(points), result)
    return result, refined, parents, dict(shared_edges=len(selected),
        skipped_exact_straight_edges=skipped_straight_edges,
        maximum_endpoint_curve_error=max_endpoint_error,
        maximum_midpoint_shift=float(np.linalg.norm(midpoints-points[selected].mean(axis=1), axis=1).max(initial=0)),
        neighbour_face_tags_private=sorted(neighbours),
        changed_face_tags_private=sorted(set(chosen) | neighbours),
        original_nodes_unchanged=True, curve_element_mesh_updated=False)


def run(args):
    import gmsh
    import OCP
    from OCP.TopAbs import TopAbs_FACE
    from trial_bounded_tip_cut import encode
    start = time.monotonic()
    sources = [Path(__file__), Path(native.__file__)] + [Path(__file__).with_name(name) for name in
        ('trial_constrained_patch.py', 'trial_compound_junction_mesh.py', 'run_parallel_cad_trials.py',
         'run_bounded_chamfer.py')]
    pins = {p: native.sha256(p) for p in [args.body, args.mesh, args.receipt, *sources]}
    record = json.loads(args.receipt.read_text())
    witness = None
    if args.local_shape_witnesses:
        pins[args.local_shape_witnesses] = native.sha256(args.local_shape_witnesses)
        witness = json.loads(args.local_shape_witnesses.read_text())
        if (not args.split_interior_edges or args.split_shared_boundaries
                or record.get('necessary_surface_checks_passed') is not True
                or witness.get('schema') != 'm64-compound-native-shape-samples/v1'
                or witness.get('status') != 'completed_diagnostic_only'
                or witness.get('inputs_unchanged') is not True
                or witness.get('source_hashes', {}).get(args.mesh.name) != pins[args.mesh]
                or witness.get('source_hashes', {}).get(args.receipt.name) != pins[args.receipt]
                or witness.get('source_hashes', {}).get(args.body.name) != BODY_SHA):
            raise ValueError('bound_completed_shape_audit_and_screened_parent_required')
    if (args.output.exists() or args.output.is_symlink() or any(p.is_symlink() for p in pins)
            or (args.split_shared_boundaries and not args.split_interior_edges)
            or gmsh.__version__ != '4.15.2' or OCP.__version__ != '7.9.3.1'
            or pins[args.body] != BODY_SHA or record.get('input_sha256') != BODY_SHA
            or record.get('schema') != ('m64-projected-compound-screen/v1' if witness else 'm64-compound-junction-screen/v1')
            or record.get('status') != 'completed_diagnostic_only' or record.get('compound_classify') != 1
            or record.get('surface_sha256') != pins[args.mesh] or record.get('inputs_unchanged') is not True
            or record.get('groups') != {k: list(v) for k, v in PATCHES.items()}):
        raise ValueError('pinned_classified_parent_surface_and_fresh_output_required')
    binding = record['native_face_binding_private']
    if binding.get('descriptor_bijection_verified') is not True: raise ValueError('native_face_binding_required')
    tags = {r['source_face_index']: r['gmsh_face_tag'] for r in binding['matches_private']}
    args.output.mkdir(mode=0o700)
    report = dict(schema='m64-projected-compound-screen/v1', status='incomplete',
        input_sha256=BODY_SHA, parent_surface_sha256=pins[args.mesh],
        parent_receipt_sha256=pins[args.receipt], source_hashes={p.name: pins[p] for p in sources},
        native_face_binding_private=binding, compound_classify=1, groups=PATCHES,
        split_interior_edges=args.split_interior_edges,
        split_shared_boundaries=args.split_shared_boundaries,
        local_shape_witness_sha256=pins[args.local_shape_witnesses] if witness else None,
        local_refinement_radius_scan_units=.4 if witness else None,
        two_edge_split_diagonal='alternate_only_if_default_fails_orientation_and_alternate_passes',
        maximum_allowed_projection_scan_units=.1, geometry_modified=False, mesh_nodes_modified=True,
        master_replaced=False, CAE_authorized=False, manufacturing_authorized=False)
    def save(): native.save(args.output/'report.json', report)
    save()
    gmsh.initialize(['project-compound', '-nopopup'], readConfigFiles=False, run=False)
    gmsh.option.setNumber('General.Terminal', 0)
    try:
        body = read_native(args.body); before_body = encode(body); faces = indexed(body, TopAbs_FACE)
        gmsh.open(str(args.mesh))
        if len(gmsh.model.mesh.getElements(3)[0]): raise ValueError('surface_only_input_required')
        node_tags, xyz, _ = gmsh.model.mesh.getNodes(); order = np.argsort(node_tags)
        node_tags = node_tags[order]; xyz = np.asarray(xyz).reshape(-1, 3)[order]
        types, elements, nodes = gmsh.model.mesh.getElements(2)
        if list(types) != [2] or not 0 < len(elements[0]) <= 2000000: raise ValueError('bounded_linear_surface_required')
        triangles = np.asarray(nodes[0]).reshape(-1, 3); indices = np.searchsorted(node_tags, triangles)
        if indices.max() >= len(node_tags) or not np.array_equal(node_tags[indices], triangles):
            raise ValueError('known_node_tags_required')
        updated = xyz.copy(); all_free = np.zeros(len(xyz), dtype=bool); rows = {}
        for name, group in PATCHES.items():
            selected = []
            for i in group:
                t, e, _ = gmsh.model.mesh.getElements(2, tags[i])
                if list(t) != [2]: raise ValueError('nonempty_linear_classified_patch_required')
                selected.extend(e[0])
            mask = np.isin(elements[0], selected)
            if int(mask.sum()) != len(selected): raise ValueError('unique_patch_element_tags_required')
            free = np.setdiff1d(np.unique(indices[mask]), np.unique(indices[~mask]))
            movable = np.zeros(len(xyz), dtype=bool); movable[free] = True
            if (all_free & movable).any(): raise ValueError('disjoint_local_interiors_required')
            updated = project_points(updated, compound([faces[i-1] for i in group]), movable)
            all_free |= movable
            rows[name] = dict(projected_nodes=len(free),
                maximum_shift=float(np.linalg.norm(updated[free]-xyz[free], axis=1).max()))
        report.update(projection=rows, protected_nodes_unchanged=np.array_equal(updated[~all_free], xyz[~all_free]),
                      native_in_memory_unchanged=encode(body) == before_body)
        a, b = xyz[indices], updated[indices]
        normals = lambda p: np.cross(p[:, 1]-p[:, 0], p[:, 2]-p[:, 0])
        report['nonpositive_normal_dot_products'] = int((np.einsum('ij,ij->i', normals(a), normals(b)) <= 0).sum())
        for i in np.flatnonzero(all_free): gmsh.model.mesh.setNode(int(node_tags[i]), updated[i].tolist(), [])
        if args.split_interior_edges:
            report['refinement'] = {}
            for name, group in PATCHES.items():
                arrays, labels = [], []
                for i in group:
                    _, _, n = gmsh.model.mesh.getElements(2, tags[i])
                    local = np.searchsorted(node_tags, np.asarray(n[0]).reshape(-1, 3))
                    arrays.append(local); labels.extend([tags[i]]*len(local))
                local = np.vstack(arrays); labels = np.asarray(labels)
                mask = witness_region(updated, local, [witness['groups'][name][direction]['maximum_witness_private']['point']
                    for direction in ('mesh_to_native', 'native_to_mesh')]) if witness else np.ones(len(local), dtype=bool)
                if not mask.any(): raise ValueError('nonempty_witness_region_required')
                if 3*int(mask.sum())+len(gmsh.model.mesh.getElements(2)[1][0]) > 2000000:
                    raise ValueError('bounded_refined_surface_required')
                new_points, refined, parents = refine_patch(updated, local[mask], compound([faces[i-1] for i in group]))
                new_count = len(new_points)-len(updated)
                new_tags = np.arange(int(node_tags[-1])+1, int(node_tags[-1])+1+new_count, dtype=node_tags.dtype)
                gmsh.model.mesh.addNodes(2, tags[group[0]], new_tags, new_points[len(updated):].ravel())
                node_tags = np.concatenate([node_tags, new_tags])
                old_normals = normals(updated[local[mask]])[parents]; new_normals = normals(new_points[refined])
                reversed_count = int((np.einsum('ij,ij->i', old_normals, new_normals) <= 0).sum())
                report['nonpositive_normal_dot_products'] += reversed_count
                child_labels = np.concatenate([labels[~mask], labels[mask][parents]])
                refined = np.vstack([local[~mask], refined])
                next_element = int(gmsh.model.mesh.getMaxElementTag())+1
                for i in group:
                    cells = refined[child_labels == tags[i]]
                    gmsh.model.mesh.removeElements(2, tags[i])
                    gmsh.model.mesh.addElementsByType(tags[i], 2,
                        np.arange(next_element, next_element+len(cells)), node_tags[cells].ravel())
                    next_element += len(cells)
                updated = new_points
                report['refinement'][name] = dict(new_nodes=new_count, old_triangles=len(local),
                    selected_triangles=int(mask.sum()), new_triangles=len(refined), nonpositive_normal_dot_products=reversed_count)
        if args.split_shared_boundaries:
            arrays, labels = [], []
            for _, tag in gmsh.model.getEntities(2):
                t, _, n = gmsh.model.mesh.getElements(2, tag)
                if not len(t): continue
                if list(t) != [2]: raise ValueError('linear_neighbour_faces_required')
                local = np.searchsorted(node_tags, np.asarray(n[0]).reshape(-1, 3))
                arrays.append(local); labels.extend([tag]*len(local))
            local, labels = np.vstack(arrays), np.asarray(labels)
            new_points, refined, parents, shared = refine_shared_boundaries(updated, local, labels,
                {tag: faces[i-1] for i, tag in tags.items()},
                {name: [tags[i] for i in group] for name, group in PATCHES.items()})
            if len(refined) > 2000000: raise ValueError('bounded_refined_surface_required')
            new_count = len(new_points)-len(updated)
            new_tags = np.arange(int(node_tags[-1])+1, int(node_tags[-1])+1+new_count, dtype=node_tags.dtype)
            gmsh.model.mesh.addNodes(2, tags[PATCHES['lower'][0]], new_tags, new_points[len(updated):].ravel())
            node_tags = np.concatenate([node_tags, new_tags])
            reversed_count = int((np.einsum('ij,ij->i', normals(updated[local])[parents], normals(new_points[refined])) <= 0).sum())
            report['nonpositive_normal_dot_products'] += reversed_count
            next_element = int(gmsh.model.mesh.getMaxElementTag())+1
            for tag in shared['changed_face_tags_private']:
                cells = refined[labels[parents] == tag]
                gmsh.model.mesh.removeElements(2, tag)
                gmsh.model.mesh.addElementsByType(tag, 2,
                    np.arange(next_element, next_element+len(cells)), node_tags[cells].ravel())
                next_element += len(cells)
            shared['nonpositive_normal_dot_products'] = reversed_count
            report['shared_boundary_refinement'] = shared
            updated = new_points
        types, elements, nodes = gmsh.model.mesh.getElements(2)
        if list(types) != [2]: raise ValueError('refined_linear_surface_required')
        triangles = np.asarray(nodes[0]).reshape(-1, 3)
        q = np.asarray(gmsh.model.mesh.getElementQualities(elements[0], 'minSICN'))
        if not np.isfinite(q).all(): raise ValueError('finite_surface_quality_required')
        report.update(triangles=len(q), minimum=float(q.min()), incompatible_triangles=int((q < 2*.1/(3-.1)).sum()),
                      edge_audit=surface_edges(triangles))
        gmsh.option.setNumber('Mesh.Binary', 1); gmsh.option.setNumber('Mesh.SaveAll', 1)
        path = args.output/'surface-private.msh'; gmsh.write(str(path)); path.chmod(0o600)
        gmsh.clear(); gmsh.open(str(path))
        nt, coordinates, _ = gmsh.model.mesh.getNodes(); ix = np.argsort(nt)
        rt, re, rn = gmsh.model.mesh.getElements(2)
        report['export_roundtrip_exact'] = bool(np.array_equal(nt[ix], node_tags)
            and np.array_equal(np.asarray(coordinates).reshape(-1, 3)[ix], updated)
            and list(rt) == [2] and np.array_equal(re[0], elements[0]) and np.array_equal(rn[0], nodes[0]))
        report.update(surface_sha256=native.sha256(path), status='completed_diagnostic_only')
        report['necessary_surface_checks_passed'] = bool(report['export_roundtrip_exact']
            and report['protected_nodes_unchanged'] and report['native_in_memory_unchanged']
            and not report['incompatible_triangles'] and not report['nonpositive_normal_dot_products']
            and not report['edge_audit']['not_incident_twice'] and not report['edge_audit']['duplicate_triangles'])
    except Exception as error:
        report.update(status='failed', error=type(error).__name__+': '+str(error))
    finally:
        gmsh.finalize()
        report.update(seconds=time.monotonic()-start, inputs_unchanged=all(native.sha256(p) == h for p, h in pins.items()))
        save()
    print(json.dumps({k: report.get(k) for k in ('status', 'error', 'projection', 'incompatible_triangles',
        'minimum', 'nonpositive_normal_dot_products', 'necessary_surface_checks_passed', 'inputs_unchanged', 'seconds')}))
    return 0 if report['status'] == 'completed_diagnostic_only' and report['inputs_unchanged'] else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('body', 'mesh', 'receipt', 'output'): parser.add_argument('--'+key, type=Path, required=True)
    parser.add_argument('--split-interior-edges', action='store_true', help='One conforming local subdivision; exterior edges stay fixed.')
    parser.add_argument('--split-shared-boundaries', action='store_true', help='Also subdivide shared curves and adjacent triangles; diagnostic surface only.')
    parser.add_argument('--local-shape-witnesses', type=Path, help='Bound completed parent shape audit: refine within 0.4 scan unit of its worst samples.')
    signal.alarm(600)
    raise SystemExit(run(parser.parse_args()))
