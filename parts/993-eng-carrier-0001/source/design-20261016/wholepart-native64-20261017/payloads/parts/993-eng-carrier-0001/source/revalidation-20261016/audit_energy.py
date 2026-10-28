"""Independent energy closure for the retained, affine C3D10 linear study.

Four equal tetrahedron quadrature weights integrate the quadratic elastic
energy exactly for straight midsides. This checks a numerical model, not a part.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

# Seven significant digits in DAT stresses/displacements limit this comparison.
ENERGY_RELATIVE_TOLERANCE = 1e-4
# Mesh INP coordinates are rounded when written; NPZ retains the binary values.
COORDINATE_ROUNDOFF_MM = 1e-10
EDGE_PAIRS = np.array([[0, 1], [1, 2], [2, 0], [0, 3], [1, 3], [2, 3]])


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def blocks(path):
    """Read keyword blocks without accepting comments as keywords."""
    result = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('**'):
            continue
        if line.startswith('*'):
            result.append((line.upper().replace(' ', ''), []))
        else:
            require(bool(result), 'Data before first keyword')
            result[-1][1].append(line)
    return result


def read_mesh(path):
    nodes, elements = [], []
    for key, lines in blocks(path):
        if key == '*NODE':
            nodes.extend([[float(v) for v in line.split(',')] for line in lines])
        elif key.startswith('*ELEMENT'):
            require('TYPE=C3D10,' in key + ',', 'Only C3D10 elements are supported')
            elements.extend([[int(v) for v in line.split(',')] for line in lines])
    n, e = np.asarray(nodes), np.asarray(elements, dtype=np.int64)
    require(n.ndim == 2 and n.shape[1] == 4 and np.isfinite(n).all(), 'Invalid mesh nodes')
    require(e.ndim == 2 and e.shape[1] == 11, 'Invalid C3D10 connectivity')
    tags = n[:, 0].astype(np.int64)
    require(np.array_equal(n[:, 0], tags) and np.all(np.diff(tags) > 0), 'Node IDs must be sorted and unique')
    require(len(np.unique(e[:, 0])) == len(e), 'Duplicate element IDs')
    ids = np.searchsorted(tags, e[:, 1:])
    require(np.all(ids < len(tags)) and np.array_equal(tags[ids], e[:, 1:]), 'Unknown element node')
    require(np.all(np.diff(np.sort(e[:, 1:], axis=1), axis=1) > 0), 'Repeated element node')
    return tags, n[:, 1:], e[:, 0], ids


def strain_energy(points, stress, elastic_modulus, poisson_ratio):
    require(np.isfinite([elastic_modulus, poisson_ratio]).all() and elastic_modulus > 0 and -1 < poisson_ratio < .5, 'Invalid isotropic elasticity')
    require(np.isfinite(points).all() and np.isfinite(stress).all(), 'Nonfinite energy input')
    require(points.ndim == 3 and points.shape[1:] == (10, 3), 'Expected C3D10 coordinates')
    require(stress.shape == (len(points), 4, 6), 'Expected four stress tensors per element')
    midpoint = (points[:, EDGE_PAIRS[:, 0]] + points[:, EDGE_PAIRS[:, 1]]) / 2
    require(np.max(np.abs(points[:, 4:] - midpoint)) <= 1e-10, 'Curved midsides need a different quadrature audit')
    determinant = np.linalg.det(points[:, 1:4] - points[:, [0]])
    require(np.isfinite(determinant).all() and np.all(determinant > 0), 'Nonpositive affine Jacobian')
    normal, shear = stress[..., :3], stress[..., 3:]
    cross = normal[..., 0] * normal[..., 1] + normal[..., 0] * normal[..., 2] + normal[..., 1] * normal[..., 2]
    # Tensor shear stresses pair with engineering shear strain tau/G in sigma:epsilon.
    density = (np.sum(normal**2, axis=-1) - 2 * poisson_ratio * cross
               + 2 * (1 + poisson_ratio) * np.sum(shear**2, axis=-1)) / (2 * elastic_modulus)
    require(np.isfinite(density).all() and np.all(density >= 0), 'Invalid strain energy density')
    # Each reference-tetrahedron Gauss weight is 1/24; volume is det(J)/6.
    return float(np.sum(density * determinant[:, None] / 24)), float(determinant.sum() / 6)


def dat_fields(path):
    fields = {'displacements': [], 'stresses': []}
    active = None
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        for key in (*fields, 'forces'):
            if line.startswith(key + ' ('):
                active = key if key in fields else None
                if active:
                    fields[active] = []
        row = line.split()
        if active and len(row) == (8 if active == 'stresses' else 4) and row[0].isdigit():
            fields[active].append([float(v.replace('D', 'E')) for v in row])
    return {key: np.asarray(value) for key, value in fields.items()}


def audit(mesh_folder, case):
    folder = Path(mesh_folder)
    receipt = json.loads((folder / (case + '.json')).read_text())
    require(receipt['procedure'] == 'static' and receipt['name'] == case, 'Only identified linear static cases are supported')
    require(receipt['mesh_sha256'] == sha(folder / 'mesh.inp'), 'Mesh hash mismatch')
    require(receipt['input_sha256'] == sha(folder / (case + '.inp')), 'Solver deck hash mismatch')
    mesh_meta = json.loads((folder / 'mesh.json').read_text())
    require(mesh_meta['STEP_sha256'] == sha(folder.parent / 'carrier.step'), 'STEP identity mismatch')
    tags, xyz, element_ids, connectivity = read_mesh(folder / 'mesh.inp')
    with np.load(folder / 'mesh.npz', allow_pickle=False) as mesh:
        require(np.array_equal(tags, mesh['tags']) and np.allclose(xyz, mesh['xyz'], atol=COORDINATE_ROUNDOFF_MM, rtol=0), 'Mesh NPZ identity mismatch')
    deck = blocks(folder / (case + '.inp'))
    require(sum(key.startswith('*STEP') for key, _ in deck) == 1, 'Expected one load step')
    require(not any('NLGEOM' in key or key.startswith(('*PLASTIC', '*TEMPERATURE', '*INITIALCONDITIONS')) for key, _ in deck), 'Nonlinear or thermal case is unsupported')
    require([key for key, _ in deck if key.startswith('*INCLUDE')] == ['*INCLUDE,INPUT=MESH.INP'], 'Unexpected mesh include')
    elastic = [lines for key, lines in deck if key == '*ELASTIC']
    require(len(elastic) == 1 and len(elastic[0]) == 1, 'Expected one isotropic elastic material')
    modulus, nu = map(float, elastic[0][0].split(','))
    fields = dat_fields(folder / (case + '.dat'))
    stress_rows, urows = fields['stresses'], fields['displacements']
    require(stress_rows.shape == (len(element_ids) * 4, 8), 'Missing stress integration points')
    expected = np.column_stack((np.repeat(element_ids, 4), np.tile(np.arange(1, 5), len(element_ids))))
    require(np.array_equal(stress_rows[:, :2], expected), 'Stress element/integration-point identity mismatch')
    require(urows.shape == (len(tags), 4) and np.array_equal(urows[:, 0], tags), 'Displacement node identity mismatch')
    with np.load(folder / (case + '.npz'), allow_pickle=False) as values:
        require(np.array_equal(values['tags'], tags) and np.allclose(values['xyz'], xyz, atol=COORDINATE_ROUNDOFF_MM, rtol=0), 'Result NPZ mesh identity mismatch')
        require(np.array_equal(values['element_ids'], expected[:, 0]) and np.array_equal(values['stress'], stress_rows[:, 2:]), 'Result NPZ stress mismatch')
        displacement, force = values['displacement'], values['force']
        require(np.array_equal(displacement, urows[:, 1:]), 'Result NPZ displacement mismatch')
        require(displacement.shape == force.shape == xyz.shape and np.isfinite(displacement).all() and np.isfinite(force).all(), 'Invalid nodal fields')
        cload = np.zeros_like(force)
        springs, spring_energy, prescribed = {}, 0., []
        for key, lines in deck:
            if key == '*CLOAD':
                for line in lines:
                    node, dof, value = map(float, line.split(','))
                    index = np.searchsorted(tags, int(node))
                    require(index < len(tags) and tags[index] == node and dof in (1, 2, 3), 'Invalid force identity')
                    cload[index, int(dof) - 1] += value
            elif key.startswith('*ELEMENT'):
                require('TYPE=SPRING1,' in key + ',', 'Unexpected auxiliary element')
                label = key.split('ELSET=')[1]
                require(label not in springs, 'Duplicate spring set')
                springs[label] = np.array([[int(v) for v in line.split(',')] for line in lines])[:, 1]
            elif key.startswith('*SPRING,'):
                label = key.split('ELSET=')[1]
                require(label in springs and len(lines) == 2, 'Missing spring connectivity')
                dof, stiffness = int(lines[0]), float(lines[1])
                require(dof in (1, 2, 3) and np.isfinite(stiffness) and stiffness > 0, 'Invalid spring stiffness')
                nodes = springs.pop(label)
                ids = np.searchsorted(tags, nodes)
                require(np.all(ids < len(tags)) and np.array_equal(tags[ids], nodes), 'Unknown spring node')
                spring_energy += float(.5 * stiffness * np.sum(displacement[ids, dof - 1]**2))
            elif key == '*BOUNDARY':
                require(lines == ['FIXED,1,3'], 'Unsupported prescribed displacement')
                prescribed.extend(values['fixed'])
        require(not springs, 'Spring stiffness missing')
        require(not prescribed or np.max(np.abs(displacement[np.searchsorted(tags, prescribed)])) == 0, 'Nonzero prescribed displacement')
        require(np.allclose(force, cload, rtol=1e-10, atol=1e-9), 'Nodal loads do not match solver deck')
        external = float(.5 * np.sum(cload * displacement))
        solid_energy, volume = strain_energy(xyz[connectivity], stress_rows[:, 2:].reshape(-1, 4, 6), modulus, nu)
    require(np.isfinite(external) and external > 0, 'Nonpositive external work')
    total = solid_energy + spring_energy
    relative = abs(total / external - 1)
    paths = [folder / name for name in ('mesh.inp', 'mesh.npz', 'mesh.json', case + '.json', case + '.inp', case + '.dat', case + '.npz')]
    paths += [folder.parent / name for name in ('carrier.step', 'study.json', 'geometry.json')]
    return {'case': case, 'E_MPa': modulus, 'nu': nu, 'C3D10_elements': len(element_ids),
            'volume_mm3': volume, 'solid_strain_energy_Nmm': solid_energy,
            'spring_strain_energy_Nmm': spring_energy, 'half_load_dot_displacement_Nmm': external,
            'relative_energy_closure_error': relative, 'tolerance': ENERGY_RELATIVE_TOLERANCE,
            'energy_closure_pass': relative <= ENERGY_RELATIVE_TOLERANCE,
            'inputs_sha256': {str(path.relative_to(folder.parent)): sha(path) for path in paths}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mesh_folder', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cases = [path.stem for path in sorted(args.mesh_folder.glob('*-static.json'))]
    require(bool(cases), 'No retained static cases')
    report = {'scope': 'Independent elastic energy closure of a hypothetical linear FE model',
              'quadrature': 'Affine C3D10, four equal reference tetrahedron weights of 1/24',
              'tolerance_basis': 'Predeclared 1e-4 relative closure; seven significant digits in printed stresses/displacements',
              'source_sha256': sha(__file__), 'coordinate_roundoff_tolerance_mm': COORDINATE_ROUNDOFF_MM,
              'mesh_convergence_established': False, 'physical_validation': False,
              'manufacturing_authorized': False}
    try:
        report['cases'] = [audit(args.mesh_folder, case) for case in cases]
    except Exception as error:
        report.update(status='failed_closed', error=str(error))
        (args.output / 'energy-audit.json').write_text(json.dumps(report, indent=2) + '\n')
        raise
    (args.output / 'energy-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    passed = all(case['energy_closure_pass'] for case in report['cases'])
    print(json.dumps({'cases': len(cases), 'energy_closure_pass': passed,
                      'maximum_relative_error': max(case['relative_energy_closure_error'] for case in report['cases'])}))
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
