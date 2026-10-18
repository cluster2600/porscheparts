"""Check complete exposure segments against the recorded part section, preserving holes."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import time

import numpy as np
import shapely
from shapely.geometry import GeometryCollection, Polygon

AREA_RELATIVE_TOLERANCE = 1e-10


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def paths(points, offsets):
    if (points.ndim != 2 or points.shape[1] != 2 or not np.isfinite(points).all()
            or offsets.ndim != 1 or not np.issubdtype(offsets.dtype, np.integer)
            or not len(offsets) or offsets[0] != 0 or offsets[-1] != len(points)
            or np.any(np.diff(offsets) < 0)):
        raise ValueError('Invalid packed section paths')
    return [points[a:b] for a, b in zip(offsets[:-1], offsets[1:])]


def section_domain(rings):
    polygons = []
    for ring in rings:
        if len(ring) < 4 or not np.array_equal(ring[0], ring[-1]):
            raise ValueError('Open section ring')
        polygon = Polygon(ring)
        if not polygon.is_valid or polygon.area <= 0:
            raise ValueError('Invalid section ring')
        for previous in polygons:
            if polygon.overlaps(previous) or polygon.equals(previous):
                raise ValueError('Crossing or duplicate section rings')
        polygons.append(polygon)
    domain = GeometryCollection()
    # Odd-even nesting preserves holes and islands without trusting ring orientation.
    # Do not use symmetric_difference_all: upstream marks that API incorrect/deprecated.
    for polygon in polygons:
        domain = domain.symmetric_difference(polygon)
    if not domain.is_valid:
        raise ValueError('Invalid reconstructed section domain')
    return domain


def segments_check(segments, domain):
    if segments.ndim != 3 or segments.shape[1:] != (2, 2) or not np.isfinite(segments).all():
        raise ValueError('Invalid exposure segments')
    zero = np.all(segments[:, 0] == segments[:, 1], axis=1)
    canonical = segments.copy()
    reverse = ((canonical[:, 0, 0] > canonical[:, 1, 0]) |
               ((canonical[:, 0, 0] == canonical[:, 1, 0]) & (canonical[:, 0, 1] > canonical[:, 1, 1])))
    canonical[reverse] = canonical[reverse, ::-1]
    duplicates = len(segments) - len(np.unique(canonical.reshape(-1, 4), axis=0))
    lines = shapely.linestrings(segments)
    shapely.prepare(domain)
    outside = ~shapely.covers(domain, lines)
    outside_parts = shapely.difference(lines[outside], domain)
    outside_length = float(np.sum(shapely.length(outside_parts)))
    return {'segments': len(segments), 'zero_length_segments': int(zero.sum()),
            'exact_duplicate_segments': int(duplicates), 'segments_not_covered': int(outside.sum()),
            'outside_length_mm': outside_length,
            'first_outside_segment_mm': segments[np.flatnonzero(outside)[0]].tolist() if outside.any() else None,
            'passed': not zero.any() and duplicates == 0 and not outside.any()}


def layer_check(data, expected_area):
    rings = paths(data['part_boundary_points_mm'], data['part_boundary_offsets'])
    domain = section_domain(rings)
    contours = paths(data['part_scan_contour_points_mm'], data['part_scan_contour_offsets'])
    for contour in contours:
        if len(contour) < 4 or not np.array_equal(contour[0], contour[-1]):
            raise ValueError('Open scan contour')
    pieces = [np.stack((path[:-1], path[1:]), axis=1) for path in contours]
    contour_segments = np.concatenate(pieces) if pieces else np.empty((0, 2, 2))
    hatch = segments_check(data['part_hatch_segments_mm'], domain)
    contour = segments_check(contour_segments, domain)
    difference = float(domain.area - expected_area)
    area_pass = abs(difference) <= AREA_RELATIVE_TOLERANCE * max(1, abs(expected_area))
    return {'area_from_rings_mm2': float(domain.area), 'area_recorded_mm2': expected_area,
            'area_difference_mm2': difference, 'area_pass': area_pass, 'hatches': hatch,
            'contours': contour, 'passed': area_pass and hatch['passed'] and contour['passed']}


def audit(directory, output, indices=None):
    directory, output = Path(directory).resolve(), Path(output).resolve()
    receipt_path = directory / ('report.json' if (directory / 'report.json').is_file() else 'partial.json')
    receipt = json.loads(receipt_path.read_text())
    with (directory / 'layers.csv').open() as stream:
        areas = {int(row['layer']): float(row['part_area_mm2']) for row in csv.DictReader(stream)}
    names = sorted(name for name in receipt['outputs_sha256'] if re.fullmatch(r'layers/layer-[0-9]{5}\.npz', name))
    if indices is not None:
        wanted = set(indices)
        names = [name for name in names if int(Path(name).stem.split('-')[1]) in wanted]
        if len(names) != len(wanted):
            raise ValueError('A requested layer is absent from the source receipt')
    if not names:
        raise ValueError('No recorded layers to audit')
    source_hash, own_hash = sha(receipt_path), sha(__file__)
    output.mkdir(parents=True, exist_ok=False)
    started, rows = time.monotonic(), []
    for name in names:
        path = directory / name
        if sha(path) != receipt['outputs_sha256'][name]:
            raise ValueError('Layer identity mismatch: ' + name)
        index = int(path.stem.split('-')[1])
        if index not in areas:
            raise ValueError('Layer area absent from CSV: ' + name)
        with np.load(path, allow_pickle=False) as data:
            row = layer_check(data, areas[index])
            row.update(layer=index, z_mm=float(data['z_mm']), sha256=receipt['outputs_sha256'][name])
        rows.append(row)
    if sha(receipt_path) != source_hash or sha(__file__) != own_hash:
        raise ValueError('Receipt or audit source changed during the audit')
    complete = (receipt_path.name == 'report.json' and indices is None
                and [row['layer'] for row in rows] == list(range(receipt['n_layers'])))
    result = {'status': 'passed' if all(row['passed'] for row in rows) else 'rejected',
              'scope': 'all_recorded_part_scanpaths' if complete else 'selected_or_partial_part_scanpaths',
              'complete_build_audited': complete, 'layers_audited': len(rows), 'rows': rows,
              'input_receipt_sha256': source_hash, 'audit_source_sha256': own_hash,
              'Shapely_version': shapely.__version__, 'GEOS_version': shapely.geos_version_string,
              'criteria': {'outside_segment_count_max': 0, 'zero_segments_max': 0, 'exact_duplicates_max': 0,
                           'area_relative_tolerance': AREA_RELATIVE_TOLERANCE,
                           'area_tolerance_scope': 'Double precision reconstruction/CSV comparison only; no buffer or segment-coverage allowance.'},
              'support_scanpaths_audited': False, 'elapsed_seconds': time.monotonic() - started}
    (output / 'assessment.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--layers', type=int, nargs='+')
    args = parser.parse_args()
    report = audit(args.directory, args.output, args.layers)
    print(json.dumps({key: report[key] for key in ('status', 'scope', 'complete_build_audited', 'layers_audited')}))
    raise SystemExit(0 if report['status'] == 'passed' else 3)
