"""Render the actual two-face section at the audited carrier crease."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Fresh output required')
    report = json.loads(args.audit.read_text())
    import hashlib
    if hashlib.sha256(args.input.read_bytes()).hexdigest() != report['input_sha256']:
        raise ValueError('Audited geometry required')
    with np.load(args.input, allow_pickle=False) as data:
        v, f = data['vertices'], data['triangles']
    record = report['most_reentrant_edges'][0]
    edge = np.asarray(record['vertices'])
    ids = np.flatnonzero(np.isin(f, edge).sum(axis=1) == 2)
    if len(ids) != 2:
        raise ValueError('Two incident faces required')
    triangles = v[f[ids]]
    origin = v[edge].mean(axis=0)
    axis = v[edge[1]] - v[edge[0]]
    axis /= np.linalg.norm(axis)
    endpoints = []
    for triangle in triangles:
        local = triangle - origin
        axial = local @ axis
        crossings = []
        for i, j in [(0, 1), (1, 2), (2, 0)]:
            if axial[i] * axial[j] < 0:
                crossings.append(local[i] - axial[i] / (axial[j] - axial[i]) * (local[j] - local[i]))
            elif axial[i] == 0:
                crossings.append(local[i])
        if not crossings:
            raise ValueError('Section does not cross triangle')
        endpoints.append(max(crossings, key=np.linalg.norm))
    endpoints = np.array(endpoints)
    radial = np.sum(endpoints / np.linalg.norm(endpoints, axis=1)[:, None], axis=0)
    radial /= np.linalg.norm(radial)
    transverse = np.cross(axis, radial)
    sections = np.column_stack([endpoints @ radial, endpoints @ transverse])
    fig = plt.figure(figsize=(12, 5.5), facecolor='#f6f7f9')
    ax = fig.add_subplot(121, projection='3d')
    colours = ['#287a8d', '#d67835']
    for triangle, colour in zip(triangles, colours):
        local = triangle - origin
        ax.add_collection3d(Poly3DCollection([local], facecolor=colour, edgecolor=colour, alpha=.65))
        normal = np.cross(local[1] - local[0], local[2] - local[0])
        normal /= np.linalg.norm(normal)
        point = local.mean(axis=0)
        ax.quiver(*point, *(normal * .04), color=colour)
    limit = float(np.abs(triangles - origin).max()) * 1.15
    ax.set(xlim=(-limit, limit), ylim=(-limit, limit), zlim=(-limit, limit),
           xlabel='x (mm)', ylabel='y (mm)', zlabel='z (mm)', title='Actual incident faces and outward normals')
    ax.set_box_aspect([1, 1, 1])
    bx = fig.add_subplot(122)
    for section, colour in zip(sections, colours):
        bx.plot([0, section[0] * 1e3], [0, section[1] * 1e6], color=colour, linewidth=2)
    bx.set(xlabel='Distance from edge along bisector (µm)',
           ylabel='Transverse distance (nm)', title='Actual edge-normal section: different axis units')
    bx.grid(alpha=.2)
    fig.suptitle('993 carrier | Nearly closed reentrant crease', fontsize=18, x=.06, ha='left')
    fig.text(.06, .03, f"Normal turn: {record['normal_turn_degrees']:.8f}° · Edge length: {record['length_mm']:.6f} mm\n"
             'Diagnostic of the frozen nominal surface. This figure does not prove a continuum stress singularity.', fontsize=9)
    fig.subplots_adjust(left=.06, right=.97, bottom=.22, top=.82, wspace=.35)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__ == '__main__':
    main()
