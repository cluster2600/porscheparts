"""Retain compact correction evidence and hashes; large raw files stay in work/."""
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import sys

from corrected_cad import BASE, ROOT, SOURCE, sha


def read(path):
    return json.loads(path.read_text())


def retain(work):
    work = Path(work).resolve()
    selected = work/'v6f'
    destination = ROOT/'parts/993-eng-carrier-0001/derived/correction-20261013'
    media = ROOT/'parts/993-eng-carrier-0001/media/correction-20261013'
    destination.mkdir(exist_ok=True); media.mkdir(exist_ok=True)
    files = [(selected/'carrier.step', destination/'carrier.step'),
             (work/'flat/carrier-flat.step', destination/'carrier-flat.step'),
             (work/'flat/carrier-flat.glb', destination/'carrier-flat.glb'),
             (selected/'cad-views.png', media/'cad-views.png'),
             (work/'flat/flat-build.png', media/'flat-build.png'),
             (selected/'mesh-7/combined-rigid-static.png', media/'combined-rigid-static.png')]
    for source, output in files:
        shutil.copy2(source, output)
    settings = read(selected/'study.json')
    settings['design_id'] = 'carrier-correction-20261013'
    (SOURCE/'selected-study.json').write_text(json.dumps(settings, indent=2)+'\n')
    variants = []
    for path in sorted(work.glob('v6*')):
        if not path.is_dir():
            continue
        item = {'id': path.name}
        for name in ('geometry.json', 'volume-integration.json'):
            if (path/name).exists(): item[name.removesuffix('.json')] = read(path/name)
        if (path/'requested-study.json').exists():
            item['parameters'] = read(path/'requested-study.json')['geometry']
        if (path/'source-snapshot.py').exists():
            item['executed_generator_sha256'] = sha(path/'source-snapshot.py')
        result = path/'mesh-9/combined-rigid-static.json'
        if result.exists(): item['rigid_combined'] = read(result)
        item['selected_for_further_study'] = path == selected
        item['manufacturing_authorized'] = False
        variants.append(item)
    refined = {name.removesuffix('.json'): read(selected/'mesh-7'/name) for name in
               ('mesh.json','quality.json','combined-rigid-static.json','combined-spring-1000-static.json')}
    mechanical = read(selected/'mesh-9/mechanics-summary.json')
    a = mechanical['loads']['combined-rigid-static']
    b = refined['combined-rigid-static']
    r = {'date': '2026-10-13', 'status': 'geometry_corrected_structural_screen_rejected',
         'selection': 'v6f for further provisional study; no manufacturing acceptance',
         'geometry': read(selected/'geometry.json'), 'inspection': read(selected/'inspection.json'),
         'mechanics': mechanical, 'mesh_9': read(selected/'mesh-9/mesh.json'),
         'mesh_9_quality': read(selected/'mesh-9/quality.json'), 'refined_mesh_7': refined,
         'refinement': {'displacement_change_fraction': b['displacement_max_mm']/a['displacement_max_mm']-1,
                        'peak_stress_change_fraction': b['integration_point_VM_max_MPa']/a['integration_point_VM_max_MPa']-1,
                        'mesh_convergence_established': False},
         'flat_build': read(work/'flat/flat-summary.json'),
         'whole_part_print_control': read(work/'flat/whole-part-control/result.json'),
         'staged_print_distortion_corrected_or_qualified': False,
         'native': read(work/'native-run/native-results.json'),
         'native_surface_audit': read(work/'native-run/surface-audit.json'),
         'transfer': read(work/'transfer/transfer.json'),
         'variants': variants,
         'material': {'alloy_proposal': 'Ti-6Al-4V Grade 5', 'density_kg_per_mm3': 4.42e-6,
                      'elastic_modulus_MPa': 107000, 'poisson_ratio': .31,
                      'process': 'Metal LPBF, flat build; supplier and parameter set unselected',
                      'qualified_AM_allowable_MPa': None, 'heat_treatment': None,
                      'HIP_process': None, 'fatigue_SN_or_strain_life_curve': None,
                      'machining_allowance_and_mass_budget_qualified': False,
                      'inspection_plan_approved': False, 'galvanic_isolation_qualified': False},
         'runtime': {'python': platform.python_version(), 'host': platform.system()+' '+platform.machine(),
                     'packages': {name: importlib.metadata.version(name) for name in
                                  ('build123d','gmsh','numpy','scipy','trimesh','pyvista','manifold3d')},
                     'solver': 'CalculiX 2.21, Linux ARM64, one thread per solve',
                     'solver_image_id': 'sha256:c9772ae9223a4f800a3ceda77d2494e67e34c8526eb0f204b3c8e052266641b4'},
         'native_toolchain': read(ROOT/'work/carrier-leap71-20261012/toolchain.json'),
         'raw_results_root': str(work.relative_to(ROOT)),
         'raw_solver_retention': read(work/'solver-retention.json'),
         'assets_sha256': {str(p.relative_to(ROOT)): sha(p) for _,p in files},
         'source_sha256': {str(p.relative_to(SOURCE)): sha(p) for p in
                          [*sorted(SOURCE.glob('*.py')), SOURCE/'interface-study.json',
                           SOURCE/'selected-study.json', *sorted((SOURCE/'native').glob('*.*'))]
                          if p.is_file()},
         'retained_dependencies_sha256': {str(p.relative_to(ROOT)): sha(p) for p in
                                         [BASE/name for name in ('cad.py','simulate.py','slice_print.py','flat_build.py',
                                                               'print_simulation.py','render.py','native-leap71/prepare.py')]},
         'fitment_validated': False, 'strength_qualified': False, 'fatigue_life_cycles': None,
         'fatigue_qualified': False, 'manufacturing_authorized': False}
    # No extrapolation of high elastic stresses into a strength or fatigue margin.
    assert r['inspection']['study_assembly_screen_pass']
    assert r['geometry']['mass_ceiling_pass']
    assert r['native_surface_audit']['baseline']['export_accepted']
    assert not r['native_surface_audit']['candidate']['export_accepted']
    (SOURCE/'results.json').write_text(json.dumps(r, indent=2)+'\n')
    inventory = []
    for p in sorted(work.rglob('*')):
        if p.is_file() and p.name != 'inventory.json':
            inventory.append({'path': str(p.relative_to(work)), 'bytes': p.stat().st_size, 'sha256': sha(p)})
    (work/'inventory.json').write_text(json.dumps(inventory, indent=2)+'\n')
    (SOURCE/'raw-inventory.json').write_bytes((work/'inventory.json').read_bytes())
    print(json.dumps({'retained_assets': len(files), 'raw_files': len(inventory),
                      'raw_bytes': sum(i['bytes'] for i in inventory), 'status': r['status']}))


if __name__ == '__main__':
    retain(sys.argv[1])
