"""Render three retained support surfaces, with no geometry construction or admission."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REGIONS = ROOT/'work/carrier-process-20261016/real-support-v5-regions-001'
STORE = ROOT/'work/carrier-process-20261016/sealed-envelopes-v2-001'
INDICES = (3, 9, 10)
CHECKPOINTS = {
    3: 'f968a52e955fd621bc457d0c615d6d9039bb5dcc43cb242342308a5a4713cb74',
    9: 'c8cb26890e206dbdba7950c5ddc4ab98eadb5c1cc99baa9c01d87b178a4c5464',
    10: 'de3b6bf7be05e5caebd97cf4b82c14be242f888b272368f0e9cf60ae3439f4d1',
}
PALETTE = {3: '#0072B2', 9: '#009E73', 10: '#D55E00'}
BACKGROUND = '#f5f7f9'
VISIBLE_STATUS = '3 régions calculées / 7 ; contrôle global encore en cours'


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def identity(array):
    return dict(dtype=array.dtype.str, shape=list(array.shape),
                sha256=hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest())


def join(meshes, colors):
    cursor, faces = 0, []
    for vertices, triangles in meshes:
        faces.append(triangles+cursor)
        cursor += len(vertices)
    return (np.concatenate([m[0] for m in meshes]), np.concatenate(faces),
            np.concatenate([np.tile(matplotlib.colors.to_rgba(c), (len(m[1]), 1))
                            for m, c in zip(meshes, colors)]))


def draw(ax, pixels, proof, title):
    height, width = pixels.shape[:2]
    ax.imshow(pixels)
    ax.set_xlim(-.5, width-.5)
    ax.set_ylim(height+84, -8)
    ax.axis('off')
    bar = proof['drawn_bar_pixels']
    start = (width-bar)/2
    ax.plot([start, start+bar], [height+24]*2, color='#20364a', lw=2.7)
    ax.text(width/2, height+56, f"{proof['drawn_bar_mm']:g} mm", ha='center',
            va='center', fontsize=10, color='#20364a')
    ax.set_title(title, loc='left', fontsize=12, color='#20364a', pad=12)


def scale_for(vertices, bounds, elevation, azimuth, camera):
    right, up = camera.basis(elevation, azimuth)
    extent = 2*np.abs((vertices-bounds.mean(0)) @ np.stack([right, up], axis=1)).max(0)
    return max(extent[1], extent[0]/(2000/720))*1.10


def save(fig, output, name):
    for suffix in ('png', 'svg', 'pdf'):
        fig.savefig(output/(name+'.'+suffix), dpi=180, facecolor=fig.get_facecolor())
    plt.close(fig)


def main(review_path, review_sha):
    started = time.monotonic()
    recorded_at = datetime.now(timezone.utc).isoformat()
    output = HERE/'reference-002'
    if output.exists() or output.is_symlink():
        raise FileExistsError('The rendering output must be fresh')
    review_path = Path(review_path).resolve()
    if sha(review_path) != review_sha:
        raise ValueError('The independent local review receipt differs')
    review = json.loads(review_path.read_text())
    # The exact review contract is deliberately checked in the small local adapter.
    review_adapter = load('_local_review_adapter', HERE/'review_adapter.py')
    review_adapter.verify(review, CHECKPOINTS)
    helpers = json.loads((HERE/'source-reuse.json').read_text())['source_sha256']
    inputs = {review_path: review_sha, Path(__file__): sha(__file__),
              HERE/'review_adapter.py': sha(HERE/'review_adapter.py'),
              HERE/'source-reuse.json': sha(HERE/'source-reuse.json')}
    for name, digest in helpers.items():
        path = HERE/'sources'/name
        if sha(path) != digest:
            raise ValueError('A retained visual helper differs')
        inputs[path] = digest
    ghost = load('_calculated_surface_ghost', HERE/'sources/raster_ghost.py')
    plain = load('_calculated_surface_plain', HERE/'sources/raster_unlit.py')
    camera = load('_calculated_surface_camera', HERE/'sources/render_v4c.py')
    cache_path = ROOT/'work/carrier-process-20261016/part-layer-cache-001/report.json'
    cache = json.loads(cache_path.read_text())
    stl_path = ROOT/'work/part-workflow/run-001/surface/carrier-remeshed.stl'
    if cache['input_sha256'] != sha(stl_path):
        raise ValueError('The posed part cache and current STL differ')
    part_path = STORE/'input-part.npz'
    if sha(part_path) != '13fb2ff1f8861e48069b56b47d50ab9002d9ffafc516ce96604e0134ba8a9a3e':
        raise ValueError('The posed part NPZ differs')
    with np.load(part_path, allow_pickle=False) as data:
        part = data['vertices'].copy(), data['faces'].copy()
    if any(identity(a) != cache['part_pose_and_arrays'][name]
           for name, a in zip(['vertices', 'faces'], part)):
        raise ValueError('The posed real part arrays differ from the full part cache')
    for path in [cache_path, stl_path, part_path]:
        inputs[path] = sha(path)
    meshes, rows, mesh_types = [], [], []
    for index in INDICES:
        directory = REGIONS/f'source-{index:03d}'
        checkpoint_path = directory/'region-checkpoint.json'
        if sha(checkpoint_path) != CHECKPOINTS[index]:
            raise ValueError('The retained region checkpoint differs')
        checkpoint = json.loads(checkpoint_path.read_text())
        if (checkpoint['source_index'] != index or
                checkpoint['status'] != 'region_geometry_completed_no_global_admission' or
                not checkpoint['runtime_unchanged'] or
                checkpoint['runtime_before'] != checkpoint['runtime_after']):
            raise ValueError('The region checkpoint is incomplete')
        if checkpoint['block_identity']['part'] != {
                name: identity(array) for name, array in zip(['vertices', 'faces'], part)}:
            raise ValueError('The region input part pose differs from the rendered part')
        for name, digest in checkpoint['files_sha256'].items():
            path = directory/name
            if sha(path) != digest:
                raise ValueError('A real checkpoint output differs')
            inputs[path] = digest
        inputs[checkpoint_path] = CHECKPOINTS[index]
        with np.load(directory/'support.npz', allow_pickle=False) as data:
            vertices, faces = data['vertices'].copy(), data['faces'].copy()
            types = data['type'].copy()
            if (not np.isfinite(vertices).all() or faces.dtype.kind not in 'iu' or
                    faces.min() < 0 or faces.max() >= len(vertices) or
                    data['order'].shape != (len(faces),) or data['type'].shape != (len(faces),)):
                raise ValueError('Invalid support surface arrays')
        graph = json.loads((directory/'material-connections.json').read_text())
        actual = hashlib.sha256(vertices.tobytes()+faces.tobytes()).hexdigest()
        if (graph['status'] != 'passed' or graph['input_geometry_sha256'] != actual or
                graph['faces'] != len(faces) or not graph['components'] or
                not all(c['passed'] and c['upper_contact_group_ids'] and c['lower_contact_group_ids']
                        for c in graph['components'])):
            raise ValueError('The actual material graph does not bind these triangles')
        meshes.append((vertices, faces))
        mesh_types.append(types)
        rows.append(dict(source_index=index, source_directory=str(directory.relative_to(ROOT)),
                         checkpoint_sha256=CHECKPOINTS[index], support_sha256=inputs[directory/'support.npz'],
                         vertices=len(vertices), faces=len(faces), groups=graph['groups'],
                         material_components=len(graph['components']), graph_status=graph['status'],
                         bounds_mm=[vertices.min(0).tolist(), vertices.max(0).tolist()],
                         coordinate_transform_applied=False, all_faces_drawn=True,
                         historical_generation_label='diagnostic_generated_contacts_unproven',
                         local_checkpoint_review_passed=True, whole_build_admission=False,
                         supervisor_exit_code_read=False,
                         source010_supervisor_status=(
                             'Local geometric checkpoint and material graph PASS; supervisor exit code still awaiting collection.'
                             if index == 10 else None)))
    output.mkdir(exist_ok=False)
    view_proofs = []
    vertices, faces, colors = join([part]+meshes, ['#718093']+[PALETTE[i] for i in INDICES])
    bounds = np.array([vertices.min(0), vertices.max(0)])
    fig, axes = plt.subplots(2, 1, figsize=(16, 10), facecolor=BACKGROUND)
    for ax, el, az, title in [
        (axes[0], -67, 45, 'Vue depuis le dessous - les trois surfaces dans la pose conservée'),
        (axes[1], -19, 225, 'Vue oblique opposée - mêmes coordonnées, même géométrie')]:
        scale = scale_for(vertices, bounds, el, az, camera)
        proof = camera.calibrate(bounds.mean(0), el, az, scale, 100.)
        view_proofs.append(dict(kind='posed_overview', **proof))
        pixels = ghost.raster(vertices, faces, colors, el, az, bounds, part_faces=len(part[1]))
        draw(ax, pixels, proof, title)
    fig.suptitle('993 TURBO / SURFACES DE SUPPORTS CALCULÉES', x=.045, ha='left',
                 fontsize=22, weight='bold', color='#173249')
    fig.text(.045, .919, VISIBLE_STATUS, fontsize=14, weight='bold', color='#98600b')
    fig.legend(handles=[Patch(facecolor='#718093', alpha=.35, label='Pièce posée (translucide)')]+
               [Patch(facecolor=PALETTE[i], label=f'Région {i:03d}') for i in INDICES],
               loc='lower center', bbox_to_anchor=(.5, .059), ncol=4, frameon=False, fontsize=11)
    fig.text(.045, .034, 'Surfaces réellement générées - toutes les facettes conservées - aucune enveloppe volumique affichée',
             fontsize=10, color='#536477')
    fig.text(.045, .014, 'Repère d’impression en mm : rotation Z 45°, bas de pièce Z 10 mm, plateau Z 0 - aucune translation pour le rendu',
             fontsize=10, color='#536477')
    fig.subplots_adjust(left=.035, right=.975, top=.87, bottom=.13, hspace=.22)
    save(fig, output, 'calculated-surfaces-overview')
    fig, axes = plt.subplots(1, 3, figsize=(16, 8), width_ratios=[1, 1, 1.6], facecolor=BACKGROUND)
    for ax, index, mesh, row, types in zip(axes, INDICES, meshes, rows, mesh_types):
        v, f = mesh
        box = np.array([v.min(0), v.max(0)])
        el, az = 23, 100
        scale = scale_for(v, box, el, az, camera)
        proof = camera.calibrate(box.mean(0), el, az, scale, 10.)
        view_proofs.append(dict(kind='isolated_surface_zoom', source_index=index, **proof))
        from pyslm.support.gridBlockSupport import GridMeshType
        if [int(GridMeshType.BOUNDARY), int(GridMeshType.SLICE_X), int(GridMeshType.SLICE_Y)] != [0, 1, 2]:
            raise ValueError('The stored surface type semantics differ')
        enum_source = Path(inspect.getfile(GridMeshType))
        inputs[enum_source] = sha(enum_source)
        boundary = np.flatnonzero(types == int(GridMeshType.BOUNDARY))
        grids = np.flatnonzero(types != int(GridMeshType.BOUNDARY))
        drawing_order = np.concatenate([boundary, grids])
        if not len(boundary) or not len(grids) or not np.array_equal(np.sort(drawing_order), np.arange(len(f))):
            raise ValueError('The visual order must preserve every surface face exactly once')
        detail_colors = np.tile(matplotlib.colors.to_rgba(PALETTE[index]), (len(f), 1))
        detail_colors[types == int(GridMeshType.SLICE_Y), :3] *= .62
        pixels = ghost.raster(v, f[drawing_order], detail_colors[drawing_order], el, az, box,
                              part_faces=len(boundary))
        row['detail_visualisation'] = dict(boundary_faces=int(len(boundary)),
            grid_faces=int(len(grids)), boundary_alpha=.18, grids_opaque=True,
            all_face_indices_drawn_exactly_once=True,
            stored_coordinates_and_connectivity_unchanged=True)
        title = f'Région {index:03d}' + (' / grand détail' if index == 10 else '')
        draw(ax, pixels, proof, title)
        ax.text(.5, -.025, f"{len(f):,} facettes - {row['groups']} groupes".replace(',', ' '),
                transform=ax.transAxes, ha='center', fontsize=10, color='#536477')
        extents = box[1]-box[0]
        ax.text(.5, -.065, ('Étendue XYZ : '+ ' / '.join(f'{a:.2f}' for a in extents)+' mm').replace('.', ','),
                transform=ax.transAxes, ha='center', fontsize=8.5, color='#536477')
    fig.suptitle('GRILLES, PEAUX ET DENTS / TROIS RÉGIONS RÉELLES', x=.045, ha='left',
                 fontsize=21, weight='bold', color='#173249')
    fig.text(.045, .91, VISIBLE_STATUS, fontsize=13, weight='bold', color='#98600b')
    fig.text(.045, .066, 'Peaux translucides pour voir les grilles ; chaque face réelle est affichée une seule fois.', fontsize=11, color='#536477')
    fig.text(.045, .034, 'Deux tons pour les directions de grille - caméras seules déplacées - aucun lissage ni suppression de face.', fontsize=10, color='#536477')
    fig.text(.045, .012, 'Ces surfaces ne sont ni des enveloppes de construction, ni une admission globale des sept régions ou de leurs couches.', fontsize=10, color='#536477')
    fig.subplots_adjust(left=.035, right=.975, top=.82, bottom=.20, wspace=.16)
    save(fig, output, 'calculated-surfaces-details')
    if any(sha(path) != digest for path, digest in inputs.items()):
        raise ValueError('A source or real rendering input changed')
    from vispy.scene.cameras import TurntableCamera
    import vispy
    installed_sources = {str(Path(inspect.getfile(TurntableCamera))): sha(inspect.getfile(TurntableCamera))}
    receipt = dict(schema='calculated-support-surfaces-visual-receipt-1',
                   status='rendered_three_independently_reviewed_local_results_no_global_admission',
                   recorded_at_utc=recorded_at, source_indices=list(INDICES), visible_status=VISIBLE_STATUS,
                   local_review_receipt_sha256=review_sha, local_review_receipt_path=str(review_path),
                   source_sha256=sha(__file__), input_sha256={str(p): h for p, h in inputs.items()},
                   inputs_unchanged=True, meshes=rows, posed_part_faces=len(part[1]),
                   geometry_modified=False, faces_removed=False, regions_regenerated=False,
                   full_support_preparation_admitted=False, full_layers_generated=False,
                   scale_projection_checks=view_proofs, installed_vispy_sources_sha256=installed_sources,
                   versions={'numpy': np.__version__, 'matplotlib': matplotlib.__version__, 'vispy': vispy.__version__},
                   outputs_sha256={p.name: sha(p) for p in output.iterdir() if p.is_file()},
                   elapsed_seconds=time.monotonic()-started)
    (output/'render-receipt.json').write_text(json.dumps(receipt, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'status': receipt['status'], 'source_indices': list(INDICES),
                      'scale_checks': len(view_proofs), 'seconds': receipt['elapsed_seconds']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local-review', type=Path, required=True)
    parser.add_argument('--local-review-sha256', required=True)
    arguments = parser.parse_args()
    main(arguments.local_review, arguments.local_review_sha256)
