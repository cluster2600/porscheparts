"""Retain v4 builder gates and replay both explicitly recorded authorities."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

baseline_spec = importlib.util.spec_from_file_location('carrier_cached_v5_baseline_tests',
    Path(__file__).with_name('test_carrier_cached_build_v4.py'))
baseline = importlib.util.module_from_spec(baseline_spec)
baseline_spec.loader.exec_module(baseline)
SOURCE = baseline.baseline.SOURCE
OLD_HOOKS = copy.deepcopy(baseline.driver.RUNTIME_HOOKS)
spec = importlib.util.spec_from_file_location('carrier_cached_v5', SOURCE/'build_cached_v5.py')
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)

import shapely
from grid_intervals import contacts


def load(name):
    spec = importlib.util.spec_from_file_location('carrier_v5_test_'+name, SOURCE/(name+'.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CachedBuildV5(baseline.CachedBuildV4):
    def setUp(self):
        for module in (baseline, baseline.baseline):
            scoped = patch.object(module, 'driver', driver)
            scoped.start()
            self.addCleanup(scoped.stop)

    def test_incremental_helper_and_its_dependencies_are_source_bound(self):
        self.assertEqual(len(driver.POLICY_FILES), 6)
        hook = driver.RUNTIME_HOOKS['combinatorial_constructor_dispatch']
        self.assertEqual(hook['sha256'], driver.sha(driver.POLICY_FILES[0]))
        self.assertEqual(set(hook['authorities']),
                         {driver.OLD_CONSTRUCTION_SHA256, driver.REDUNDANT_SHA256})
        self.assertEqual(driver._index.ASSEMBLY_SHA256, driver.ASSEMBLY_SHA256)
        self.assertEqual(driver._index._OLD.INDEX_SHA256, driver.LINE_INDEX_SHA256)
        self.assertEqual(driver.admissions_v3.CONSTRUCTION_SHA256, driver.OLD_CONSTRUCTION_SHA256)
        self.assertEqual(driver._new_admission.CONSTRUCTION_SHA256, driver.REDUNDANT_SHA256)
        self.assertIs(driver._new_admission._construction, driver._redundant)
        self.assertIsNot(driver.admissions_v3, driver._new_admission)
        self.assertEqual(driver.admissions_v3.seal.__code__.co_filename,
                         str(SOURCE/'admissions_v3.py'))
        self.assertEqual(tuple(driver.KEYS), ('envelopes', 'regions', 'skins', 'grids', 'contacts', 'collisions'))
        for path in driver.POLICY_FILES[2:]:
            with self.subTest(path=path), patch.dict(driver.POLICY_SHA256, {path:'0'*64}), \
                    patch.object(driver._base, 'build') as build:
                with self.assertRaisesRegex(ValueError, 'policy changed'):
                    driver.build('input', 'output', 'store', 'cache')
                build.assert_not_called()

    def test_old_and_new_small_reconstructions_keep_their_own_authority(self):
        free = shapely.box(0., 10., 5., 11.)
        pairs = [('continuous_combinatorial_interfaces', driver.OLD_CONSTRUCTION_SHA256,
                  dict(upper=[[[0., 11.], [5., 11.]]], lower=[[[0., 10.], [5., 10.]]])),
                 ('continuous_redundant_interfaces', driver.REDUNDANT_SHA256,
                  dict(upper=[[[0., 10.], [5., 10.]]], lower=[[[0., 11.], [5., 11.]]]))]
        for name, authority, interfaces in pairs:
            with self.subTest(authority=authority):
                material, receipt = load(name).repair(shapely.Polygon(), free, interfaces, .2)
                original = copy.deepcopy(receipt)
                result = driver.continuous_admission(receipt, contacts(material, free, interfaces), .2)
                self.assertTrue(result['passed'])
                self.assertEqual(result['construction_source_sha256'], authority)
                self.assertEqual(receipt['combinatorial_construction_source_sha256'], authority)
                self.assertEqual(receipt, original)

    def test_retained_reentrant_chart_is_replayed_and_cannot_be_relabeled_old(self):
        fixture = json.loads((SOURCE/'combinatorial-evidence/reentrant-chart002.json').read_text())
        free = shapely.from_wkb(fixture['source_domain_geometry_wkb_hex'])
        interfaces = fixture['attested_source_interfaces']
        material, receipt = load('continuous_redundant_interfaces').repair(
            shapely.Polygon(), free, interfaces, .2)
        actual = contacts(material, free, interfaces)
        self.assertTrue(driver.continuous_admission(receipt, actual, .2)['passed'])
        relabeled = copy.deepcopy(receipt)
        relabeled['combinatorial_construction_source_sha256'] = driver.OLD_CONSTRUCTION_SHA256
        with self.assertRaisesRegex(ValueError, 'upper interface points'):
            driver.continuous_admission(relabeled, actual, .2)
        corrupted = copy.deepcopy(receipt)
        certificates = corrupted['intervals'][0]['combinatorial_construction']['whole_edge_interfaces']
        next(row for row in certificates if 'redundancy_certificate' in row)[
            'redundancy_certificate']['exact_redundancy_coverage']['passed'] = False
        with self.assertRaisesRegex(ValueError, 'construction proof differs'):
            driver.continuous_admission(corrupted, actual, .2)

    def test_unknown_or_missing_authority_cannot_select_a_constructor(self):
        for receipt in [{}, {'combinatorial_construction_source_sha256':'0'*64}, None]:
            with self.subTest(receipt=receipt), \
                    patch.object(driver, '_old_continuous_admission') as old, \
                    patch.object(driver._new_admission, 'continuous_admission') as new:
                with self.assertRaisesRegex(ValueError, 'constructor authority'):
                    driver.continuous_admission(receipt, [], .2)
                old.assert_not_called(); new.assert_not_called()

    def test_an_entire_v4_stage_cannot_start_v5_reuse(self):
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory)/'stage'
            checkpoint = self.stage(stage)
            checkpoint['admission_runtime_hooks'] = OLD_HOOKS
            self.save_checkpoint(stage, checkpoint)
            for key in driver.KEYS:
                self.change_receipt(stage, checkpoint, key, admission_runtime_hooks=OLD_HOOKS)
            with patch.object(driver._base, 'build') as build, self.assertRaisesRegex(ValueError, 'runtime hook'):
                driver.build('input', Path(directory)/'output', 'store', 'cache', reuse_support_stage=stage)
            build.assert_not_called()
