"""Reuse a constitutive sensitivity only for its exact mesh and linear reference deck."""
import argparse
import json
from pathlib import Path
import shutil

from run_part_workflow import inside, sha, write

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / 'parts/993-eng-carrier-0001/source/design-20261016'
CASE = 'published_Flat1_NLGEOM_0125_unload'


def bind(cad, output):
    cad, output = Path(cad).resolve(), Path(output).resolve()
    summary_path = DESIGN / 'constitutive-results.json'
    summary = json.loads(summary_path.read_text())
    case = next(item for item in summary['cases'] if item['id'] == CASE)
    original = inside(ROOT, case['retained_folder'])
    frozen = {summary_path: sha(summary_path), Path(__file__): sha(__file__)}
    for name, expected in case['raw_inputs_sha256'].items():
        path = inside(original, name)
        if not path.is_file() or sha(path) != expected:
            raise ValueError('Retained constitutive evidence identity mismatch: ' + name)
        frozen[path] = expected
    plan = json.loads((original / 'plan.json').read_text())
    mesh_hash = sha(cad / 'mesh-9/mesh.npz')
    deck_hash = sha(cad / 'mesh-9/combined-spring-1000-static.inp')
    if mesh_hash != case['raw_inputs_sha256']['mesh.npz']:
        raise ValueError('Constitutive reuse requires an identical discrete mesh')
    if deck_hash != plan['reference_deck_sha256'] or deck_hash != sha(original / 'reference-linear.inp'):
        raise ValueError('Constitutive reuse requires the identical linear deck, loads and fixture')
    for path in (cad / 'mesh-9/mesh.npz', cad / 'mesh-9/combined-spring-1000-static.inp',
                 original / 'reference-linear.inp', cad / 'geometry.json', cad / 'carrier.step'):
        frozen[path] = sha(path)
    geometry = json.loads((cad / 'geometry.json').read_text())
    if frozen[cad / 'carrier.step'] != geometry['geometry_sha256']['carrier.step']:
        raise ValueError('Current CAD export identity mismatch')
    evidence = DESIGN / 'constitutive-evidence'
    copied = {}
    for name, expected in case['compact_evidence'].items():
        path = inside(evidence, name)
        if sha(path) != expected:
            raise ValueError('Compact constitutive evidence identity mismatch: ' + name)
        frozen[path] = expected
        copied[name] = path
    work = json.loads((evidence / 'luo-flat1-finite-work.json').read_text())
    if (work.get('all_frames_pass') is not True or not isinstance(work.get('frames'), list)
            or len(work['frames']) != 16
            or work['solver_dat_sha256'] != case['raw_inputs_sha256']['combined-spring-1000-luo-flat1-NLGEOM.dat']
            or not case['unloading_complete'] or not case['within_measured_pre_necking_domain']):
        raise ValueError('The complete admitted sixteen-state work audit must match this solve')
    copied['constitutive-results.json'] = summary_path
    if output.exists():
        raise FileExistsError('Use a fresh constitutive binding directory')
    output.mkdir(parents=True, exist_ok=False)
    for name, source in copied.items():
        shutil.copyfile(source, output / name)
        if sha(output / name) != frozen[source]:
            raise ValueError('Constitutive evidence changed during copying')
    if any(sha(path) != expected for path, expected in frozen.items()):
        raise ValueError('Constitutive binding sources changed during verification')
    receipt = {'status': 'identical_discrete_reference_verified', 'case_id': CASE,
               'scope': 'Reuse of an existing constitutive sensitivity for the exact same finite-element mesh, linear reference deck, loads and springs. No new solve and no equivalence of STEP exports is claimed.',
               'source_geometry_STEP_sha256': summary['geometry_STEP_sha256'],
               'current_geometry_STEP_sha256': frozen[cad / 'carrier.step'],
               'identical_mesh_npz_sha256': mesh_hash, 'identical_reference_deck_sha256': deck_hash,
               'material_model': case['constitutive_model'], 'unloaded_residual': case['unloaded_residual'],
               'independent_work': case['independent_work'], 'ENER_all_frames_pass': case['ENER_all_frames_pass'],
               'retained_original_folder': case['retained_folder'],
               'inputs_sha256': {str(path): expected for path, expected in frozen.items()},
               'outputs_sha256': {name: sha(output / name) for name in copied}}
    write(output / 'binding.json', receipt)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cad', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = bind(args.cad, args.output)
    print(json.dumps({key: result[key] for key in ('status', 'identical_mesh_npz_sha256', 'identical_reference_deck_sha256')}))
