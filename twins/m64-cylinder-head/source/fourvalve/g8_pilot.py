#!/usr/bin/env python3
"""Bounded G7 component-compliance benchmark; not an assembled/hot strength test."""
import argparse
from collections import defaultdict
import json
import math
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / 'twins/reference-917-engine/source'))
from run_f37_carrier_calculix import parse_dat, percentile, sha256, write_set
import rocker_geometry

BASELINE = REPO / 'twins/m64-cylinder-head/evidence/g7-local-supports-cooling-20260925/native-audit.json'
E, NU = 70000., .33  # N/mm2; generic isotropic sensitivity, NOT a selected alloy/hot card.
IMAGE = 'sha256:22e5ea95954ede922b9666b74e0db1c7fdc34667abc2254ab37002ed4d90996b'


def ccx_tetra10(nodes):
    if len(nodes) != 10 or len(set(nodes)) != 10:
        raise ValueError('expected ten distinct tetrahedron nodes')
    return list(nodes[:8]) + [nodes[9], nodes[8]]


def surface_weights(triangles, points):
    """Consistent constant traction on straight-sided quadratic triangles."""
    weights = defaultdict(float)
    for tri in triangles:
        if len(tri) != 6:
            raise ValueError('expected quadratic boundary triangles')
        a, b, c = (np.array(points[int(n)]) for n in tri[:3])
        area = float(np.linalg.norm(np.cross(b-a, c-a))) / 2
        if not math.isfinite(area) or area <= 0:
            raise ValueError('degenerate surface triangle')
        # Corner shape functions integrate to zero; each edge node gets A/3.
        for n in tri[3:]:
            weights[int(n)] += area / 3
    area = sum(weights.values())
    if area <= 0:
        raise ValueError('empty load surface')
    return {n: w/area for n, w in weights.items()}, area


def vectors(path, heading):
    active, result = False, {}
    for line in path.read_text().splitlines():
        if heading in line.lower():
            active = True
            continue
        if not active or not line.strip():
            continue
        fields = line.split()
        try:
            n = int(fields[0])
            if len(fields) != 4:
                raise ValueError()
            values = tuple(map(float, fields[1:]))
        except ValueError:
            active = False
            continue
        if n in result or not all(math.isfinite(x) for x in values):
            raise ValueError('duplicate or nonfinite solver vector')
        result[n] = values
    if not result:
        raise ValueError('missing solver vectors: ' + heading)
    return result


def mesh(step, size, p, axes, component, case):
    import gmsh
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.NumThreads', 4)
        if step is None:
            gmsh.model.occ.addBox(0, 0, 0, 10, 10, 40)
            gmsh.model.occ.synchronize()
        else:
            gmsh.merge(str(step))
        if len(gmsh.model.getEntities(3)) != 1:
            raise ValueError('pilot requires one solid')
        for key, value in {'MeshSizeMin':size, 'MeshSizeMax':size,
                           'ElementOrder':2, 'SecondOrderLinear':1, 'Algorithm3D':10}.items():
            gmsh.option.setNumber('Mesh.'+key, value)
        gmsh.model.mesh.generate(3)
        nt, xyz, _ = gmsh.model.mesh.getNodes()
        points = {int(n):tuple(map(float, q)) for n, q in zip(nt, xyz.reshape(-1,3))}
        types, tags, conn = gmsh.model.mesh.getElements(3)
        if list(types) != [11]:
            raise ValueError('expected only quadratic tetrahedra')
        elements = [(int(n), ccx_tetra10([int(i) for i in row]))
                    for n, row in zip(tags[0], conn[0].reshape(-1,10))]
        ip, _ = gmsh.model.mesh.getIntegrationPoints(11, 'Gauss4')
        _, det, _ = gmsh.model.mesh.getJacobians(11, ip)
        if not np.isfinite(det).all() or min(det) <= 0:
            raise ValueError('invalid element Jacobian')
        support, zones = set(), {s:[] for s in axes}
        for _, surface in gmsh.model.getEntities(2):
            types2, _, conn2 = gmsh.model.mesh.getElements(2, surface)
            if list(types2) != [9]:
                raise ValueError('expected only quadratic boundary triangles')
            triangles = conn2[0].reshape(-1,6)
            corners = np.array([points[int(n)] for tri in triangles for n in tri[:3]])
            bottom = 0. if step is None else p['carrier_face_height']
            if np.all(np.abs(corners[:,2]-bottom) < 1e-5):
                support.update(int(n) for n in triangles.flat)
            for side, axis in axes.items():
                if step is None:
                    selected = np.all(np.abs(corners[:,2]-40) < 1e-5)
                else:
                    radius = p['rocker_pivot_radius']+p['carrier_journal_radial_clearance']
                    radial = np.hypot(corners[:,0]-axis[0], corners[:,2]-axis[2])
                    selected = (gmsh.model.getType(2,surface) == 'Cylinder'
                                and np.all(np.abs(radial-radius) < 1e-5))
                    if component == 'carrier_base_p':
                        # Only the new local rib, NOT the separate end-frame bearing.
                        selected = selected and np.max(corners[:,1]) < p['carrier_end_y']-p['carrier_wall_thickness']/2-1e-5
                if selected:
                    zones[side].extend(triangles)
        weights, areas = {}, {}
        for side, triangles in zones.items():
            weights[side], areas[side] = surface_weights(triangles, points)
            if support.intersection(weights[side]):
                raise ValueError('load and support nodes overlap')
            if step is not None:
                width = 10. if component == 'central_diaphragm' else 8.
                nominal = 2*math.pi*(p['rocker_pivot_radius']+p['carrier_journal_radial_clearance'])*width
                if not .85 < areas[side]/nominal < 1.01:
                    raise ValueError('journal surface area outside expected band')
        if len(support) < 6:
            raise ValueError('insufficient fixed-foot nodes')
        gmsh.write(str(case/'mesh.msh'))
        return points, elements, sorted(support), weights, {'size_mm':size, 'nodes':len(points),
            'elements':len(elements), 'fixed_nodes':len(support), 'surface_area_mm2':areas,
            'minimum_Gauss4_Jacobian_mm3':float(min(det)), 'gmsh_version':gmsh.__version__}
    finally:
        gmsh.finalize()


def solve(case, points, elements, support, weights, forces, direction, name):
    job = case/name
    applied = defaultdict(float)
    for side, zone in weights.items():
        for n, w in zone.items():
            applied[n] += forces[side]*w
    with job.with_suffix('.inp').open('w') as f:
        f.write('*HEADING\nG8 generic linear compliance pilot, not strength qualification\n*NODE\n')
        for n, q in sorted(points.items()):
            f.write(f'{n},'+','.join(f'{v:.12g}' for v in q)+'\n')
        f.write('*ELEMENT,TYPE=C3D10,ELSET=EALL\n')
        for n, q in elements:
            f.write(f'{n},'+','.join(map(str,q))+'\n')
        write_set(f,'NSET','NALL',sorted(points))
        write_set(f,'NSET','SUPPORT',support)
        f.write(f'*MATERIAL,NAME=GENERIC\n*ELASTIC\n{E},{NU}\n*SOLID SECTION,ELSET=EALL,MATERIAL=GENERIC\n')
        f.write('*STEP\n*STATIC\n*BOUNDARY\nSUPPORT,1,3\n*CLOAD\n')
        for n, force in sorted(applied.items()):
            for d, v in enumerate(direction,1):
                if v:
                    f.write(f'{n},{d},{force*v:.12g}\n')
        f.write('*NODE PRINT,NSET=SUPPORT\nRF\n*EL PRINT,ELSET=EALL\nS\n*NODE PRINT,NSET=NALL\nU\n*END STEP\n')
    t = time.monotonic()
    with job.with_suffix('.log').open('w') as log:
        done = subprocess.run(['ccx',name],cwd=case,stdout=log,stderr=subprocess.STDOUT,timeout=600,
                              env=dict(os.environ,OMP_NUM_THREADS='4',CCX_NPROC_STIFFNESS='4'))
    if done.returncode or '*ERROR' in job.with_suffix('.log').read_text():
        raise ValueError('CalculiX failed: '+str(job))
    dat = job.with_suffix('.dat')
    stress, displacement = parse_dat(dat)
    u, rf = vectors(dat,'displacements ('), vectors(dat,'forces (')
    if set(u) != set(points) or set(rf) != set(support):
        raise ValueError('incomplete displacement or reaction output')
    applied_vector = np.array(direction)*sum(applied.values())
    reaction = np.sum(list(rf.values()),axis=0)
    error = np.linalg.norm(reaction+applied_vector)/np.linalg.norm(applied_vector)
    moment = sum((np.cross(points[n],np.array(direction)*v) for n,v in applied.items()),np.zeros(3))
    reaction_moment = sum((np.cross(points[n],v) for n,v in rf.items()),np.zeros(3))
    moment_error = np.linalg.norm(moment+reaction_moment)/(np.linalg.norm(applied_vector)*100)
    if error > 1e-4 or moment_error > 1e-4 or not all(math.isfinite(v) for v in stress+displacement):
        raise ValueError('nonfinite result or force/moment equilibrium failed')
    return {'solver_seconds':time.monotonic()-t, 'direction':direction,
            'applied_N':applied_vector.tolist(), 'reaction_N':reaction.tolist(),
            'force_balance_relative_error':float(error), 'moment_balance_F_times_100mm_error':float(moment_error),
            'maximum_displacement_mm':max(displacement), 'von_Mises_p95_MPa':percentile(stress,.95),
            'von_Mises_max_MPa':max(stress),
            'journal_weighted_displacement_mm':{s:sum(w*np.array(u[n]) for n,w in z.items()).tolist() for s,z in weights.items()}}


def run(args):
    if sys.platform != 'linux':
        raise ValueError('resource benchmark must run on native Linux')
    sizes = [float(v) for v in args.sizes.split(',')]
    if len(sizes) < 2 or any(not math.isfinite(s) or s <= 0 for s in sizes) or any(a <= b for a,b in zip(sizes,sizes[1:])):
        raise ValueError('mesh sizes must be positive, finite and strictly decreasing')
    audit = json.loads(BASELINE.read_text())
    for name in ('central_diaphragm','carrier_base_p'):
        if sha256(args.cad/(name+'.step')) != audit['files_sha256'][name+'.step']:
            raise ValueError('G7 STEP fingerprint mismatch: '+name)
    for path, expected in audit['source_sha256'].items():
        if sha256(REPO/path) != expected:
            raise ValueError('G7 source fingerprint mismatch: '+path)
    p = audit['values']
    axes = {s:rocker_geometry.frame(p,s,1)[0] for s in ('intake','exhaust')}
    args.output.mkdir(parents=True,exist_ok=False)
    start = time.monotonic()
    results = []
    ccx = Path(shutil.which('ccx'))
    # This packaged ccx prints its version but returns 201 for -v (not a solve).
    version = subprocess.run([str(ccx),'-v'],text=True,capture_output=True)
    if 'This is Version ' not in version.stdout:
        raise ValueError('unrecognized CalculiX version output')
    report = {'classification':'G8_isolated_component_linear_compliance_resource_pilot',
              'manufacturing_authorized':False, 'engine_start_authorized':False,
              'assembled_stiffness_qualified':False, 'material_selected':False,
              'generic_material':{'E_MPa':E,'nu':NU,'temperature_C':None,'strength_allowable_MPa':None},
              'expected_image_id':IMAGE, 'image_registry_publication_verified':False,
              'ccx_sha256':sha256(ccx), 'ccx_version':version.stdout.strip(),
              'ccx_version_query_exit_code':version.returncode,
              'baseline_sha256':sha256(BASELINE), 'pilot_source_sha256':sha256(Path(__file__)),
              'helper_sha256':sha256(REPO/'twins/reference-917-engine/source/run_f37_carrier_calculix.py'),
              'cases':results}
    # ponytail: fixed feet and uniform vector traction measure component compliance only;
    # an assembled contact/preload model must replace them before journal-motion qualification.
    for component in ('witness','central_diaphragm','carrier_base_p'):
        step = None if component == 'witness' else args.cad/(component+'.step')
        field = 'centre_wall_reaction_per_bay_N' if component == 'central_diaphragm' else 'outer_rib_reaction_N'
        factor = 2 if component == 'central_diaphragm' else 1
        loads = {s:factor*max(r['G7_shaft_only'][field] for r in audit['screens']['shaft_comparison'] if r['side']==s) for s in axes}
        local_axes = axes if step else {'tip':None}
        for size in (sizes if step else [2.]):
            case = args.output/(component+'-'+str(size))
            case.mkdir()
            t = time.monotonic()
            points, elements, support, weights, info = mesh(step,size,p,local_axes,component,case)
            row = {'component':component,'mesh':info,'meshing_seconds':time.monotonic()-t,
                   'journal_forces_N':loads if step else {'tip':1000.},'solutions':{}}
            for name, direction in ([('x',[1,0,0]),('minus_z',[0,0,-1])] if step else [('x',[1,0,0])]):
                row['solutions'][name] = solve(case,points,elements,support,weights,loads if step else {'tip':1000.},direction,name)
            if not step:
                analytical = 1000*40**3/(3*E*(10**4/12)) + 1000*40/((5/6)*(E/(2*(1+NU)))*100)
                numeric = row['solutions']['x']['journal_weighted_displacement_mm']['tip'][0]
                row['beam_plus_shear_reference_mm'] = analytical
                row['reference_relative_error'] = abs(numeric/analytical-1)
                if row['reference_relative_error'] > .05:
                    raise ValueError('cantilever witness differs by over 5 percent')
            row['files_sha256'] = {f.name:sha256(f) for f in sorted(case.iterdir()) if f.is_file()}
            results.append(row)
            print(json.dumps({'completed':component,'size_mm':size,'nodes':info['nodes']}),flush=True)
            (args.output/'report.partial.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    report['wall_seconds'] = time.monotonic()-start
    report['python_peak_RSS_MiB'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
    report['maximum_child_RSS_MiB_not_sum'] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss/1024
    memory = Path('/sys/fs/cgroup/memory.peak')
    report['container_memory_peak_bytes'] = int(memory.read_text()) if memory.exists() else None
    report['complete'] = True
    (args.output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cad',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--sizes',default='3,2,1.5')
    run(parser.parse_args())
