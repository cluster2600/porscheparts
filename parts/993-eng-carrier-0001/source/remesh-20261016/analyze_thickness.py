"""Localise the unchanged 008 per-face ray-thickness dump; never rerun or alter its checker."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

import numpy as np


def read_dump(path):
    data = Path(path).read_bytes()
    if len(data) < 4:
        raise ValueError('Truncated thickness dump')
    count = struct.unpack('<i', data[:4])[0]
    if count <= 0 or len(data) != 4 + 40 * count:
        raise ValueError('Thickness dump count/length mismatch')
    rows = np.frombuffer(data[4:], '<f4').reshape(count, 10)
    if not np.isfinite(rows).all() or np.any(rows[:, 9] < 0):
        raise ValueError('Finite nonnegative thickness data required')
    return rows[:, :9].reshape(-1, 3, 3).astype(float), rows[:, 9].astype(float)


def regions(triangles):
    centres = triangles.mean(1)
    cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    area = np.linalg.norm(cross, axis=1) / 2
    if np.any(area == 0):
        raise ValueError('Nondegenerate triangles required for area classification')
    normal_z = cross[:, 2] / (2 * area)
    labels = np.full(len(triangles), 'edges_and_transitions', dtype=object)
    interfaces = (np.abs(centres[:, 0]) > 260) | ((np.abs(centres[:, 0]) < 75) & (np.abs(np.abs(centres[:, 2]) - 4) < 1e-4))
    labels[interfaces] = 'centre_and_mount_regions'
    webs = (np.abs(centres[:, 0]) >= 80) & (np.abs(centres[:, 0]) < 260) & (np.abs(normal_z) < 1e-3) & ~interfaces
    labels[webs] = 'webs'
    ribs = (np.abs(centres[:, 0]) < 110) & (centres[:, 2] > 4.0001) & ~interfaces
    labels[ribs] = 'ribs_and_feet'
    for z in (-22, -20.5, 20.5, 22):
        labels[(np.abs(triangles[:, :, 2] - z) < 1e-5).all(1)] = 'plane_caps'
    return centres, area, labels


def components(triangles, selected):
    indices = np.flatnonzero(selected)
    vertices, inverse = np.unique(triangles[selected].reshape(-1, 3), axis=0, return_inverse=True)
    faces = inverse.reshape(-1, 3)
    parent = np.arange(len(faces))
    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index
    owner = {}
    for index, face in enumerate(faces):
        for a, b in zip(face, np.roll(face, -1)):
            key = tuple(sorted((int(a), int(b))))
            if key in owner:
                parent[find(index)] = find(owner[key])
            else:
                owner[key] = index
    groups = {}
    for index, source_index in enumerate(indices):
        groups.setdefault(find(index), []).append(int(source_index))
    return list(groups.values())


def analyse(dump, output):
    triangles, thickness = read_dump(dump)
    centres, area, labels = regions(triangles)
    report = {'input_dump_sha256': hashlib.sha256(Path(dump).read_bytes()).hexdigest(),
              'triangles': len(triangles), 'surface_area_mm2': float(area.sum()),
              'original_checker_minimum_mm': 1.5, 'original_wall_screen_status': 'rejected' if np.any(thickness < 1.5) else 'passed',
              'regions_are_geometric_classification_not_CAD_feature_labels': True,
              'region_rules': {'plane_caps': 'all triangle Z coordinates at +/-22 or +/-20.5 within 1e-5 mm',
                               'centre_and_mount_regions': '|X|>260 or central |X|<75 at Z=+/-4',
                               'ribs_and_feet': '|X|<110 and Z>4, excluding plane caps and centre plane',
                               'webs': 'remaining |X|>=80 and |X|<260 extruded vertical faces, |normal_Z|<1e-3',
                               'edges_and_transitions': 'remaining faces'},
              'regions': {}, 'total_area_below_mm2': {str(value): float(area[thickness < value].sum()) for value in (1.5, 1.49, 1.4, 1.3)},
              'mesh_face_probes': []}
    for label in sorted(set(labels)):
        selected = labels == label
        worst = int(np.flatnonzero(selected)[np.argmin(thickness[selected])])
        report['regions'][label] = {'area_mm2': float(area[selected].sum()),
            'area_below_mm2': {str(value): float(area[selected & (thickness < value)].sum()) for value in (1.5, 1.49, 1.4, 1.3)},
            'area_1p49_to_1p5_mm2': float(area[selected & (thickness >= 1.49) & (thickness < 1.5)].sum()),
            'worst_face': worst, 'minimum_ray_mm': float(thickness[worst]), 'worst_centroid_mm': centres[worst].tolist()}
        # Probe one actual worst face per region and weighted quartiles of the dominant web band.
        report['mesh_face_probes'].append({'region': label, 'face': worst, 'centroid_mm': centres[worst].tolist(),
                                           'outward_normal': (np.cross(triangles[worst, 1] - triangles[worst, 0], triangles[worst, 2] - triangles[worst, 0]) / (2 * area[worst])).tolist(),
                                           'checker_ray_mm': float(thickness[worst])})
    selected = (labels == 'webs') & (thickness >= 1.49) & (thickness < 1.5)
    ids = np.flatnonzero(selected); ordered = ids[np.argsort(thickness[ids])]; cumulative = np.cumsum(area[ordered])
    for quantile in ((.25, .5, .75) if len(ordered) else ()):
        index = int(ordered[np.searchsorted(cumulative, quantile * cumulative[-1])])
        normal = np.cross(triangles[index, 1] - triangles[index, 0], triangles[index, 2] - triangles[index, 0]) / (2 * area[index])
        report['mesh_face_probes'].append({'region': 'web_1p49_to_1p5_area_quartile', 'quartile': quantile,
            'face': index, 'centroid_mm': centres[index].tolist(), 'outward_normal': normal.tolist(), 'checker_ray_mm': float(thickness[index])})
    report['below_1p4_connected_patches'] = []
    patches = components(triangles, thickness < 1.4)
    for ids in sorted(patches, key=lambda rows: area[rows].sum(), reverse=True)[:20]:
        points = triangles[ids].reshape(-1, 3)
        report['below_1p4_connected_patches'].append({'area_mm2': float(area[ids].sum()), 'triangles': len(ids),
            'bounds_mm': [points.min(0).tolist(), points.max(0).tolist()],
            'minimum_ray_mm': float(thickness[ids].min()), 'area_below_1p3_mm2': float(area[np.array(ids)[thickness[ids] < 1.3]].sum()),
            'regional_area_mm2': {label: float(area[np.array(ids)[labels[ids] == label]].sum()) for label in sorted(set(labels[ids]))}})
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    (output / 'thickness-localisation.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dump', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); result = analyse(args.dump, args.output)
    print(json.dumps({'regions': result['regions'], 'largest_below_1p4_patches': result['below_1p4_connected_patches'][:6]}))
