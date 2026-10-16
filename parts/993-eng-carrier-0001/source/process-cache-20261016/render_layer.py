"""Render an actual audited part-cache layer without adding any support geometry."""
import argparse
import importlib.util
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np

SOURCE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('layer_figure_audit', SOURCE.parent / 'process-slicing-20261016/audit_scanpaths.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def render(directory, output, index):
    directory, output = Path(directory), Path(output)
    report_path = directory / 'report.json'
    report_hash = audit.sha(report_path)
    report = json.loads(report_path.read_text())
    if report['status'] != 'part_layers_completed' or not 0 <= index < report['n_layers']:
        raise ValueError('Select a recorded layer from a completed part cache')
    name = f'layers/layer-{index:05d}.npz'
    path = directory / name
    expected = report['outputs_sha256'][name]
    if audit.sha(path) != expected:
        raise ValueError('Layer identity mismatch')
    own_hash = audit.sha(__file__)
    with np.load(path, allow_pickle=False) as data:
        result = audit.layer_check(data, float(data['part_area_mm2']))
        if not result['passed']:
            raise ValueError('Only an independently admitted part layer may be rendered')
        rings = audit.paths(data['part_boundary_points_mm'], data['part_boundary_offsets'])
        contours = audit.paths(data['part_scan_contour_points_mm'], data['part_scan_contour_offsets'])
        hatches, z = data['part_hatch_segments_mm'].copy(), float(data['z_mm'])
    if not rings:
        raise ValueError('Select a nonempty layer for this diagram')
    boundary = np.concatenate(rings)
    minimum, maximum = boundary.min(axis=0), boundary.max(axis=0)
    with plt.rc_context({'font.family': 'DejaVu Sans', 'font.size': 10, 'svg.fonttype': 'none'}):
        figure, axes = plt.subplots(1, 2, figsize=(13, 6), facecolor='#f7f5ef', layout='constrained')
        for axis in axes:
            axis.set_facecolor('#f7f5ef')
            axis.add_collection(LineCollection(rings, colors='#245b78', linewidths=.8))
            axis.set(xlim=(minimum[0]-6, maximum[0]+6), ylim=(minimum[1]-6, maximum[1]+6),
                     xlabel='X plateau (mm)', ylabel='Y plateau (mm)', aspect='equal')
            axis.grid(alpha=.15)
        axes[0].set_title('Section de la pièce · trous conservés', loc='left', weight='bold')
        axes[1].add_collection(LineCollection(hatches, colors='#c15a2b', linewidths=.25, alpha=.8))
        axes[1].add_collection(LineCollection(contours, colors='#192c38', linewidths=.55))
        axes[1].set_title('Contours et hachures réels', loc='left', weight='bold')
        figure.suptitle(f'Couche {index} / {report["n_layers"]-1} · Z = {z:.3f} mm · pièce seule',
                       fontsize=16, weight='bold', color='#192c38')
        output.mkdir(parents=True, exist_ok=False)
        for extension in ('png', 'svg'):
            figure.savefig(output / ('part-layer.' + extension), dpi=180, facecolor=figure.get_facecolor())
        plt.close(figure)
    if audit.sha(report_path) != report_hash or audit.sha(path) != expected or audit.sha(__file__) != own_hash:
        raise ValueError('Figure sources changed during rendering')
    receipt = {'scope': 'Actual part-only cache layer; no support trajectories are shown.',
               'layer': index, 'z_mm': z, 'layer_sha256': expected, 'cache_report_sha256': report_hash,
               'source_sha256': own_hash, 'independent_layer_check': result,
               'outputs_sha256': {p.name: audit.sha(p) for p in sorted(output.iterdir())}}
    (output / 'figure.json').write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cache', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--layer', type=int, required=True)
    args = parser.parse_args()
    result = render(args.cache, args.output, args.layer)
    print(json.dumps({key: result[key] for key in ('scope', 'layer', 'z_mm')}))
