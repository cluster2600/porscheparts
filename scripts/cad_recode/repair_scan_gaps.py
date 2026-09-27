#!/usr/bin/env python3
"""Close small, locally planar scan gaps; preserve protected circular openings."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.csgraph import connected_components

from scripts.cad_recode.pipeline import digest, new_output, write_json
from scripts.cad_recode.recover_planes import loops_from_boundary


def triangulate_polygon(points):
    """Ear clipping preserves the original boundary vertices, including concavities."""
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2 or not 3 <= len(points) <= 128 or not np.isfinite(points).all():
        raise ValueError('invalid polygon')
    def cross(a,b):
        return a[0]*b[1]-a[1]*b[0]
    area = sum(cross(a,b) for a,b in zip(points,np.roll(points,-1,axis=0)))
    if abs(area) < 1e-10:
        raise ValueError('degenerate polygon')
    order = list(range(len(points)))
    orientation = np.sign(area)
    triangles = []
    while len(order) > 3:
        for i in range(len(order)):
            a,b,c = order[i-1],order[i],order[(i+1)%len(order)]
            pa,pb,pc = points[[a,b,c]]
            if orientation*cross(pb-pa,pc-pb) <= 1e-12:
                continue
            others = points[[j for j in order if j not in (a,b,c)]]
            inside = ((orientation*np.array([cross(pb-pa,q-pa) for q in others]) >= -1e-12)
                      & (orientation*np.array([cross(pc-pb,q-pb) for q in others]) >= -1e-12)
                      & (orientation*np.array([cross(pa-pc,q-pc) for q in others]) >= -1e-12))
            if inside.any():
                continue
            triangles.append([a,b,c]); del order[i]
            break
        else:
            raise ValueError('non-simple or degenerate polygon')
    triangles.append(order)
    triangles = np.array(triangles,dtype=np.int64)
    actual = sum(cross(points[b]-points[a],points[c]-points[a]) for a,b,c in triangles)
    if abs(actual-area) > max(1e-8,abs(area)*1e-8):
        raise ValueError('triangulation area mismatch')
    return triangles


def repair(source, profiles_path, output, expected, max_gap=3.0, max_planarity=.25):
    import trimesh
    if (not np.isfinite([max_gap,max_planarity]).all() or min(max_gap,max_planarity) <= 0
            or digest(source) != expected):
        raise ValueError('invalid repair limits or source hash')
    profiles = json.loads(Path(profiles_path).read_text())
    if profiles['source_sha256'] != expected:
        raise ValueError('protected profiles belong to another scan')
    mesh = trimesh.load(source,force='mesh',process=False)
    if not len(mesh.faces) or not np.isfinite(mesh.vertices).all():
        raise ValueError('invalid source mesh')
    output = new_output(output)
    counts = np.bincount(mesh.edges_unique_inverse)
    boundary_ids = np.flatnonzero(counts == 1)
    edges = mesh.edges_unique[boundary_ids]
    _, first = np.unique(mesh.edges_unique_inverse, return_index=True)
    original_edges = mesh.edges[first[boundary_ids]]
    existing_edges = csr_matrix((np.ones(len(mesh.edges_unique),dtype=bool),
        (mesh.edges_unique[:,0],mesh.edges_unique[:,1])),shape=(len(mesh.vertices),)*2)
    directed = {tuple(sorted(e)):tuple(map(int,d)) for e,d in zip(edges,original_edges)}
    edge_normals = {tuple(e):normal for e,normal in zip(edges,mesh.face_normals[first[boundary_ids]//3])}
    vertices, inverse = np.unique(edges,return_inverse=True); compact = inverse.reshape(-1,2)
    graph = coo_matrix((np.ones(len(edges)),(compact[:,0],compact[:,1])),shape=(len(vertices),)*2)
    _, labels = connected_components(graph,directed=False)
    edge_labels = labels[compact[:,0]]
    additions, filled, skipped = [], [], {}
    def skip(reason):
        skipped[reason] = skipped.get(reason,0)+1
    for label in np.unique(edge_labels):
        group = edges[edge_labels == label]
        if len(group) > 128:
            skip('large_boundary'); continue
        try:
            loops = loops_from_boundary(group)
            if len(loops) != 1:
                raise ValueError('multiple loops')
            loop = loops[0]; points = mesh.vertices[loop]
            diameter = float(np.linalg.norm(np.ptp(points,axis=0)))
            if diameter > max_gap:
                skip('gap_exceeds_size_limit'); continue
            center = points.mean(0)
            protected = False
            for profile in profiles['profiles']:
                delta = center-profile['center']; n = np.array(profile['normal'])
                axial = float(delta @ n)
                radial = np.linalg.norm(delta-axial*n)
                if abs(axial) < max_gap and radial < profile['radius']+diameter/2:
                    protected = True; break
            if protected:
                skip('protected_functional_opening'); continue
            _,_,basis = np.linalg.svd(points-center,full_matrices=False)
            normal = basis[-1]
            flatness = float(abs((points-center) @ normal).max())
            adjacent = np.array([edge_normals[tuple(e)] for e in group])
            if flatness > max_planarity or np.quantile(abs(adjacent @ normal),.1) < .8:
                skip('not_a_small_tangent_surface_gap'); continue
            # New triangles must oppose every existing directed boundary edge.
            if directed[tuple(sorted(loop[:2]))] == tuple(loop[:2]):
                loop.reverse(); points = mesh.vertices[loop]
            if any(directed[tuple(sorted((a,b)))] != (b,a) for a,b in zip(loop,loop[1:]+loop[:1])):
                skip('inconsistent_boundary_winding'); continue
            triangles = np.array(loop)[triangulate_polygon((points-center) @ basis[:2].T)]
            vectors = mesh.vertices[triangles]
            cross = np.cross(vectors[:,1]-vectors[:,0],vectors[:,2]-vectors[:,0])
            lengths = np.linalg.norm(cross,axis=1)
            if lengths.min() <= 2e-12 or np.quantile(adjacent @ (cross.sum(0)/np.linalg.norm(cross.sum(0))),.1) < .8:
                skip('degenerate_cap_or_back_of_existing_surface'); continue
            cap_edges = np.sort(np.concatenate([triangles[:,[0,1]],triangles[:,[1,2]],triangles[:,[2,0]]]),axis=1)
            unique, number = np.unique(cap_edges,axis=0,return_counts=True)
            interior = unique[number == 2]
            if len(interior) and np.asarray(existing_edges[interior[:,0],interior[:,1]]).ravel().any():
                skip('cap_would_overlap_existing_edges'); continue
            additions.extend(triangles.tolist())
            filled.append(dict(boundary_vertices=loop,diameter_upper_bound=diameter,
                               planarity_max=flatness,added_triangles=len(triangles)))
        except ValueError as error:
            skip(str(error))
    if not additions:
        raise ValueError('no unprotected gap satisfied repair limits')
    repaired = trimesh.Trimesh(mesh.vertices.copy(),np.vstack([mesh.faces,additions]),process=False)
    after = np.bincount(repaired.edges_unique_inverse)
    expected_removed = sum(len(gap['boundary_vertices']) for gap in filled)
    if (np.count_nonzero(after == 1) != len(edges)-expected_removed
            or np.count_nonzero(after > 2) != np.count_nonzero(counts > 2)
            or (repaired.area_faces[len(mesh.faces):] <= 1e-12).any()):
        raise ValueError('repair topology check failed')
    if not np.array_equal(repaired.vertices,mesh.vertices) or not np.array_equal(repaired.faces[:len(mesh.faces)],mesh.faces):
        raise ValueError('source geometry changed')
    repaired_path = output/'scan-repaired.obj'
    repaired_path.write_text(trimesh.exchange.obj.export_obj(repaired,digits=17,
        include_normals=False,include_color=False))
    reread = trimesh.load(repaired_path,force='mesh',process=False)
    if not np.array_equal(reread.vertices,mesh.vertices) or not np.array_equal(reread.faces,repaired.faces):
        raise ValueError('repaired OBJ roundtrip changed vertices or triangles')
    report = dict(status='provisional_small_gap_repair',source_sha256=expected,
        protected_profiles_sha256=digest(profiles_path),units='unknown_OBJ_units',
        max_gap_obj_units=max_gap,max_planarity_obj_units=max_planarity,
        filled_gaps=len(filled),added_triangles=len(additions),
        boundary_edges_before=len(edges),boundary_edges_after=int(np.count_nonzero(after == 1)),
        nonmanifold_edges_unchanged=True,original_vertices_and_faces_preserved=True,
        skipped_boundaries=skipped,repairs=filled,watertight=bool(repaired.is_watertight),
        inferred_surfaces=True,geometry_accepted=False,physics_validated=False,
        manufacturing_authorized=False,repaired_sha256=digest(repaired_path))
    write_json(output/'repair.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='repairs'},indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('profiles',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--sha256',required=True);parser.add_argument('--max-gap',type=float,default=3)
    parser.add_argument('--max-planarity',type=float,default=.25)
    args=parser.parse_args()
    repair(args.source,args.profiles,args.output,args.sha256,args.max_gap,args.max_planarity)
