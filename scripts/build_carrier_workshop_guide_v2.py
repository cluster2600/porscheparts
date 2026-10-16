"""Package one carrier revision only after support admission and complete scanpath audits."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import zipfile

from build_part_workflow_guide import build

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'manufacturing/workflows/993-carrier-guide.json'
ADMISSION_KEYS = ('envelopes', 'regions', 'skins', 'grids', 'contacts', 'collisions')
PROCESS_RENDERER = ROOT / 'parts/993-eng-carrier-0001/source/process-coverage-20261016/render_pyslm.py'


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def admitted_process(process_directory, process):
    if process.get('manufacturing_preparation_admitted') is not True:
        raise ValueError('Support preparation has not passed its admission criteria')
    admission = process.get('admission', {})
    checkpoint = json.loads((process_directory / 'support-stage.json').read_text())
    if checkpoint.get('admission') != admission or checkpoint.get('manufacturing_preparation_admitted') is not True:
        raise ValueError('Support checkpoint and final admission differ')
    if checkpoint['input_sha256'] != process['input_sha256']:
        raise ValueError('Support checkpoint refers to another input mesh')
    for key in ADMISSION_KEYS:
        item = admission.get(key, {})
        if item.get('status') != 'passed':
            raise ValueError('Unpassed support admission: ' + key)
        path = (process_directory / item['receipt']).resolve()
        if not path.is_relative_to(process_directory) or not path.is_file() or sha(path) != item['receipt_sha256']:
            raise ValueError('Support admission receipt identity mismatch: ' + key)
    return admission


def admitted_scanpaths(run, process):
    path = run / 'scanpath-audit/assessment.json'
    audit = json.loads(path.read_text())
    if (audit.get('status') != 'passed' or audit.get('complete_build_audited') is not True
            or audit.get('input_receipt_sha256') != sha(run / 'process/report.json')
            or audit.get('layers_audited') != process['n_layers']):
        raise ValueError('Complete scanpath audit of this exact process receipt required')
    return audit


def admitted_support_scanpaths(run, process):
    return admitted_support_receipt(run / 'support-scanpath-audit', process, sha(run / 'process/report.json'))


def admitted_support_receipt(directory, process, report_hash):
    audit = json.loads((directory / 'assessment.json').read_text())
    if (audit.get('status') != 'passed' or audit.get('complete_build_audited') is not True
            or audit.get('input_receipt_sha256') != report_hash
            or audit.get('layers_audited') != process['n_layers']
            or any(audit.get(key) is not True for key in
                   ('support_scanpaths_audited', 'geometric_confinement_passed',
                    'exposure_connectivity_passed', 'every_material_group_exposed',
                    'rational_part_contact_intersections'))):
        raise ValueError('Complete support path, geometric encoding and exposure contact audit of support paths required')
    for name, field, checks in (
            ('scanpaths/assessment.json', 'scanpath_audit_receipt_sha256',
             ('support_scanpaths_audited', 'geometric_confinement_passed', 'exposure_connectivity_passed',
              'rational_part_contact_intersections')),
            ('group-exposure-coverage.json', 'group_coverage_receipt_sha256', ('every_material_group_exposed',))):
        path = directory / name
        if not path.is_file() or sha(path) != audit.get(field):
            raise ValueError('Support path and group coverage receipt identity mismatch')
        item = json.loads(path.read_text())
        if (item.get('status') != 'passed' or item.get('complete_build_audited') is not True
                or item.get('input_receipt_sha256') != report_hash
                or item.get('layers_audited') != process['n_layers']
                or any(item.get(key) is not True for key in checks)):
            raise ValueError('Complete support path and every material group exposure are required')
    return audit


def admitted_visuals(run, process, mesh_hash):
    """Require actual render receipts; filenames alone cannot identify a figure."""
    prefix = run / ('provenance/source-workflow.json' if (run / 'assembly.json').is_file() else 'workflow.json')
    if not prefix.is_file():
        raise ValueError('Recorded CAD, dimension and field rendering provenance is required')
    if (run / 'assembly.json').is_file():
        assembly = json.loads((run / 'assembly.json').read_text())
        if assembly['source_workflow']['sha256'] != sha(prefix):
            raise ValueError('Image rendering provenance differs from the verified assembly')
    workflow = json.loads(prefix.read_text())
    images = {}
    for identity, names in (
            ('dimensions', ('dimensions/carrier-dimensions.png', 'dimensions/drawing.json')),
            ('surface-figure', ('surface-figure/carrier-remesh-comparison.png',)),
            ('fields', ('fields/combined.png', 'fields/combined.json'))):
        stages = [stage for stage in workflow['stages'] if stage['id'] == identity]
        if len(stages) != 1 or stages[0].get('status') != 'executed' or stages[0].get('returncode') != 0:
            raise ValueError('Successful recorded rendering stage required: ' + identity)
        for name in names:
            path = run / name
            if not path.is_file() or stages[0]['outputs_sha256'].get(name) != sha(path):
                raise ValueError('Guide visual differs from its recorded rendering stage: ' + name)
            if path.suffix == '.png':
                images[name] = sha(path)
    drawing = json.loads((run / 'dimensions/drawing.json').read_text())
    if drawing.get('STL_sha256') != mesh_hash or drawing.get('study_sha256') != sha(run / 'cad/study.json'):
        raise ValueError('Dimension figure uses another surface or study revision')
    fields = json.loads((run / 'fields/combined.json').read_text())
    case = 'combined-rigid-static'
    folder = run / 'cad/mesh-7'
    if fields.get('case') != case:
        raise ValueError('Mechanical figure uses another comparison case')
    for key, name in (('mesh_sha256', 'mesh.inp'), ('mesh_npz_sha256', 'mesh.npz'),
                      ('solver_deck_sha256', case + '.inp'), ('result_npz_sha256', case + '.npz'),
                      ('result_record_sha256', case + '.json')):
        if fields.get(key) != sha(folder / name):
            raise ValueError('Mechanical figure uses another retained result: ' + key)
    directory = run / 'process'
    figures_path = directory / 'figures.json'
    figures = json.loads(figures_path.read_text())
    if (figures.get('partial_witness') is not False or
            figures.get('input_receipt_sha256') != sha(directory / 'report.json') or
            figures.get('render_source_sha256') != sha(PROCESS_RENDERER)):
        raise ValueError('Complete same-process support and layer figure receipts are required')
    expected_supports = {f"support-{support['index']:03d}.npz" for support in process['supports']}
    if {path.name for path in directory.glob('support-*.npz')} != expected_supports:
        raise ValueError('Support scene contains missing or unreported support surfaces')
    for name in ('build-supports.png', 'support-teeth.png', 'layer-contours-hatches.png'):
        path = directory / name
        if not path.is_file() or figures.get('images_sha256', {}).get(name) != sha(path):
            raise ValueError('Support or layer image differs from its same-process render receipt: ' + name)
        images['process/' + name] = sha(path)
    index = figures.get('layer_index')
    if type(index) is not int or not 0 <= index < process['n_layers']:
        raise ValueError('Figure must select an actual audited layer of this process')
    layer_name = f'layers/layer-{index:05d}.npz'
    if process['outputs_sha256'].get(layer_name) != sha(directory / layer_name):
        raise ValueError('Selected layer figure uses another retained layer')
    with (directory / 'layers.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != process['n_layers'] or int(rows[index]['layer']) != index or float(rows[index]['part_area_mm2']) <= 0:
        raise ValueError('Figure must show a nonempty recorded part layer')
    return dict(prefix_workflow_sha256=sha(prefix), process_figures_sha256=sha(figures_path),
                process_report_sha256=sha(directory / 'report.json'), layer_index=index,
                layer_sha256=sha(directory / layer_name), images_sha256=images)


def package(run):
    run = run.resolve()
    if not run.is_relative_to(ROOT / 'work'):
        raise ValueError('Carrier guide runs must remain in repository work/')
    read = lambda name: json.loads((run / name).read_text())
    geometry, surface, comparison, process = map(read, ('cad/geometry.json', 'surface-audit/cad-mesh-audit.json',
                                                       'comparison/comparison.json', 'process/report.json'))
    step_hash = sha(run / 'cad/carrier.step')
    mesh_hash = sha(run / 'surface/carrier-remeshed.stl')
    if any(value != step_hash for value in (geometry['geometry_sha256']['carrier.step'],
                                            surface['STEP_sha256'], comparison['STEP_sha256'])):
        raise ValueError('Mixed STEP identities in workshop data')
    if surface['candidate_STL_sha256'] != mesh_hash or process['input_sha256'] != mesh_hash:
        raise ValueError('Mixed surface and slicing identities in workshop data')
    if (surface['status'] != 'passed' or not comparison['selection']['selection_pass']
            or process['status'] != 'open_build_preparation_completed'
            or not process['source_and_runtime_unchanged_at_completion']):
        raise ValueError('Complete accepted numerical stages required for this delivery guide')
    if (not math.isfinite(geometry['dense_reference_mass_kg'])
            or not 0 < geometry['dense_reference_mass_kg'] <= 1.30):
        raise ValueError('The requested 1.30 kg part mass ceiling must pass')
    if process.get('fits_500mm_square_plate') is not True:
        raise ValueError('The declared build plate must contain the prepared geometry')
    admission = admitted_process(run / 'process', process)
    scanpaths = admitted_scanpaths(run, process)
    admitted_support_scanpaths(run, process)
    for name, expected in process['outputs_sha256'].items():
        path = (run / 'process' / name).resolve()
        if not path.is_relative_to(run / 'process') or sha(path) != expected:
            raise ValueError('Slicing artifact identity mismatch: ' + name)
    visuals = admitted_visuals(run, process, mesh_hash)
    assets = run / 'delivery-assets'
    assets.mkdir(exist_ok=False)
    for name, selection in [('supports.zip', lambda n: n.startswith('support-')),
                            ('scanpaths.zip', lambda n: n.startswith('layers/'))]:
        with zipfile.ZipFile(assets / name, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
            for source in process['outputs_sha256']:
                if selection(source):
                    archive.write(run / 'process' / source, source)
            archive.write(run / 'process/report.json', 'report.json')
    data = json.loads(TEMPLATE.read_text())
    data['visual_provenance'] = visuals
    fr = lambda value, digits=3: f'{value:.{digits}f}'.replace('.', ',')
    case = next(row for row in comparison['cases'] if row['mesh'] == 'mesh-7' and row['case'] == 'combined-rigid-static')
    metrics = case['metrics']
    distance = max(surface['mesh_to_exact_CAD']['maximum_distance_to_STEP_shell_mm'],
                   surface['exact_CAD_to_mesh']['maximum_mm'])
    data['revision'] = geometry['design_id'] + ' / STEP ' + step_hash[:12]
    data['metrics'] = [{'value': fr(geometry['dense_reference_mass_kg']) + ' kg', 'label': 'masse dense calculée'},
                       {'value': str(surface['topology']['needle_triangles']), 'label': 'triangles aiguilles'},
                       {'value': fr(distance) + ' mm', 'label': 'écart maximal échantillonné au STEP'},
                       {'value': str(process['n_layers']), 'label': 'couches calculées intégralement'}]
    def fill(index, checks, files, image=None, commands=()):
        stage = data['stages'][index]
        stage['checks'] = [{'label': a, 'value': str(b)} for a, b in checks]
        stage['files'] = [{'source': str((run / source).relative_to(ROOT)), 'label': label} for source, label in files]
        stage['commands'] = list(commands)
        if image:
            stage['image'] = {'source': str((run / image[0]).relative_to(ROOT)), 'alt': image[1]}
    protected = read('cad/protected-interfaces.json')
    fill(0, [('Masse dense calculée', fr(geometry['dense_reference_mass_kg']) + ' kg'),
             ('Plafond demandé', fr(comparison['selection']['declared_mass_ceiling_kg'], 2) + ' kg'),
             ('Écart de volume des interfaces conservées', str(protected['central_pad_symmetric_difference_mm3']) + ' mm³')],
         [('cad/carrier.step', 'Maître STEP'), ('cad/study.json', 'Paramètres éditables'),
          ('cad/geometry.json', 'Géométrie et masse'), ('cad/protected-interfaces.json', 'Contrôle des fixations'),
          ('dimensions/drawing.json', 'Origine des cotes et de la vue')],
         ('dimensions/carrier-dimensions.png', 'Vues de la surface contrôlée et cotes des paramètres de cette révision.'))
    fill(1, [('Triangles', surface['topology']['triangles']), ('Défauts topologiques / intersections', '0 / 0'),
             ('Écart maximal échantillonné au STEP', fr(distance, 5) + ' mm'), ('Seuil conservé', '0,06 mm')],
         [('surface/carrier-remeshed.stl', 'STL contrôlé'), ('surface-audit/cad-mesh-audit.json', 'Audit de surface'),
          ('surface/meshing.json', 'Réglages de triangulation')],
         ('surface-figure/carrier-remesh-comparison.png', 'Comparaison réelle du STL brut et de la triangulation contrôlée, dans les coordonnées du maître STEP.'))
    fill(2, [('Cas combiné de comparaison', '4 000 N + 850 N·m'),
             ('Déplacement maximal, maillage 7', fr(metrics['displacement_max_mm']['candidate']) + ' mm'),
             ('Pic de von Mises, maillage 7', fr(metrics['integration_point_VM_max_MPa']['candidate'], 1) + ' MPa'),
             ('Évolution du pic par rapport à V6f', fr(metrics['integration_point_VM_max_MPa']['change_percent'], 1) + ' %'),
             ('Comparaisons rigide / ressorts, deux maillages', '4 cas admis'), ('Énergie et superposition', 'Conformes aux critères déclarés')],
         [('comparison/comparison.json', 'Comparaison mécanique complète'), ('comparison/selection.json', 'Critères et décision numérique'),
          ('cad/simulation-runtime.json', 'Solveur, ressources et nettoyage'),
          ('fields/combined.json', 'Origine du champ et de la déformée')],
         ('fields/combined.png', 'Champ de contraintes et déformée du vrai calcul. Les unités et le facteur d’amplification figurent sur la vue.'))
    fill(3, [('Rotation dans le plateau', '45° ; pièce à plat'), ('Plateau du dossier', '500 × 500 mm'),
             ('Régions de support', len(process['supports'])), ('Encombrement du plateau', 'Compatible' if process['fits_500mm_square_plate'] else 'Hors plateau')],
         [('delivery-assets/supports.zip', 'Surfaces et données des supports'), ('process/build.glb', 'Scène 3D du plateau'),
          ('process/report.json', 'Réglages et résultats de préparation'),
          ('process/support-teeth.png', 'Détail réel des dents de contact'),
          ('process/figures.json', 'Origine des vues de préparation')],
         ('process/build-supports.png', 'Pièce en bleu, supports calculés en orange et plateau gris.'))
    data['stages'][3]['checks'] += [
        {'label': 'Enveloppes, régions et peaux', 'value': 'Trois contrôles admis'},
        {'label': 'Grilles, contacts et collisions', 'value': 'Trois contrôles admis'}]
    data['stages'][3]['files'] += [
        {'source': str((run / 'process' / admission[key]['receipt']).relative_to(ROOT)),
         'label': 'Contrôle : ' + label}
        for key, label in zip(ADMISSION_KEYS, ('enveloppes', 'régions', 'peaux', 'grilles', 'contacts', 'collisions'))]
    fill(4, [('Hauteur des couches', fr(process['parameters']['layer_height_mm'] * 1000, 0) + ' µm'),
             ('Couches terminées', process['n_layers']), ('Segments de hachures pièce', process['part_hatch_segments']),
             ('Segments de supports', process['support_scan_segments']), ('Réglage laser / format machine', 'À affecter au procédé retenu')],
         [('delivery-assets/scanpaths.zip', 'Toutes les couches et trajectoires'), ('process/figures.json', 'Origine des vues')],
         ('process/layer-contours-hatches.png', 'Couche réellement calculée : sections, contours et trajectoires.'))
    data['stages'][4]['checks'] += [
        {'label': 'Couches auditées intégralement', 'value': str(scanpaths['layers_audited'])},
        {'label': 'Hachures et contours de pièce', 'value': 'Segments entiers dans les sections ; trous conservés'}]
    data['stages'][4]['files'].append({'source': str((run / 'scanpath-audit/assessment.json').relative_to(ROOT)),
                                      'label': 'Audit complet des trajectoires de pièce'})
    data['stages'][4]['checks'].append({'label': 'Trajectoires des supports',
                                      'value': 'Encodage géométrique et contacts exposés contrôlés'})
    data['stages'][4]['files'].append({'source': str((run / 'support-scanpath-audit/assessment.json').relative_to(ROOT)),
                                      'label': 'Audit complet des trajectoires et contacts des supports'})
    relative = run.relative_to(ROOT).as_posix()
    verify_command = ('python3 scripts/assemble_carrier_workflow.py verify '
                      if (run / 'assembly.json').is_file() else 'python3 scripts/run_part_workflow.py verify ')
    fill(5, [('Révision', geometry['design_id']), ('Identité du STEP', step_hash[:16] + '…'),
             ('Règle de comparaison', 'V6f, mêmes charges et appuis'), ('Consultation', 'HTML hors ligne et PDF')],
         [('guide-description.json', 'Description du dossier'), ('comparison/selection.json', 'Décision numérique')],
         commands=['python3 scripts/run_part_workflow.py run manufacturing/workflows/993-carrier-lpbf-v2.json --runtime work/part-workflow/runtime-v2.json --output work/part-workflow/NOUVEAU_PASSAGE',
                   verify_command + relative])
    descriptor = run / 'guide-description.json'
    descriptor.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    return build(descriptor, run / 'guide')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    package(parser.parse_args().run)
