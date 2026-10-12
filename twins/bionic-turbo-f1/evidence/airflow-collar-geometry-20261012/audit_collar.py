"""Check one homothetic collar against pinned CFD surfaces; no mesh admission."""
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from audit_rear_interface import crossing_facets, geometry, planar_annulus, read_patches
from prepare_case import sha
from profile_background import validate_profile

BASE = Path(__file__).resolve().parent
PROFILE = Path('work/bionic-airflow-20261012/profile-background-030/manifest.json')
BANDS = [Path('work/bionic-interface-profile-20261012') / name for name in
         ('profile-023.json', 'candidate-profile-023.json')]
EXPECTED = ['a9bfe013789b8707b82a4b89c524ea3f18dbf3e9d7f094664fe38ad2c89cb840',
            'acb534d47805d7c74b8a0b386ec99e6d996a688b5f6a29cb7c4a2e629ac452f9']


def extrema(nodes, lo, hi):
    """Affine segments attain extrema at endpoints or retained interior knots."""
    if not nodes[0, 0] <= lo <= hi <= nodes[-1, 0]:
        raise ValueError('Interval outside profile')
    samples = np.r_[lo, nodes[(nodes[:, 0] > lo) & (nodes[:, 0] < hi), 0], hi]
    values = np.interp(samples, nodes[:, 0], nodes[:, 1])
    return float(values.min()), float(values.max())


def self_check():
    nodes = np.array([[0., 4.], [1., 2.], [2., 6.]])
    assert extrema(nodes, .5, 1.5) == (2., 4.)
    assert extrema(nodes, .25, .5) == (3., 3.5)
    assert extrema(nodes, 1., 1.) == (2., 2.)
    try:
        extrema(nodes, -1, 1)
    except ValueError:
        pass
    else:
        raise AssertionError('Out-of-domain interval accepted')


def main():
    self_check()
    output = BASE / 'collar-062.json'
    if output.exists():
        raise FileExistsError(output)
    assert sha(PROFILE) == '8b13f2a154d8c3b14ba75bc7ba5b13808054ece7477e7c6ce21d6e373a68f71e'
    assert [sha(p) for p in BANDS] == EXPECTED
    reports = [json.loads(p.read_text()) for p in BANDS]
    nodes = np.array(json.loads(PROFILE.read_text())['simplified_profile_nodes_mm'])
    clearance = .905690
    central = validate_profile(nodes, reports, clearance)
    eta = clearance / (2 * nodes[:, 1].max())
    inner, outer = 1 - eta, 1 + eta
    cosine = math.cos(math.pi / 128)
    variants = {}
    for label, case_name, report in zip(('baseline', 'candidate'),
            ('baseline-conformal-022', 'candidate-parallel-014'), reports):
        case = Path('work/bionic-airflow-20261012') / case_name
        manifest = case / 'case-manifest.json'
        assert sha(manifest) == report['case_manifest_sha256']
        info = json.loads(manifest.read_text())['surface']
        assert info['sha256'] == report['surface_sha256']
        assert report['source_sha256'] == sha(Path('twins/bionic-turbo-f1/cfd/audit_interface_corridor.py'))
        assert report['geometry_source_sha256'] == sha(Path(geometry.__file__))
        print('Reading exact surface:', label, flush=True)
        patches = read_patches(case / 'constant/triSurface/domain.stl', info)
        bands = []
        for i in range(3, 359):
            b = report['bands'][i]
            low, high = extrema(nodes, b['z_low_mm'], b['z_high_mm'])
            gaps = [inner * low * cosine - b['rotor_upper_mm'],
                    b['stator_lower_mm'] - outer * high]
            assert min(gaps) >= clearance / 2
            bands.append(dict(index=i, z_mm=[b['z_low_mm'], b['z_high_mm']],
                              collar_radial_bounds_mm=[inner * low * cosine, outer * high],
                              rotor_stator_separations_mm=gaps))
        annulus = planar_annulus(patches['stator'])
        rear_low, rear_high = inner * 32 * cosine, outer * 32
        assert annulus['annulus_inner_radius_mm'] < rear_low < rear_high < annulus['annulus_outer_radius_mm']
        top = nodes[-1, 1]
        crossings = {}
        for name, t in patches.items():
            selected = crossing_facets(t, -4, -3.5, rear_low, rear_high)
            assert not len(selected) or (name == 'stator' and np.all(t[selected, :, 2] == -3.75))
            checks = dict(bottom_disk=crossing_facets(t, -4, -4, 0, rear_high),
                          front_disk=crossing_facets(t, 33, 33, 0, outer * top),
                          front_extension=crossing_facets(t, 32.1, 33, inner * top * cosine, outer * top))
            if name in ('inlet', 'outlet'):
                checks['ports'] = crossing_facets(t, -4, 33, 0, outer * nodes[:, 1].max())
            assert all(len(v) == 0 for v in checks.values())
            crossings[name] = dict(rear_candidates=selected.tolist(), **{k: len(v) for k, v in checks.items()})
        winding = {}
        for name, point, expected in [('bottom', [0, 0, -4], 0), ('front', [0, 0, 33], 1),
                                     ('rear_above', [32, 0, -3.6], 1), ('rear_below', [32, 0, -3.9], 0)]:
            value = sum(geometry.solid_winding_number(t, point) for t in patches.values())
            assert abs(value - expected) < 1e-6
            winding[name] = dict(point_mm=point, value=value, expected=expected)
        rotor = patches['rotor']
        lo, hi = rotor[:, :, 2].min(axis=1), rotor[:, :, 2].max(axis=1)
        assert lo.min() > nodes[0, 0] and hi.max() < nodes[-1, 0]
        upper = np.linalg.norm(rotor[:, :, :2], axis=2).max(axis=1) + geometry.MARGIN_MM
        # Whole-facet norm maximum bounds every point; each overlapping affine segment is checked.
        margins = np.full(len(rotor), np.inf)
        covered = np.zeros(len(rotor), dtype=bool)
        for a, b in zip(nodes[:-1], nodes[1:]):
            selected = (lo <= b[0]) & (hi >= a[0])
            z0, z1 = np.maximum(lo[selected], a[0]), np.minimum(hi[selected], b[0])
            r0 = np.interp(z0, nodes[:, 0], nodes[:, 1])
            r1 = np.interp(z1, nodes[:, 0], nodes[:, 1])
            bound = inner * np.minimum(r0, r1) * cosine - upper[selected]
            margins[selected] = np.minimum(margins[selected], bound)
            covered |= selected
        assert covered.all() and np.isfinite(margins).all() and margins.min() > 0
        worst = int(margins.argmin())
        variants[label] = dict(surface_sha256=info['sha256'], case_manifest_sha256=sha(manifest),
            bands=bands, annulus=annulus, terminal_candidates=crossings, closed_boundary_winding=winding,
            rotor=dict(facets=len(rotor), all_facets_inside_inner_boundary=True,
                minimum_radial_bound_mm=float(margins.min()), worst_facet=worst,
                worst_triangle_mm=rotor[worst].tolist(), axial_bounds_mm=[float(lo.min()), float(hi.max())],
                float64_mm_sha256=hashlib.sha256(rotor.astype('<f8').tobytes()).hexdigest()))
        print('Verified collar:', label, flush=True)
    result = dict(schema='bionic-turbo-collar-geometry/v1', source_sha256=sha(Path(__file__)),
        reused_source_sha256={name: sha(Path('twins/bionic-turbo-f1/cfd') / name) for name in
                             ('audit_rear_interface.py', 'audit_interface_corridor.py', 'profile_background.py')},
        geometry_source_sha256=sha(Path(geometry.__file__)), profile_manifest_sha256=sha(PROFILE),
        band_report_sha256=EXPECTED, nodes_z_radius_mm=nodes.tolist(), sectors=128,
        central_required_clearance_mm=clearance, central_verified_clearance_mm=central,
        eta=float(eta), inner_ratio=float(inner), outer_ratio=float(outer),
        minimum_required_lateral_collar_separation_mm=clearance / 2, variants=variants,
        geometry_verified=True, mesh_admission=False, performance_ranking_authorized=False,
        interpretation='A connected lateral collar inside the closed CFD fluid boundary above the planar rear termination; lower extension and disk outside fluid. No native mesh, physical clearance, layers or performance qualification.')
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
