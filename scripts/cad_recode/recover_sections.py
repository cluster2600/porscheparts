#!/usr/bin/env python3
"""Recover scan-derived circular profiles; never infer a complete head or solid."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

from scripts.cad_recode.pipeline import digest, new_output, write_json


def fit_circle(points, tolerance):
    """Reject short arcs even when a huge fitted circle has tiny residuals."""
    points = np.asarray(points, dtype=float)
    if (points.ndim != 2 or points.shape[1] != 2 or len(points) < 40
            or not np.isfinite(points).all() or not np.isfinite(tolerance) or tolerance <= 0):
        raise ValueError('invalid circle input')
    guess = np.linalg.lstsq(np.c_[2 * points, np.ones(len(points))],
                            (points * points).sum(1), rcond=None)[0]
    radius = np.sqrt(max(0, guess[2] + sum(guess[:2] ** 2)))
    train, holdout = points[::2], points[1::2]
    fit = least_squares(lambda x: np.linalg.norm(train - x[:2], axis=1) - x[2],
                        np.r_[guess[:2], radius])
    center, radius = fit.x[:2], float(fit.x[2])
    angles = np.sort(np.arctan2(*(points - center)[:, ::-1].T))
    coverage = float(360 - np.degrees(np.diff(np.r_[angles, angles[0] + 2*np.pi]).max()))
    residual = abs(np.linalg.norm(holdout - center, axis=1) - radius)
    p95, maximum = float(np.quantile(residual, .95)), float(residual.max())
    return dict(center=center.tolist(), radius=radius, coverage_degrees=coverage,
                holdout_p95=p95, holdout_max=maximum,
                retained=bool(fit.success and radius > 4*tolerance and coverage >= 330
                              and p95 <= tolerance and maximum <= 2*tolerance))


def discover_planes(mesh, seed):
    """Find dominant planes directly from raw triangle normals, without old datums."""
    import trimesh
    points, indices = trimesh.sample.sample_surface(mesh, 100000, seed=seed)
    normals = mesh.face_normals[indices]
    rng = np.random.default_rng(seed)
    remaining = np.ones(len(points), dtype=bool)
    planes = []
    # ponytail: bounded RANSAC discovery, not an exhaustive surface segmentation.
    for _ in range(18):
        ids = np.flatnonzero(remaining)
        if len(ids) < 250:
            break
        subset = rng.choice(ids, min(8000, len(ids)), replace=False)
        best = None
        for index in rng.choice(ids, 250, replace=False):
            normal, offset = normals[index], points[index] @ normals[index]
            score = np.count_nonzero((abs(points[subset] @ normal-offset) < .25)
                                     & (abs(normals[subset] @ normal) > .995))
            if best is None or score > best[0]:
                best = score, normal, offset
        _, normal, offset = best
        mask = remaining & (abs(points @ normal-offset) < .25) & (abs(normals @ normal) > .995)
        if mask.sum() < 3:
            break
        center = points[mask].mean(0)
        _, _, vectors = np.linalg.svd(points[mask]-center, full_matrices=False)
        normal, offset = vectors[-1], float(center @ vectors[-1])
        mask = remaining & (abs(points @ normal-offset) < .25) & (abs(normals @ normal) > .995)
        planes.append(dict(normal=normal.tolist(), offset=offset, support=int(mask.sum())))
        remaining[mask] = False
    selected = []
    for plane in sorted(planes, key=lambda p: -p['support']):
        n, d = np.array(plane['normal']), plane['offset']
        if any(abs(n @ q['normal']) > .99 and
               abs(d-np.sign(n @ q['normal'])*q['offset']) < 4 for q in selected):
            continue
        selected.append(plane)
        if len(selected) == 6:
            break
    return selected


def recover(source, output, expected, tolerance=.6):
    import cadquery as cq
    import trimesh
    if not np.isfinite(tolerance) or tolerance <= 0:
        raise ValueError('positive profile tolerance required in OBJ units')
    if digest(source) != expected:
        raise ValueError('source hash mismatch')
    mesh = trimesh.load(source, force='mesh', process=False)
    if not len(mesh.faces) or not np.isfinite(mesh.vertices).all():
        raise ValueError('invalid raw scan')
    output = new_output(output)
    planes = discover_planes(mesh, 935)
    profiles, wires, rejected, open_paths = [], [], 0, 0
    for plane_id, plane in enumerate(planes):
        normal = np.array(plane['normal'])
        u = np.cross(normal, np.eye(3)[np.argmin(abs(normal))]); u /= np.linalg.norm(u)
        basis = np.array([u, np.cross(normal, u)])
        for delta in [-4, -2, -1, 0, 1, 2, 4]:
            offset = plane['offset'] + delta
            section = mesh.section(plane_origin=normal*offset, plane_normal=normal)
            if section is None:
                continue
            for entity in section.entities:
                curve = section.vertices[entity.points]
                if np.linalg.norm(curve[0]-curve[-1]) > 1e-6:
                    open_paths += 1
                    continue
                if len(curve) < 41:
                    continue
                fit = fit_circle(curve[:-1] @ basis.T, tolerance)
                if not fit['retained']:
                    rejected += 1
                    continue
                center = np.array(fit.pop('center')) @ basis + normal*offset
                radius = fit['radius']
                angles = np.linspace(0, 2*np.pi, 512, endpoint=False)
                samples = center + radius*(np.cos(angles)[:,None]*basis[0]
                                           + np.sin(angles)[:,None]*basis[1])
                distances = np.concatenate([trimesh.proximity.closest_point(mesh, batch)[1]
                                            for batch in np.array_split(samples, 16)])
                reverse = dict(p95=float(np.quantile(distances,.95)), sampled_max=float(distances.max()))
                if reverse['p95'] > tolerance or reverse['sampled_max'] > 2*tolerance:
                    rejected += 1
                    continue
                profiles.append(dict(**fit, center=center.tolist(), normal=normal.tolist(),
                    plane_id=plane_id, offset=offset, circle_to_scan=reverse,
                    source_curve=curve.tolist()))
                wires.append(cq.Wire.makeCircle(radius, cq.Vector(*center), cq.Vector(*normal)))
    if not wires:
        raise ValueError('no circular profile passed; no STEP produced')
    step = output / 'circular-profiles.step'
    cq.exporters.export(cq.Compound.makeCompound(wires), str(step))
    imported = cq.importers.importStep(str(step)).val()
    if not imported.isValid() or len(imported.Edges()) != len(wires) or imported.Solids():
        raise ValueError('STEP roundtrip mismatch')
    report = dict(status='partial_scan_derived_profiles', source_sha256=expected,
        units='unknown_OBJ_units', scale_verified=False, legacy_inputs_used=[],
        discovery_seed=935, planes=planes, profile_tolerance_obj_units=tolerance,
        threshold_scope='exploratory_profile_fit_not_engineering_acceptance',
        holdout_scope='alternating_vertices_of_same_scan_section_not_independent_measurement',
        reverse_check='512 circle samples to original triangle surface',
        retained_profiles=len(profiles), rejected_closed_profiles=rejected,
        open_section_paths=open_paths, step_sha256=digest(step), step_roundtrip_valid=True,
        complete_head=False, geometry_accepted=False, physics_validated=False,
        manufacturing_authorized=False, profiles=profiles)
    write_json(output/'profiles.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--profile-tolerance', type=float, default=.6)
    args = parser.parse_args()
    result = recover(args.source, args.output, args.sha256, args.profile_tolerance)
    print(json.dumps({key: value for key, value in result.items() if key not in ('profiles','planes')}, indent=2))
