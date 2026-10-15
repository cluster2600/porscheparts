#!/usr/bin/env python3
"""Render actual witness STL sections, not a proposed head or a physics result."""
import argparse
import hashlib
import json
from pathlib import Path


def run(directory, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    from vtkmodules.vtkIOGeometry import vtkSTLReader
    from vtkmodules.vtkCommonDataModel import vtkPlane
    from vtkmodules.vtkFiltersCore import vtkCutter
    if output.exists():
        raise FileExistsError(output)
    report = json.loads((directory/'run-report.json').read_text())
    if report['schema'] != 'm64-picogk-protected-junction-witness/v1' or report['private_head_processed'] is not False:
        raise ValueError('Synthetic witness required')
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for name, color in (('before', '#596673'), ('after', '#00899b')):
        path = directory/(name+'.stl')
        if path.stat().st_size > 25_000_084 or hashlib.sha256(path.read_bytes()).hexdigest() != report['exports'][name]['sha256']:
            raise ValueError('STL hash or size mismatch')
        reader = vtkSTLReader(); reader.SetFileName(str(path)); reader.Update()
        plane = vtkPlane(); plane.SetOrigin(0,0,0); plane.SetNormal(0,0,1)
        cutter = vtkCutter(); cutter.SetCutFunction(plane); cutter.SetInputData(reader.GetOutput()); cutter.Update()
        cut = cutter.GetOutput()
        assert cut.GetNumberOfCells() > 0, 'Actual STL section must not be empty'
        lines = [[cut.GetCell(i).GetPoints().GetPoint(j)[:2] for j in range(cut.GetCell(i).GetNumberOfPoints())]
                 for i in range(cut.GetNumberOfCells())]
        for ax in axes:
            ax.add_collection(LineCollection(lines, colors=color, linewidths=1.8 if name=='after' else 3,
                                            label='Après' if name=='after' else 'Avant'))
    axes[0].set(xlim=(-11,11), ylim=(-11,11), title='Coupe Z = 0 des STL réels du témoin')
    axes[1].set(xlim=(4.5,6.5), ylim=(-1.2,.8), title='Détail du raccord — aucun lissage visuel')
    for ax in axes:
        ax.set_aspect('equal'); ax.grid(alpha=.2); ax.legend(); ax.set_xlabel('X, unité du témoin'); ax.set_ylabel('Y')
    fig.suptitle('PicoGK — mélange implicite local protégé', fontsize=16)
    fig.text(.5,.02,'Témoin logiciel synthétique, pas la culasse. Ni CFD, ni résistance, ni qualification de fabrication.',ha='center',fontsize=10)
    fig.tight_layout(rect=(0,.06,1,.93))
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160); plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.directory, args.output)
