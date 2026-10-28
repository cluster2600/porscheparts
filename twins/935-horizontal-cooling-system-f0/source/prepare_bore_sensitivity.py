#!/usr/bin/env python3
"""Change only a pinned 935 bore node set; keep mesh, material and loads fixed."""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def replace_bore(deck, bore, tolerance, expected_nodes):
    if any(isinstance(x, bool) or not math.isfinite(x) or x <= 0 for x in (bore, tolerance)) or tolerance >= bore / 2:
        raise ValueError('Finite positive bore and bounded radial tolerance required')
    start, end = '*NSET,NSET=BORE\n', '*NSET,NSET=NALL,GENERATE\n'
    if deck.count(start) != 1 or deck.count(end) != 1 or '*ELEMENT,TYPE=C3D8,ELSET=ROTOR\n' not in deck:
        raise ValueError('One original C3D8 bore clamp and all-node set required')
    prefix, _, tail = deck.partition(start)
    _, marker, suffix = tail.partition(end)
    if not marker:
        raise ValueError('Bore node set must precede the all-node set')
    nodes = {}; active = False
    for line in prefix.splitlines():
        if line.startswith('*'):
            active = line == '*NODE'
        elif active:
            row = line.split(','); tag = int(row[0]); point = tuple(map(float, row[1:]))
            if tag in nodes or len(point) != 3 or not all(math.isfinite(x) for x in point):
                raise ValueError('Distinct nodes with three finite coordinates required')
            nodes[tag] = point
    if len(nodes) != expected_nodes or set(nodes) != set(range(1, expected_nodes + 1)):
        raise ValueError('Original complete consecutive node coverage required')
    fixed = [tag for tag, (x, y, _) in nodes.items() if abs(math.hypot(x, y) - bore) < tolerance]
    if len(fixed) < 12:
        raise ValueError('At least twelve bore nodes required')
    # shortcut: this is an artificial radial selection band, not a measured bearing or contact.
    block = '\n'.join(','.join(map(str, fixed[i:i+12])) for i in range(0, len(fixed), 12)) + '\n'
    result = prefix + start + block + end + suffix
    assert result.partition(start)[0] == prefix and result.partition(end)[2] == suffix
    radii = [math.hypot(nodes[tag][0], nodes[tag][1]) for tag in fixed]
    return result, {'clamped_bore_nodes': len(fixed), 'selected_radius_range_assumed_mm': [min(radii), max(radii)],
                    'unchanged_non_bore_text_sha256': hashlib.sha256((prefix + end + suffix).encode()).hexdigest()}


def prepare(case_path, output):
    case = json.loads(Path(case_path).read_text())
    if case['purpose'] != 'hypothesis_screen' or case['scale_verified'] is not False:
        raise ValueError('Uncalibrated hypothesis required')
    parent = Path(case['parent_prepared_path'])
    expected = case['parent_sha256']
    if set(expected) != {'receipt.json', 'case.json', 'rotor.inp'} or any(sha(parent/name) != value for name, value in expected.items()):
        raise ValueError('Pinned parent preparation required')
    receipt = json.loads((parent/'receipt.json').read_text()); original = json.loads((parent/'case.json').read_text())
    if (original['purpose'] != 'hypothesis_screen' or original['scale_verified'] is not False or
            receipt['deck_sha256'] != expected['rotor.inp'] or receipt['case_sha256'] != expected['case.json']):
        raise ValueError('Parent receipt does not match its case/deck')
    grid = ROOT / Path(original['grid_path']).relative_to('/repo')
    geometry = Path(case['rotor_path'])
    if sha(grid) != receipt['grid_sha256'] or sha(geometry) != receipt['geometry_sha256']:
        raise ValueError('Geometry or grid changed')
    tolerance = case['bore_selection_tolerance_mm']
    deck, audit = replace_bore((parent/'rotor.inp').read_text(), original['bore_radius_mm'], tolerance, receipt['nodes'])
    original.update(bore_selection_tolerance_mm=tolerance, bore_band_is_measured=False)
    out = Path(output).resolve()
    if out.exists() or not any((p/'.git').exists() and out.relative_to(p).parts[0] == 'work' for p in out.parents):
        raise ValueError('New private work directory required')
    out.mkdir(mode=0o700)
    (out/'rotor.inp').write_text(deck)
    (out/'case.json').write_text(json.dumps(original, indent=2)+'\n')
    receipt.update(audit, deck_sha256=sha(out/'rotor.inp'), case_sha256=sha(out/'case.json'),
                   parent_prepared_sha256=expected, preparation_source_sha256=sha(__file__),
                   sensitivity_case_sha256=sha(case_path), bore_selection_tolerance_mm=tolerance,
                   bore_band_is_measured=False, mesh_material_and_loads_unchanged=True,
                   physical_validation=False, scale_verified=False)
    (out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    (out/'sensitivity-case.json').write_text(json.dumps(case, indent=2)+'\n')
    if any(sha(parent/name) != value for name, value in expected.items()):
        raise ValueError('Parent changed during preparation')
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', type=Path); parser.add_argument('new_output', type=Path)
    args = parser.parse_args(); print(prepare(args.case, args.new_output))
