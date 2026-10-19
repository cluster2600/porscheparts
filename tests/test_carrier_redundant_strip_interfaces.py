import hashlib
import json
from pathlib import Path
import sys
import unittest
try:
    import shapely
    from shapely.geometry import box,Polygon
except ImportError:
    shapely=None
SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-skins-20261016'
sys.path.insert(0,str(SOURCE))
AVAILABLE=shapely is not None and hasattr(shapely,'constrained_delaunay_triangles')
if AVAILABLE:
    import redundant_strip_interfaces as new
    import incremental_combinatorial_interfaces_ids as old

@unittest.skipUnless(AVAILABLE,'Constrained-triangulation runtime required')
class RedundantStripTests(unittest.TestCase):
    def test_five_existing_cases_are_byte_identical_without_redundancy(self):
        fixture=json.loads((SOURCE/'combinatorial-evidence/fixtures.json').read_text())
        self.assertEqual(len(fixture['cases']),5)
        for case in fixture['cases']:
            d=shapely.from_wkb(case['source_domain_geometry_wkb_hex'])
            a,ar=old.construct(d,case['attested_source_interfaces'],fixture['penetration_mm'])
            b,br=new.construct(d,case['attested_source_interfaces'],fixture['penetration_mm'])
            self.assertEqual(a.wkb,b.wkb);self.assertEqual(ar,br)

    def test_entire_inward_strip_already_in_source_is_not_added_or_relabeled(self):
        d=box(0,10,5,11);interfaces=dict(upper=[[[0,10],[5,10]]],lower=[[[0,11],[5,11]]])
        result,receipt=new.construct(d,interfaces,.2)
        self.assertTrue(result.equals_exact(d,0,normalize=True))
        redundant=[r for r in receipt['whole_edge_interfaces'] if r.get('strip_status')=='excluded_redundant_inside_source_domain']
        self.assertEqual(len(redundant),2);self.assertEqual(receipt['added_triangles'],0)
        for r in redundant:
            self.assertTrue(any(r['whole_edge_attested'].values()))
            self.assertTrue(r['redundancy_certificate']['exact_redundancy_coverage']['passed'])
            self.assertTrue(r['redundancy_certificate']['contact_role_unchanged'])

    def test_partially_covered_strip_preserves_original_refusal(self):
        d=box(0,10,5,10.1)
        with self.assertRaisesRegex(ValueError,'upper interface points'):
            new.construct(d,dict(upper=[[[0,10],[5,10]]],lower=[]),.2)
        with self.assertRaisesRegex(ValueError,'lower interface points'):
            new.construct(d,dict(upper=[],lower=[[[0,10.1],[5,10.1]]]),.2)

    def test_endpoints_inside_do_not_hide_a_hole_in_the_proposed_strip(self):
        d=Polygon(box(0,10,5,11).exterior.coords,[box(2,10.05,3,10.1).exterior.coords])
        with self.assertRaisesRegex(ValueError,'upper interface points'):
            new.construct(d,dict(upper=[[[0,10],[5,10]]],lower=[]),.2)

    def test_real_failed_chart_keeps_roles_and_certifies_exactly_five_redundancies(self):
        path=SOURCE/'combinatorial-evidence/reentrant-chart002.json'
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),'679ce5d3f3b96af77bccf3fddacd76c814b9dfd9293c6be851c982ccf51cd21f')
        fixture=json.loads(path.read_text());d=shapely.from_wkb(fixture['source_domain_geometry_wkb_hex'])
        self.assertEqual(hashlib.sha256(d.wkb).hexdigest(),fixture['source_domain_geometry_sha256'])
        with self.assertRaisesRegex(ValueError,'upper interface points'):
            old.construct(d,fixture['attested_source_interfaces'],.2)
        result,receipt=new.construct(d,fixture['attested_source_interfaces'],.2)
        redundant=[r for r in receipt['whole_edge_interfaces'] if r.get('strip_status')=='excluded_redundant_inside_source_domain']
        self.assertEqual([r['edge'] for r in redundant],fixture['expected_redundant_edges'])
        self.assertTrue(receipt['source_domain_coverage']['passed'])
        for r in redundant:self.assertTrue(r['whole_edge_attested']['upper'])
        self.assertTrue(new._BAND.prove_band_covered(result,d,.2)['passed'])

if __name__=='__main__':unittest.main()
