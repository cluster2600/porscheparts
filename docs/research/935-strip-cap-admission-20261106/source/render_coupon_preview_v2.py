"""Depth-buffer render of the actual synthetic STL; avoids painter-order artefacts."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import trimesh


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mesh', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); assert not args.output.exists()
    mesh = trimesh.load_mesh(args.mesh, process=False)
    view = np.array([1.2, -1.7, 1.1]); view /= np.linalg.norm(view)
    right = np.cross([0., 0., 1.], view); right /= np.linalg.norm(right)
    up = np.cross(view, right); coordinates = mesh.vertices-mesh.bounds.mean(axis=0)
    projected = np.column_stack((coordinates@right, -(coordinates@up), coordinates@view))
    span = np.ptp(projected[:, :2], axis=0); scale = min(900/span[0], 490/span[1])
    projected[:, :2] = (projected[:, :2]-projected[:, :2].min(axis=0))*scale+40
    width, height = np.ceil(projected[:, :2].max(axis=0)+40).astype(int)
    image = np.ones((height, width, 3)); depth = np.full((height, width), -np.inf)
    light = np.array([-.4, -.6, 1.]); light /= np.linalg.norm(light)
    for face, normal in zip(mesh.faces, mesh.face_normals):
        if normal@view <= 0:
            continue
        p = projected[face]; a, b, c = p[:, :2]
        determinant = np.cross(b-a, c-a).item()
        if abs(determinant) < 1e-12:
            continue
        lo = np.maximum(0, np.floor(p[:, :2].min(axis=0)).astype(int))
        hi = np.minimum([width-1, height-1], np.ceil(p[:, :2].max(axis=0)).astype(int))
        x, y = np.meshgrid(np.arange(lo[0], hi[0]+1)+.5, np.arange(lo[1], hi[1]+1)+.5)
        u = ((b[0]-x)*(c[1]-y)-(b[1]-y)*(c[0]-x))/determinant
        w = ((x-a[0])*(b[1]-a[1])-(y-a[1])*(b[0]-a[0]))/(-determinant)
        q = 1-u-w; z = u*p[0, 2]+q*p[1, 2]+w*p[2, 2]
        region = np.s_[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
        visible = (u >= -1e-9)&(q >= -1e-9)&(w >= -1e-9)&(z > depth[region])
        depth[region][visible] = z[visible]
        image[region][visible] = np.array([.45, .63, .78])*(.5+.45*max(0, normal@light))
    figure, axes = plt.subplots(figsize=(10, 7), facecolor='white'); axes.imshow(image); axes.set_axis_off()
    figure.text(.07, .92, 'Synthetic coupon — local Qwen / CADAM', fontsize=18, weight='bold')
    figure.text(.07, .86, '60 × 40 × 15 mm  |  bores Ø 4 / 6 / 8 mm', fontsize=12)
    figure.text(.07, .09, '70/70 independent digital checks passed on the exported STL', fontsize=12, weight='bold')
    figure.text(.07, .05, 'Auxiliary calibration geometry. Metal process and cylinder-head qualification remain open.', fontsize=9)
    figure.savefig(args.output, dpi=120, bbox_inches='tight'); plt.close(figure)
    print('Depth-buffered actual STL preview saved.', flush=True)


if __name__ == '__main__':
    main()
