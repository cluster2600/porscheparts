"""Repair the inherited all-water cell zone in a separate native dual-mesh candidate."""
import argparse
import json
from pathlib import Path
import re
import shutil

from prepare_restart import sha, verify


def labels(text, zone=False):
    prefix = r'cellLabels\s+List<label>\s+' if zone else r'^\s*'
    match = re.search(prefix + r'(\d+)\s*\((.*?)\)', text, re.MULTILINE | re.DOTALL)
    if not match:
        raise ValueError('Missing native ASCII label list')
    values = list(map(int, match[2].split()))
    if len(values) != int(match[1]) or any(v < 0 for v in values):
        raise ValueError('Invalid native label count or value')
    return values, match


def cell_count(mesh):
    owner, _ = labels((mesh / 'owner').read_text())
    neighbour, _ = labels((mesh / 'neighbour').read_text())
    present = set(owner) | set(neighbour)
    count = max(present) + 1
    if present != set(range(count)):
        raise ValueError('Native cell labels are not contiguous')
    note = re.search(r'nCells:(\d+)', (mesh / 'owner').read_text())
    if not note or int(note[1]) != count:
        raise ValueError('Native owner header disagrees with connectivity')
    return count


def repair(source, reference, output):
    receipt = json.loads((reference / 'mesh-report.json').read_text())
    verify(reference, receipt['source_hashes'])
    if receipt['status'] != 'mesh_numerical_gate_passed_not_physical_validation':
        raise ValueError('Missing admitted parent tetrahedral mesh')
    original = reference / 'constant/polyMesh/cellZones'
    inherited = source / 'constant/polyMesh/cellZones'
    if sha(original) != sha(inherited):
        raise ValueError('Dual zone is not the unchanged inherited parent zone')
    text = original.read_text()
    if not re.search(r'^\s*1\s*\(\s*coolant\s*\{', text, re.MULTILINE):
        raise ValueError('Expected exactly one all-water zone')
    old, match = labels(text, zone=True)
    if old != list(range(receipt['cells'])):
        raise ValueError('Original zone does not represent the entire water domain')
    count = cell_count(source / 'constant/polyMesh')
    if count == receipt['cells']:
        raise ValueError('No cell-count change observed after dual conversion')
    if output.exists():
        raise ValueError('Repair output must be a fresh directory')
    output.mkdir(parents=True)
    for name in ('constant', 'system'):
        shutil.copytree(source / name, output / name)
    shutil.copy2(reference / 'accept_mesh.py', output / 'accept_mesh.py')
    rewritten = 'cellLabels List<label>\n' + str(count) + '\n(\n' + '\n'.join(map(str, range(count))) + '\n)'
    (output / 'constant/polyMesh/cellZones').write_text(text[:match.start()] + rewritten + text[match.end():])
    unchanged = {}
    for p in sorted((source / 'constant/polyMesh').iterdir()):
        if p.is_file() and p.name != 'cellZones':
            target = output / p.relative_to(source)
            if sha(p) != sha(target):
                raise ValueError('Geometry or connectivity changed during metadata repair')
            unchanged[str(p.relative_to(source))] = sha(p)
    report = dict(status='dual_zone_metadata_repair_not_flow_validation',
        parent_tet_mesh_report_sha256=sha(reference / 'mesh-report.json'),
        rejected_dual_case_report_sha256=sha(source / 'case-report.json'),
        old_zone_sha256=sha(inherited), new_zone_sha256=sha(output / 'constant/polyMesh/cellZones'),
        old_cells=receipt['cells'], new_cells=count,
        unchanged_dual_mesh_hashes=unchanged, source_sha256=sha(Path(__file__)),
        source_helper_sha256=sha(Path(__file__).with_name('prepare_restart.py')),
        manufacturing_authorized=False)
    (output / 'case-report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'reference', 'output'): parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print(json.dumps(repair(*(p.resolve() for p in
        (args.source, args.reference, args.output))), indent=2))
