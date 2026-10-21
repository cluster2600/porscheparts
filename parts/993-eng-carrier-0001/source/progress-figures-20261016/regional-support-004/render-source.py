"""Draw a hash-verified completed region without implying whole-build admission."""
import argparse
import json
from pathlib import Path
import shutil
import sys

import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np

from render_carrier_progress import raster, sha

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'parts/993-eng-carrier-0001/source/process-skins-20261016'))
from region_checkpoints import PreparedRegion


def render(directory, output):
    region = PreparedRegion(directory)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    mesh, graph = region.surface, region.graph
    source = region.receipt['source_index']
    colours = np.tile([.83, .50, .19, 1.], (len(mesh.faces), 1))
    figure, axes = plt.subplots(2, 1, figsize=(15, 9), facecolor='#f5f7f9')
    axes[0].imshow(raster(mesh.vertices, mesh.faces, colours, 25, 45))
    axes[0].set_title('Vue oblique · toutes les surfaces générées', loc='left', fontsize=11, color='#243a50')
    axes[0].axis('off')
    groups = region.metadata['peripheral_skin']['support_surface_face_groups']
    group = max((g for g in groups if g['kind'] == 'grid'),
                key=lambda g:mesh.area_faces[slice(*g['face_range'])].sum())
    triangles = mesh.vertices[mesh.faces[slice(*group['face_range'])]]
    axis, plane = group['fixed_axis'], group['plane_coordinate_mm']
    if not np.all(triangles[:, :, axis] == plane):
        raise ValueError('The selected grid triangles do not lie in their recorded plane')
    axes[1].add_collection(PolyCollection(triangles[:, :, [1-axis, 2]], facecolors='#d48030', edgecolors='none'))
    axes[1].autoscale()
    axes[1].set_aspect('equal')
    axes[1].set(xlabel=f"{'Y' if axis == 0 else 'X'} (mm)", ylabel='Z (mm)')
    axes[1].grid(alpha=.15)
    axes[1].set_title(f"Une grille dans son plan réel · {'X' if axis == 0 else 'Y'} = {plane:.3f} mm",
                      loc='left', fontsize=11, color='#243a50')
    figure.suptitle(f'SUPPORTS 993 / RÉGION {source:03d}', x=.045, ha='left',
                   fontsize=22, weight='bold', color='#173249')
    figure.text(.045, .917, f"{len(mesh.faces):,} triangles · {graph['groups']} groupes · "
                f"{len(graph['components'])} composantes 3D avec les deux ancrages", fontsize=11)
    figure.text(.045, .035, 'Connectivité matérielle contrôlée · surfaces réelles, sans lissage de forme', fontsize=10)
    figure.text(.045, .012, 'Une région seule · admissions globales et audit des couches encore à exécuter',
                fontsize=9, color='#536477')
    figure.subplots_adjust(left=.075, right=.975, top=.865, bottom=.12, hspace=.25)
    path = output / 'region-material.png'
    figure.savefig(path, dpi=160, facecolor=figure.get_facecolor())
    plt.close(figure)
    region.verify()
    shutil.copyfile(__file__, output / 'render-source.py')
    receipt = dict(status='rendered_verified_region_geometry', source_index=source,
        source_sha256=sha(__file__), raster_source_sha256=sha(ROOT/'scripts/render_carrier_progress.py'),
        region_checkpoint_sha256=region.receipt_sha256,
        region_files_sha256=region.receipt['files_sha256'], images_sha256={path.name:sha(path)},
        faces=len(mesh.faces), groups=graph['groups'], material_components=len(graph['components']),
        actual_grid_group_id=group['id'], actual_grid_face_range=group['face_range'],
        region_geometry_graph_passed=True, whole_build_preparation_admitted=False)
    (output/'figures.json').write_text(json.dumps(receipt, indent=2)+'\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(json.dumps(render(args.directory, args.output)))
