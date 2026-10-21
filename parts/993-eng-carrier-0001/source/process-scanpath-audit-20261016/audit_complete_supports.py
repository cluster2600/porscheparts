"""Mandatory complete support-path audit plus actual exposure of every group."""
import argparse
from functools import lru_cache
import json
from pathlib import Path
import shutil
import time

import numpy as np

import audit_support_scanpaths as base

BASE_SHA256 = '4ace9f24b61fa8f2d514f18d2e3eb6e9794983d6dee41fad4a8f44dc1f4c53ef'


def group_witness(vertices, faces, group, heights, actual_segments):
    """A whole group between sampling planes must not silently disappear."""
    for face in range(*group['face_range']):
        triangle = vertices[faces[face]]
        lower, upper = triangle[:, 2].min(), triangle[:, 2].max()
        candidates = np.flatnonzero((heights >= lower) & (heights <= upper))
        for layer in candidates:
            cut = base.triangle_section(triangle, heights[layer])
            if cut is not None:
                encoded = base.encode(cut)
                if encoded in actual_segments(int(layer)):
                    return dict(group_id=group['id'], passed=True, source_face=face,
                        layer=int(layer), z_mm=float(heights[layer]), vector_mm=encoded)
    return dict(group_id=group['id'], passed=False,
                reason='No actual exposure represents this material group on any recorded layer')


def audit(directory, output, source_stl, part_cache=None):
    directory, output = Path(directory).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('Complete support audit output directory must be new')
    own = base.sha(__file__)
    if base.sha(base.__file__) != BASE_SHA256:
        raise ValueError('Mandatory base support audit identity changed')
    receipt_path = directory/'report.json'
    process_sha = base.sha(receipt_path)
    report = json.loads(receipt_path.read_text())
    output.mkdir(parents=True)
    started = time.monotonic()
    measured = base.audit(directory, output/'scanpaths', source_stl, part_cache)
    if measured['input_receipt_sha256'] != process_sha or base.sha(receipt_path) != process_sha:
        raise ValueError('Process identity changed across mandatory path audit')
    rows, inputs = [], {receipt_path: process_sha}
    heights = np.asarray([(i+.5)*report['parameters']['layer_height_mm'] for i in range(report['n_layers'])])

    @lru_cache(maxsize=8)
    def actual_segments(layer):
        name = f'layers/layer-{layer:05d}.npz'
        path = base.verified_file(directory, name, report['outputs_sha256'][name])
        inputs[path] = report['outputs_sha256'][name]
        with np.load(path, allow_pickle=False) as data:
            if float(data['z_mm']) != heights[layer]:
                raise ValueError('Group exposure witness uses another layer height')
            return {base.canonical(tuple(tuple(float(c) for c in p) for p in segment))
                    for segment in data['support_scan_segments_mm']}

    if measured['status'] == 'passed':
        for support in report['supports']:
            name = f"support-{support['index']:03d}.npz"
            path = base.verified_file(directory, name, report['outputs_sha256'][name])
            inputs[path] = report['outputs_sha256'][name]
            with np.load(path, allow_pickle=False) as data:
                vertices, faces = data['vertices'], data['faces']
            for group in support['peripheral_skin']['support_surface_face_groups']:
                row = group_witness(vertices, faces, group, heights, actual_segments)
                rows.append(dict(row, region=support['index'], support_mesh_sha256=inputs[path]))
    coverage_pass = bool(rows) and all(row['passed'] for row in rows)
    coverage = dict(status='passed' if coverage_pass else 'rejected',
        scope='Every admitted material face group must have an actual recorded exposure',
        input_receipt_sha256=process_sha, groups_checked=len(rows),
        layers_audited=measured['layers_audited'], complete_build_audited=measured['complete_build_audited'],
        every_material_group_exposed=coverage_pass,
        complete_schedule_authority='Mandatory complete scanpath audit in scanpaths/assessment.json',
        unique_group_witness_layers_read=sum(path.parent.name == 'layers' for path in inputs),
        groups_without_exposure=sum(not row['passed'] for row in rows),
        skipped_due_to_rejected_base_audit=measured['status'] != 'passed', rows=rows,
        source_sha256=own)
    coverage_path = output/'group-exposure-coverage.json'
    coverage_path.write_text(json.dumps(coverage, indent=2, allow_nan=False)+'\n')
    passed = measured['status'] == 'passed' and coverage_pass
    if (base.sha(__file__) != own or base.sha(base.__file__) != BASE_SHA256 or
            any(base.sha(path) != expected for path, expected in inputs.items())):
        raise ValueError('Sources or exposure witness inputs changed during the complete audit')
    shutil.copy2(__file__, output/Path(__file__).name)
    result = dict(schema='carrier-complete-support-exposure-audit-v1',
        status='passed' if passed else 'rejected', complete_build_audited=measured['complete_build_audited'],
        input_receipt_sha256=process_sha, layers_audited=measured['layers_audited'],
        support_scanpaths_audited=True, part_scanpaths_audited=False,
        geometric_confinement_passed=measured['geometric_confinement_passed'],
        exposure_connectivity_passed=measured['exposure_connectivity_passed'],
        every_material_group_exposed=coverage_pass,
        support_scan_segments=measured['support_scan_segments'],
        scanpath_audit_receipt='scanpaths/assessment.json',
        scanpath_audit_receipt_sha256=base.sha(output/'scanpaths/assessment.json'),
        group_coverage_receipt=coverage_path.name, group_coverage_receipt_sha256=base.sha(coverage_path),
        base_audit_source_sha256=BASE_SHA256, audit_source_sha256=own,
        elapsed_seconds=time.monotonic()-started)
    (output/'assessment.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--source-stl', type=Path, required=True)
    parser.add_argument('--part-cache', type=Path)
    args = parser.parse_args()
    result = audit(args.directory, args.output, args.source_stl, args.part_cache)
    print(json.dumps({key: result[key] for key in ('status', 'every_material_group_exposed', 'layers_audited')}))
    raise SystemExit(0 if result['status'] == 'passed' else 3)
