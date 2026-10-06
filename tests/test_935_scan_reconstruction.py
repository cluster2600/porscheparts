import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'twins/935-horizontal-cooling-system-f0/source'))
try:
    import numpy as np
    from scipy.optimize import least_squares
    from run_reconstruction import cylinder, fitted_profile, fresh, ordered_contours, require_result, sha, contiguous_regions, run
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, 'Requires working numpy/scipy numerical runtime')
class ScanReconstructionTests(unittest.TestCase):
    def test_acquired_shaft_periodicity_is_inferred_across_bands_and_disagreement_rejected(self):
        from reconstruct_drive_shaft import periodic_profiles
        theta = np.linspace(0, 2*np.pi, 1100, endpoint=False)
        theta = theta[(theta < .2) | (theta > .4)]  # A real missing sector must remain recorded.
        bands = [[20,23],[23,26],[26,29]]
        def points(counts):
            rows = []
            for (lo, hi), count in zip(bands, counts):
                radius = 12 + .4*np.cos(count*theta+.1) + .06*np.sin(2*count*theta) + .03*np.cos(theta)
                for height in np.linspace(lo+.2, hi-.2, 4):
                    rows.append(np.column_stack([radius*np.cos(theta), radius*np.sin(theta), np.full(len(theta),height)]))
            return np.concatenate(rows)
        result = periodic_profiles(points([22,22,22]), bands, list(range(6,41)))
        self.assertEqual(result['observed_periodicity'], 22)
        self.assertFalse(result['axis_or_tooth_standard_verified'])
        for row in result['bands']:
            self.assertLess(row['heldout_rms_source_units'], 1e-8)
            self.assertGreater(row['maximum_unsampled_angular_gap_deg'], 10)
            self.assertFalse(set(row['train_sample_indices']) & set(row['test_sample_indices']))
        with self.assertRaisesRegex(ValueError, 'Periodicity disagrees'):
            periodic_profiles(points([22,14,22]), bands, list(range(6,41)))
        with self.assertRaises(ValueError):
            periodic_profiles(points([22,22,22]), bands, list(range(6,41)), samples=32)

    def test_bounded_hub_models_recover_inclined_analytic_surfaces_on_heldout_sectors(self):
        from reconstruct_hub_surfaces import fit_surface
        angle, height = np.meshgrid(np.linspace(0, 2 * np.pi, 360, endpoint=False), np.linspace(-10, 10, 8))
        axis = np.array([.08, -.12, 1]); axis /= np.linalg.norm(axis)
        x = np.cross([0, 1, 0], axis); x /= np.linalg.norm(x)
        radial = np.outer(np.cos(angle.ravel()), x) + np.outer(np.sin(angle.ravel()), np.cross(axis, x))
        for kind, slope in [('cylinder', 0), ('cone', .025)]:
            points = radial * (11 + slope * height.ravel())[:, None] + np.outer(height.ravel(), axis) + [.3, -.4, 0]
            normals = (radial - slope * axis) / np.sqrt(1 + slope ** 2)
            fit = fit_surface(points, normals, [0, 0, 0, 0, 11], [8, 16], kind)
            self.assertLess(fit['heldout_rms_source_units'], 1e-7)
            self.assertAlmostEqual(fit['radius_slope'], slope, delta=1e-7)
            np.testing.assert_allclose(fit['axis_in_seed_frame'], axis, atol=1e-7)
            self.assertFalse(set(fit['test_sample_indices']) & set(fit['train_sample_indices']))
            self.assertEqual(len(fit['test_sample_indices']) + len(fit['train_sample_indices']), len(points))
            self.assertFalse(fit['functional_datum_verified'])
        with self.assertRaises(ValueError):
            fit_surface(points, normals, [0, 0, 0, 0, 11], [8, 16], 'cone', robust_scale=float('nan'))
        with self.assertRaises(ValueError):
            fit_surface(points[:100], normals[:100], [0, 0, 0, 0, 11], [8, 16], 'cone')

    def test_observed_cylinder_recovers_tilt_without_using_global_pca_axis(self):
        angle = np.linspace(0, 2 * np.pi, 360, endpoint=False)
        angle, height = np.meshgrid(angle, np.linspace(-10, 10, 8))
        axis = np.array([.08, -.12, 1]); axis /= np.linalg.norm(axis)
        x = np.cross([0, 1, 0], axis); x /= np.linalg.norm(x)
        basis = np.column_stack((x, np.cross(axis, x), axis))
        radial = np.column_stack((np.cos(angle.ravel()), np.sin(angle.ravel()), np.zeros(angle.size))) @ basis.T
        points = radial * 11 + np.outer(height.ravel(), axis) + [.3, -.4, 0]
        points += np.random.default_rng(42).normal(0, .01, points.shape)
        origin, fitted, report = cylinder(points, radial, [8, 16], 2, .2)
        self.assertGreater(abs(fitted[:, 2] @ axis), .99999)
        self.assertAlmostEqual(report['radius_source_units'], 11, delta=.02)
        self.assertLess(report['radial_rms_source_units'], .02)
        self.assertGreater(report['angular_coverage_deg'], 350)
        self.assertLess(np.linalg.norm(origin - [.3, -.4, 0]), .02)

    def test_small_section_gap_is_labelled_and_large_gap_remains_open(self):
        angle = np.linspace(0, 2 * np.pi, 64, endpoint=False)
        points = np.column_stack((np.zeros(64), np.cos(angle), np.sin(angle)))
        segments = np.stack((points, np.roll(points, -1, axis=0)), axis=1)
        closed = ordered_contours(segments, .12)
        self.assertEqual(len(closed), 1); self.assertEqual(closed[0][1], [])
        repaired = ordered_contours(segments[:-1], .12)
        self.assertEqual(len(repaired), 1); self.assertEqual(len(repaired[0][1]), 1)
        self.assertEqual(ordered_contours(segments[:-16], .12), [])

    def test_periodic_fit_stays_in_observed_section_plane(self):
        t = np.linspace(0, 2 * np.pi, 100, endpoint=False)
        direction = np.array([np.cos(.4), np.sin(.4), 0])
        tangent = np.cross([0, 0, 1], direction)
        points = 50 * direction + np.outer(10 * np.cos(t), tangent) + np.outer(3 * np.sin(t), [0, 0, 1])
        profile = fitted_profile(points[::-1], direction, 128, 0)
        self.assertEqual(profile.shape, (128, 3))
        self.assertLess(np.max(np.abs(profile @ direction - 50)), 1e-10)
        self.assertLess(np.min(profile[:, 2]), -2.99)

    def test_missing_station_splits_lofts_and_cannot_be_silently_bridged(self):
        blade = {'id': 'synthetic', 'phase_radians': 0, 'profiles': [[i] for i in [0, 2, 4, 8, 10, 12]],
                 'sections': [{'station': i, 'accepted': i != 6} for i in range(0, 14, 2)]}
        regions = contiguous_regions(blade, list(range(0, 14, 2)))
        self.assertEqual([r['stations_source_units'] for r in regions], [[0, 2, 4], [8, 10, 12]])

    def test_private_outputs_are_fresh_and_upstream_hashes_are_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = fresh(Path(tmp) / 'new')
            with self.assertRaises(ValueError): fresh(output)
            path = output / 'result.json'; path.write_text(json.dumps({'value': 1}))
            self.assertEqual(require_result(path, sha(path)), {'value': 1})
            with self.assertRaises(ValueError): require_result(path, 'a' * 64)
            repo = Path(tmp) / 'repo'; repo.mkdir(); (repo / '.git').mkdir()
            with self.assertRaises(ValueError): fresh(repo / 'public')

    def test_volume_inertia_uses_axis_origin_and_controlled_length_power(self):
        try:
            import trimesh
            from review_reconstruction import properties
        except ImportError:
            self.skipTest('Requires trimesh')
        box = trimesh.creation.box(extents=[2, 4, 6]); box.apply_translation([2, 3, 4])
        result = properties(box)
        self.assertAlmostEqual(result['conditional_volume_mm3'], 48)
        np.testing.assert_allclose(np.diag(result['conditional_volume_inertia_about_axis_origin_mm5']), [1408, 1120, 704])
        box.apply_scale(2)
        doubled = properties(box)
        self.assertAlmostEqual(doubled['conditional_volume_mm3'] / result['conditional_volume_mm3'], 2 ** 3)
        np.testing.assert_allclose(np.array(doubled['conditional_volume_inertia_about_axis_origin_mm5']) /
                                   result['conditional_volume_inertia_about_axis_origin_mm5'], 2 ** 5)

    def test_failed_stage_is_retained_and_resume_cannot_overwrite_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / 'case.json'; output = Path(tmp) / 'failed'
            case.write_text(json.dumps({'native': {'image_id': 'mutable-tag', 'root': tmp}}))
            previous = os.umask(0o077)
            try:
                with self.assertRaisesRegex(ValueError, 'immutable'):
                    run(case, 'cad', output)
                self.assertTrue(json.loads((output / 'failure.json').read_text())['partial_outputs_retained'])
                with self.assertRaisesRegex(ValueError, 'new private'):
                    run(case, 'cad', output)
                with self.assertRaisesRegex(ValueError, 'Implemented stages'):
                    run(case, 'cfd', Path(tmp) / 'fake-solve')
                self.assertFalse((Path(tmp) / 'fake-solve').exists())
            finally:
                os.umask(previous)


if __name__ == '__main__':
    unittest.main()
