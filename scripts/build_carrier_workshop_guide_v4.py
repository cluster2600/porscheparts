"""Expose bounded mechanical findings only for the identical retained FE problem."""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import shutil

from build_part_workflow_guide import build, digest

ROOT = Path(__file__).resolve().parents[1]
BASE = Path(__file__).with_name('build_carrier_workshop_guide_v3.py')
BASE_SHA256 = 'd1e43e2b39043020829e255f0993200de942750fe108524a0ebe7706e4fe1f5c'
SOURCE_SHA256 = digest(Path(__file__))
OLD_RECIPE = 'manufacturing/workflows/993-carrier-lpbf-v3.json'
NEW_RECIPE = 'manufacturing/workflows/993-carrier-lpbf-v4.json'
CASE_ID = 'published_Flat1_NLGEOM_0125_unload'
REFERENCE_ROOT = ROOT/'parts/993-eng-carrier-0001/source/design-20261016'
REFERENCE_FILES = {
    'constitutive-results.json': (REFERENCE_ROOT/'constitutive-results.json', '8b37d9d6832cd350b90ec1be1bc2608ba22a97898b969cd71a150835c42275e8'),
    'constitutive-binding-result.json': (REFERENCE_ROOT/'constitutive-binding-result.json', 'f7b5ae477bd014d8f0556f98ccb6a72bf0d625edb00b0e5534efe1afaa02525f'),
    'luo-flat1-analysis.json': (REFERENCE_ROOT/'constitutive-evidence/luo-flat1-analysis.json', '42a37d1f736fc0ffd29c67d34caca54989f6faa8c49229f7814c4d81cdefc450'),
    'luo-flat1-finite-work.json': (REFERENCE_ROOT/'constitutive-evidence/luo-flat1-finite-work.json', 'dcb6e61829ddf09548da0c537068943ef443233fdad232d4f9abe3dec1afd46a'),
    'luo-flat1-cycle.json': (REFERENCE_ROOT/'constitutive-evidence/luo-flat1-cycle.json', '66fe96b0be4ad3ebe99a026ff4945738b10f22dcb6deea99b73760ed5dbaa6ce'),
    'luo-flat1-cycle.png': (REFERENCE_ROOT/'constitutive-evidence/luo-flat1-cycle.png', 'fd76752e49dfffdb93fdc3a4ac26faabff1992ccfca734e000435b30b508e2ae'),
}


def verify_sources():
    if digest(BASE) != BASE_SHA256 or digest(Path(__file__)) != SOURCE_SHA256:
        raise ValueError('Carrier guide sources changed')
    if any(digest(path) != expected for path, expected in REFERENCE_FILES.values()):
        raise ValueError('Retained constitutive reference changed')


verify_sources()
_spec = importlib.util.spec_from_file_location('_carrier_workshop_v4_base', BASE)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)


def reference_binding(run):
    """Inspect retained JSON/identities only; no DAT parse or solver replay."""
    verify_sources()
    read = lambda name: json.loads(REFERENCE_FILES[name][0].read_text())
    summary, binding, analysis, work, cycle = map(read, (
        'constitutive-results.json', 'constitutive-binding-result.json',
        'luo-flat1-analysis.json', 'luo-flat1-finite-work.json', 'luo-flat1-cycle.json'))
    cases = [row for row in summary['cases'] if row['id'] == CASE_ID]
    if len(cases) != 1 or binding['case_id'] != CASE_ID or binding['status'] != 'identical_discrete_reference_verified':
        raise ValueError('The retained constitutive case identity differs')
    case = cases[0]
    for name in ['luo-flat1-analysis.json', 'luo-flat1-finite-work.json']:
        if case['compact_evidence'][name] != REFERENCE_FILES[name][1]:
            raise ValueError('Constitutive compact evidence differs from its case summary')
    mesh = run/'cad/mesh-9/mesh.npz'
    deck = run/'cad/mesh-9/combined-spring-1000-static.inp'
    if digest(mesh) != binding['identical_mesh_npz_sha256'] or digest(deck) != binding['identical_reference_deck_sha256']:
        raise ValueError('Current mesh or reference deck differs from the retained sensitivity')
    if (case['raw_inputs_sha256']['mesh.npz'] != binding['identical_mesh_npz_sha256'] or
            cycle['mesh_npz_sha256'] != binding['identical_mesh_npz_sha256'] or
            summary['geometry_STEP_sha256'] != binding['source_geometry_STEP_sha256']):
        raise ValueError('Retained discrete/reference identities are inconsistent')
    if (cycle['analysis_sha256'] != REFERENCE_FILES['luo-flat1-analysis.json'][1] or
            cycle['work_audit_sha256'] != REFERENCE_FILES['luo-flat1-finite-work.json'][1] or
            cycle['outputs_sha256']['.png'] != REFERENCE_FILES['luo-flat1-cycle.png'][1] or
            work['solver_dat_sha256'] != cycle['solver_dat_sha256'] or
            work['mesh_sha256'] != cycle['mesh_sha256'] or
            analysis['inputs_sha256']['mesh.inp'] != work['mesh_sha256']):
        raise ValueError('Retained cycle/work evidence identities differ')
    times = [i/8 for i in range(1, 17)]
    factors = [min(t, 2-t) for t in times]
    for frames in [work['frames'], analysis['frames']]:
        if (len(frames) != 16 or [f['total_time'] for f in frames] != times or
                [f['load_factor'] for f in frames] != factors):
            raise ValueError('The complete sixteen-state load/unload cycle is required')
    if (work['all_frames_pass'] is not True or any(f['work_pass'] is not True for f in work['frames']) or
            binding['independent_work'] != case['independent_work'] or
            case['independent_work']['all_frames_pass'] is not True or
            case['ENER_all_frames_pass'] is not False or binding['ENER_all_frames_pass'] is not False or
            analysis['all_frames_ENER_diagnostic_pass'] is not False or
            cycle['times'] != times or cycle['load_factors'] != factors):
        raise ValueError('Retained Piola/ENER verdicts or cycle states differ')
    diagnostic = next(row for row in summary['cases'] if row['id'] == 'perfect900_small_strain_025')
    if diagnostic['constitutive_model']['true_VM_yield_MPa'] != 900:
        raise ValueError('The declared ideal diagnostic is not 900 MPa')
    return dict(schema='carrier-guide-constitutive-reference-1', case_id=CASE_ID,
        attribution='Identical FE mesh and linear reference deck; no STEP-export equivalence asserted.',
        current_STEP_sha256=digest(run/'cad/carrier.step'),
        retained_source_STEP_sha256=summary['geometry_STEP_sha256'],
        retained_binding_target_STEP_sha256=binding['current_geometry_STEP_sha256'],
        STEP_equivalence_claimed=False, identical_mesh_npz_sha256=digest(mesh),
        identical_reference_deck_sha256=digest(deck), frames_verified=16,
        independent_Piola_all_frames_pass=True, ENER_all_frames_pass=False,
        ideal_diagnostic_VM_MPa=900,
        reference_files_sha256={name: expected for name, (_, expected) in REFERENCE_FILES.items()})


def prepare_reference(run):
    binding = reference_binding(run)
    target = run/'constitutive-reference'
    target.mkdir(exist_ok=False)
    for name, (source, expected) in REFERENCE_FILES.items():
        shutil.copyfile(source, target/name)
        if digest(target/name) != expected or digest(source) != expected:
            raise ValueError('Constitutive reference changed while copying')
    (target/'current-reference-binding.json').write_text(json.dumps(binding, indent=2)+'\n')


def render(description, output):
    run = description.resolve().parent
    binding = reference_binding(run)
    folder = run/'constitutive-reference'
    if (json.loads((folder/'current-reference-binding.json').read_text()) != binding or
            any(digest(folder/name) != expected for name, (_, expected) in REFERENCE_FILES.items())):
        raise ValueError('Copied constitutive reference differs')
    data = json.loads(description.read_text())
    if data['stages'][2]['id'] != 'mechanics' or data['stages'][5]['id'] != 'delivery':
        raise ValueError('The six-stage carrier guide layout changed')
    command = data['stages'][5]['commands'][0]
    if command.split().count(OLD_RECIPE) != 1:
        raise ValueError('The v3 carrier reproduction command changed')
    comparison = json.loads((run/'comparison/comparison.json').read_text())
    matches = [row for row in comparison['cases'] if row['mesh'] == 'mesh-9' and row['case'] == 'combined-spring-1000-static']
    if len(matches) != 1:
        raise ValueError('One current K1000 mesh-9 comparison is required')
    peak = matches[0]['metrics']['integration_point_VM_max_MPa']['candidate']
    if type(peak) not in (int, float) or not math.isfinite(peak) or peak <= 0:
        raise ValueError('The current elastic K1000 peak must be finite and positive')
    state = 'dépassé' if peak > 900 else 'atteint' if peak == 900 else 'non dépassé'
    stage = data['stages'][2]
    stage['checks'] += [
        dict(label='K1000 élastique, maillage 9 mm / diagnostic idéal',
             value=f"{peak:.2f}".replace('.', ',')+' MPa ; diagnostic parfaitement plastique : 900 MPa ('+state+').'),
        dict(label='Loi de sensibilité Flat1', value='Référence publiée Grade 23 ELI ; aucune loi effective Grade 5 du carrier déduite.'),
        dict(label='Cycle chargé / déchargé — 16 états', value='Bilan Piola indépendant : PASS ; diagnostic ENER sur tous les états : REFUSÉ.')]
    labels = ['Résultats constitutifs retenus', 'Rattachement discret retenu', 'Analyse du cycle Grade 23',
              'Bilan Piola des 16 états', 'Provenance de la figure du cycle', 'Cycle Grade 23 : plasticité, résidu ×20 et chargement/décharge']
    stage['files'] += [dict(source=str((folder/name).relative_to(ROOT)), label=label)
                       for name, label in zip(REFERENCE_FILES, labels)]
    stage['files'].append(dict(source=str((folder/'current-reference-binding.json').relative_to(ROOT)),
                               label='Rattachement de ce passage au même problème discret'))
    data['stages'][5]['commands'][0] = command.replace(OLD_RECIPE, NEW_RECIPE)
    data['constitutive_reference'] = binding
    data['workshop_adapter'] = dict(source='scripts/build_carrier_workshop_guide_v4.py',
        sha256=SOURCE_SHA256, base_sha256=BASE_SHA256, retained_adapter=data.get('workshop_adapter'))
    description.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
    return build(description, output)


# Change only the generic-renderer hook of this private v3 module.
_base.build = render


def package(run):
    run = run.resolve()
    if not run.is_relative_to(ROOT/'work'):
        raise ValueError('Carrier guide runs must remain in repository work/')
    prepare_reference(run)
    result = _base.package(run)
    reference_binding(run)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    package(parser.parse_args().run)
