"""One periodic gyroid cell solved at a tuned threshold.

The refinement study of 2026-10-22 held the gyroid level-set threshold fixed
at every resolution. A fixed threshold resampled on a different grid does not
reproduce the same solid: the actual solid fraction moved between 0.39648 and
0.41204 across N=16..64, and the full tensor change tracked that drift. The
2% spatial condition was therefore charging a geometry change to
discretisation.

This case keeps the formulation of the earlier study unchanged -- the same
C3D8 grid, periodic equations, six strain modes, energy, reciprocity and
positivity checks -- and changes one thing: the threshold is solved per
resolution so that the actual solid fraction matches a declared target. Only
then does a change between two resolutions describe discretisation alone.

It establishes no carrier convergence, no cellular part and no manufacturing
release.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[5]
SOURCE = ROOT / 'parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022'

E_MPA = 107000.0
NU = 0.31
AMPLITUDE = 0.001


def gyroid_magnitude(n: int) -> np.ndarray:
    """|g| sampled at the centre of every cell of an n^3 grid."""
    k, j, i = np.indices((n, n, n))
    x = 2 * np.pi * (i + .5) / n
    y = 2 * np.pi * (j + .5) / n
    z = 2 * np.pi * (k + .5) / n
    g = np.sin(x) * np.cos(y) + np.sin(y) * np.cos(z) + np.sin(z) * np.cos(x)
    return np.abs(g).ravel()


def threshold_for_fraction(n: int, target: float) -> tuple[float, float]:
    """Threshold placing as close to `target` solid fraction as an n^3 grid allows.

    The attainable fractions are the multiples of 1/n^3, so the target is met
    to within half a cell. The midpoint between the two bracketing magnitudes
    is returned, which keeps the selection away from a tie.
    """
    magnitudes = np.sort(gyroid_magnitude(n))
    count = int(round(target * magnitudes.size))
    count = max(1, min(magnitudes.size - 1, count))
    threshold = float((magnitudes[count - 1] + magnitudes[count]) / 2)
    return threshold, float((magnitudes <= threshold).mean())


def main() -> None:
    config = json.loads(Path(sys.argv[1]).read_text())
    out = Path(sys.argv[2])
    assert not out.exists(), 'output directory must not already exist'
    n = config['resolution']
    assert isinstance(n, int) and 4 <= n <= 64
    floor = config['void_relative_stiffness']
    target = config['target_solid_fraction']
    assert 1e-8 <= floor <= 1e-2 and 0 < target < 1
    binary = Path(config['solver_binary'])
    identity = hashlib.sha256(binary.read_bytes()).hexdigest()
    assert identity == config['solver_binary_sha256'], 'solver binary is not the declared one'
    out.mkdir(parents=True)

    threshold, rho = threshold_for_fraction(n, target)
    contract = dict(
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        parameters_sha256=hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest(),
        parameters=config,
        geometry='periodic gyroid sheet in a full solid/ersatz-void C3D8 grid',
        threshold_policy='solved per resolution to hold the actual solid fraction',
        grid=n, amplitude=AMPLITUDE, E_MPa=E_MPA, nu=NU,
        tuned_threshold=threshold, actual_solid_fraction=rho,
        target_solid_fraction=target,
        solver_binary_sha256=identity,
        solver_threads=config['solver_threads'],
        periodic_displacement_residual_limit_mm=1e-8,
        relative_energy_limit=1e-4,
        carrier_geometry_changed=False,
        carrier_convergence_demonstrated=False,
    )
    (out / 'contract.json').write_text(json.dumps(contract, indent=2) + '\n')

    def node(i, j, k):
        return 1 + i + (n + 1) * (j + (n + 1) * k)

    physical = (n + 1) ** 3
    refs = np.arange(physical + 1, physical + 4)
    points = np.array([[i / n, j / n, k / n]
                       for k in range(n + 1) for j in range(n + 1) for i in range(n + 1)])
    cells = np.array([[node(i, j, k), node(i + 1, j, k), node(i + 1, j + 1, k), node(i, j + 1, k),
                       node(i, j, k + 1), node(i + 1, j, k + 1), node(i + 1, j + 1, k + 1),
                       node(i, j + 1, k + 1)]
                      for k in range(n) for j in range(n) for i in range(n)])
    pairs = []
    for k in range(n + 1):
        for j in range(n + 1):
            for i in range(n + 1):
                q = np.array([i, j, k])
                if np.any(q == n):
                    pairs.append((node(i, j, k), node(*(q % n)), np.flatnonzero(q == n)))

    solid = gyroid_magnitude(n) <= threshold
    assert abs(solid.mean() - rho) < 1e-12
    cell_E = np.where(solid, E_MPA, E_MPA * floor)
    voigt_upper = rho + (1 - rho) * floor

    # The solid phase must be one connected periodic component, as before.
    remaining = set(map(int, np.flatnonzero(solid)))
    components = 0
    while remaining:
        components += 1
        stack = [remaining.pop()]
        while stack:
            q = stack.pop()
            k, t = divmod(q, n * n)
            j, i = divmod(t, n)
            for a, b, c in [((i + 1) % n, j, k), ((i - 1) % n, j, k),
                            (i, (j + 1) % n, k), (i, (j - 1) % n, k),
                            (i, j, (k + 1) % n), (i, j, (k - 1) % n)]:
                neighbour = a + n * (b + n * c)
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    stack.append(neighbour)
    assert components == 1, 'periodic solid phase is disconnected'

    C = np.empty((6, 6))
    rows = []
    for mode in range(6):
        H = np.zeros((3, 3))
        if mode < 3:
            H[mode, mode] = AMPLITUDE
        else:
            i, j = [(0, 1), (0, 2), (1, 2)][mode - 3]
            H[i, j] = H[j, i] = AMPLITUDE / 2
        lines = ['*HEADING', 'Owned periodic gyroid C3D8 homogenization fixture', '*NODE']
        lines += [f'{i + 1},' + ','.join(format(float(x), '.17g') for x in p)
                  for i, p in enumerate(points)]
        lines += [f'{int(ref)},' + ','.join(map(str, 2 * np.eye(3)[i]))
                  for i, ref in enumerate(refs)]
        lines += ['*NSET,NSET=ALLN,GENERATE', f'1,{physical + 3},1',
                  '*ELEMENT,TYPE=C3D8,ELSET=ALLE']
        lines += [str(i + 1) + ',' + ','.join(map(str, c)) for i, c in enumerate(cells)]
        for phase, selected, modulus in [('SOLID', solid, E_MPA), ('VOID', ~solid, E_MPA * floor)]:
            ids = np.flatnonzero(selected) + 1
            lines += ['*ELSET,ELSET=' + phase]
            lines += [','.join(map(str, ids[start:start + 16])) for start in range(0, len(ids), 16)]
            lines += ['*MATERIAL,NAME=TI_' + phase, '*ELASTIC', f'{modulus},{NU}',
                      '*SOLID SECTION,ELSET=' + phase + ',MATERIAL=TI_' + phase]
        for slave, master, axes in pairs:
            for component in range(3):
                terms = ([(slave, component + 1, 1), (master, component + 1, -1)] +
                         [(int(refs[axis]), component + 1, -1) for axis in axes])
                lines += ['*EQUATION', str(len(terms))]
                lines += [','.join(map(str, t)) for t in terms]
        lines += ['*STEP', '*STATIC', '1,1', '*BOUNDARY', '1,1,3,0']
        lines += [f'{int(refs[axis])},{component + 1},{component + 1},{H[component, axis]:.17g}'
                  for axis in range(3) for component in range(3)]
        lines += ['*NODE PRINT,NSET=ALLN', 'U,RF', '*EL PRINT,ELSET=ALLE', 'S', '*END STEP']
        deck = out / f'case-{mode}.inp'
        deck.write_text('\n'.join(lines) + '\n')
        execution = out / f'case-{mode}'
        subprocess.run([sys.executable, str(SOURCE / 'run_local_ccx_solver_parallel.py'),
                        '--binary', str(binary), '--expected-binary', identity,
                        '--deck', str(deck), '--output', str(execution),
                        '--seconds', str(config['seconds']),
                        '--rss-gib', str(config['rss_gib']),
                        '--solver-threads', str(config['solver_threads'])], check=True)

        receipt = json.loads((execution / 'actual-terminal.json').read_text())
        assert receipt['actual_returncode'] == 0 and receipt['process_reaped']
        assert receipt['inputs_unchanged']
        assert (hashlib.sha256((execution / 'case/job.dat').read_bytes()).hexdigest()
                == receipt['output_sha256']['job.dat'])

        fields = {k: [] for k in ['displacements', 'forces', 'stresses']}
        current = None
        for line in (execution / 'case/job.dat').read_text().splitlines():
            stripped = line.strip()
            for key in fields:
                if stripped.startswith(key + ' ('):
                    assert not fields[key]
                    current = key
            values = stripped.split()
            if current and len(values) == (8 if current == 'stresses' else 4) and values[0].isdigit():
                fields[current].append(values)
        assert len(fields['displacements']) == physical + 3
        assert len(fields['forces']) == physical + 3
        assert len(fields['stresses']) == 8 * len(cells)

        U = np.array([[float(y) for y in x[1:]] for x in fields['displacements']])
        F = np.array([[float(y) for y in x[1:]] for x in fields['forces']])
        stress = np.array([[float(y) for y in x[2:]] for x in fields['stresses']])
        assert all(np.isfinite(x).all() for x in [U, F, stress])
        pbc = max(float(abs(U[s - 1] - U[m - 1] - H[:, axes].sum(axis=1)).max())
                  for s, m, axes in pairs)
        assert pbc <= 1e-8
        assert abs(U[refs - 1] - H.T).max() <= 1e-8

        average = stress.mean(0)
        C[:, mode] = average / AMPLITUDE
        d = stress[:, :3]
        shear = stress[:, 3:]
        density = ((np.sum(d * d, 1)
                    - 2 * NU * (d[:, 0] * d[:, 1] + d[:, 1] * d[:, 2] + d[:, 2] * d[:, 0])
                    + 2 * (1 + NU) * np.sum(shear * shear, 1))
                   / (2 * np.repeat(cell_E, 8)))
        internal = float(density.mean())
        macro = .5 * average[mode] * AMPLITUDE
        work = .5 * float(np.sum(F[:physical] * U[:physical]))
        residual = abs(internal - macro) / macro
        rows.append(dict(mode=mode, pbc_max_mm=pbc, independent_internal_energy=internal,
                         macro_energy=macro, physical_RF_work=work,
                         relative_energy_residual=residual))
        assert residual <= 1e-4 and abs(work - macro) / macro <= 1e-4
        (out / 'progress.json').write_text(json.dumps(rows, indent=2) + '\n')

    G = E_MPA / (2 * (1 + NU))
    lam = E_MPA * NU / ((1 + NU) * (1 - 2 * NU))
    expected = np.zeros((6, 6))
    expected[:3, :3] = lam
    expected[np.arange(3), np.arange(3)] += 2 * G
    expected[3:, 3:] = np.eye(3) * G
    symmetry = float(np.linalg.norm(C - C.T) / np.linalg.norm(C))
    assert symmetry <= 1e-4
    values, vectors = np.linalg.eigh(expected)
    inverse = (vectors * (1 / np.sqrt(values))) @ vectors.T
    normalized = inverse @ ((C + C.T) / 2) @ inverse
    eigenvalues = np.linalg.eigvalsh(normalized)
    assert eigenvalues.min() > 0 and eigenvalues.max() <= voigt_upper + 1e-4

    report = dict(
        status='constant_fraction_periodic_gyroid_six_strain_energy_checks_passed',
        effective_C_MPa=C.tolist(),
        relative_antisymmetry=symmetry,
        normalized_stiffness_eigenvalues=eigenvalues.tolist(),
        minimum_tensor_stiffness_ratio=float(eigenvalues.min()),
        solid_fraction=rho,
        target_solid_fraction=target,
        solid_fraction_error_relative=float((rho - target) / target),
        solid_periodic_components=components,
        void_relative_stiffness=floor,
        gyroid_threshold=threshold,
        threshold_policy='solved per resolution to hold the actual solid fraction',
        resolution=n,
        voigt_upper_ratio=voigt_upper,
        solver_binary_sha256=identity,
        cases=rows,
        source_sha256=contract['source_sha256'],
        parameters_sha256=contract['parameters_sha256'],
        carrier_convergence_demonstrated=False,
        cellular_part_generated=False,
        unitcell_mesh_convergence_demonstrated=False,
    )
    (out / 'assessment.json').write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'], n, rho, float(eigenvalues.min()), flush=True)


if __name__ == '__main__':
    main()
