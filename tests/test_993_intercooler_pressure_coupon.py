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

HYDRAULICS=STUDY/'derived/fillet-hydraulics/fillet-hydraulics.json'
spec=importlib.util.spec_from_file_location('fillet_hydraulics',STUDY/'source/fillet_hydraulics.py');H=importlib.util.module_from_spec(spec);spec.loader.exec_module(H)


class FilletHydraulicsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads(HYDRAULICS.read_text())

    def test_receipt_provenance_and_flags(self):
        r=self.r;self.assertEqual(sha(STUDY/'source/fillet_hydraulics.py'),r['source_sha256'])
        for path,digest in r['dependency_hashes'].items():self.assertEqual(sha(ROOT/path),digest)
        self.assertTrue(r['fillet_radii_are_assumptions'])
        for key in ['hydraulic_performance_accepted','thermal_gain_claimed','manufacturing_authorized','resolved_thermal_or_flow_simulation']:self.assertFalse(r[key])
        self.assertEqual(r['clear_widths_mm'],[1.8,5.2,5.2,5.2,1.8]);self.assertEqual(H.widths(),r['clear_widths_mm'])

    def test_sections_match_exact_rectangle_and_drawn_fillet_area(self):
        # Square duct: the exact series gives the textbook Darcy fRe of 56.91.
        self.assertAlmostEqual(H.friction_re(9,12,H.rectangle_w_integral(3,3)),56.908,places=2)
        for s in self.r['sections']:
            self.assertAlmostEqual(s['fe_area_mm2'],s['analytic_area_mm2'],delta=1e-6 if s['element_size_mm']<=.05 else 2e-4)
            self.assertAlmostEqual(s['cad_perimeter_mm'],s['analytic_perimeter_mm'],delta=1e-9)
            if s['fillet_radius_mm']==0:self.assertAlmostEqual(s['w_integral_mm4']/H.rectangle_w_integral(s['width_mm'],s['height_mm']),1,delta=1e-4 if s['element_size_mm']>.05 else 1e-6)
        for v in self.r['variants'].values():
            for c in v['w_integral_convergence'].values():self.assertTrue(c['converged_within_gci']);self.assertLess(c['gci_fine'],1e-6)
            self.assertAlmostEqual(v['open_area_mm2'],57.6-20*(1-3.141592653589793/4)*v['fillet_radius_mm']**2,places=5)

    def test_equal_pressure_split_reproduces_study_and_orders_radii(self):
        r=self.r;drops=[]
        self.assertAlmostEqual(r['study_rectangular_proxy']['pressure_drop_pa'],M.hydraulic(4)['pressure_drop_pa'],places=9)
        self.assertAlmostEqual(r['sharp_exact_series_split']['pressure_drop_pa']/r['study_rectangular_proxy']['pressure_drop_pa'],1,delta=1e-3)
        for radius in ['0.0','0.2','0.4']:
            v=r['variants'][radius];split=H.split(v['channel_sections']);self.assertEqual(split,v['split'])
            self.assertAlmostEqual(split['mass_flow_closure'],0,places=12);self.assertEqual(split['total_mass_flow_kg_s'],M.hydraulic(4)['total_mass_flow_kg_s'])
            for c in split['channels']:self.assertAlmostEqual(c['pressure_drop_pa'],split['pressure_drop_pa'],places=7);self.assertLess(c['re'],2300)
            drops.append(split['pressure_drop_pa'])
        self.assertAlmostEqual(drops[0]/r['sharp_exact_series_split']['pressure_drop_pa'],1,delta=1e-6)
        self.assertLess(drops[0],drops[1]);self.assertLess(drops[1],drops[2])
        # Developing flow is not resolved: the wide channels never become fully developed in 24 mm.
        self.assertGreater(max(c['hydrodynamic_entry_length_over_length'] for c in r['variants']['0.2']['split']['channels']),1)

CFD=STUDY/'derived/channel-cfd'
spec=importlib.util.spec_from_file_location('channel_cfd',STUDY/'source/channel_cfd.py');C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)


class ChannelCfdTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads((CFD/'channel-cfd.json').read_text())

    def test_receipts_logs_and_provenance(self):
        r=self.r;self.assertEqual(sha(STUDY/'source/channel_cfd.py'),r['source_sha256'])
        for path,digest in r['dependency_hashes'].items():self.assertEqual(sha(ROOT/path),digest)
        self.assertEqual(len(r['cases']),len(C.RADII)*2*(len(C.SIZES_MM)+1))
        for c in r['cases']:
            folder=CFD/f"r{c['fillet_radius_mm']}-w{c['width_mm']}-level-{c['level']}-dp{c['pressure_factor']}"
            self.assertEqual(json.loads((folder/'receipt.json').read_text()),c)
            for name in ['mesh.log','solver.log']:self.assertEqual(hashlib.sha256(gzip.decompress((folder/(name+'.gz')).read_bytes())).hexdigest(),c['source_hashes'][name])
            for name in ['system/controlDict','system/fvSchemes','system/fvSolution','constant/physicalProperties','constant/momentumTransport','0/U','0/p']:self.assertEqual(sha(folder/name),c['source_hashes'][name])
            self.assertTrue(c['simple_converged']);self.assertLess(c['flow_rate_drift_last_50'],1e-5);self.assertAlmostEqual(c['outlet_to_inlet_flow_ratio'],1,delta=1e-6)
            self.assertEqual(c['cells'],c['hexahedra']);self.assertEqual(c['cells'],c['section_cells']*c['axial_cells']);self.assertTrue(c['fillet_radius_is_assumption'])
            self.assertAlmostEqual(c['cad_quarter_area_mm2'],H.channel_area(c['width_mm'],3,c['fillet_radius_mm'])/4,places=9)
        for key in ['hydraulic_performance_accepted','thermal_gain_claimed','manufacturing_authorized','resolved_thermal_or_flow_simulation']:self.assertFalse(r[key])

    def test_dictionaries_regenerate_and_axial_spacing(self):
        rho,mu,_=H.gas();c=self.r['cases'][0]
        folder=CFD/f"r{c['fillet_radius_mm']}-w{c['width_mm']}-level-{c['level']}-dp{c['pressure_factor']}"
        for name,text in C.dictionaries(mu/rho,c['pressure_difference_pa']/rho).items():self.assertEqual((folder/name).read_text(),text)
        for size in C.SIZES_MM:
            h=C.axial_layers(size);self.assertEqual(h[-1],1.);self.assertTrue(all(b>a for a,b in zip(h,h[1:])))

    def test_split_and_comparison_with_proxy(self):
        r=self.r;proxy=json.loads(HYDRAULICS.read_text())
        for radius,v in r['variants'].items():
            curves=[tuple(v['finest_fit_a_b'][str(w)]) for w in r['clear_widths_mm']];split=C.split(curves)
            self.assertEqual(split,v['finest_split']);self.assertAlmostEqual(sum(split['channel_mass_flow_kg_s'])/split['total_mass_flow_kg_s'],1,delta=1e-12)
            for (a,b),m in zip(curves,split['channel_mass_flow_kg_s']):self.assertAlmostEqual(a*m+b*m*m,split['pressure_drop_pa'],places=6);self.assertGreater(a,0)
            self.assertEqual(v['fully_developed_proxy_pressure_drop_pa'],proxy['variants'][radius]['split']['pressure_drop_pa'])
            # The unstructured section meshes do not converge monotonically everywhere; the level-to-level spread stays below 1.5 %.
            for w in v['mass_flow_convergence_at_0_95_proxy_dp']:
                flows=[c['mass_flow_kg_s'] for c in r['cases'] if (str(c['fillet_radius_mm']),str(c['width_mm']),c['pressure_factor'])==(radius,w,C.CONVERGENCE_FACTOR)]
                self.assertEqual(len(flows),len(C.SIZES_MM));self.assertLess(max(flows)/min(flows)-1,.015)
            # Developing flow with a quiescent-plenum inlet costs a few percent more than the fully developed proxy with K = 2.
            self.assertGreater(v['finest_over_proxy'],1);self.assertLess(v['finest_over_proxy'],1.05)

GEOMETRY=STUDY/'derived/fillet-geometry/fillet-geometry.json'


class FilletGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads(GEOMETRY.read_text())

    def test_sources_runtime_and_flags(self):
        r=self.r
        for path,digest in r['source_hashes'].items():self.assertEqual(sha(STUDY/path),digest)
        for path,digest in r['output_hashes'].items():self.assertEqual(sha(GEOMETRY.parent/path),digest)
        for run in r['runs']:
            rt,receipt=run['runtime'],run['native_receipt']
            self.assertEqual(rt['program_sha256'],sha(STUDY/'source/picogk-fillet/Program.cs'));self.assertEqual(rt['project_sha256'],sha(STUDY/'source/picogk-fillet/CouponFillet.csproj'))
            self.assertEqual(rt['picogk_runtime_commit'],'0f26321c18ed878a7820ef769c38fd5d49d39242');self.assertFalse(rt['latticelibrary_locked'])
            self.assertTrue(receipt['fillet_radius_is_assumption']);self.assertFalse(receipt['manufacturing_authorized']);self.assertFalse(receipt['pressure_qualified'])
            self.assertTrue(receipt['geometry_roundtrip_exact']);self.assertEqual(receipt['field_count'],7);self.assertEqual(receipt['vdb_sha256'],run['vdb_sha256'])
            if receipt['fillet_radius_mm']:self.assertGreaterEqual(receipt['fillet_radius_mm']/receipt['voxel_mm'],4-1e-6)
        for key in ['pressure_qualified','manufacturing_authorized','stl_and_vdb_committed','thermal_or_hydraulic_solver_executed']:self.assertFalse(r[key])
        # The Mac receipts stay the record of the Mac runs.
        self.assertEqual(json.loads((STUDY/'runtime.json').read_text())['source_hashes']['source/picogk/Program.cs'],sha(STUDY/'source/picogk/Program.cs'))

    def test_channels_topology_and_fillet_area(self):
        r=self.r
        for run in r['runs']:
            self.assertLess(run['volume_partition_error'],.01)
            hot=run['parts']['hot_fluid_mm'];self.assertEqual(hot['components'],5)
            for c,width in zip(hot['channels'],[1.8,5.2,5.2,5.2,1.8]):self.assertAlmostEqual(c['width_y_mm'],width,delta=.02);self.assertAlmostEqual(c['height_z_mm'],3,delta=.02)
            for part in run['parts'].values():self.assertLess(part['cleanup_volume_error'],1e-7);self.assertTrue(part['closed_after_cleanup'])
        self.assertEqual({(x['fillet_radius_mm'],x['voxel_mm']) for x in r['fillet_area_checks']},{(.4,.1),(.2,.05),(.4,.05)})
        for check in r['fillet_area_checks']:
            self.assertAlmostEqual(check['analytic_corner_area_mm2'],(1-3.141592653589793/4)*check['fillet_radius_mm']**2,places=12)
            self.assertEqual(check['within_tolerance'],all(abs(e)<=r['fillet_area_tolerance'] for e in check['relative_errors']))
            # At 0.05 mm voxels both assumed fillets match (1 - pi/4) r^2 within the tolerance fixed before the runs.
            if check['voxel_mm']==.05:self.assertTrue(check['within_tolerance'])
        # At 0.1 mm voxels the 0.4 mm fillet spans only four voxels; the middle channel misses the tolerance and stays recorded as failed.
        self.assertEqual(r['fillet_area_checks_failed'],['r0.4-v0.1'])
        self.assertEqual(r['fillet_area_tolerance'],.15)

    def test_fillet_error_depends_on_measured_body(self):
        # The README quotes the fillet error on both the solid and the hot-fluid side, because the meshes do not partition exactly.
        r=self.r;runs={x['name']:x for x in r['runs']};vol=lambda run,part:run['parts'][part]['volume_mm3']
        expected={'r0.2-v0.05':(.012,-.053,.27),'r0.4-v0.05':(-.005,-.0215,.27),'r0.4-v0.1':(-.018,-.083,1.06)}
        for check in r['fillet_area_checks']:
            run=runs['r0-'+check['name'].split('-')[1]];filleted=runs[check['name']]
            analytic=check['analytic_solid_volume_gain_mm3']
            solid=vol(filleted,'solid_mm')-vol(run,'solid_mm');hot=vol(run,'hot_fluid_mm')-vol(filleted,'hot_fluid_mm')
            self.assertAlmostEqual(solid,check['solid_volume_gain_mm3'],places=9);self.assertAlmostEqual(analytic,20*check['analytic_corner_area_mm2']*24,places=9)
            self.assertAlmostEqual(hot,4*24*sum(check['measured_corner_area_mm2']),delta=1e-3)
            self.assertEqual(vol(filleted,'cold_fluid_mm'),vol(run,'cold_fluid_mm'))
            solid_error,hot_error,mismatch=expected[check['name']]
            self.assertAlmostEqual(solid/analytic-1,solid_error,delta=.0005);self.assertAlmostEqual(hot/analytic-1,hot_error,delta=.0005);self.assertAlmostEqual(solid-hot,mismatch,delta=.005)

import math
CHOICE=STUDY/'derived/fillet-radius-choice/fillet-radius-choice.json'
CRITERION=STUDY/'fillet-radius/criterion.json'
CAPABILITY=STUDY/'fillet-radius/process-capability.json'
PLAN=STUDY/'fillet-radius/3d-study-plan.json'
DECISION=ROOT/'docs/decisions/0023-intercooler-rib-root-fillet-0-4-mm.md'
spec=importlib.util.spec_from_file_location('fillet_radius_choice',STUDY/'source/fillet_radius_choice.py');R=importlib.util.module_from_spec(spec);spec.loader.exec_module(R)


class FilletRadiusChoiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads(CHOICE.read_text());cls.criterion=json.loads(CRITERION.read_text());cls.capability=json.loads(CAPABILITY.read_text());cls.plan=json.loads(PLAN.read_text())

    def test_criterion_is_the_one_committed_before_the_source_search(self):
        # The criterion was committed alone, before the sources and the evaluation. Amending it must be a visible act: this digest changes.
        self.assertEqual(sha(CRITERION),'03c00b96fb120dce3bfb5509c51f01f72f21aee8b4cc68ead3499f909cbd829b')
        self.assertEqual(self.criterion['candidates_mm'],[.2,.4]);self.assertEqual([t['id'] for t in self.criterion['tests']],['M1','H1','M2','P1','P2','P3'])
        self.assertEqual(list(self.criterion['classes_best_first']),R.CLASSES)
        for key in ['pressure_qualified','manufacturing_authorized','lpbf_process_qualified']:self.assertFalse(self.criterion[key])

    def test_report_is_reproduced_from_its_inputs_without_a_solver(self):
        self.assertEqual(R.evaluate(),self.r);self.assertEqual(sha(STUDY/'source/fillet_radius_choice.py'),self.r['source_sha256'])
        for path,digest in self.r['input_hashes'].items():self.assertEqual(sha(ROOT/path),digest)
        self.assertEqual(len(self.r['input_hashes']),5)
        for key in ['pressure_qualified','manufacturing_authorized','lpbf_process_qualified','new_finite_element_or_cfd_run']:self.assertFalse(self.r[key])
        source=(STUDY/'source/fillet_radius_choice.py').read_text()
        for word in ['docker','ccx','gmsh','numpy']:self.assertNotIn(word,source)

    def test_closed_forms(self):
        lam=R.williams_lambda();self.assertAlmostEqual(math.sin(1.5*math.pi*lam),lam,places=12);self.assertAlmostEqual(lam,.5445,places=4)
        # A straight edge (180 degrees of solid) has no singular root in the bracket: the function refuses rather than returning a number.
        with self.assertRaises(ValueError):R.williams_lambda(180.)
        self.assertAlmostEqual(R.sagitta(.2),.2*math.sqrt(2)-.2,places=15);self.assertAlmostEqual(R.sagitta(.4)/R.sagitta(.2),2)
        self.assertIsNone(R.low_radius_peak(10.,.2,.2,.4555));self.assertIsNone(R.low_radius_peak(10.,.2,.3,.4555))
        self.assertAlmostEqual(R.low_radius_peak(10.,.4,.2,.5),10*math.sqrt(2));self.assertEqual(R.low_radius_peak(10.,.4,0.,.5),10.)
        s=self.r['scaling_validity_check'];self.assertTrue(s['valid']);self.assertAlmostEqual(s['predicted_peak_ratio'],2**(1-lam));self.assertLess(abs(s['relative_difference']),.01)
        summary=json.loads((FILLET/'fillet-convergence.json').read_text())['summary']
        self.assertAlmostEqual(s['retained_nodal_peak_ratio'],summary['0.2']['root_nodal_richardson']['extrapolated']/summary['0.4']['root_nodal_richardson']['extrapolated'])
        for radius in ['0.2','0.4']:
            upper=R.upper_peak(summary[radius]);self.assertEqual(upper,self.r['radii'][radius]['tests']['M1']['upper_peak_mpa'])
            self.assertGreaterEqual(upper,summary[radius]['root_nodal_richardson']['extrapolated']);self.assertLess(upper/summary[radius]['root_nodal_richardson']['extrapolated'],1.03)

    def test_decision_rules(self):
        d=R.decide({.2:'unsettled',.4:'unsettled'});self.assertEqual((d['proposed_radius_mm'],d['rule'],d['other_radius_stays_in_3d_study']),(.4,'R4',True))
        d=R.decide({.2:'sourced',.4:'unsettled'});self.assertEqual((d['proposed_radius_mm'],d['rule'],d['design_assumption_only']),(.2,'R3',False))
        d=R.decide({.2:'not_distinguishable',.4:'unsettled'});self.assertEqual((d['proposed_radius_mm'],d['rule'],d['other_radius_stays_in_3d_study']),(.4,'R3',False))
        for classes in [{.2:'not_distinguishable',.4:'not_distinguishable'},{.2:'rejected',.4:'not_distinguishable'}]:
            d=R.decide(classes);self.assertIsNone(d['proposed_radius_mm']);self.assertEqual(d['rule'],'R2')
        base={k:{'result':'pass'} for k in ['M1','H1','M2','P1','P3']};base['P2']={'result':'pass','every_scale_sourced':True}
        self.assertEqual(R.classify(base),'sourced')
        for key,expected in [('M1','rejected'),('H1','rejected'),('M2','not_distinguishable'),('P1','not_distinguishable'),('P2','not_distinguishable')]:
            self.assertEqual(R.classify({**base,key:{**base[key],'result':'fail'}}),expected)
        self.assertEqual(R.classify({**base,'P3':{'result':'not_met'}}),'unsettled');self.assertEqual(R.classify({**base,'M2':{'result':'not_evaluable'}}),'unsettled')
        self.assertEqual(R.classify({**base,'P2':{'result':'pass','every_scale_sourced':False}}),'unsettled')

    def test_p3_counts_only_a_complete_on_route_measurement(self):
        route=self.capability['route']
        good={'source_id':'SRC-EOS-ALSI10MG-M290-30UM','alloy':'AlSi10Mg','process':'laser powder bed fusion','feature':'concave_radius',
              'design_radius_mm':.4,'as_built_radius_mm':.37,'uncertainty_mm':.02}
        self.assertEqual(R.p3_refusals(good,.4,route),[])
        self.assertEqual(R.p3_refusals(good,.2,route),['designed above 0.2 mm'])
        for change,reason in [({'source_id':'SRC-NOT-REGISTERED'},'no registered source record'),({'alloy':'Ti6Al4V'},'not AlSi10Mg by laser powder bed fusion'),
                              ({'feature':'wall_thickness'},'not a concave radius'),({'as_built_radius_mm':None},'no as-built radius'),
                              ({'uncertainty_mm':0},'no positive uncertainty'),({'design_radius_mm':'0.4'},'no design radius')]:
            with self.subTest(change=change):
                self.assertIn(reason,R.p3_refusals({**good,**change},.4,route))
        bare=[{'design_radius_mm':.2}]
        self.assertEqual([R.p3_refusals(m,.4,route) for m in bare],[['no registered source record','not AlSi10Mg by laser powder bed fusion','not a concave radius','no as-built radius','no positive uncertainty']])

    def test_every_process_figure_has_a_source_record_and_gaps_stay_null(self):
        c=self.capability;ids=set()
        for name,scale in c['scales'].items():
            for row in scale['on_route']+scale['indicative']+scale.get('recommendations_that_are_not_capability_limits',[]):
                self.assertIsInstance(row['value'],float,name);self.assertGreater(row['value'],0);ids.add(row['source_id'])
        for entry in c['context_not_deciding'].values():ids.update([entry['source_id']] if 'source_id' in entry else entry.get('source_ids',[]))
        ids.update(s['source_id'] for s in c['standards_cited_by_designation_only'])
        self.assertEqual(len(ids),13)
        for source_id in ids:
            record=json.loads((ROOT/'catalog/sources'/(source_id.lower()+'.json')).read_text());self.assertEqual(record['source_id'],source_id)
        for s in c['standards_cited_by_designation_only']:
            self.assertFalse(s['read']);self.assertEqual(json.loads((ROOT/'catalog/sources'/(s['source_id'].lower()+'.json')).read_text())['access']['status'],'paywalled')
        # What the sources do not give stays empty rather than filled: no Rz, accuracy or minimum detail on the reference route, and no measured radius.
        for name in ['as_built_roughness_rz_mm','delta_offset_mm','minimum_internal_radius_or_detail_mm']:self.assertEqual(c['scales'][name]['on_route'],[])
        self.assertEqual(c['as_built_concave_radius_measurements'],[])
        for key in ['does_any_source_state_a_minimum_internal_radius_for_lpbf_alsi10mg','does_any_source_measure_an_as_built_concave_radius_in_lpbf_alsi10mg','do_the_sources_settle_whether_0_2_mm_can_be_held','do_the_sources_settle_whether_0_4_mm_can_be_held']:self.assertFalse(c['verdict'][key])
        for key in ['measured_or_printed_by_this_project','lpbf_process_qualified','manufacturing_authorized']:self.assertFalse(c[key])
        process=json.loads((ROOT/'catalog/manufacturing/processes/eos-m290-alsi10mg-30um.json').read_text())['process_reference']
        self.assertEqual(c['scales']['layer_thickness_mm']['on_route'][0]['value'],process['layer_thickness_um']/1000)
        self.assertEqual(max(x['value'] for x in c['scales']['powder_upper_size_mm']['on_route']),process['sieve_um']/1000)
        self.assertEqual(c['context_not_deciding']['minimum_wall_mm']['value'],process['minimum_wall_thickness_mm'])
        machine=json.loads((ROOT/'catalog/manufacturing/machines/eos-m290.json').read_text());self.assertEqual(c['context_not_deciding']['laser_focus_diameter_mm']['value'],machine['focus_diameter_um']/1000)

    def test_outcome_and_how_narrow_it_is(self):
        r=self.r;small,large=r['radii']['0.2'],r['radii']['0.4']
        self.assertEqual(r['classes'],{'0.2':'not_distinguishable','0.4':'unsettled'})
        self.assertEqual(r['decision'],{'proposed_radius_mm':.4,'rule':'R3','design_assumption_only':True,'other_radius_mm':.2,'other_radius_stays_in_3d_study':False})
        for radius in [small,large]:
            self.assertEqual({k:v['result'] for k,v in radius['tests'].items() if k!='P2'},{'M1':'pass','H1':'pass','M2':'not_evaluable','P1':'not_evaluable','P3':'not_met'})
            self.assertEqual(radius['tests']['P2']['scales_not_sourced_on_route'],['as_built_roughness_rz_mm']);self.assertLess(radius['tests']['M1']['upper_peak_mpa'],r['assumed_screen_mpa'])
        # 0.2 mm fails on one figure only, the 0.09 mm sieve cut, by about 8 %.
        failed=[x for x in small['tests']['P2']['on_route'] if not x['form_above_scale']]
        self.assertEqual([(x['scale'],x['value_mm']) for x in failed],[('powder_upper_size_mm',.09)]);self.assertAlmostEqual(failed[0]['form_over_scale'],.92,places=2)
        self.assertEqual(large['tests']['P2']['result'],'pass');self.assertGreater(min(x['form_over_scale'] for x in large['tests']['P2']['on_route']),1.8)
        # The other reading of the powder scale keeps 0.2 mm as an arm but proposes the same radius.
        a=r['criterion_ambiguity'];self.assertTrue(a['found_at_evaluation']);self.assertEqual(a['classes_if_only_the_smaller_figure_counted'],{'0.2':'unsettled','0.4':'unsettled'})
        self.assertEqual(a['decision_if_only_the_smaller_figure_counted']['proposed_radius_mm'],.4);self.assertTrue(a['decision_if_only_the_smaller_figure_counted']['other_radius_stays_in_3d_study'])
        hydraulics=json.loads(HYDRAULICS.read_text())['variants']
        for key,radius in [('0.2',small),('0.4',large)]:self.assertAlmostEqual(radius['tests']['H1']['hydraulic_penalty'],hydraulics[key]['split']['pressure_drop_pa']/hydraulics['0.0']['split']['pressure_drop_pa']-1)
        # Indicative figures never decide: a 0.2 mm shortfall would leave the 0.2 mm root sharp, with no stress to quote.
        sharp=[x for x in small['tests']['M2']['indicative_not_deciding'] if x['low_radius_peak_mpa'] is None];self.assertEqual([x['delta_offset_mm'] for x in sharp],[.2])
        self.assertTrue(all(x['below_assumed_screen'] for x in large['tests']['M2']['indicative_not_deciding']))

    def test_3d_plan_is_predeclared_not_executed_and_keeps_unknowns_null(self):
        p=self.plan;self.assertEqual(p['status'],'predeclared_not_executed');self.assertFalse(p['executed']);self.assertTrue(p['blocked'])
        self.assertEqual([(a['id'],a['radius_mm']) for a in p['arms']],[('A',self.r['decision']['proposed_radius_mm']),('S',0.),('L',None)])
        self.assertEqual(p['analyses']['CHT']['arms'],['A','S'])
        for name in ['M-P','M-T']:self.assertNotIn('S',p['analyses'][name]['arms'])
        supports=p['analyses']['M-T']['supports'];self.assertIn('declared bench support of IN-03',supports);self.assertIn('waits for IN-02',supports);self.assertNotIn('Waits for IN-03',supports)
        self.assertFalse(self.r['decision']['other_radius_stays_in_3d_study']);self.assertIn('0.2 mm',p['arms_excluded'][0]['root'])
        inputs={i['id']:i for i in p['required_inputs']};self.assertEqual(len(inputs),15)
        for i in inputs.values():
            self.assertTrue(i['must_come_from']);self.assertIn('value',i)
            if i['value'] is not None:self.assertIn('status',i)
        # 2026-11-18: closure and fixture are declared design decisions; the fitting, its loads and the cold-side flow still block.
        self.assertEqual(sorted(k for k,i in inputs.items() if i['blocking']),['IN-02','IN-04','IN-10'])
        for key in ['IN-02','IN-06','IN-07','IN-13','IN-14','IN-15']:self.assertIsNone(inputs[key]['value'])
        for key in ['IN-01','IN-03']:
            self.assertTrue(inputs[key]['status'].startswith('declared design decision'));self.assertEqual(inputs[key]['depends_on'],['IN-02'])
        self.assertTrue(inputs['IN-04']['status'].startswith('declared bench load'))
        self.assertEqual(inputs['IN-04']['remaining_null'],['outlet_end_load_n','fitting_preload_n'])
        for key in inputs['IN-04']['remaining_null']:self.assertIsNone(inputs['IN-04']['value'][key])
        # Filling inputs changed nothing else: method, arms, rules and limits keep the digest they had on 2026-11-12.
        rest={k:v for k,v in p.items() if k!='required_inputs'}
        self.assertEqual(hashlib.sha256(json.dumps(rest,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),'831203561ae882ee799cdecdcc3e232479cbd619ba964c9d875c70c05993af62')
        self.assertIsNone(inputs['IN-10']['value']['cold_kg_s']);self.assertEqual(inputs['IN-10']['value']['hot_kg_s'],M.hydraulic(4)['total_mass_flow_kg_s'])
        self.assertEqual(inputs['IN-05']['value']['numerical_proof_case_mpa'],M.PRESSURE);self.assertEqual(inputs['IN-11']['value'],{'elastic_modulus_mpa':M.E,'poisson_ratio':M.NU})
        pressure=json.loads((STUDY.parent/'hot-weather/assumptions.json').read_text())['pressure']
        self.assertEqual(inputs['IN-05']['value'],{'service_mpa':pressure['service_gauge_pa']/1e6,'numerical_proof_case_mpa':pressure['exploratory_proof_gauge_pa']/1e6})
        self.assertIsNone(json.loads((STUDY.parent/'requirements.json').read_text())['unknown']['boost_bar_gauge'])
        # The closed-form perimeter bound quoted in the plan follows from the retained hydraulic report.
        sections={(s['fillet_radius_mm'],s['width_mm']):s['cad_perimeter_mm'] for s in json.loads(HYDRAULICS.read_text())['sections']}
        perimeter=lambda radius:sum(sections[radius,w] for w in H.widths())
        self.assertAlmostEqual(1-perimeter(.4)/perimeter(0.),.0502,places=4);self.assertAlmostEqual(1-perimeter(.2)/perimeter(0.),.0251,places=4)
        self.assertAlmostEqual(perimeter(0.)-perimeter(.4),20*(2-math.pi/2)*.4,places=9)
        self.assertEqual(set(p['separate_gates_not_addressed_by_this_study']),{'gyroid_header','lpbf_orientation_and_overhang','depowdering','sealing','hot_material'})
        for gate in p['separate_gates_not_addressed_by_this_study'].values():self.assertEqual(gate['state'],'open')
        limits=p['compute_limits'];self.assertIn('none',limits['paid_or_remote_compute']);self.assertIsNone(limits['largest_mesh']);self.assertIsNone(limits['wall_clock_budget_per_case_h'])
        self.assertIn('0019',p['contributor_request']['basis']);self.assertIn('never a task for the owner',p['contributor_request']['addressed_to'])
        for key in ['pressure_qualified','manufacturing_authorized','lpbf_process_qualified','physical_test_authorized']:self.assertFalse(p[key])

    def test_decision_record_is_accepted_and_claims_nothing_else(self):
        text=DECISION.read_text()
        for phrase in ['**Accepted** as written by the project owner on 2026-11-18','issues/467#issuecomment-6975630822','0.2 mm is not kept as a second arm','carries a 0.4 mm rib-root fillet','design assumption for the 3D study only','**No pressure strength.**','**No print authorisation and no pressure-test authorisation.**','**No LPBF qualification.**','nobody is paid or commissioned']:self.assertIn(phrase,text)
        self.assertNotIn('**Proposed**',text)
        readme=(STUDY/'README.md').read_text();self.assertIn('accepted as a design assumption, not shown to be held by any machine',readme);self.assertIn('planned, not run',readme)
        self.assertEqual(self.plan['blocked_by'],'the null entries of required_inputs marked blocking')


import os
import re
INPUTS=STUDY/'fillet-radius/3d-inputs.json'
PROGRAM=STUDY/'source/picogk/Program.cs'
DDK_BRIDGE=ROOT/'twins/964-chassis/ddk-interface-bridge-20261104/reviewed-leads.json'
spec=importlib.util.spec_from_file_location('owner_data_screen',STUDY/'source/owner_data_screen.py');S=importlib.util.module_from_spec(spec);spec.loader.exec_module(S)


def walk(value):
    if isinstance(value,dict):
        for k,v in value.items():yield k,v;yield from walk(v)
    elif isinstance(value,list):
        for v in value:yield from walk(v)


class ThreeDInputsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d=json.loads(INPUTS.read_text());cls.plan=json.loads(PLAN.read_text())

    def test_every_cited_source_record_is_registered(self):
        ids={i for k,v in walk([self.d,self.plan['required_inputs']]) if k=='source_ids' for i in v}
        self.assertIn('SRC-AUTOATLANTA-993-TURBO-60MM-HOSE-CLAMP',ids);self.assertLessEqual(ids,set(self.d['source_ids']))
        for source_id in ids:
            record=json.loads((ROOT/'catalog/sources'/(source_id.lower()+'.json')).read_text());self.assertEqual(record['source_id'],source_id)
        for path in [v for k,v in walk(self.d) if k=='repository_file']:self.assertTrue((ROOT/path).exists(),path)
        for i in ['IN-01','IN-02','IN-03','IN-04','IN-10']:
            entry=next(x for x in self.plan['required_inputs'] if x['id']==i)
            self.assertIn('3d-inputs.json',json.dumps(entry));self.assertEqual(entry['blocking'],self.d['inputs'][i]['blocking'])

    def test_declared_numbers_trace_to_the_retained_coupon(self):
        text=PROGRAM.read_text()
        lo,hi={},{}
        for name in ['envelope','hot','coldBox']:
            m=re.search(r'Voxels '+name+r'=Box\(new\(([^)]*)\),new\(([^)]*)\)\)',text);lo[name],hi[name]=[[float(v.rstrip('f')) for v in g.split(',')] for g in m.groups()]
        c=self.d['inputs']['IN-01']['decision']
        self.assertEqual(c['C3_plenum']['inner_section_mm'],[round(hi['hot'][1]-lo['hot'][1],6),round(hi['hot'][2]-lo['hot'][2],6)])
        self.assertAlmostEqual(c['C1_topology']['port_axis_z_mm'],(lo['hot'][2]+hi['hot'][2])/2);self.assertEqual(c['C1_topology']['port_axis_y_mm'],0)
        self.assertEqual(c['C2_ribbed_length']['length_mm'],hi['envelope'][0]-lo['envelope'][0])
        self.assertAlmostEqual(c['C5_walls']['wall_mm'],lo['hot'][2]);self.assertAlmostEqual(c['C6_rib_ends']['nose_radius_mm'],.8/2)
        self.assertIn('Box(new(-13,y-.4f,.6f),new(13,y+.4f,4f))',text)  # the 0.8 mm rib whose half-thickness is the nose radius
        process=json.loads((ROOT/'catalog/manufacturing/processes/eos-m290-alsi10mg-30um.json').read_text())['process_reference']
        self.assertEqual(c['C5_walls']['wall_mm'],2*process['minimum_wall_thickness_mm'])
        m=self.d['inputs']['IN-10']['method_when_sourced']
        self.assertAlmostEqual(m['A_open_coupon_mm2'],(hi['coldBox'][0]-lo['coldBox'][0])*(hi['coldBox'][2]-lo['coldBox'][2]))
        self.assertFalse(m['applied']);self.assertEqual(m['inputs_needed'],{'m_cold_core_kg_s':None,'A_open_core_mm2':None})
        # Every rule states its basis; a design choice also says that it is one.
        declared=0
        for key in ['IN-01','IN-03','IN-04']:
            for name,rule in self.d['inputs'][key]['decision'].items():
                self.assertTrue(rule['rule'],name)
                if name!='L7_reactions':self.assertTrue(rule.get('basis'),name)
                declared+=bool(rule.get('declared'))
        self.assertEqual(declared,12)

    def test_self_weight_bound_and_end_load_rule(self):
        l6=self.d['inputs']['IN-04']['decision']['L6_self_weight'];reference=M.PRESSURE*M.hydraulic(4)['open_area_mm2']
        self.assertAlmostEqual(reference,21.6,places=9)
        weight=24*24*11.4e-9*json.loads((STUDY.parent/'requirements.json').read_text())['assumed']['metal_density_kg_m3']*9.80665
        self.assertAlmostEqual(l6['retained_body_bound_n'],weight,places=4);self.assertLess(weight/reference,l6['threshold_fraction'])
        self.assertAlmostEqual(weight/reference,.0080,places=4)
        l=self.d['inputs']['IN-04']['decision'];self.assertIsNone(l['L2_outlet_end_load']['value_n']);self.assertIsNone(l['L3_fitting_preload']['value_n'])
        self.assertEqual((l['L4_pipe_bending_and_transverse_force']['moment_n_m'],l['L4_pipe_bending_and_transverse_force']['force_n']),(0.,0.))
        self.assertEqual(self.d['inputs']['IN-04']['remaining_null'],['L2_outlet_end_load','L3_fitting_preload'])

    def test_unsupplied_inputs_stay_null(self):
        i=self.d['inputs'];self.assertIsNone(i['IN-02']['value']);self.assertIsNone(i['IN-10']['cold_kg_s'])
        for key in ['IN-02','IN-04','IN-10']:self.assertTrue(i[key]['blocking'])
        for key in ['IN-01','IN-03']:self.assertFalse(i[key]['blocking'])
        for key in ['drawing_made','solver_run','pressure_qualified','manufacturing_authorized','physical_test_authorized']:self.assertFalse(self.d[key])

    def test_screen_keeps_ids_and_bases_only(self):
        screen=self.d['screen'];ddk=screen['computed']['ddk_forum_measurements']
        # Same DDK file as the 964 interface bridge.
        self.assertEqual(ddk['sha256'],json.loads(DDK_BRIDGE.read_text())['dataset']['sha256']);self.assertEqual(ddk['records'],5916)
        for key,value in ddk.items():
            if isinstance(value,list):
                for row in value:self.assertEqual(set(row),{'id','basis'});self.assertTrue(row['id'].startswith('ddk-'))
        self.assertEqual(screen['review']['ddk_forum_measurements']['relevant_records'],[])
        keys={k for k,_ in walk(self.d)}
        for forbidden in ['author','topicTitle','post','postedOn','context','asStated']:self.assertNotIn(forbidden,keys)
        self.assertTrue(screen['data']['read_only']);self.assertFalse(screen['data']['modified'])
        source=(STUDY/'source/owner_data_screen.py').read_text()
        for word in ['write_text','urllib','requests','subprocess']:self.assertNotIn(word,source)

    @unittest.skipUnless(os.environ.get('PORSCHEFANATICS_DATA'),'set PORSCHEFANATICS_DATA to a local PorscheFanatics checkout to recompute the screen')
    def test_screen_reproduces_from_the_data(self):
        self.assertEqual(S.run(Path(os.environ['PORSCHEFANATICS_DATA']).expanduser()),self.d['screen']['computed'])

if __name__=='__main__':unittest.main()
