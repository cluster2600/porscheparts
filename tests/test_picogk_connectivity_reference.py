"""Optional SciPy cross-check on synthetic lattices, not physical validation."""
import importlib.util
from pathlib import Path
import unittest


SOURCE = (Path(__file__).resolve().parents[1]
          / 'twins/m64-cylinder-head/source/picogk-connectivity/connectivity.py')
spec = importlib.util.spec_from_file_location('picogk_connectivity_reference', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

HAS_REFERENCE_DEPENDENCIES = all(
    importlib.util.find_spec(name) is not None for name in ('numpy', 'scipy'))


@unittest.skipUnless(HAS_REFERENCE_DEPENDENCIES,
                     'optional NumPy/SciPy reference runtime unavailable')
class PicoGKConnectivityReferenceTests(unittest.TestCase):
    def test_eighty_noncubic_cases_match_independent_scipy_labels(self):
        # A package spec can exist while its optional native extension cannot
        # load. Skip only dependency loading, never reference computation or
        # an assertion; the qualified QA runtime must execute all 80 cases.
        try:
            import numpy as np
            from scipy.ndimage import generate_binary_structure, label
        except (ImportError, OSError) as error:
            self.skipTest('optional NumPy/SciPy native runtime cannot load: '
                          + type(error).__name__)

        random = np.random.default_rng(729)
        spacing = 1.2
        checked = 0
        for shape in ((3, 5, 7), (6, 4, 9), (11, 7, 5), (4, 12, 3)):
            for repeat in range(10):
                # NumPy C order is Z/Y/X here, matching X-fastest mask bytes.
                cells = random.random(shape[::-1]) < random.uniform(.1, .85)
                mask = cells.astype(np.uint8).tobytes()
                for neighbours, rank in ((6, 1), (26, 3)):
                    with self.subTest(shape_xyz=shape, repeat=repeat,
                                      neighbours=neighbours):
                        labels, component_count = label(
                            cells, generate_binary_structure(3, rank))
                        boundary_labels = np.concatenate((
                            labels[0].ravel(), labels[-1].ravel(),
                            labels[:, 0].ravel(), labels[:, -1].ravel(),
                            labels[:, :, 0].ravel(), labels[:, :, -1].ravel()))
                        exterior_labels = set(np.unique(boundary_labels)) - {0}
                        sizes = np.bincount(labels.ravel())
                        exterior = sum(int(sizes[index])
                                       for index in exterior_labels)
                        isolated_sizes = sorted(
                            (int(sizes[index])
                             for index in range(1, component_count + 1)
                             if index not in exterior_labels), reverse=True)

                        result = module.classify(mask, shape, spacing, neighbours)
                        self.assertEqual(result['shape_xyz'], list(shape))
                        self.assertEqual(result['total_void_sample_count'],
                                         int(cells.sum()))
                        self.assertEqual(result['exterior_connected_sample_count'],
                                         exterior)
                        self.assertEqual(result['isolated_sample_count'],
                                         sum(isolated_sizes))
                        self.assertEqual(result['potential_isolated_component_count'],
                                         len(isolated_sizes))
                        self.assertEqual(
                            [item['sample_count']
                             for item in result['isolated_components_private']],
                            isolated_sizes)
                        self.assertEqual(result['voxel_sum_isolated_volume_mm3_estimate'],
                                         sum(isolated_sizes) * spacing**3)
                        self.assertEqual(result['total_void_sample_count'],
                                         exterior + sum(isolated_sizes))
                        self.assertFalse(result['physical_sealed_cavity_proved'])
                        self.assertFalse(result['CFD_domain_qualified'])
                        self.assertFalse(result['manufacturing_authorized'])
                        checked += 1
        self.assertEqual(checked, 80)


if __name__ == '__main__':
    unittest.main()
