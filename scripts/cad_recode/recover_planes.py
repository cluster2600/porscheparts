#!/usr/bin/env python3
"""Recover trimmed planar CAD faces from raw triangles, preserving scan gaps."""
import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from scripts.cad_recode.pipeline import digest, new_output, write_json
from scripts.cad_recode.recover_sections import discover_planes


def boundary(faces):
    edges = np.sort(np.concatenate([faces[:, [0,1]], faces[:, [1,2]], faces[:, [2,0]]]), axis=1)
    unique, counts = np.unique(edges, axis=0, return_counts=True)
    if np.any(counts > 2):
        raise ValueError('nonmanifold triangles')
    return unique[counts == 1]


def loops_from_boundary(edges):
    adjacent = defaultdict(list)
    for a, b in edges:
        adjacent[int(a)].append(int(b)); adjacent[int(b)].append(int(a))
    if not adjacent or any(len(v) != 2 for v in adjacent.values()):
        raise ValueError('open or branching boundary')
    loops = []
    while adjacent:
        start = next(iter(adjacent)); loop = [start]; previous, current = None, start
        while True:
            following = next(v for v in adjacent[current] if v != previous)
            previous, current = current, following
            if current == start:
                break
            loop.append(current)
        for vertex in loop:
            del adjacent[vertex]
        loops.append(loop)
    return loops


def recover(source, output, expected, tolerance=.4):
    import cadquery as cq
    import trimesh
    if not np.isfinite(tolerance) or tolerance <= 0 or digest(source) != expected:
        raise ValueError('invalid tolerance or source hash')
    mesh = trimesh.load(source, force='mesh', process=False)
    if not len(mesh.faces) or not np.isfinite(mesh.vertices).all():
        raise ValueError('invalid raw scan')
    output = new_output(output)
    planes = discover_planes(mesh, 935)
    faces, records, skipped = [], [], []
    for plane_id, plane in enumerate(planes):
        n, offset = np.array(plane['normal']), plane['offset']
        distances = mesh.vertices @ n-offset
        indices = np.flatnonzero((np.max(abs(distances[mesh.faces]), axis=1) < tolerance)
                                 & (abs(mesh.face_normals @ n) > .97))
        original_count = len(indices)
        # Remove pinched boundary triangles only; never close a gap or add material.
        for _ in range(12):
            edges = boundary(mesh.faces[indices])
            vertices, degree = np.unique(edges, return_counts=True)
            bad = vertices[degree != 2]
            if not len(bad):
                break
            indices = indices[~np.isin(mesh.faces[indices], bad).any(1)]
        triangles = mesh.faces[indices]
        adjacent = trimesh.graph.face_adjacency(faces=triangles)
        graph = coo_matrix((np.ones(len(adjacent)), (adjacent[:,0],adjacent[:,1])),
                           shape=(len(triangles),len(triangles)))
        _, labels = connected_components(graph, directed=False)
        for label in np.unique(labels):
            selected = indices[labels == label]
            if mesh.area_faces[selected].sum() < 80:
                continue
            try:
                loops = loops_from_boundary(boundary(mesh.faces[selected]))
                curves = [mesh.vertices[loop]-np.outer(distances[loop],n) for loop in loops]
                curves.sort(key=lambda q: -abs(np.sum(np.cross(q,np.roll(q,-1,axis=0)),axis=0) @ n))
                wires = [cq.Wire.makePolygon([cq.Vector(*v) for v in q],close=True) for q in curves]
                face = cq.Face.makeFromWires(wires[0],wires[1:])
                projected_area = float(np.sum(mesh.area_faces[selected]*abs(mesh.face_normals[selected] @ n)))
                if not face.isValid() or abs(face.Area()-projected_area) > 1e-3:
                    raise ValueError('invalid face or projected area mismatch')
                verts, tris = face.tessellate(.02,.1)
                model = trimesh.Trimesh([v.toTuple() for v in verts],tris,process=False)
                sample, _ = trimesh.sample.sample_surface(model,512,seed=936)
                reverse = np.concatenate([trimesh.proximity.closest_point(mesh,b)[1]
                                          for b in np.array_split(sample,16)])
                if reverse.max() > tolerance+.02:
                    raise ValueError('reconstructed face extends beyond scanned support')
                faces.append(face)
                records.append(dict(plane_id=plane_id,normal=n.tolist(),offset=offset,
                    area_obj_units_squared=float(face.Area()),scan_triangles=len(selected),
                    boundary_loops=[q.tolist() for q in curves],
                    removed_pinched_triangles_for_plane=original_count-len(indices),
                    projection_max=float(abs(distances[np.unique(mesh.faces[selected])]).max()),
                    cad_to_scan_p95=float(np.quantile(reverse,.95)),cad_to_scan_sampled_max=float(reverse.max())))
                print(f'plane {plane_id}: retained face {len(faces)}',flush=True)
            except (ValueError, RuntimeError) as error:
                skipped.append(dict(plane_id=plane_id,reason=str(error)))
    if not faces:
        raise ValueError('no supported planar faces; no STEP produced')
    step = output/'planar-faces.step'
    cq.exporters.export(cq.Compound.makeCompound(faces),str(step))
    shape = cq.importers.importStep(str(step)).val()
    if not shape.isValid() or len(shape.Faces()) != len(faces) or shape.Solids():
        raise ValueError('STEP roundtrip mismatch')
    write_json(output/'surfaces.json',dict(status='partial_trimmed_planar_surfaces',
        source_sha256=expected,units='unknown_OBJ_units',legacy_inputs_used=[],
        scale_verified=False,geometry_accepted=False,complete_head=False,
        physics_validated=False,manufacturing_authorized=False,
        tolerance_obj_units=tolerance,threshold_scope='exploratory_not_engineering_acceptance',
        minimum_patch_area_obj_units_squared=80,planes=planes,faces=records,skipped=skipped,
        step_sha256=digest(step),step_roundtrip_valid=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path); parser.add_argument('output',type=Path)
    parser.add_argument('--sha256',required=True)
    parser.add_argument('--projection-tolerance',type=float,default=.4)
    args = parser.parse_args()
    recover(args.source,args.output,args.sha256,args.projection_tolerance)
