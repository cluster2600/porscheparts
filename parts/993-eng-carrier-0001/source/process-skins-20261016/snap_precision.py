"""Derive the finest legal CGAL snap precision and its fixed five-round bound."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np


def plan(mesh_path):
    mesh_path=Path(mesh_path).resolve();data=np.load(mesh_path,allow_pickle=False);v=np.asarray(data['vertices'])
    if v.dtype!=np.float64 or v.ndim!=2 or v.shape[1]!=3 or not np.isfinite(v).all():raise ValueError('Finite float64 XYZ input required')
    maximum=np.max(np.abs(v),axis=0);exponents=[math.frexp(float(m))[1] for m in maximum]
    gs=51;iterations=5;steps=[math.ldexp(1.,e+1-gs) for e in exponents]
    per_axis=[iterations*s/2 for s in steps];bound=iterations*math.sqrt(sum(s*s for s in steps))/2
    return dict(input_sha256=hashlib.sha256(mesh_path.read_bytes()).hexdigest(),
        snap_grid_size=gs,number_of_iterations=iterations,
        precision_authority='maximum legal grid exponent (gs < 52), minimizing displacement; upstream five-iteration budget retained',
        bbox_mm=[v.min(axis=0).tolist(),v.max(axis=0).tolist()],maximum_absolute_coordinates_mm=maximum.tolist(),
        frexp_exponents=exponents,snap_step_mm_xyz=steps,maximum_per_iteration_coordinate_displacement_mm=[s/2 for s in steps],
        cumulative_per_axis_displacement_bound_mm=per_axis,cumulative_displacement_bound_mm=bound,
        formula='step_j = 2^(frexp(max(abs(x_j))).exponent + 1 - gs); ceil(x/step-0.5)*step; at most iterations half-steps per axis',
        source='https://github.com/CGAL/cgal/blob/109ed62eeaa7e38eb383e9444700e6ff7bd4c449/Polygon_mesh_processing/include/CGAL/Polygon_mesh_processing/internal/triangle_soup_snap_rounding.h#L282',
        outcome='parameter plan only; false return, topology, contacts or drift failure remains rejected')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mesh',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    if a.output.exists():raise ValueError('Parameter plan must be new')
    r=plan(a.mesh);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
