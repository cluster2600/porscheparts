"""Coefficient certificates must reject changed radii and missing endpoints."""
import importlib.util
import math
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'parts/993-eng-carrier-0001/source/design-20261016/resume-20261020/law_certificate.py'
SPEC = importlib.util.spec_from_file_location('carrier_point_radius_certificate', SOURCE)
LAW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LAW)
AUDIT_SPEC = importlib.util.spec_from_file_location(
    'carrier_consumed_law_audit', SOURCE.with_name('audit_consumed_law.py'))
AUDIT = importlib.util.module_from_spec(AUDIT_SPEC)
AUDIT_SPEC.loader.exec_module(AUDIT)


class PointRadiusLawTests(unittest.TestCase):
    def curve(self):
        return dict(degree=3, poles=[0., 0., 2., 0., 0.], knots_mm=[0., 2., 4.],
                    multiplicities=[4, 1, 4], rational=False, periodic=False)

    def test_known_two_span_cubic_has_whole_domain_certificate(self):
        result = LAW.certify(self.curve())
        self.assertTrue(result['passed'])
        self.assertEqual(result['pieces'][0]['local_power_coefficients'], ['0', '0', '3', '-2'])
        self.assertEqual(result['pieces'][1]['local_power_coefficients'], ['1', '0', '-3', '2'])

    def test_one_ulp_radius_excess_is_preserved_and_refused(self):
        curve = self.curve()
        curve['poles'][2] = math.nextafter(2., math.inf)
        self.assertFalse(LAW.certify(curve)['passed'])

    def test_nonzero_endpoint_is_refused(self):
        curve = self.curve()
        curve['poles'][0] = .001
        self.assertFalse(LAW.certify(curve)['passed'])

    def test_nonzero_endpoint_slope_is_refused(self):
        curve = self.curve()
        curve['poles'][1] = .01
        self.assertFalse(LAW.certify(curve)['passed'])

    def test_rational_curve_is_not_silently_approximated(self):
        curve = self.curve()
        curve['rational'] = True
        with self.assertRaises(ValueError):
            LAW.certify(curve)

    def test_extended_native_law_is_audited_at_physical_not_virtual_endpoints(self):
        curve = dict(degree=3, poles=[0., 0., -.5, 1.75, -.5, 0., 0.],
                     knots_mm=[-2., 0., 2., 4., 6.], multiplicities=[4,1,1,1,4],
                     rational=False, periodic=False)
        physical = AUDIT.at_parameter(curve, 0.)
        virtual = AUDIT.at_parameter(curve, -2.)
        self.assertTrue(all(r['value_exactly_zero'] for r in physical))
        self.assertTrue(all(r['slope'] == '3/8' for r in physical))
        self.assertTrue(all(r['slope_exactly_zero'] for r in virtual))

    def test_endpoint_outside_saved_domain_is_unresolved(self):
        with self.assertRaises(ValueError):
            AUDIT.at_parameter(self.curve(), 5.)

    def test_missing_generated_laws_cannot_pass_an_empty_all(self):
        result = AUDIT.audit(dict(consumed_laws=[]))
        self.assertFalse(result['complete'])
        self.assertIsNone(result['all_physical_endpoint_slopes_exactly_zero'])


if __name__ == '__main__':
    unittest.main()
