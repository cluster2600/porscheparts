#!/usr/bin/env python3
"""Prepare a private CAD-operator handoff for inherited nonadjacent thin patches."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('origin-report', 'attribution', 'probes', 'face-inventory'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    origin = json.loads(args.origin_report.read_text())
    attribution = json.loads(args.attribution.read_text())
    inventory = json.loads(args.face_inventory.read_text())
    for name in ('attribution', 'probes'):
        if hashlib.sha256(getattr(args, name).read_bytes()).hexdigest() != origin['source_sha256'][name]:
            raise ValueError(name+' hash mismatch')
    if inventory['source_sha256'] != origin['source_sha256']['step']:
        raise ValueError('inventory does not match candidate')
    import numpy as np
    probes = np.load(args.probes)
    faces = {row['face_id']: row for row in inventory['faces']}
    rays = {row['probe_index_private']: row for row in attribution['records_private']}
    patches = {}
    for row in origin['records_private']:
        if row['origin'] != 'inherited_envelope' or row.get('faces_share_edge') is not False:
            continue
        index = row['probe_index_private']
        ray = rays[index]
        pair = tuple(sorted((ray['entry_face_private'], ray['exit_face_private'])))
        patch = patches.setdefault(pair, {'face_pair_private': pair,
                  'faces_private': [faces[i] for i in pair], 'probes_private': []})
        point, direction = probes['points'][index], -probes['normals'][index]
        entry = point+direction*ray['entry_offset_scan_units']
        exit_point = entry+direction*ray['cad_ray_scan_units']
        patch['probes_private'].append({'index': index,
                    'entry_xyz_scan_units': entry.tolist(),
                    'exit_xyz_scan_units': exit_point.tolist(),
                    'direction': direction.tolist(),
                    'cad_ray_scan_units': ray['cad_ray_scan_units']})
    for pair, patch in patches.items():
        neighbors = sorted(set(faces[pair[0]]['adjacent_face_ids']) |
                           set(faces[pair[1]]['adjacent_face_ids']))
        patch['one_ring_faces_private'] = [faces[i] for i in neighbors]
        patch['common_neighbors_private'] = sorted(set(faces[pair[0]]['adjacent_face_ids']) &
                                                   set(faces[pair[1]]['adjacent_face_ids']))
        patch['minimum_sampled_ray_scan_units'] = min(p['cad_ray_scan_units'] for p in patch['probes_private'])
        patch['operator_proposal_not_executed'] = {
            'type': 'rebuild_local_transition_patch_not_global_offset',
            'steps': [
                'Expand paired faces through one-ring neighbors to a closed patch boundary.',
                'Classify boundary curves as retained scan-section anchors or adjustable air-channel junctions.',
                'Use BRepFill_Filling with fixed anchor curves and tangent supports; vary only unanchored junction curves inward relative to the external silhouette.',
                'Build replacement faces, then BRepTools_ReShape plus BRepBuilderAPI_Sewing and MakeSolid; do not fill functional gas/oil voids.',
                'Reject unless exact BRepCheck/BOP pass, solid count remains one, interfaces and retained contour curves are unchanged, and paired-point ray checks improve without new weak zones.',
                'Measure added/removed material, full surface deviation and air-channel area changes before CHT comparison.'
            ],
            'precondition_missing': 'No declared adjustable-vs-fixed curve set exists for these inherited transition faces.',
            'not_a_verified_working_operator': True}
    report = {'schema': 'm64-reference-local-wall-repair-handoff/v1',
              'source_sha256': origin['source_sha256'],
              'origin_report_sha256': hashlib.sha256(args.origin_report.read_bytes()).hexdigest(),
              'face_inventory_sha256': hashlib.sha256(args.face_inventory.read_bytes()).hexdigest(),
              'patches_private': list(patches.values()),
              'patch_count': len(patches), 'weak_probe_count': sum(len(p['probes_private']) for p in patches.values()),
              'source_geometry_modified': False, 'repair_executed': False,
              'classification': '935_scan_derived_reference_not_M64_interface_authority',
              'manufacturing_authorized': False}
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({key: report[key] for key in ('patch_count', 'weak_probe_count', 'repair_executed', 'manufacturing_authorized')}))


if __name__ == '__main__':
    main()
