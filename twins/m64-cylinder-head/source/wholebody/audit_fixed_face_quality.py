#!/usr/bin/env python3
"""SICN ceiling for tetrahedra retaining a fixed linear triangular face.

For triangle ideal-map singular values a,b, q2=2ab/(a*a+b*b).
The best free apex has zero shear and third singular value sqrt(ab),
giving q3 <= 3*q2/(2+q2). This is not a CAD or manufacturing certificate.
"""
import argparse
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import mesh_native_ported_head as native

MESH_SHA = '6f68a0afd2a07d163bdda07500f36727fce62768046b48abcea369bbccc89dcd'


def tetra_ceiling(triangle_quality):
    if not math.isfinite(triangle_quality) or not 0 <= triangle_quality <= 1:
        raise ValueError('triangle_quality_between_zero_and_one_required')
    return 3*triangle_quality/(2+triangle_quality)


def run(mesh, output):
    import gmsh
    if output.exists() or mesh.is_symlink() or native.sha256(mesh) != MESH_SHA:
        raise ValueError('fresh_output_and_hash_bound_reference_required')
    if gmsh.__version__ != '4.15.2': raise ValueError('qualified_gmsh_required')
    gmsh.initialize(['face-ceiling','-nopopup'],readConfigFiles=False,run=False)
    gmsh.option.setNumber('General.Terminal',0)
    try:
        gmsh.open(str(mesh))
        rows=[]
        for _, tag in gmsh.model.getEntities(2):
            types, elements, _ = gmsh.model.mesh.getElements(2,tag)
            if list(types) != [2]: raise ValueError('linear_triangles_required')
            q = list(map(float,gmsh.model.mesh.getElementQualities(elements[0],'minSICN')))
            ceilings = [tetra_ceiling(v) for v in q]
            bad = sum(v < .1 for v in ceilings)
            if bad: rows.append(dict(surface_tag=tag, incompatible_fixed_triangles=bad,
                minimum_triangle_quality=min(q), minimum_tetra_ceiling=min(ceilings)))
        rows.sort(key=lambda row:row['minimum_tetra_ceiling'])
        report = dict(schema='m64-fixed-face-sicn-ceiling/v1', mesh_sha256=MESH_SHA,
            source_sha256=native.sha256(__file__), tetra_quality_required=.1,
            necessary_triangle_quality=2*.1/(3-.1), affected_surfaces=rows,
            incompatible_fixed_triangles=sum(row['incompatible_fixed_triangles'] for row in rows),
            geometry_modified=False, mesh_input_unchanged=native.sha256(mesh)==MESH_SHA,
            exact_algebra_floating_point_inputs_not_interval_certified=True,
            scope='Fixed linear triangles only; remeshing the surface can remove this ceiling.',
            manufacturing_authorized=False)
        if not report['mesh_input_unchanged']: raise ValueError('input_changed')
        native.save(output,report)
        print({key:report[key] for key in ('incompatible_fixed_triangles','necessary_triangle_quality')})
    finally:
        gmsh.finalize()


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mesh',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    run(args.mesh,args.output)
