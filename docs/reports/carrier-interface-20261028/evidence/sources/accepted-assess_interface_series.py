"""Assess two successive refinements of one fixed STEP periodic cell."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def compare_levels(levels):
    if len(levels) != 3:
        raise ValueError('Three completed levels are required')
    for row in levels:
        if sorted(c['mode'] for c in row['mechanics']['cases']) != list(range(6)):
            raise ValueError('All six completed strain cases are required')
    if len({r['STEP_sha256'] for r in levels}) != 1:
        raise ValueError('Geometry changes cannot count as spatial refinement')
    if len({r['transport_sha256'] for r in levels}) != 3:
        raise ValueError('Replayed meshes cannot count as spatial refinement')
    comparisons = []
    for coarse, fine in zip(levels, levels[1:]):
        if fine['tetrahedra'] < 1.25 * coarse['tetrahedra'] or fine['maximum_edge_mm'] >= coarse['maximum_edge_mm']:
            raise ValueError('A clearly finer mesh with shorter maximum edges is required')
        a = np.asarray(coarse['mechanics']['effective_C_MPa'])
        b = np.asarray(fine['mechanics']['effective_C_MPa'])
        if a.shape != (6, 6) or b.shape != (6, 6) or not np.isfinite([a, b]).all() or np.linalg.norm(b) == 0:
            raise ValueError('Finite complete stiffness tensors are required')
        change = float(np.linalg.norm(b-a)/np.linalg.norm(b))
        comparisons.append(dict(relative_full_tensor_change=change, passed=change <= .02))
    return dict(comparisons=comparisons, fixed_geometry_h_converged=all(r['passed'] for r in comparisons),
                required_successive_comparisons=2, relative_tensor_limit=.02,
                implicit_geometry_convergence_demonstrated=False,
                carrier_convergence_demonstrated=False, cellular_carrier_generated=False)


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--level', nargs=3, action='append', required=True, metavar=('MESH', 'MECHANICS', 'TOPOLOGY'))
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError('Fresh output required')
    sha = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
    sources = [Path(__file__)]
    levels = []
    for mesh, mechanics, topology in a.level:
        mesh, mechanics, topology = Path(mesh), Path(mechanics), Path(topology)
        g = json.loads((mesh/'assessment.json').read_text())
        m = json.loads((mechanics/'assessment.json').read_text())
        t = json.loads(topology.read_text())
        assert m['status'] == 'explicit_periodic_T10_six_strain_checks_passed' and m['kind'] == 'gyroid'
        assert t['status'] == 'complete_periodic_T10_nodes_and_T6_facets_passed'
        identities = m['source_sha256'].values()
        assert sha(mesh/'cell.step') in identities and sha(mesh/'transport.npz') in identities
        assert sha(mesh/'cell.step') in t['source_sha256'].values() and sha(mesh/'transport.npz') in t['source_sha256'].values()
        assert g['tetrahedra'] == t['tetrahedra'] and g['nodes'] == t['nodes']
        for i in range(6):
            receipt = mechanics/f'case-{i}/actual-terminal.json'
            r = json.loads(receipt.read_text())
            assert r['actual_returncode'] == 0 and r['process_reaped'] and r['inputs_unchanged'] and r['solver_finished_marker']
            assert sha(mechanics/f'case-{i}/case/job.dat') == r['output_sha256']['job.dat']
            sources += [receipt, mechanics/f'case-{i}.inp']
        sources += [mesh/'assessment.json', mechanics/'assessment.json', topology, mesh/'transport.npz', mesh/'cell.step']
        levels.append(dict(tetrahedra=t['tetrahedra'], nodes=t['nodes'], maximum_edge_mm=t['maximum_corner_edge_mm'],
                           STEP_sha256=sha(mesh/'cell.step'), transport_sha256=sha(mesh/'transport.npz'), mechanics=m))
    report = compare_levels(levels)
    report.update(levels=levels, source_sha256={str(f): sha(f) for f in sources})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), layout='constrained')
    counts = [r['tetrahedra'] for r in levels]
    axes[0].plot(counts, [r['mechanics']['minimum_tensor_stiffness_ratio'] for r in levels], 'o-', color='#286864')
    axes[0].set(xlabel='Actual quadratic tetrahedra', ylabel='Minimum normalized stiffness eigenvalue', title='One fixed STEP geometry')
    changes = [100*r['relative_full_tensor_change'] for r in report['comparisons']]
    axes[1].bar(['Coarse → medium', 'Medium → fine'], changes, color='#286864')
    axes[1].axhline(2, color='#a74833', linestyle='--', label='Unchanged 2% threshold')
    axes[1].set(ylabel='Full stiffness tensor change (%)', title='Two successive comparisons')
    axes[1].legend()
    fig.suptitle('Explicit periodic cell / fixed-geometry mesh study\nSurface-resolution and whole-carrier convergence remain separate')
    a.output.mkdir()
    fig.savefig(a.output/'interface-convergence.png', dpi=160)
    plt.close(fig)
    report['figure_sha256'] = sha(a.output/'interface-convergence.png')
    (a.output/'assessment.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ['levels', 'source_sha256']}))


if __name__ == '__main__':
    main()
