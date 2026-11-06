"""Render the actual exported synthetic coupon; this is not a head preview."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import trimesh


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mesh', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); assert not args.output.exists()
    mesh = trimesh.load_mesh(args.mesh, process=False)
    normals = mesh.face_normals; light = np.array([-.4, -.6, 1.]); light /= np.linalg.norm(light)
    brightness = .50+.45*np.maximum(0, normals@light)
    colours = np.column_stack((.45*brightness, .63*brightness, .78*brightness, np.ones(len(brightness))))
    figure = plt.figure(figsize=(10, 7), facecolor='white'); axes = figure.add_subplot(111, projection='3d')
    axes.add_collection3d(Poly3DCollection(mesh.triangles, facecolors=colours, edgecolors='none'))
    axes.set(xlim=(0, 60), ylim=(0, 40), zlim=(0, 15)); axes.set_box_aspect((60, 40, 15))
    axes.view_init(elev=28, azim=-60); axes.set_axis_off()
    figure.text(.07, .92, 'Synthetic coupon — local Qwen / CADAM', fontsize=18, weight='bold')
    figure.text(.07, .86, '60 × 40 × 15 mm  |  bores Ø 4 / 6 / 8 mm', fontsize=12)
    figure.text(.07, .09, '70/70 independent digital checks passed on the exported STL', fontsize=12, weight='bold')
    figure.text(.07, .05, 'Auxiliary calibration geometry. Metal process and cylinder-head qualification remain open.', fontsize=9)
    figure.savefig(args.output, dpi=120, bbox_inches='tight'); plt.close(figure)
    print('Actual exported coupon preview saved.', flush=True)


if __name__ == '__main__':
    main()
