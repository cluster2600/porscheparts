import json
from pathlib import Path
import sys
import threading
import unittest

try:
    import shapely
    from shapely.geometry import Polygon
except ImportError:
    shapely = None
SOURCE = Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-skins-20261016'
sys.path.insert(0, str(SOURCE))
AVAILABLE = shapely is not None and hasattr(shapely, 'constrained_delaunay_triangles')
if AVAILABLE:
    import combinatorial_interfaces as original
    import indexed_combinatorial_interfaces as indexed
    import continuous_combinatorial_interfaces as original_repair
    import continuous_indexed_interfaces as indexed_repair


@unittest.skipUnless(AVAILABLE, 'Constrained-triangulation runtime required')
class IndexedInterfacesTests(unittest.TestCase):
    def test_all_exact_interval_rows_and_order_match_the_frozen_operation(self):
        paths = [[[0, 0], [3, 0], [5, 0]], [[5, 0], [10, 0]], [[20, 0], [30, 0]],
                 [[10, 10], [0, 10]], [[0, 0], [10, 10]], [[5, 5], [5, 8]]]
        index = indexed.InterfaceIndex(paths)
        for a, b in [([0, 0], [10, 0]), ([10, 0], [0, 0]), ([1, 0], [9, 0]),
                     ([0, 0], [10, 10]), ([5, 0], [5, 10]), ([0, 1], [10, 1])]:
            a, b = original._EXACT.point(a), original._EXACT.point(b)
            self.assertEqual(index.coverage(a, b), original._coverage(a, b, paths))

    def test_five_constructed_surfaces_and_complete_receipts_are_identical(self):
        fixture = json.loads((SOURCE/'combinatorial-evidence/fixtures.json').read_text())
        self.assertEqual([row['name'] for row in fixture['cases']],
                         ['box', 'hole', 'separated_lower', 'left', 'right'])
        for row in fixture['cases']:
            with self.subTest(name=row['name']):
                domain = shapely.from_wkb(row['source_domain_geometry_wkb_hex'])
                a, ar = original.construct(domain, row['attested_source_interfaces'], .2)
                b, br = indexed.construct(domain, row['attested_source_interfaces'], .2)
                self.assertEqual(a.wkb, b.wkb)
                self.assertEqual(ar, br)

    def test_private_operation_is_restored_after_refusal(self):
        before = indexed._BASE._coverage
        with self.assertRaises(ValueError):
            indexed.construct(Polygon([(0, 0), (10, 10), (0, 10), (10, 0)]), dict(upper=[], lower=[]), .2)
        self.assertIs(indexed._BASE._coverage, before)

    def test_two_threads_cannot_replace_each_others_private_interface_binding(self):
        first_entered, second_indexed = threading.Event(), threading.Event()
        a_interfaces = dict(upper=[[[0, 0], [10, 0]]], lower=[])
        b_interfaces = dict(upper=[[[20, 0], [30, 0]]], lower=[])
        real_construct, real_index = indexed._BASE.construct, indexed.InterfaceIndex
        outputs, errors = [], []
        class ObservedIndex(real_index):
            def __init__(self, paths):
                super().__init__(paths)
                if threading.current_thread().name == 'second' and paths is b_interfaces['lower']:
                    second_indexed.set()
        def observed_construct(domain, interfaces, penetration):
            if interfaces is a_interfaces:
                first_entered.set()
                if not second_indexed.wait(3):
                    raise RuntimeError('Second thread did not finish its independent index')
            low, _, high, _ = domain.bounds
            return indexed._BASE._coverage(original._EXACT.point([low, 0]), original._EXACT.point([high, 0]), interfaces['upper'])
        def run(domain, interfaces):
            try:
                outputs.append(indexed.construct(domain, interfaces, .2))
            except Exception as error:
                errors.append(error)
        indexed.InterfaceIndex, indexed._BASE.construct = ObservedIndex, observed_construct
        a = threading.Thread(target=run, args=(shapely.box(0, 0, 10, 1), a_interfaces), name='first')
        b = threading.Thread(target=run, args=(shapely.box(20, 0, 30, 1), b_interfaces), name='second')
        try:
            a.start()
            self.assertTrue(first_entered.wait(3))
            b.start()
            a.join(3);b.join(3)
            self.assertFalse(a.is_alive() or b.is_alive())
            self.assertEqual(errors, [])
            self.assertEqual(len(outputs), 2)
            self.assertTrue(all(row[0] for row in outputs))
            self.assertIs(indexed._BASE._coverage, indexed._ORIGINAL_COVERAGE)
        finally:
            indexed.InterfaceIndex, indexed._BASE.construct = real_index, real_construct

    def test_reentrant_call_refuses_and_restores_the_operation(self):
        real_construct = indexed._BASE.construct
        interfaces = dict(upper=[], lower=[])
        indexed._BASE.construct = lambda domain, sources, p: indexed.construct(domain, sources, p)
        try:
            with self.assertRaisesRegex(ValueError, 'reentrant'):
                indexed.construct(shapely.box(0, 0, 10, 1), interfaces, .2)
            self.assertIs(indexed._BASE._coverage, indexed._ORIGINAL_COVERAGE)
        finally:
            indexed._BASE.construct = real_construct

    def test_indexed_policy_keeps_the_complete_repair_receipt(self):
        domain = shapely.box(0, 10, 10, 20)
        interfaces = dict(upper=[[[0, 20], [10, 20]]], lower=[[[0, 10], [10, 10]]])
        a, ar = original_repair.repair(domain, domain, interfaces, .2)
        b, br = indexed_repair.repair(domain, domain, interfaces, .2)
        self.assertEqual(a.wkb, b.wkb)
        self.assertEqual(ar, br)


if __name__ == '__main__':
    unittest.main()
