"""Render every retained region000 face from a locally hashed evidence capsule."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np

HERE = Path(__file__).resolve().parent
matplotlib.rcParams['svg.hashsalt'] = 'carrier-region000-material-20261017'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load():
    manifest = json.loads((HERE / 'inputs.json').read_text())
    for name, digest in manifest['files_sha256'].items():
        if Path(name).name != name or sha(HERE / name) != digest:
            raise ValueError('A retained rendering input differs')
    owners = json.loads((HERE / 'owners.json').read_text())
    graph = json.loads((HERE / 'material-connections.json').read_text())
    checkpoint = json.loads((HERE / 'region-checkpoint.json').read_text())
    extraction = json.loads((HERE / 'owner-extraction.json').read_text())
    refusal = json.loads((HERE / 'original-strict-refusal.json').read_text())
    with np.load(HERE / 'surface.npz', allow_pickle=False) as data:
        arrays = {name: data[name] for name in ('vertices', 'faces', 'order', 'type')}
    vertices, faces = arrays['vertices'], arrays['faces']
    if (owners['surface_sha256'] != sha(HERE / 'surface.npz') or
            checkpoint['files_sha256']['support.npz'] != owners['surface_sha256'] or
            extraction['output_sha256'] != sha(HERE / 'owners.json') or
            extraction['metadata_sha256'] != owners['metadata_sha256'] or
            extraction['files_unchanged'] is not True or
            graph['input_geometry_sha256'] != hashlib.sha256(vertices.tobytes() + faces.tobytes()).hexdigest()):
        raise ValueError('Original geometry, owner index or material graph ancestry differs')
    if (len(vertices) != 148340 or len(faces) != 171694 or len(owners['groups']) != 337 or
            graph['status'] != 'passed' or len(graph['components']) != 1 or
            graph['components'][0]['passed'] is not True or
            refusal['completed_layers'] != 0):
        raise ValueError('The original region000 evidence differs')
    colours = np.empty((len(faces), 4))
    palette = {'grid': '#c88d3c', 'skin': '#2c789b'}
    end = 0
    counts = dict(grid=0, skin=0)
    for group in owners['groups']:
        first, last = group['face_range']
        if first != end or not first < last <= len(faces):
            raise ValueError('The complete original face partition is required')
        for name in ('order', 'type'):
            if not np.all(arrays[name][first:last] == group[name]):
                raise ValueError('Owner and original scan attributes differ')
        colours[first:last] = matplotlib.colors.to_rgba(palette[group['kind']])
        counts[group['kind']] += 1
        end = last
    if end != len(faces) or counts != dict(grid=322, skin=15):
        raise ValueError('An original face or group is missing')
    return manifest, vertices, faces, colours


def render():
    manifest, vertices, faces, colours = load()
    output = HERE / 'render'
    output.mkdir(exist_ok=False)
    spec = importlib.util.spec_from_file_location('_region000_raster', HERE / 'raster.py')
    raster = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(raster)
    figure, axes = plt.subplots(2, 1, figsize=(15, 6.5), facecolor='#f5f7f9')
    for axis, elevation, azimuth, label in zip(axes, (25, 0), (45, 0),
            ('Vue oblique · toutes les surfaces', 'Vue latérale · mêmes coordonnées, sans lissage')):
        axis.imshow(raster.raster(vertices, faces, colours, elevation, azimuth))
        axis.set_title(label, loc='left', fontsize=12, color='#243a50')
        axis.axis('off')
    figure.suptitle('SUPPORTS D’IMPRESSION / ZONE 000', x=.05, ha='left',
                   fontsize=23, weight='bold', color='#173249')
    figure.text(.05, .89, '171 694 triangles réels · 337 groupes · 1 composante matérielle connectée',
                fontsize=12, color='#243a50')
    figure.legend(handles=[Patch(color='#c88d3c', label='322 grilles'),
                           Patch(color='#2c789b', label='15 peaux de support')],
                  loc='lower left', bbox_to_anchor=(.045, .076), ncol=2, frameon=False)
    figure.text(.05, .059, 'Graphe matériel : PASS. Découpage en couches : correction de triangulation en cours.',
                fontsize=11, color='#243a50')
    figure.text(.05, .033, 'Zone 000 seule · les couleurs suivent les groupes sources · affichage de tous les triangles, sans simplification.',
                fontsize=9, color='#536477')
    figure.subplots_adjust(left=.05, right=.97, top=.82, bottom=.19, hspace=.3)
    files = {}
    for suffix in ('png', 'svg', 'pdf'):
        path = output / ('carrier-supports-zone-000.' + suffix)
        metadata = {'Creator': 'Carrier evidence renderer'}
        if suffix == 'svg':
            metadata['Date'] = None
        if suffix == 'pdf':
            metadata.update(CreationDate=None, ModDate=None)
        figure.savefig(path, dpi=180, facecolor=figure.get_facecolor(),
                       metadata=metadata)
        if suffix == 'svg':
            path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines()) + '\n')
        files[path.name] = sha(path)
    plt.close(figure)
    load()
    receipt = dict(status='rendered_original_region000_all_faces', faces=len(faces),
        vertices=len(vertices), groups=337, material_graph_passed=True,
        original_strict_sections_passed=False, global_admission=False,
        input_manifest_sha256=sha(HERE / 'inputs.json'), inputs_sha256=manifest['files_sha256'],
        outputs_sha256=files)
    with (output / 'figures.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps({key: receipt[key] for key in ('status', 'faces', 'groups', 'global_admission')}))


if __name__ == '__main__':
    load() if sys.argv[1:] == ['--check'] else render()
