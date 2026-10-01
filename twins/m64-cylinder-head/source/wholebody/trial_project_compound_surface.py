#!/usr/bin/env python3
"""Project only compound-interior mesh nodes onto the unchanged trimmed CAD.

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
    ids = {tuple(edge): len(points)+i for i, edge in enumerate(interior)}
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
        refined.extend(children); parents.extend([index]*len(children))
    return np.vstack([points, mids]), np.asarray(refined, dtype=np.int64), np.asarray(parents)


def run(args):
    import gmsh
    import OCP
    from OCP.TopAbs import TopAbs_FACE
    from trial_bounded_tip_cut import encode
    start = time.monotonic()
    sources = [Path(__file__), Path(native.__file__)] + [Path(__file__).with_name(name) for name in
        ('trial_constrained_patch.py', 'trial_compound_junction_mesh.py', 'run_parallel_cad_trials.py')]
    pins = {p: native.sha256(p) for p in [args.body, args.mesh, args.receipt, *sources]}
    record = json.loads(args.receipt.read_text())
    if (args.output.exists() or args.output.is_symlink() or any(p.is_symlink() for p in pins)
            or gmsh.__version__ != '4.15.2' or OCP.__version__ != '7.9.3.1'
            or pins[args.body] != BODY_SHA or record.get('input_sha256') != BODY_SHA
            or record.get('schema') != 'm64-compound-junction-screen/v1'
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
                if 4*len(local)+len(gmsh.model.mesh.getElements(2)[1][0])-len(local) > 2000000:
                    raise ValueError('bounded_refined_surface_required')
                new_points, refined, parents = refine_patch(updated, local, compound([faces[i-1] for i in group]))
                new_count = len(new_points)-len(updated)
                new_tags = np.arange(int(node_tags[-1])+1, int(node_tags[-1])+1+new_count, dtype=node_tags.dtype)
                gmsh.model.mesh.addNodes(2, tags[group[0]], new_tags, new_points[len(updated):].ravel())
                node_tags = np.concatenate([node_tags, new_tags])
                old_normals = normals(updated[local])[parents]; new_normals = normals(new_points[refined])
                reversed_count = int((np.einsum('ij,ij->i', old_normals, new_normals) <= 0).sum())
                report['nonpositive_normal_dot_products'] += reversed_count
                next_element = int(gmsh.model.mesh.getMaxElementTag())+1
                for i in group:
                    cells = refined[labels[parents] == tags[i]]
                    gmsh.model.mesh.removeElements(2, tags[i])
                    gmsh.model.mesh.addElementsByType(tags[i], 2,
                        np.arange(next_element, next_element+len(cells)), node_tags[cells].ravel())
                    next_element += len(cells)
                updated = new_points
                report['refinement'][name] = dict(new_nodes=new_count, old_triangles=len(local),
                    new_triangles=len(refined), nonpositive_normal_dot_products=reversed_count)
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
    signal.alarm(600)
    raise SystemExit(run(parser.parse_args()))
