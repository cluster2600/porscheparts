"""Prepare the unchanged published sensitivity for a new export of the same discrete carrier."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

from run_part_workflow import sha, write

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / 'parts/993-eng-carrier-0001/source/design-20261016'


def mesh_without_heading(path):
    kept, drop = [], False
    for line in path.read_text().splitlines(keepends=True):
        if line.strip().upper() == '*HEADING':
            drop = True
            continue
        if drop and line.startswith('*') and not line.startswith('**'):
            drop = False
        if not drop:
            kept.append(line)
    return ''.join(kept).encode()


def prepare(run, output):
    run, output = Path(run).resolve(), Path(output).resolve()
    template_path = DESIGN / 'luo-flat1-nlgeom-plan.json'
    witness_path = DESIGN / 'constitutive-evidence/constitutive-binding-independent-002.json'
    template, witness = [json.loads(path.read_text()) for path in (template_path, witness_path)]
    geometry = json.loads((run / 'cad/geometry.json').read_text())
    comparison = json.loads((run / 'comparison/comparison.json').read_text())
    mass = geometry['dense_reference_mass_kg']
    if not comparison['selection']['selection_pass'] or not math.isfinite(mass) or not 0 < mass <= 1.30:
        raise ValueError('The retained carrier comparison and 1.30 kg ceiling must pass')
    mesh = run / 'cad/mesh-9'
    canonical = hashlib.sha256(mesh_without_heading(mesh / 'mesh.inp')).hexdigest()
    if (sha(mesh / 'mesh.npz') != witness['mesh_NPZ_sha256']
            or canonical != witness['mesh_INP_after_only_heading_removal_sha256']
            or sha(mesh / 'combined-spring-1000-static.inp') != witness['reference_deck_sha256']
            or template['reference_deck_sha256'] != witness['reference_deck_sha256']):
        raise ValueError('Only the identical mesh, load deck and fixture may reuse this frozen constitutive plan')
    step_hash = sha(run / 'cad/carrier.step')
    if step_hash != geometry['geometry_sha256']['carrier.step']:
        raise ValueError('Current STEP identity mismatch')
    plan = copy.deepcopy(template)
    plan.update(frozen_at_UTC=datetime.now(timezone.utc).isoformat(), geometry_STEP_sha256=step_hash,
                mesh_inp_sha256=sha(mesh / 'mesh.inp'))
    changed = [key for key in template if template[key] != plan[key]]
    if set(changed) - {'frozen_at_UTC', 'geometry_STEP_sha256', 'mesh_inp_sha256'}:
        raise ValueError('Constitutive conditions changed while rebinding metadata')
    output.mkdir(parents=True, exist_ok=False)
    write(output / 'plan.json', plan)
    receipt = {'status': 'plan_prepared_no_solver_execution',
               'scope': 'Fresh export/heading identities for the exact same discrete problem; material, loads, springs, increments, unloading and criteria unchanged.',
               'changed_fields': changed, 'template_sha256': sha(template_path),
               'independent_witness_sha256': sha(witness_path), 'source_sha256': sha(__file__),
               'mesh_INP_without_heading_sha256': canonical, 'plan_sha256': sha(output / 'plan.json')}
    write(output / 'binding.json', receipt)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.run, args.output)))
