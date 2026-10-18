"""Render actual C3D10 integration-point stresses and displacements without nodal extrapolation."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib.collections import PolyCollection
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'parts/993-eng-carrier-0001/source/bionic-20261011'))
from simulate import elements


def boundary_values(faces, connectivity, element_ids, vm):
    values = {}
    unique, reverse = np.unique(element_ids, return_inverse=True)
    peaks = np.full(len(unique), -np.inf)
    np.maximum.at(peaks, reverse, vm)
    assert set(unique) == set(connectivity)
    wanted = {tuple(sorted(face)) for face in faces}
    for element, peak in zip(unique, peaks):
        nodes = connectivity[int(element)]
        for indices in ((0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)):
            key = tuple(sorted(nodes[index] for index in indices))
            if key in wanted:
                if key in values:
                    raise ValueError('Declared surface face is internal to two elements')
                values[key] = peak
    result = np.asarray([values[tuple(sorted(face))] for face in faces])
    assert np.isfinite(result).all()
    return result


def camera_basis(azimuth_deg=8, elevation_deg=22):
    azimuth, elevation = np.radians([azimuth_deg, elevation_deg])
    horizontal = np.array([np.cos(azimuth), np.sin(azimuth), 0.])
    vertical = np.array([-np.sin(azimuth) * np.sin(elevation),
                         np.cos(azimuth) * np.sin(elevation), np.cos(elevation)])
    return np.vstack((horizontal, vertical, np.cross(horizontal, vertical)))


def project(points, basis):
    coordinates = np.asarray(points) @ basis.T
    return coordinates[:, :2], coordinates[:, 2]


def render(folder, case, output, context=None):
    if any(output.with_suffix(suffix).exists() for suffix in ('.png', '.svg', '.json')):
        raise FileExistsError('Preserve previous field figures')
    record = json.loads((folder / (case + '.json')).read_text())
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    if record['mesh_sha256'] != sha(folder / 'mesh.inp') or record['input_sha256'] != sha(folder / (case + '.inp')):
        raise ValueError('Solver input identity mismatch')
    with np.load(folder / 'mesh.npz', allow_pickle=False) as mesh, \
         np.load(folder / (case + '.npz'), allow_pickle=False) as field:
        tags, xyz, faces = mesh['tags'], mesh['xyz'], mesh['faces']
        assert np.array_equal(tags, field['tags']) and np.array_equal(xyz, field['xyz'])
        displacement, vm = field['displacement'], field['VM']
        assert np.isfinite(displacement).all() and np.isfinite(vm).all()
        assert abs(vm.max() - record['integration_point_VM_max_MPa']) < 1e-8
        stress = boundary_values(faces, elements(folder / 'mesh.inp'), field['element_ids'], vm)
    indices = np.searchsorted(tags, faces)
    assert np.array_equal(tags[indices], faces)
    amplitude = np.linalg.norm(displacement, axis=1)
    assert abs(amplitude.max() - record['displacement_max_mm']) < 1e-8
    factor = 10
    basis = camera_basis()
    rest, _ = project(xyz, basis)
    deformed, _ = project(xyz + factor * displacement, basis)
    all_points = np.vstack((rest, deformed))
    lower, upper = all_points.min(0), all_points.max(0)
    padding = np.array([8., 6.])
    figure, axes = plt.subplots(2, 2, figsize=(15, 6.8), facecolor='white',
                               gridspec_kw={'width_ratios': [1, .018], 'wspace': .035})
    for row, (points, values, label, title) in enumerate([
        (xyz, stress, 'von Mises (MPa)', 'Contraintes : maximum des quatre points d’intégration de chaque élément'),
        (xyz + factor * displacement, amplitude[indices].max(1), '|u| réel (mm)', f'Déformée amplifiée ×{factor} ; couleur = déplacement réel')]):
        ax = axes[row, 0]
        norm = colors.Normalize(vmin=0, vmax=float(vm.max() if row == 0 else amplitude.max()))
        cmap = plt.get_cmap('viridis')
        projected, depth = project(points, basis)
        order = np.argsort(depth[indices].mean(1), kind='stable')
        if row:
            ax.add_collection(PolyCollection(rest[indices], facecolors='#e4e7eb', edgecolors='none', rasterized=True))
        ax.add_collection(PolyCollection(projected[indices][order], facecolors=cmap(norm(values[order])),
                                         edgecolors='none', rasterized=True))
        ax.set(xlim=(lower[0] - padding[0], upper[0] + padding[0]),
               ylim=(lower[1] - padding[1], upper[1] + padding[1]),
               xlabel='U projeté (mm)', ylabel='V projeté (mm)', title=title)
        ax.set_aspect('equal', adjustable='box')
        ax.grid(alpha=.15); ax.set_axisbelow(True)
        ax.tick_params(labelsize=8)
        bar = figure.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=axes[row, 1])
        bar.set_label(label)
    context = context or (folder.parent.name + ' / ' + folder.name + ' — calcul d’étude')
    figure.suptitle('Support 993 — ' + case, fontsize=18, weight='bold', y=.98)
    figure.text(.5, .925, context, ha='center', fontsize=10, color='#4a4a4a')
    figure.text(.5, .025, f"Pic IP : {vm.max():.2f} MPa · Déplacement maximal : {amplitude.max():.4f} mm · Maillage {sha(folder / 'mesh.inp')[:12]}…\nProjection orthographique 8° / 22° ; même échelle dans les deux vues. Gris : silhouette au repos.\nContraintes constantes par élément, sans extrapolation aux nœuds ; couleurs de déplacement non amplifiées.", ha='center', fontsize=10)
    figure.subplots_adjust(left=.055, right=.935, bottom=.20, top=.85, hspace=.43)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=180)
    figure.savefig(output.with_suffix('.svg'))
    plt.close(figure)
    output.with_suffix('.json').write_text(json.dumps({'case': case, 'mesh_sha256': sha(folder / 'mesh.inp'),
          'result_npz_sha256': sha(folder / (case + '.npz')), 'solver_deck_sha256': record['input_sha256'],
          'mesh_npz_sha256': sha(folder / 'mesh.npz'), 'result_record_sha256': sha(folder / (case + '.json')),
          'plot_source_sha256': sha(Path(__file__)), 'stress': 'maximum integration-point von Mises per boundary element',
          'context': context, 'camera_basis_U_V_depth': basis.tolist(), 'projection': 'orthographic, equal metric axes',
          'face_draw_order': 'ascending mean camera depth, back to front',
          'integration_point_VM_max_MPa': float(vm.max()), 'maximum_displayed_boundary_element_VM_MPa': float(stress.max()),
          'deformation_amplification': factor, 'displacement_colours': 'actual magnitude in mm'}, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('case')
    parser.add_argument('output', type=Path)
    parser.add_argument('--context', help='Study context to display verbatim on the figure')
    args = parser.parse_args()
    render(args.folder, args.case, args.output, args.context)
