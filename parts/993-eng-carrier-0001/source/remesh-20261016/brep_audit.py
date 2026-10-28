"""Measure deterministic mesh samples against the unchanged exact STEP shell."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from build123d import import_step
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.gp import gp_Pnt, gp_Pnt2d
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepClass import BRepClass_FaceClassifier
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.TopAbs import TopAbs_IN, TopAbs_ON

from remesh import read_stl
from gmsh_remesh import identity_step_sha256


def run(step, source, candidate, output, expected_sha256):
    step, output = Path(step), Path(output)
    if hashlib.sha256(step.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError('Exact retained STEP required')
    output.mkdir(parents=True, exist_ok=False)
    body = import_step(step)
    if not body.is_valid or len(body.solids()) != 1 or len(body.shells()) != 1:
        raise ValueError('One valid source solid/shell required')
    shell = body.shells()[0].wrapped
    cad_points = []
    for face in body.faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        for u in np.linspace(surface.FirstUParameter(), surface.LastUParameter(), 7):
            for v in np.linspace(surface.FirstVParameter(), surface.LastVParameter(), 7):
                classifier = BRepClass_FaceClassifier(face.wrapped, gp_Pnt2d(float(u), float(v)), 1e-7)
                if classifier.State() in (TopAbs_IN, TopAbs_ON):
                    cad_points.append(surface.Value(float(u), float(v)).Coord())
    samples_path = output / 'exact-CAD-surface-samples.npz'
    np.savez_compressed(samples_path, points_mm=np.asarray(cad_points))
    reports = {}
    for label, path in [('original_STL', source), ('candidate_STL', candidate)]:
        vertices, faces = read_stl(path)
        triangles = vertices[faces]
        area = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]), axis=1)
        rng = np.random.RandomState(9931016)
        selected = triangles[rng.choice(len(faces), 2048, p=area / area.sum())]
        u, v = rng.random_sample((2, len(selected)))
        r = np.sqrt(u)
        samples = np.vstack((vertices[np.linspace(0, len(vertices) - 1, 512).astype(int)],
                             triangles.mean(1)[np.linspace(0, len(faces) - 1, 512).astype(int)],
                             (1-r[:, None])*selected[:, 0] + (r*(1-v))[:, None]*selected[:, 1] + (r*v)[:, None]*selected[:, 2]))
        distances = []
        start = time.monotonic()
        for index, point in enumerate(samples):
            vertex = BRepBuilderAPI_MakeVertex(gp_Pnt(*map(float, point))).Shape()
            query = BRepExtrema_DistShapeShape(vertex, shell)
            query.Perform()
            if not query.IsDone():
                raise ValueError('Exact shell distance failed')
            distances.append(query.Value())
        distances = np.asarray(distances)
        maximum = int(distances.argmax())
        np.savez_compressed(output / (label + '-samples.npz'), points=samples, distances_mm=distances)
        reports[label] = {'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(), 'samples': len(samples),
                          'maximum_distance_to_STEP_shell_mm': float(distances[maximum]),
                          'p99_distance_mm': float(np.quantile(distances, .99)),
                          'worst_sample_mm': samples[maximum].tolist(), 'wall_seconds': time.monotonic() - start}
        print(label, reports[label], flush=True)
    bounds = body.bounding_box()
    volume = GProp_GProps()
    volume_error = BRepGProp.VolumeProperties_s(body.wrapped, volume, 1e-10, True, False)
    result = {'method': 'OCP BRepExtrema_DistShapeShape against exact source shell, not solid occupancy',
              'STEP_sha256': hashlib.sha256(step.read_bytes()).hexdigest(), 'random_seed': 9931016,
              'exact_CAD_surface_samples': len(cad_points), 'CAD_sampling': '7x7 UV grid per trimmed face, IN/ON classified',
              'exact_CAD_surface_samples_sha256': hashlib.sha256(samples_path.read_bytes()).hexdigest(),
              'exact_CAD_surface_samples_file': samples_path.name, 'exact_CAD_volume_mm3': volume.Mass(),
              'CAD_volume_method': 'OCP adaptive VolumeProperties, requested relative error 1e-10',
              'CAD_volume_estimated_relative_error': volume_error,
              'exact_CAD_bounds_mm': [list(bounds.min), list(bounds.max)],
              'sampling': '512 vertices, 512 face centroids and 2048 area-weighted points per STL',
              'documented_source_STL_requested_chord_tolerance_mm': .06, 'results': reports,
              'candidate_sampled_chord_screen_pass': reports['candidate_STL']['maximum_distance_to_STEP_shell_mm'] <= .06,
              'manufacturing_authorized': False}
    (output / 'brep-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('step', 'source', 'candidate', 'output'):
        parser.add_argument(name, type=Path)
    identity = parser.add_mutually_exclusive_group(required=True)
    identity.add_argument('--expected-step-sha256')
    identity.add_argument('--identity-receipt', type=Path)
    args = parser.parse_args()
    expected = identity_step_sha256(args.identity_receipt) if args.identity_receipt else args.expected_step_sha256
    result = run(args.step, args.source, args.candidate, args.output, expected)
    if not result['candidate_sampled_chord_screen_pass']:
        raise SystemExit(2)
