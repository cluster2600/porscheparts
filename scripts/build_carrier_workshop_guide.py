"""Package one completed carrier run without mixing its geometry and calculation revisions."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from build_part_workflow_guide import build

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'manufacturing/workflows/993-carrier-guide.json'


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


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
    for name, expected in process['outputs_sha256'].items():
        path = (run / 'process' / name).resolve()
        if not path.is_relative_to(run / 'process') or sha(path) != expected:
            raise ValueError('Slicing artifact identity mismatch: ' + name)
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
          ('cad/geometry.json', 'Géométrie et masse'), ('cad/protected-interfaces.json', 'Contrôle des fixations')],
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
          ('cad/simulation-runtime.json', 'Solveur, ressources et nettoyage')],
         ('fields/combined.png', 'Champ de contraintes et déformée du vrai calcul. Les unités et le facteur d’amplification figurent sur la vue.'))
    fill(3, [('Rotation dans le plateau', '45° ; pièce à plat'), ('Plateau du dossier', '500 × 500 mm'),
             ('Régions de support', len(process['supports'])), ('Encombrement du plateau', 'Compatible' if process['fits_500mm_square_plate'] else 'Hors plateau')],
         [('delivery-assets/supports.zip', 'Surfaces et données des supports'), ('process/build.glb', 'Scène 3D du plateau'),
          ('process/report.json', 'Réglages et résultats de préparation')],
         ('process/build-supports.png', 'Pièce en bleu, supports calculés en orange et plateau gris.'))
    fill(4, [('Hauteur des couches', fr(process['parameters']['layer_height_mm'] * 1000, 0) + ' µm'),
             ('Couches terminées', process['n_layers']), ('Segments de hachures pièce', process['part_hatch_segments']),
             ('Segments de supports', process['support_scan_segments']), ('Réglage laser / format machine', 'À affecter au procédé retenu')],
         [('delivery-assets/scanpaths.zip', 'Toutes les couches et trajectoires'), ('process/figures.json', 'Origine des vues')],
         ('process/layer-contours-hatches.png', 'Couche réellement calculée : sections, contours et trajectoires.'))
    relative = run.relative_to(ROOT).as_posix()
    fill(5, [('Révision', geometry['design_id']), ('Identité du STEP', step_hash[:16] + '…'),
             ('Règle de comparaison', 'V6f, mêmes charges et appuis'), ('Consultation', 'HTML hors ligne et PDF')],
         [('guide-description.json', 'Description du dossier'), ('comparison/selection.json', 'Décision numérique')],
         commands=['python3 scripts/run_part_workflow.py run manufacturing/workflows/993-carrier.json --runtime work/part-workflow/runtime.json --output work/part-workflow/NOUVEAU_PASSAGE',
                   'python3 scripts/run_part_workflow.py verify ' + relative])
    descriptor = run / 'guide-description.json'
    descriptor.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    return build(descriptor, run / 'guide')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    package(parser.parse_args().run)
