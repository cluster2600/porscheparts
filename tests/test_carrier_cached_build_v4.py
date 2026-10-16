"""Replay the same cached-builder contract with the incremental constructor."""
import importlib.util
from unittest.mock import patch

from tests import test_carrier_cached_build_v3 as baseline

spec = importlib.util.spec_from_file_location('carrier_cached_v4', baseline.SOURCE/'build_cached_v4.py')
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


class CachedBuildV4(baseline.CachedBuildV3):
    def setUp(self):
        scoped = patch.object(baseline, 'driver', driver)
        scoped.start()
        self.addCleanup(scoped.stop)

    def test_incremental_helper_and_its_dependencies_are_source_bound(self):
        self.assertEqual(len(driver.POLICY_FILES), 5)
        self.assertEqual(driver.RUNTIME_HOOKS['combinatorial_constructor']['source'],
                         'incremental_combinatorial_interfaces_ids.py')
        self.assertEqual(driver._index.ASSEMBLY_SHA256, driver.ASSEMBLY_SHA256)
        self.assertEqual(driver._index._OLD.INDEX_SHA256, driver.LINE_INDEX_SHA256)
        self.assertEqual(driver._index._OLD._INDEX.CONSTRUCTION_SHA256,
                         driver.admissions_v3.CONSTRUCTION_SHA256)
        for path in driver.POLICY_FILES[2:]:
            with self.subTest(path=path), patch.dict(driver.POLICY_SHA256, {path:'0'*64}), \
                    patch.object(driver._base, 'build') as build:
                with self.assertRaisesRegex(ValueError, 'policy changed'):
                    driver.build('input', 'output', 'store', 'cache')
                build.assert_not_called()
