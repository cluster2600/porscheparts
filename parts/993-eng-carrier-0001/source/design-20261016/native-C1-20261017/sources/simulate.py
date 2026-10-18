"""Mesh and solve the authorised provisional study with Gmsh and CalculiX.

The six-component bore load transfer is an equivalent fixture, not a bolt/contact
model. Rigid or distributed-spring end supports are sensitivity cases.
"""
import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

import numpy as np

DOCKER = '/usr/local/bin/docker'
CONTAINER = os.environ.get('CARRIER_STUDY_CONTAINER', 'carrier-bionic-native-20261012')


def mesh(folder, size):
    import gmsh
    out = folder / f'mesh-{size:g}'
    out.mkdir(exist_ok=False)
    g = json.loads((folder / 'study.json').read_text())['geometry']
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal', 0)
        gmsh.option.setNumber('General.NumThreads', 1)
        gmsh.model.occ.importShapes(str(folder / 'carrier.step'))
        gmsh.model.occ.synchronize()
        volumes = gmsh.model.getEntities(3)
        assert len(volumes) == 1
        gmsh.model.addPhysicalGroup(3, [volumes[0][1]], name='BODY')
        gmsh.option.setNumber('Mesh.MeshSizeMin', 2)
        gmsh.option.setNumber('Mesh.MeshSizeMax', 8)
        gmsh.option.setNumber('Mesh.MeshSizeFromCurvature', 18)
        gmsh.option.setNumber('Mesh.MeshSizeFactor', size/8)
        gmsh.option.setNumber('Mesh.ElementOrder', 2)
        # Straight midsides avoid inverted curved elements at small OCC blends;
        # geometry error is reported and checked through mesh refinement.
        gmsh.option.setNumber('Mesh.SecondOrderLinear', 1)
        gmsh.option.setNumber('Mesh.SaveAll', 0)
        gmsh.model.mesh.generate(3)
        types, elements, _ = gmsh.model.mesh.getElements(3)
        assert list(types) == [11], types
        jac = gmsh.model.mesh.getElementQualities(elements[0], 'minDetJac')
        quality = {'minimum_Jacobian': float(min(jac)),
                   'nonpositive_elements': int(np.count_nonzero(jac <= 0)),
                   'finite': bool(np.isfinite(jac).all()), 'elements': len(jac)}
        (out/'quality.json').write_text(json.dumps(quality, indent=2)+'\n')
        assert np.isfinite(jac).all() and min(jac) > 0
        tags, xyz, _ = gmsh.model.mesh.getNodes()
        order = np.argsort(tags); tags = tags[order]; xyz = xyz.reshape(-1, 3)[order]
        faces = []
        for kind, _, conn in zip(*gmsh.model.mesh.getElements(2)):
            assert kind == 9
            faces.extend(conn.reshape(-1, 6)[:, :3])
        groups = {**{f'bolt{i}': [] for i in range(4)}, **{f'end{i}': [] for i in range(2)}}
        for _, face in gmsh.model.getEntities(2):
            if gmsh.model.getType(2, face) != 'Cylinder':
                continue
            lo, hi = gmsh.model.getParametrizationBounds(2, face)
            p = gmsh.model.getValue(2, face, (lo+hi)/2)
            names = []
            for i, (x, y) in enumerate(g['central_bolt_centres_xy_mm']):
                if abs(np.hypot(p[0]-x, p[1]-y)-g['central_bore_radius_mm']) < 1e-5:
                    names.append(f'bolt{i}')
            for i, x in enumerate(g['end_centres_x_mm']):
                if abs(np.hypot(p[0]-x, p[2])-g['end_bore_radius_mm']) < 1e-5:
                    names.append(f'end{i}')
            assert len(names) <= 1
            for name in names:
                groups[name].extend(gmsh.model.mesh.getNodes(2, face, includeBoundary=True)[0])
        groups = {k: np.unique(v).astype(int) for k, v in groups.items()}
        assert min(map(len, groups.values())) >= 12
        assert len(set(np.concatenate(list(groups.values())))) == sum(map(len, groups.values()))
        gmsh.write(str(out / 'mesh.inp'))
        np.savez_compressed(out / 'mesh.npz', tags=tags, xyz=xyz,
                            faces=np.asarray(faces), **groups)
        mesh_volume = float(gmsh.model.mesh.getElementQualities(elements[0], 'volume').sum())
        cad_volume = json.loads((folder/'geometry.json').read_text())['volume_mm3']
        meta = {'nodes': len(tags), 'C3D10_elements': len(elements[0]),
                'minimum_sampled_Jacobian': float(min(jac)),
                'bore_node_counts': {k: len(v) for k, v in groups.items()},
                'gmsh_version': gmsh.__version__, 'element_order': 2, 'straight_midsides': True,
                'global_mesh_size_factor': size/8,
                'mesh_volume_mm3': mesh_volume, 'volume_relative_error': mesh_volume/cad_volume-1,
                'STEP_sha256': hashlib.sha256((folder/'carrier.step').read_bytes()).hexdigest()}
        (out/'mesh.json').write_text(json.dumps(meta, indent=2)+'\n')
        print(json.dumps(meta), flush=True)
    finally:
        gmsh.finalize()
    return out


def distribute(xyz, groups, force, moment):
    """Minimum weighted norm nodal forces with exact force and moment resultants."""
    # shortcut: equivalent bore loads omit joint contact; replace with measured joints before design acceptance.
    weights = np.zeros(len(xyz))
    for group in groups:
        weights[group] = 1 / (len(groups) * len(group))
    ids = np.flatnonzero(weights)
    r = xyz[ids] / 100
    A = np.zeros((len(ids), 3, 6)); A[:, :, :3] = np.eye(3)
    for i, (x, y, z) in enumerate(r):
        A[i, :, 3:] = [[0, z, -y], [-z, 0, x], [y, -x, 0]]
    K = np.einsum('n,nij,nik->jk', weights[ids], A, A)
    assert np.linalg.matrix_rank(K) == 6
    target = np.r_[force, np.asarray(moment)/100]
    f = np.zeros_like(xyz)
    f[ids] = weights[ids, None] * np.einsum('nij,j->ni', A, np.linalg.solve(K, target))
    assert np.max(abs(f.sum(0)-force)) < 1e-8
    assert np.max(abs(np.cross(xyz, f).sum(0)-moment)) < 1e-6
    return f


def parse_dat(path):
    """Read only numeric rows in the requested CalculiX print blocks."""
    fields = {'displacements': [], 'forces': [], 'stresses': []}
    current = None
    for line in path.read_text().splitlines():
        line = line.strip()
        for name in fields:
            if line.startswith(name + ' ('):
                current = name
                fields[name] = []
        row = line.split()
        n = 8 if current == 'stresses' else 4
        if current and len(row) == n and row[0].isdigit():
            fields[current].append([float(v.replace('D', 'E')) for v in row])
    return {k: np.asarray(v) for k, v in fields.items()}


def von_mises(tensor):
    sx, sy, sz, xy, xz, yz = tensor.T
    return np.sqrt(((sx-sy)**2+(sy-sz)**2+(sz-sx)**2)/2+3*(xy*xy+xz*xz+yz*yz))


def eigenvalues(text, procedure):
    marker = ('E I G E N V A L U E   O U T P U T' if procedure == 'modal'
              else 'B U C K L I N G   F A C T O R   O U T P U T')
    rows = []
    for line in text.split(marker, 1)[1].splitlines():
        fields = line.split()
        if len(fields) == (5 if procedure == 'modal' else 2) and fields[0].isdigit():
            rows.append([float(v.replace('D', 'E')) for v in fields])
        elif rows and fields:
            break
    assert rows and np.isfinite(rows).all()
    return np.asarray(rows)


def elements(path):
    result = {}; active = False
    for line in path.read_text().splitlines():
        if line.startswith('*'):
            active = line.upper().startswith('*ELEMENT')
        elif active and line.strip():
            row = [int(v) for v in line.split(',') if v.strip()]
            assert len(row) == 11
            result[row[0]] = row[1:]
    return result


def nset(name, ids):
    ids = list(map(int, ids))
    return [f'*NSET,NSET={name}'] + [','.join(map(str, ids[i:i+12])) for i in range(0, len(ids), 12)]


def execute(folder, name, timeout_seconds=590):
    assert 1 <= timeout_seconds <= 1800
    remote = f'/study/{folder.parent.name}/{folder.name}'
    subprocess.run([DOCKER, 'exec', CONTAINER, 'mkdir', '-p', remote], check=True)
    for item in ['mesh.inp', name+'.inp']:
        subprocess.run([DOCKER, 'cp', str(folder/item), f'{CONTAINER}:{remote}/{item}'], check=True)
    start = time.monotonic()
    with (folder/(name+'.log')).open('w') as log:
        try:
            proc = subprocess.run([DOCKER, 'exec', '-w', remote, '-e', 'OMP_NUM_THREADS=1',
                                   '-e', 'CCX_NPROC_RESULTS=1', '-e', 'OPENBLAS_NUM_THREADS=1',
                                   CONTAINER, 'timeout', str(timeout_seconds), 'ccx', '-i', name],
                                  stdout=log, stderr=subprocess.STDOUT, timeout=timeout_seconds+10)
        except subprocess.TimeoutExpired:
            subprocess.run([DOCKER, 'exec', CONTAINER, 'pkill', '-x', 'ccx'], check=False)
            raise
    for suffix in ['dat', 'frd', 'sta', 'cvg']:
        subprocess.run([DOCKER, 'cp', f'{CONTAINER}:{remote}/{name}.{suffix}',
                        str(folder/(name+'.'+suffix))], capture_output=True)
    text = (folder/(name+'.log')).read_text()
    assert proc.returncode == 0 and '*ERROR' not in text.upper(), text[-3000:]
    return time.monotonic()-start


def solve(folder, case, support=None, procedure='static'):
    config = json.loads((folder.parent/'study.json').read_text())
    material = config['material']
    data = np.load(folder/'mesh.npz')
    tags, xyz = data['tags'], data['xyz']
    groups = [np.searchsorted(tags, data[f'bolt{i}']) for i in range(4)]
    ends = [data[f'end{i}'] for i in range(2)]
    force = np.zeros_like(xyz)
    if procedure not in ('modal', 'warpage', 'thermal'):
        c = config['load_cases'][case]
        force = distribute(xyz, groups, c['force_N'], c['moment_Nmm'])
    name = case + (f'-spring-{support:g}' if support else '-rigid') + '-' + procedure
    assert not (folder/(name+'.inp')).exists(), 'Preserve previous calculations'
    lines = ['** Provisional carrier: assumed interfaces, equivalent bore loading',
             '*INCLUDE,INPUT=mesh.inp', '*MATERIAL,NAME=REFERENCE', '*ELASTIC',
             f"{material['E_MPa']},{material['nu']}", '*DENSITY', str(material['density_tonne_mm3']),
             '*EXPANSION', str(material['expansion_per_K']),
             '*SOLID SECTION,ELSET=BODY,MATERIAL=REFERENCE']
    fixed = np.concatenate(ends)
    anchors = []
    if procedure == 'warpage':
        assert support is None
        plane = fixed[abs(xyz[np.searchsorted(tags, fixed), 2]) < 1e-8]
        for point in [(-286.75, -23, 0), (286.75, -23, 0), (-286.75, 23, 0)]:
            anchors.append(plane[np.linalg.norm(xyz[np.searchsorted(tags, plane)]-point, axis=1).argmin()])
        assert len(set(anchors)) == 3
        fixed = np.array(anchors)
    lines += nset('ALLN', tags) + nset('FIXED', fixed)
    if procedure in ('warpage', 'thermal'):
        lines += ['*INITIAL CONDITIONS,TYPE=TEMPERATURE', 'ALLN,0']
    if support:
        # Total translational stiffness per eye stays constant across meshes.
        eid = max(elements(folder/'mesh.inp')) + 1
        for eye, nodes in enumerate(ends):
            for dof in (1, 2, 3):
                label = f'S{eye}{dof}'
                lines += [f'*ELEMENT,TYPE=SPRING1,ELSET={label}']
                for node in nodes:
                    lines.append(f'{eid},{node}'); eid += 1
                lines += [f'*SPRING,ELSET={label}', str(dof), str(support/len(nodes))]
    lines += ['*STEP,NLGEOM,INC=100' if procedure == 'nonlinear' else '*STEP']
    if procedure == 'modal': lines += ['*FREQUENCY,SOLVER=SPOOLES', '8']
    elif procedure == 'buckling': lines += ['*BUCKLE,SOLVER=SPOOLES', '4']
    else:
        lines += ['*STATIC,SOLVER=SPOOLES']
        if procedure == 'nonlinear': lines += ['0.1,1,0.001,0.2']
    if procedure == 'warpage':
        lines += ['*BOUNDARY', f'{anchors[0]},1,3', f'{anchors[1]},2,3', f'{anchors[2]},3,3',
                  '*TEMPERATURE']
        lines += [f"{node},{50*p[2]/config['geometry']['thickness_mm']:.12g}" for node, p in zip(tags, xyz)]
    elif not support: lines += ['*BOUNDARY', 'FIXED,1,3']
    if procedure == 'thermal':
        lines += ['*TEMPERATURE', 'ALLN,60']
    if procedure not in ('modal', 'warpage', 'thermal'):
        lines += ['*CLOAD']
        lines += [f'{node},{d+1},{v:.12g}' for node, f in zip(tags, force)
                  for d, v in enumerate(f) if abs(v) > 1e-12]
    lines += ['*NODE PRINT,NSET=ALLN', 'U', '*NODE PRINT,NSET=FIXED', 'RF',
              '*EL PRINT,ELSET=BODY', 'S', '*NODE FILE', 'U', '*EL FILE', 'S', '*END STEP']
    (folder/(name+'.inp')).write_text('\n'.join(lines)+'\n')
    seconds = execute(folder, name)
    result = {'name': name, 'procedure': procedure, 'seconds': seconds,
              'solver_container': CONTAINER,
              'input_sha256': hashlib.sha256((folder/(name+'.inp')).read_bytes()).hexdigest(),
              'mesh_sha256': hashlib.sha256((folder/'mesh.inp').read_bytes()).hexdigest(),
              'geometry_provisional': True, 'load_assumed': True,
              'material_allowable': None, 'physical_validation': False}
    if procedure in ('static', 'nonlinear', 'warpage', 'thermal'):
        values = parse_dat(folder/(name+'.dat'))
        urows = values['displacements']; s = values['stresses']; rf = values['forces']
        assert len(urows) == len(tags) and len(s) > 0
        assert np.array_equal(urows[:, 0].astype(int), tags)
        u = urows[:, 1:]; tensor = s[:, 2:]
        vm = von_mises(tensor)
        if support:
            reaction = np.zeros((len(fixed), 3)); offset = 0
            for nodes in ends:
                reaction[offset:offset+len(nodes)] = -u[np.searchsorted(tags, nodes)]*support/len(nodes)
                offset += len(nodes)
        else:
            assert len(rf) == len(fixed)
            fixed = rf[:, 0].astype(int); reaction = rf[:, 1:]
        residual_f = reaction.sum(0)+force.sum(0)
        positions = xyz+u if procedure == 'nonlinear' else xyz
        residual_m = np.cross(positions[np.searchsorted(tags, fixed)], reaction).sum(0)+np.cross(positions, force).sum(0)
        scale = max(1, np.abs(force).sum(), np.abs(reaction).sum())
        assert max(abs(residual_f)) < 1e-4*scale, residual_f
        assert max(abs(residual_m)) < 1e-4*scale*300, residual_m
        assert np.isfinite(u).all() and np.isfinite(vm).all()
        result.update(displacement_max_mm=float(np.linalg.norm(u, axis=1).max()),
                      integration_point_VM_max_MPa=float(vm.max()),
                      VM_peak_element=int(s[vm.argmax(), 0]),
                      force_residual_N=residual_f.tolist(), moment_residual_Nmm=residual_m.tolist(),
                      external_work_Nmm=float((force*u).sum()),
                      bolt_group_forces_N=[force[g].sum(0).tolist() for g in groups])
        if procedure == 'warpage':
            result['thermal_sensitivity'] = '50 K through plate thickness; free expansion with 3-2-1 rigid-body restraint. Not a calibrated print, weld or residual-distortion prediction.'
        elif procedure == 'thermal':
            result['thermal_sensitivity'] = 'Uniform +60 K operational temperature hypothesis, constant dense-reference elasticity; no calibrated temperature-dependent AM properties.'
        np.savez_compressed(folder/(name+'.npz'), tags=tags, xyz=xyz, displacement=u,
                            element_ids=s[:, 0].astype(int), stress=tensor, VM=vm,
                            force=force, fixed=fixed, reaction=reaction)
    else:
        text = (folder/(name+'.dat')).read_text()
        rows = eigenvalues(text, procedure)
        result['frequencies_Hz' if procedure == 'modal' else 'buckling_load_factors'] = rows[:, 3 if procedure == 'modal' else 1].tolist()
    (folder/(name+'.json')).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)
    return result


def selfcheck():
    xyz = np.array([[-48, -23, 0], [-48, 23, 0], [48, -23, 0], [48, 23, 0]], dtype=float)
    groups = [np.array([i]) for i in range(4)]
    for i in range(6):
        load = np.eye(6)[i]*1000
        f = distribute(xyz, groups, load[:3], load[3:])
        v = np.array([.1, -.3, .2])+np.cross([.004, .002, -.001], xyz)
        expected = np.dot(load[:3], [.1, -.3, .2])+np.dot(load[3:], [.004, .002, -.001])
        assert abs((f*v).sum()-expected) < 1e-8
    print('Six load-transfer resultant and virtual-work checks passed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', type=Path, nargs='?')
    parser.add_argument('--mesh', type=float)
    parser.add_argument('--case', default='combined')
    parser.add_argument('--support', type=float)
    parser.add_argument('--procedure', choices=['static', 'nonlinear', 'modal', 'buckling', 'warpage', 'thermal'], default='static')
    parser.add_argument('--selfcheck', action='store_true')
    args = parser.parse_args()
    if args.selfcheck: selfcheck()
    elif args.mesh: mesh(args.folder, args.mesh)
    else: solve(args.folder, args.case, args.support, args.procedure)
