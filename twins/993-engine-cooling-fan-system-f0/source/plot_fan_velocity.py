#!/usr/bin/env python3
"""Render an actual OpenFOAM cell-sampled plane; arrows are in-plane velocity."""
import argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from audit_fan_pressure_physicsnemo import read_patch

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('vtk', type=Path)
parser.add_argument('--title', default='Isolated rotor in an assumed test duct')
args = parser.parse_args()
points, faces, pressure = read_patch(args.vtk)
tokens = args.vtk.read_text().split()
i = tokens.index('U', tokens.index('CELL_DATA'))
if int(tokens[i+1]) != 3 or int(tokens[i+2]) != len(faces):
    raise ValueError('Expected three velocity components per sampled cell')
u = np.asarray(tokens[i+4:i+4+3*len(faces)], dtype=float).reshape(-1,3)
if not np.isfinite(u).all():
    raise ValueError('Nonfinite sampled velocity')
polygons = [points[face][:,[0,2]]*1000 for face in faces]
centres = np.array([p.mean(axis=0) for p in polygons])
speed = np.linalg.norm(u,axis=1)
fig,ax = plt.subplots(figsize=(7,8),layout='constrained')
collection = PolyCollection(polygons,array=speed,cmap='viridis',edgecolors='none',clim=(0,float(speed.max())))
ax.add_collection(collection);fig.colorbar(collection,ax=ax,label='3D speed (m/s), full sampled range')
_,selected = np.unique(np.floor(centres/14).astype(int),axis=0,return_index=True)
q=ax.quiver(centres[selected,0],centres[selected,1],u[selected,0],u[selected,2],
            color='white',angles='xy',scale_units='xy',scale=1.5,width=.0025)
ax.quiverkey(q,.86,.98,10,'10 m/s',labelpos='W',color='black',coordinates='axes')
ax.autoscale();ax.set_aspect('equal');ax.set_xlabel('x (mm)');ax.set_ylabel('z (mm)')
ax.set_title(args.title+'\nSection y = 1 mm • 3,000 rpm • exploratory result\nArrows: in-plane velocity components, not streamlines')
fig.savefig(args.vtk.with_suffix('.png'),dpi=160)
print(f'Plane rendered: {len(faces)} cells; maximum sampled speed {speed.max():.3f} m/s')
