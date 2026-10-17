"""Private preparation: retain guide6 gates and attach the archived32-state supplement."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_part_workflow_guide import build,digest

BASE=ROOT/'scripts/build_carrier_workshop_guide_v6.py'
BASE_SHA256='e08f443d24773876abb4d0651677ccb2d0455d54702f7396050e6654b78711aa'
CAPSULE=ROOT/'parts/993-eng-carrier-0001/source/design-20261016/constitutive-refinement-20261017'
MANIFEST_SHA256='6cb968444e7fe55c2f8b1c09a418ef47894908f5de4ed35cc5f1275015d6afc9'
SOURCE_SHA256=digest(Path(__file__))
TARGET='constitutive-reference/refinement-32'
RECEIPT='current-refinement-reference-binding.json'


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def verify_sources():
    if digest(BASE)!=BASE_SHA256 or digest(Path(__file__))!=SOURCE_SHA256:
        raise ValueError('Guide32 or frozen guide6 source changed')
    manifest=CAPSULE/'manifest.json'
    if manifest.is_symlink() or digest(manifest)!=MANIFEST_SHA256:
        raise ValueError('Refinement capsule manifest changed')
    files=json.loads(manifest.read_text())['files_sha256']
    if len(files)!=44:raise ValueError('The complete44-payload refinement capsule is required')
    for name,expected in files.items():
        relative=Path(name);path=CAPSULE/relative
        if relative.is_absolute() or '..' in relative.parts or path.is_symlink() or digest(path)!=expected:
            raise ValueError('Refinement capsule payload changed: '+name)
    return files


verify_sources()
_base=load(BASE,'_private_refinement32_guide6')
_historical=_base._base._base
_comparison=load(CAPSULE/'sources/compare.py','_private_refinement32_comparison')


def refinement_binding(run):
    """Recompare archived JSON only after the unchanged16-state attribution guard."""
    historical=_historical.reference_binding(run)
    files=verify_sources();read=lambda name:json.loads((CAPSULE/name).read_text())
    proposal=read('guide-attachment-proposal.json');required=proposal['required_bindings']
    mesh,deck=run/'cad/mesh-9/mesh.npz',run/'cad/mesh-9/combined-spring-1000-static.inp'
    old_path=run/'constitutive-reference/current-reference-binding.json'
    if (digest(mesh)!=required['current_mesh_npz_sha256'] or digest(deck)!=required['current_linear_reference_deck_sha256'] or
            historical['identical_mesh_npz_sha256']!=digest(mesh) or historical['identical_reference_deck_sha256']!=digest(deck) or
            old_path.is_symlink() or json.loads(old_path.read_text())!=historical):
        raise ValueError('Current mesh/deck or historical current-reference binding differs')
    binding=read('current-reference-binding.json')
    identities={'current_mesh_npz_sha256':digest(mesh),'current_linear_deck_sha256':digest(deck),
        'historical_16_binding_sha256':files['binding/constitutive-binding-result.json']}
    if (any(binding.get(k)!=v for k,v in identities.items()) or
            files['binding/constitutive-binding-result.json']!=required['historical_constitutive_binding_sha256'] or
            files['current-reference-binding.json']!=required['new_capsule_binding_sha256'] or
            files['baseline-16/ener.json']!=historical['reference_files_sha256']['luo-flat1-analysis.json'] or
            files['baseline-16/piola.json']!=historical['reference_files_sha256']['luo-flat1-finite-work.json'] or
            not all(binding.get(k) is True for k in ('nonlinear_deck_only_two_STATIC_increment_lines_changed',
                'baseline_and_refined_mesh_inp_byte_identical','curve_input_byte_identical','old_ENER16_rejection_retained'))):
        raise ValueError('Historical16 and refined32 discrete/material identities differ')
    changed=[line for line in (CAPSULE/'deck/deck.diff').read_text().splitlines()
             if line.startswith(('+','-')) and not line.startswith(('+++','---'))]
    if changed!=['-0.125,1,0.001,0.125','+0.0625,1,0.001,0.0625']*2:
        raise ValueError('The retained deck diff is not exactly the two STATIC increment lines')
    solver,ener_exec,piola_exec=map(read,('receipts/solver-execution.json','receipts/ENER-audit-execution.json','receipts/Piola-audit-execution.json'))
    if (solver.get('status')!='solver_executed_no_numeric_admission' or
            type(solver.get('actual_container_exit_code')) is not int or solver['actual_container_exit_code']!=0 or
            not all(solver.get(k) is True for k in ('container_removed','input_hashes_unchanged','plan_unchanged','within_global_budget')) or
            solver.get('plan_sha256')!=files['receipts/solver-supervision-plan.json']):
        raise ValueError('The refined solver execution is incomplete or unbound')
    for execution in (ener_exec,piola_exec):
        if (type(execution.get('actual_child_returncode')) is not int or execution['actual_child_returncode']!=0 or
                execution.get('timed_out') is not False or execution.get('preflight_sha256')!=files['receipts/postprocess-preflight.json']):
            raise ValueError('A refined numeric audit execution failed or is unbound')
    old_a,old_p,new_a,new_p=map(read,('baseline-16/ener.json','baseline-16/piola.json','refined-32/ener.json','refined-32/piola.json'))
    runtime,plan,supervision=map(read,('refined-32/runtime.json','refined-32/plan.json','receipts/solver-supervision-plan.json'))
    case=runtime['name'];dat=solver['outputs'][case+'.dat']['sha256']
    if (solver['runtime_json_sha256']!=files['refined-32/runtime.json'] or runtime['plan_sha256']!=files['refined-32/plan.json'] or
            runtime['status']!='executed' or runtime['owned_container_removed'] is not True or
            runtime['image']!=supervision['image'] or runtime['ccx_binary_sha256']!=supervision['binary_sha256'] or
            runtime['supervision_plan_sha256']!=solver['plan_sha256'] or
            new_a['runtime_sha256']!=files['refined-32/runtime.json'] or new_p['runtime_sha256']!=files['refined-32/runtime.json'] or
            new_a['inputs_sha256'][case+'.dat']!=dat or new_p['solver_dat_sha256']!=dat or
            new_a['inputs_sha256'][case+'.sta']!=files['refined-32/schedule.sta'] or
            new_a['inputs_sha256'][case+'.inp']!=binding['refined_nonlinear_deck_sha256'] or
            new_a['inputs_sha256']['mesh.inp']!=plan['mesh_inp_sha256'] or new_p['mesh_sha256']!=plan['mesh_inp_sha256'] or
            new_a['source_sha256']!=files['sources/analyze_plastic900.py'] or
            new_p['source_sha256']!=files['sources/audit_finite_work.py'] or new_p['field_parser_sha256']!=new_a['source_sha256'] or
            new_p['material_curve_sha256']!=files['law/flat-set-1-plastic.inp'] or
            new_a['constitutive_model']!=runtime['constitutive_model'] or runtime['constitutive_model']!=plan['plasticity']):
        raise ValueError('Refined runtime, native outputs or audit source identities differ')
    comparison=_comparison.compare_reports(old_a,old_p,new_a,new_p)
    saved=read('refined-32/comparison.json');summary=read('summary.json')
    if (any(saved.get(k)!=v for k,v in comparison.items()) or
            saved.get('bound_files_unchanged') is not True or saved.get('source_sha256')!=files['sources/compare.py'] or
            saved.get('plan_sha256')!=files['receipts/postprocess-plan.json'] or
            summary.get('comparison_sha256')!=files['refined-32/comparison.json'] or
            any(summary.get(k)!=comparison[k] for k in ('baseline_states','refined_states','baseline_checks','refined_checks','thresholds',
                'worst_ENER_relative_to_gross','worst_Piola_relative_to_gross','unloaded_residual')) or
            comparison['status']!='comparison_completed_all_refined_numeric_checks_pass' or
            comparison['baseline_checks']['ENER_all_states_pass'] is not False or
            comparison['baseline_checks']['Piola_all_states_pass'] is not True):
        raise ValueError('The complete16/32 comparison or its retained rejection differs')
    _comparison.check_frames(saved['native_schedule']['states'],32,16)
    if verify_sources()!=files:raise ValueError('Refinement capsule changed during its comparison')
    return dict(schema='carrier-guide-refinement32-reference-1',capsule_manifest_sha256=MANIFEST_SHA256,
        historical_current_reference_binding_sha256=digest(old_path),current_mesh_npz_sha256=digest(mesh),
        current_linear_reference_deck_sha256=digest(deck),files_sha256=files,frames_verified=32,
        historical_ENER16_rejection_retained=True,refined_checks=comparison['refined_checks'],
        thresholds=comparison['thresholds'],worst_ENER_relative_to_gross=comparison['worst_ENER_relative_to_gross'],
        worst_Piola_relative_to_gross=comparison['worst_Piola_relative_to_gross'],
        unloaded_residual=comparison['unloaded_residual'],DAT_or_solver_replayed=False,
        mesh_convergence_claimed=False,STEP_equivalence_claimed=False,global_admission=False)


def render(description,output):
    run=description.resolve().parent;reference=refinement_binding(run)
    target=run/TARGET
    if target.exists() or target.is_symlink():raise FileExistsError('Preserve the refinement32 supplement destination')
    target.mkdir()
    for name,expected in reference['files_sha256'].items():
        destination=target/name;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(CAPSULE/name,destination)
        if digest(destination)!=expected:raise ValueError('Copied refinement payload differs')
    shutil.copyfile(CAPSULE/'manifest.json',target/'manifest.json')
    (target/RECEIPT).write_text(json.dumps(reference,indent=2,allow_nan=False)+'\n')
    data=json.loads(description.read_text())
    if data['stages'][2]['id']!='mechanics':raise ValueError('The mechanics stage changed')
    stage=data['stages'][2]
    stage['checks'] += [dict(label='Raffinement du cycle —32 états',value='ENER et Piola : PASS aux seuils inchangés1e−3/1e−4 ; refus ENER16 conservé.'),
        dict(label='Portée du raffinement',value='Piola augmente tout en restant sous1e−4 ; résidu mesuré sans seuil ; un seul raffinement ne prouve pas une convergence de maillage.')]
    for name,label in [('summary.json','Comparaison mécanique16/32 états'),('refined-32/comparison.json','Recomparaison des états JSON'),
            ('refined-32/ener.json','Bilan ENER32 états'),('refined-32/piola.json','Bilan Piola32 états'),
            ('manifest.json','Manifeste du supplément32 états'),(RECEIPT,'Rattachement du supplément au problème discret courant')]:
        stage['files'].append(dict(source=str((target/name).relative_to(ROOT)),label=label))
    data['constitutive_refinement32']=reference
    data['workshop_adapter']=dict(source=str(Path(__file__).relative_to(ROOT)),sha256=SOURCE_SHA256,
        base_sha256=BASE_SHA256,retained_adapter=data.get('workshop_adapter'))
    description.write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    result=build(description,output)
    if (refinement_binding(run)!=reference or digest(target/'manifest.json')!=MANIFEST_SHA256 or
            any(digest(target/name)!=expected for name,expected in reference['files_sha256'].items()) or
            json.loads((target/RECEIPT).read_text())!=reference):
        raise ValueError('Refinement evidence changed during guide publication')
    return result


# Only the generic renderer of this private guide6 instance is replaced.
_base.build=render


def package(run):
    verify_sources();result=_base.package(run);verify_sources();return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run',type=Path)
    package(parser.parse_args().run)
