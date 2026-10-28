"""Inspect a frozen analysis-core mask before attempting finite cellular geometry."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def face_components(cells):
    if cells.ndim != 2 or cells.shape[1] != 4 or not len(cells):
        raise ValueError('Nonempty tetrahedral selection required')
    if len(np.unique(np.sort(cells, axis=1), axis=0)) != len(cells):
        raise ValueError('Duplicate tetrahedra refused')
    faces = np.concatenate([cells[:, f] for f in [[0,1,2], [0,1,3], [0,2,3], [1,2,3]]])
    owners = np.tile(np.arange(len(cells)), 4)
    _, first, inverse, count = np.unique(np.sort(faces, axis=1), axis=0,
                                        return_index=True, return_inverse=True, return_counts=True)
    if count.max() > 2:
        raise ValueError('Nonmanifold volume-face incidence')
    order = np.argsort(inverse)
    paired = inverse[order][1:] == inverse[order][:-1]
    pairs = np.column_stack([owners[order][1:][paired], owners[order][:-1][paired]])
    graph = coo_matrix((np.ones(len(pairs)), pairs.T), shape=(len(cells), len(cells)))
    number, labels = connected_components(graph, directed=False)
    boundary = faces[first[count == 1]]
    edges = np.concatenate([boundary[:, f] for f in [[0,1], [1,2], [2,0]]])
    _, edge_counts = np.unique(np.sort(edges, axis=1), axis=0, return_counts=True)
    return number, labels, int((edge_counts != 2).sum())


def main():
    p = argparse.ArgumentParser(__doc__)
    for name in ['volume', 'selection', 'reference', 'output']:
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError('Fresh output required')
    sha = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
    reference = json.loads(a.reference.read_text())
    assert reference['status'] == 'frozen_core_T10_baseline_energy_audited'
    assert sha(a.volume) in reference['source_sha256'].values() and sha(a.selection) in reference['source_sha256'].values()
    z = np.load(a.volume); selection = np.load(a.selection)
    ids = selection['indices']; vertices = z['vertices']; cells = z['tetrahedra'][ids]
    assert len(ids) == reference['selected_cells'] and len(np.unique(ids)) == len(ids)
    points = vertices[cells]
    assert np.array_equal(points.mean(1), selection['centres'])
    volume = np.linalg.det((points[:,1:]-points[:,0,None,:]).transpose(0,2,1))/6
    assert np.all(volume > 0) and np.isclose(volume.sum(), reference['selected_T10_volume_mm3'], rtol=1e-12)
    number, labels, bad_edges = face_components(cells)
    components = []
    for i in range(number):
        keep = labels == i; x = points[keep].reshape(-1,3)
        components.append(dict(component=i, cells=int(keep.sum()), volume_mm3=float(volume[keep].sum()),
                               bounds_mm=[x.min(0).tolist(), x.max(0).tolist()]))
    components.sort(key=lambda r: -r['volume_mm3'])
    report = dict(status='frozen_selected_core_face_connectivity_inspected', selected_cells=len(cells),
                  selected_volume_mm3=float(volume.sum()), face_connected_components=number,
                  boundary_edges_with_incidence_not_two=bad_edges, components=components,
                  selection_changed=False, cellular_carrier_generated=False,
                  vertex_manifoldness_certified=False,
                  source_sha256={str(f): sha(f) for f in [a.volume, a.selection, a.reference, Path(__file__)]})
    a.output.mkdir()
    used, inverse = np.unique(cells, return_inverse=True)
    np.savez_compressed(a.output/'selected-volume.npz', vertices=vertices[used], tetrahedra=inverse.reshape(-1,4), parent_indices=ids, component_labels=labels)
    report['selected_volume_sha256'] = sha(a.output/'selected-volume.npz')
    (a.output/'assessment.json').write_text(json.dumps(report, indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), layout='constrained')
    large = np.isin(labels, [r['component'] for r in components[:4]])
    centres = points.mean(1)
    axes[0].scatter(centres[~large,0], centres[~large,1], s=2, color='#c0873a', label='Other face-connected fragments')
    axes[0].scatter(centres[large,0], centres[large,1], s=2, color='#286864', label='Four largest components')
    axes[0].set(xlabel='Carrier X [mm]', ylabel='Carrier Y [mm]', title='Existing protected analysis mask')
    axes[0].set_aspect('equal'); axes[0].legend(fontsize=8)
    axes[1].semilogy(np.arange(1,number+1), [r['volume_mm3'] for r in components], color='#286864')
    axes[1].set(xlabel='Component rank', ylabel='Volume [mm³]', title=f'{number} face-connected components / {bad_edges} irregular boundary edges')
    fig.suptitle('993 carrier / finite-core preparation\nA numerical budget mask needs geometric reconstruction before lattice insertion')
    fig.savefig(a.output/'selected-core-topology.png', dpi=160); plt.close(fig)
    (a.output/'figure-provenance.json').write_text(json.dumps(dict(figure_sha256=sha(a.output/'selected-core-topology.png'),
        assessment_sha256=sha(a.output/'assessment.json'), source_sha256=sha(Path(__file__))), indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','face_connected_components','boundary_edges_with_incidence_not_two']}))


if __name__ == '__main__':
    main()
