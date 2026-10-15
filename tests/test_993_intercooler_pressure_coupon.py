import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT/'twins/993-intercooler/750-hp/pressure-coupon'
# study.json keeps the repository paths of its run; the 750-hp study has since moved.
MOVED=('twins/993-installed-cooling-f1/intercooler-750/','twins/993-intercooler/750-hp/')
spec=importlib.util.spec_from_file_location('pressure_coupon',STUDY/'source/study.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

class PressureCouponTests(unittest.TestCase):
    def test_mesh_area_and_independent_pressure_resultant(self):
        for count in [0,2,4]:
            nodes,elements,loads=M.mesh(count,.2);area=0;fx=fy=0
            for e in elements:
                x0,y0=nodes[e[0]];x1,y1=nodes[e[2]];self.assertGreater(x1,x0);self.assertGreater(y1,y0);area+=(x1-x0)*(y1-y0)
            for tag,face in loads:
                e=elements[tag-1];a=nodes[e[face-1]];b=nodes[e[face%4]]
                fx-=M.PRESSURE*(b[1]-a[1]);fy+=M.PRESSURE*(b[0]-a[0])
            self.assertAlmostEqual(area,12*2.3-(11.2-count*.4)*1.5,places=7)
            self.assertAlmostEqual(fx,M.PRESSURE*1.5,places=7)
            self.assertAlmostEqual(fy,M.PRESSURE*(11.2-count*.4),places=7)
        for count,h in [(3,.2),(4,0)]:
            with self.assertRaises(ValueError):M.mesh(count,h)

    def test_native_benchmarks_and_unconverged_stress_preserved(self):
        r=json.loads((STUDY/'derived/study.json').read_text())
        for case in [r['patch'],r['traction_patch']]:
            self.assertLess(case['patch_integration_point_error_mpa'],1e-4)
            self.assertLess(case['patch_displacement_error_mm'],1e-8)
            self.assertEqual(case['solver_version'],'2.21')
        self.assertAlmostEqual(r['half_pressure_displacement_ratio'],.5,places=5)
        cases={(c['rib_count'],c['mesh_mm']):c for c in r['cases']}
        self.assertEqual(len(cases),9)
        self.assertGreater(cases[2,.1]['maximum_nodal_von_mises_mpa'],40)
        self.assertFalse(cases[0,.1]['small_displacement_screen'])
        self.assertLess(cases[4,.1]['maximum_displacement_mm'],.001)
        self.assertGreater(cases[4,.1]['maximum_nodal_von_mises_mpa']/cases[4,.2]['maximum_nodal_von_mises_mpa'],1.2)
        self.assertFalse(r['pressure_qualified']);self.assertFalse(r['manufacturing_authorized'])
        self.assertEqual(sha(STUDY/'source/study.py'),r['source_sha256'])
        for path,digest in r['dependency_hashes'].items():self.assertEqual(sha(ROOT/path.replace(*MOVED)),digest)

    def test_hydraulic_equal_pressure_channels_and_area_cost(self):
        a,b=M.hydraulic(0),M.hydraulic(4)
        self.assertAlmostEqual(b['open_area_mm2']/a['open_area_mm2'],6/7)
        self.assertGreater(b['pressure_drop_pa'],a['pressure_drop_pa'])
        self.assertEqual(a['total_mass_flow_kg_s'],b['total_mass_flow_kg_s'])
        for d in b['channels']:
            self.assertEqual(d['regime'],'laminar')
            self.assertAlmostEqual(d['pressure_drop_pa'],b['pressure_drop_pa'],places=7)
        self.assertFalse(b['hydraulic_performance_accepted'])

    def test_native_geometry_and_all_retained_provenance(self):
        r=json.loads((STUDY/'derived/review.json').read_text());self.assertFalse(r['root_stress_converged'])
        for run in r['geometry_runs']:
            self.assertLess(run['volume_partition_error'],.01)
            receipt=run['native_receipt'];self.assertEqual(receipt['field_count'],7);self.assertTrue(receipt['geometry_roundtrip_exact'])
            self.assertFalse(receipt['manufacturing_authorized']);self.assertEqual(run['parts']['hot_fluid_mm']['components'],5)
            self.assertEqual(hashlib.sha256(gzip.decompress((STUDY/'derived'/run['vdb_gzip']).read_bytes())).hexdigest(),receipt['vdb_sha256'])
            for part in run['parts'].values():self.assertLess(part['cleanup_volume_error'],1e-7)
        fine=next(x for x in r['geometry_runs'] if x['voxel_mm']==.1)
        for measured,expected in zip(fine['parts']['hot_fluid_mm']['channel_widths_y_mm'],[1.8,1.8,5.2,5.2,5.2]):self.assertAlmostEqual(measured,expected,delta=.02)
        for path,digest in r['source_hashes'].items():self.assertEqual(sha(STUDY/path),digest)
        for path,digest in r['output_hashes'].items():self.assertEqual(sha(STUDY/'derived'/path),digest)
        for p in (STUDY/'derived/fea').glob('*/receipt.json'):
            for name,digest in json.loads(p.read_text())['source_hashes'].items():
                data=gzip.decompress((p.parent/(name+'.gz')).read_bytes()) if name.endswith(('.frd','.dat')) else (p.parent/name).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(),digest)
        runtime=json.loads((STUDY/'runtime.json').read_text())
        self.assertEqual(sha(STUDY/runtime['inherited_upstream_receipt']),runtime['inherited_receipt_sha256'])
        for path,digest in runtime['source_hashes'].items():self.assertEqual(sha(STUDY/path),digest)

FILLET=STUDY/'derived/fillet-convergence'
spec=importlib.util.spec_from_file_location('fillet_convergence',STUDY/'source/fillet_convergence.py');F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)


class FilletConvergenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads((FILLET/'fillet-convergence.json').read_text())

    def test_richardson_and_area_helpers(self):
        r=F.richardson([10+4.**-l for l in range(4)])
        self.assertAlmostEqual(r['observed_order'],2,places=9);self.assertAlmostEqual(r['extrapolated'],10,places=9);self.assertTrue(r['converged_within_gci'])
        self.assertFalse(F.richardson([16.,22.7,30.6,42.2])['monotone_convergence'])
        self.assertAlmostEqual(F.solid_area(0),12*2.3-1.5*(11.2-4*.4),places=12)
        self.assertEqual(F.ROOT_CORNERS,[(2.6,1.5),(3.4,1.5),(8.6,1.5),(9.4,1.5),(11.2,1.5)])

    def test_every_case_balances_pressure_and_keeps_provenance(self):
        r=self.r;self.assertEqual(len(r['cases']),len(F.RADII)*len(F.GLOBAL_MM))
        for c in r['cases']:
            fx,fy=c['pressure_resultant_n_per_mm']
            self.assertAlmostEqual(fx,M.PRESSURE*1.5,places=9);self.assertAlmostEqual(fy,M.PRESSURE*(11.2-4*.4),places=9)
            self.assertAlmostEqual(c['reaction_xsym_n_per_mm'][0],-fx,places=6);self.assertAlmostEqual(c['reaction_ysym_n_per_mm'][1],-fy,places=6)
            self.assertAlmostEqual(c['cad_area_mm2'],F.solid_area(c['fillet_radius_mm']),places=9)
            self.assertEqual(c['solver_version'],'2.21');self.assertTrue(c['fillet_radius_is_assumption']);self.assertFalse(c['pressure_qualified'])
            receipt=json.loads((FILLET/f"fillet-{c['fillet_radius_mm']}-level-{c['level']}/receipt.json").read_text());self.assertEqual(receipt,c)
            log=FILLET/f"fillet-{c['fillet_radius_mm']}-level-{c['level']}/solver.log";self.assertEqual(sha(log),c['source_hashes']['solver.log'])
        self.assertEqual(sha(STUDY/'source/fillet_convergence.py'),r['source_sha256'])
        for path,digest in r['dependency_hashes'].items():self.assertEqual(sha(ROOT/path),digest)
        self.assertTrue(r['fillet_radii_are_assumptions']);self.assertFalse(r['pressure_qualified']);self.assertFalse(r['manufacturing_authorized'])

    def test_sharp_roots_diverge_and_assumed_fillets_converge(self):
        s=self.r['summary'];sharp=s['0.0']['root_nodal_von_mises_mpa']
        # A 270-degree re-entrant corner has a Williams exponent near 0.545: each halving multiplies the peak by about 2**0.455.
        for a,b in zip(sharp,sharp[1:]):self.assertGreater(b/a,1.25);self.assertLess(b/a,1.5)
        self.assertFalse(s['0.0']['root_nodal_richardson']['monotone_convergence'])
        for radius in ['0.2','0.4']:
            for key in ['root_nodal_richardson','integration_point_richardson','displacement_richardson']:self.assertTrue(s[radius][key]['converged_within_gci'],(radius,key))
            self.assertLess(s[radius]['root_nodal_richardson']['extrapolated'],self.r['assumed_threshold_mpa'])
        self.assertLess(s['0.4']['root_nodal_richardson']['extrapolated'],s['0.2']['root_nodal_richardson']['extrapolated'])
        original=next(c for c in json.loads((STUDY/'derived/study.json').read_text())['cases'] if (c['rib_count'],c['mesh_mm'])==(4,.1))
        self.assertAlmostEqual(s['0.0']['maximum_displacement_mm'][-1]/original['maximum_displacement_mm'],1,delta=.01)

if __name__=='__main__':unittest.main()
