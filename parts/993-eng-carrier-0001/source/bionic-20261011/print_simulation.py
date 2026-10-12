"""Sequential inherent-strain sensitivity on the actual carrier tetrahedra.

The scalar TEMPERATURE is a deposition clock, not a temperature prediction.
Shrinkage and homogenised support stiffness are explicit, uncalibrated inputs.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from simulate import elements, execute, nset, von_mises


def expansion(clock, birth, shrinkage):
    return 0.0 if clock <= birth else -shrinkage/clock


def frames(path):
    result = []; field = None
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith('displacements ('):
            result.append({'displacements': [], 'forces': [], 'stresses': []})
            field = 'displacements'
        elif line.startswith('forces ('):
            field = 'forces'
        elif line.startswith('stresses ('):
            field = 'stresses'
        row = line.split()
        if field and len(row) == (8 if field == 'stresses' else 4) and row[0].isdigit():
            result[-1][field].append([float(v.replace('D', 'E')) for v in row])
    return [{k: np.asarray(v) for k, v in step.items()} for step in result]


def remove_rigid(xyz, u):
    """Small-motion least-squares registration; retain shrinkage and distortion."""
    r = xyz-xyz.mean(0)
    A = np.zeros((len(r), 3, 6)); A[:, :, :3] = np.eye(3)
    for i, (x, y, z) in enumerate(r):
        A[i, :, 3:] = [[0, z, -y], [-z, 0, x], [y, -x, 0]]
    flat = A.reshape(-1, 6)
    assert np.linalg.matrix_rank(flat) == 6
    return u-(flat@np.linalg.lstsq(flat, u.ravel(), rcond=None)[0]).reshape(-1, 3)


def build(source, output, orientation, layers=16, shrinkage=.001, support_E=1000, plastic_reference=False):
    assert 1 <= layers <= 128 and 0 < shrinkage <= .01 and support_E > 0
    output.mkdir(parents=True, exist_ok=False)
    data = np.load(source/'mesh.npz')
    tags = data['tags']; xyz = data['xyz']@np.asarray(orientation['rotation_matrix']).T
    xyz += orientation['translation_mm']
    connect = elements(source/'mesh.inp')
    eids = np.array(list(connect)); conn = np.array(list(connect.values()))
    indices = np.searchsorted(tags, conn)
    centres = xyz[indices[:, :4]].mean(1)
    zlo, zhi = xyz[:, 2].min(), xyz[:, 2].max()
    bins = np.minimum(layers-1, ((centres[:, 2]-zlo)/(zhi-zlo)*layers).astype(int))
    assert len(np.unique(bins)) == layers
    lines = ['*NODE']+[f'{tag},{p[0]:.12g},{p[1]:.12g},{p[2]:.12g}' for tag, p in zip(tags, xyz)]
    lines += ['*ELEMENT,TYPE=C3D10,ELSET=BODY']
    lines += [','.join(map(str, [eid, *nodes])) for eid, nodes in connect.items()]
    (output/'mesh.inp').write_text('\n'.join(lines)+'\n')
    np.savez_compressed(output/'mesh.npz', **{k: data[k] for k in data.files if k != 'xyz'}, xyz=xyz)

    # Use outward tetrahedral faces, including midsides, for support tributary areas.
    lookup = {}
    for element_index, nodes in enumerate(conn):
        for ids in ((0, 1, 2, 4, 5, 6), (0, 1, 3, 4, 8, 7),
                    (0, 2, 3, 6, 9, 7), (1, 2, 3, 5, 9, 8)):
            face = nodes[list(ids)]
            lookup[tuple(sorted(face[:3]))] = (element_index, face)
    area = np.zeros(len(tags)); down_area = 0.
    for face in data['faces']:
        ei, six = lookup[tuple(sorted(face))]
        ids = np.searchsorted(tags, six); tri = xyz[ids[:3]]
        normal = np.cross(tri[1]-tri[0], tri[2]-tri[0]); magnitude = np.linalg.norm(normal)
        if np.dot(normal, tri.mean(0)-centres[ei]) < 0: normal = -normal
        if normal[2]/magnitude < -np.cos(np.pi/4):
            area[ids] += magnitude/12; down_area += magnitude/2
    supported = np.flatnonzero(area)
    assert len(supported) >= 12
    height = xyz[supported, 2]-orientation['assumed_platform_thickness_mm']
    assert height.min() > 0
    stiffness = support_E*area[supported]/height
    lines = ['** Equivalent post-cycle inherent strain, not a laser/thermal process model',
             '*INCLUDE,INPUT=mesh.inp']+nset('ALLN', tags)+nset('SUPN', tags[supported])
    for i in range(layers):
        ids = eids[bins == i]
        lines += [f'*ELSET,ELSET=L{i}']+[','.join(map(str, ids[j:j+12])) for j in range(0, len(ids), 12)]
        lines += [f'*MATERIAL,NAME=M{i}', '*ELASTIC', '107000,0.31']
        if plastic_reference: lines += ['*PLASTIC', '955,0', '955,0.1']
        lines += ['*EXPANSION,TYPE=ORTHO']
        for clock in range(layers+1):
            a = expansion(clock, i, shrinkage)
            lines.append(f'{a:.14g},{a:.14g},{a/2:.14g},{clock}')
        lines += [f'*SOLID SECTION,ELSET=L{i},MATERIAL=M{i}']
    # shortcut: springs homogenise removable supports; replace with qualified support CAD before compensation.
    eid = max(eids)+1; support_elements = []
    for j, (node, k) in enumerate(zip(tags[supported], stiffness)):
        for d, scale in ((1, .1), (2, .1), (3, 1.)):
            lines += [f'*ELEMENT,TYPE=SPRING1,ELSET=SUP{j}_{d}', f'{eid},{node}',
                      f'*SPRING,ELSET=SUP{j}_{d}', str(d), f'{scale*k:.12g}']
            support_elements.append(eid); eid += 1
    lines += ['*ELSET,ELSET=SUPPORTS']
    lines += [','.join(map(str, support_elements[j:j+12])) for j in range(0, len(support_elements), 12)]
    lines += ['*INITIAL CONDITIONS,TYPE=TEMPERATURE', 'ALLN,0']
    stage_kinds = []
    for i in range(layers):
        if i:
            # Birth must finish before shrinkage; CalculiX otherwise cancels the new thermal strain.
            lines += ['*STEP,NLGEOM,INC=60', '*STATIC,SOLVER=SPOOLES', '1,1,0.00001,1',
                      '*MODEL CHANGE,TYPE=ELEMENT,ADD=STRAIN FREE', f'L{i}',
                      '*TEMPERATURE', f'ALLN,{i}', '*NODE PRINT,NSET=ALLN,FREQUENCY=999999', 'U',
                      '*EL PRINT,ELSET=BODY,FREQUENCY=999999', 'S', '*END STEP']
            stage_kinds.append('stress_free_birth')
        lines += ['*STEP,NLGEOM,INC=60', '*STATIC,SOLVER=SPOOLES', '1,1,0.00001,1']
        if i == 0 and layers > 1:
            lines += ['*MODEL CHANGE,TYPE=ELEMENT,REMOVE']+[f'L{j}' for j in range(1, layers)]
        lines += ['*TEMPERATURE', f'ALLN,{i+1}', '*NODE PRINT,NSET=ALLN,FREQUENCY=999999', 'U',
                  '*EL PRINT,ELSET=BODY,FREQUENCY=999999', 'S', '*END STEP']
        stage_kinds.append('layer_shrinkage')
    a = int(np.argmin(xyz[:, 2])); b = int(np.argmax(abs(xyz[:, 0]-xyz[a, 0])))
    c = int(np.argmax(abs(np.cross(xyz[b]-xyz[a], xyz-xyz[a])[:, 2])))
    assert len({a, b, c}) == 3
    lines += ['*STEP,NLGEOM,INC=60', '*STATIC,SOLVER=SPOOLES', '1,1,0.00001,1', '*MODEL CHANGE,TYPE=ELEMENT,REMOVE',
              'SUPPORTS', '*BOUNDARY', f'{tags[a]},1,3', f'{tags[b]},2,3', f'{tags[c]},3,3',
              '*NODE PRINT,NSET=ALLN,FREQUENCY=999999', 'U', '*EL PRINT,ELSET=BODY,FREQUENCY=999999', 'S', '*NODE FILE', 'U',
              '*EL FILE', 'S', '*END STEP']
    stage_kinds.append('support_release')
    (output/'print.inp').write_text('\n'.join(lines)+'\n')
    setup = {'macro_layers': layers, 'macro_layer_height_mm': (zhi-zlo)/layers,
             'actual_machine_layer_mm': .06, 'actual_part_layer_intervals': int(np.ceil((zhi-zlo)/.06)),
             'in_plane_shrinkage': shrinkage, 'build_axis_shrinkage': shrinkage/2,
             'support_effective_E_MPa': support_E, 'support_lateral_to_axial_stiffness': .1,
             'supported_nodes': len(supported), 'overhang_area_mm2': down_area,
             'orientation': orientation, 'element_birth_counts': np.bincount(bins).tolist(),
             'stage_kinds': stage_kinds,
             'ideal_plastic_reference_yield_MPa': 955 if plastic_reference else None,
             'source_mesh_sha256': hashlib.sha256((source/'mesh.inp').read_bytes()).hexdigest(),
             'machine_calibrated': False, 'support_removability_verified': False,
             'thermal_history_or_heat_treatment_relaxation_solved': False}
    (output/'setup.json').write_text(json.dumps(setup, indent=2)+'\n')
    return setup


def run(folder):
    seconds = execute(folder, 'print', timeout_seconds=1800)
    setup = json.loads((folder/'setup.json').read_text()); data = np.load(folder/'mesh.npz')
    rows = frames(folder/'print.dat')
    assert len(rows) == len(setup['stage_kinds']), len(rows)
    result = {'setup': setup, 'seconds': seconds, 'stages': []}
    for i, row in enumerate(rows):
        u = row['displacements']; s = row['stresses']; vm = von_mises(s[:, 2:])
        assert np.array_equal(u[:, 0].astype(int), data['tags'])
        assert np.isfinite(u).all() and np.isfinite(vm).all()
        registered = remove_rigid(data['xyz'], u[:, 1:])
        item = {'stage': i+1, 'operation': setup['stage_kinds'][i], 'released': i == len(rows)-1,
                'U_max_mm': float(np.linalg.norm(u[:, 1:], axis=1).max()),
                'registered_U_max_mm': float(np.linalg.norm(registered, axis=1).max()),
                'VM_max_MPa': float(vm.max()), 'VM_p99_MPa': float(np.quantile(vm, .99))}
        result['stages'].append(item)
        if i >= len(rows)-2:
            label = 'released' if item['released'] else 'on-plate'
            np.savez_compressed(folder/(label+'.npz'), displacement=u[:, 1:], registered=registered,
                                element_ids=s[:, 0].astype(int), stress=s[:, 2:], VM=vm)
    before, after = rows[-2]['displacements'][:, 1:], rows[-1]['displacements'][:, 1:]
    springback = remove_rigid(data['xyz'], after-before)
    result['registered_release_change_max_mm'] = float(np.linalg.norm(springback, axis=1).max())
    result['classification'] = 'sequential_macro_layer_inherent_strain_and_support_release_sensitivity'
    result['qualified_print_prediction'] = False
    result['local_stress_exceeds_coupon_reference'] = any(s['VM_max_MPa'] > 955*1.01 for s in result['stages'])
    result['input_sha256'] = hashlib.sha256((folder/'print.inp').read_bytes()).hexdigest()
    (folder/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'setup'}), flush=True)
    return result


def selfcheck():
    for born in range(16):
        for clock in range(17):
            expected = 0 if clock <= born else -.001
            assert abs(expansion(clock, born, .001)*clock-expected) < 1e-14
    xyz = np.array([[0., 0, 0], [2, 0, 0], [0, 1, 0], [1, 1, 3]])
    motion = [1., -2, 3]+np.cross([.01, -.03, .04], xyz)
    assert abs(remove_rigid(xyz, motion)).max() < 1e-12
    assert np.linalg.norm(remove_rigid(xyz, xyz*.001)) > .001
    print('Birth-clock eigenstrain and rigid-motion registration checks passed.')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('source', type=Path, nargs='?'); p.add_argument('output', type=Path, nargs='?')
    p.add_argument('--orientation', type=Path); p.add_argument('--layers', type=int, default=16)
    p.add_argument('--shrinkage', type=float, default=.001); p.add_argument('--support-E', type=float, default=1000)
    p.add_argument('--selfcheck', action='store_true'); p.add_argument('--run-existing', action='store_true')
    p.add_argument('--plastic-reference', action='store_true')
    a = p.parse_args()
    if a.selfcheck: selfcheck()
    elif a.run_existing: run(a.source)
    else:
        build(a.source, a.output, json.loads(a.orientation.read_text()), a.layers, a.shrinkage, a.support_E, a.plastic_reference)
        run(a.output)
