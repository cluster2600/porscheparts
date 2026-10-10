"""Vérifie les dix facettes témoins de 008 dans le classement 009, sans modifier les STL."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import math

BASE = Path(__file__).resolve().parent
OLD = BASE / 'baseline-surface-008'
NEW = BASE / 'baseline-surface-009'
OUT = BASE / 'rotor-label-witnesses-009.json'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def vertex_lines(witness):
    return tuple(('vertex ' + ' '.join(format(v / 1000, '.12g') for v in point)).encode('ascii')
                 for point in witness['vertices_mm'])


def main():
    assert not OUT.exists(), 'refuse_overwrite'
    old = json.loads((OLD / 'surface-report.json').read_text())
    new = json.loads((NEW / 'surface-report.json').read_text())
    diagnostic = json.loads((BASE / 'rotor-label-diagnostic-008.json').read_text())
    witnesses = diagnostic['ten_farthest']
    wanted = {vertex_lines(w): w for w in witnesses}
    assert len(wanted) == 10
    first_lines = {key[0] for key in wanted}
    counts = Counter()
    found = []
    region = None
    candidate = []
    h = hashlib.sha256()
    with (NEW / 'fluid-regions.stl').open('rb') as stream:
        for line in stream:
            h.update(line)
            stripped = line.strip()
            if stripped.startswith(b'solid '):
                region = stripped[6:].decode('ascii')
            elif stripped.startswith(b'facet normal '):
                counts[region] += 1
                candidate = []
            elif stripped.startswith(b'vertex '):
                if candidate or stripped in first_lines:
                    candidate.append(stripped)
                    if len(candidate) == 3:
                        w = wanted.get(tuple(candidate))
                        if w:
                            center = w['center_mm']
                            a = math.hypot(*center[:2]) - new['construction']['rear_seal_radius_mm']
                            b = max(center[2] + 3.75, -100 - center[2])
                            seal_distance = abs(math.hypot(max(a, 0), max(b, 0)) + min(max(a, b), 0))
                            found.append({'rank': w['rank'], 'old_rotor_patch_face_index': w['rotor_patch_face_index'],
                                          'new_patch': region, 'new_patch_face_index': counts[region] - 1,
                                          'vertices_serialized_identically': True, 'center_mm': center,
                                          'radius_mm': w['radius_mm'], 'rotor_distance_mm_from_008': w['rotor_distance_mm'],
                                          'housing_distance_mm_from_008': w['housing_distance_mm'],
                                          'fixed_seal_exact_distance_mm': seal_distance})
    assert h.hexdigest() == new['surface_sha256'], 'new_surface_hash_mismatch'
    assert dict(counts) == new['classification']['face_counts'], 'new_patch_count_mismatch'
    assert len(found) == 10 and {w['rank'] for w in found} == set(range(1, 11)), 'witnesses_not_found_once_each'
    assert all(w['new_patch'] == 'stator' for w in found), 'witness_not_fixed'
    assert old['sources'] == new['sources'], 'geometry_sources_changed'
    assert old['source_facet_count'] == new['source_facet_count'] == sum(counts.values())
    delta = {k: counts[k] - old['classification']['face_counts'][k] for k in counts}
    assert delta['rotor'] == -new['classification']['fixed_seal_faces_nearer_rotor_than_housing']
    report = {'status': 'passed', 'mesh_modified': False, 'labels_modified_by_diagnostic': False,
              'scope': 'Ten existing geometric witnesses and all new patch counts; no distance field recomputation',
              'script_sha256': sha(Path(__file__)), 'input_sha256': {
                  'old_surface_report': sha(OLD / 'surface-report.json'),
                  'new_surface_report': sha(NEW / 'surface-report.json'),
                  'old_witness_receipt': sha(BASE / 'rotor-label-diagnostic-008.json'),
                  'new_ascii_surface': h.hexdigest()},
              'identical_geometry_source_hashes': new['sources'], 'source_facet_count': sum(counts.values()),
              'new_face_counts': dict(counts), 'face_count_delta_009_minus_008': delta,
              'fixed_seal_faces_reclassified_from_rotor': new['classification']['fixed_seal_faces_nearer_rotor_than_housing'],
              'maximum_rotor_distance_mm_old': old['classification']['maximum_rotor_distance_mm'],
              'maximum_rotor_distance_mm_new': new['classification']['maximum_rotor_distance_mm'],
              'ten_witnesses': sorted(found, key=lambda w: w['rank']),
              'limitations': ['Unchanged geometry inferred from exact input hashes and report retention assertion; ten witness facet coordinates independently matched byte for byte after serialization.',
                              'Read-only classification QA, not volume mesh, motion or physical validation.']}
    with OUT.open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('ten_witnesses', 'limitations', 'input_sha256', 'identical_geometry_source_hashes')}, indent=2))


if __name__ == '__main__':
    main()
