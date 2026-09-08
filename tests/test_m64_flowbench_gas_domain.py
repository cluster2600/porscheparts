import importlib.util
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

DIR=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/flowbench-intake'
sys.path.insert(0,str(DIR))
spec=importlib.util.spec_from_file_location('m64_gas_domain',DIR/'build_gas_domain.py')
gas=importlib.util.module_from_spec(spec);spec.loader.exec_module(gas)


class GasDomainTests(unittest.TestCase):
    def test_seat_interior_retains_real_conical_segments(self):
        p=gas.inspection.design.Parameters(intake_x_mm=-18.,exhaust_x_mm=23.5)
        spec=gas.inspection.design.valve_specs(p)[0]
        profiles,_=gas.inspection.design.profiles(p,spec)
        inner=gas.interior_profile(profiles['seat'])
        expected=[(0.,.5),(19.5,.5),(18.5,1.5),(17.8,2.2),(17.8,6.),(0.,6.)]
        self.assertEqual(len(inner),len(expected))
        for actual,wanted in zip(inner,expected):
            for a,b in zip(actual,wanted):self.assertAlmostEqual(a,b,places=12)
        self.assertLess(max(r for r,z in inner),max(r for r,z in profiles['seat']))

    def test_guide_seal_annulus_is_not_full_bore_or_radial_clearance(self):
        area=gas.guide_annulus_area(6.,.03)
        self.assertAlmostEqual(area,math.pi*(3.015**2-3.**2),places=12)
        self.assertLess(area,math.pi*3.015**2/50)

    def test_invalid_or_out_of_order_profile_rejected(self):
        for profile in ([],[(1,0)]*6,[(1,math.nan)]*6):
            with self.assertRaises(ValueError):gas.interior_profile(profile)
        for args in ((6.,0.),(-6.,.03),(6.,math.inf)):
            with self.assertRaises(ValueError):gas.guide_annulus_area(*args)

    def test_each_neck_must_connect_both_end_sections_without_trunk(self):
        row={'BRep_valid':True,'solid_count':1,'BOP_no_faults':True,
             'trunk_excluded_by_axial_bound':True,'other_seat_overlap_volume':0.,
             'chamber_side_area':10.,'throat_side_area':20.}
        self.assertTrue(gas.local_neck_passes(row))
        for key,value in (('solid_count',2),('chamber_side_area',0.),
                          ('throat_side_area',math.nan),('BRep_valid',False),
                          ('BOP_no_faults',False),('other_seat_overlap_volume',1.),
                          ('other_seat_overlap_volume',-1.),
                          ('trunk_excluded_by_axial_bound',False)):
            with self.subTest(key=key):self.assertFalse(gas.local_neck_passes({**row,key:value}))

    def test_actual_seat_owns_wholly_coincident_tool_plane_not_silent_relabel(self):
        matches=[{'role':'walls_seat','source':'intake_1_seat_face_1','coincident_area':10.},
                 {'role':'walls_chamber','source':'chamber_tool_face_3','coincident_area':10.}]
        role,proof=gas.boundary_owner(matches,10.,'GeomAbs_Plane')
        self.assertEqual(role,'walls_seat')
        self.assertEqual(proof['coverage_ratios'],[1.,1.])
        for altered in ([matches[0],{**matches[1],'coincident_area':9.}],
                        [matches[0],{**matches[1],'source':'actual_body_bottom_1'}],
                        matches+[matches[0]]):
            self.assertEqual(gas.boundary_owner(altered,10.,'GeomAbs_Plane')[0],'ambiguous')
        self.assertEqual(gas.boundary_owner(matches,10.,'GeomAbs_Cone')[0],'ambiguous')

    def test_enrichment_verifies_artifacts_and_keeps_failed_geometry_gates(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            # Bytes are checksum fixtures, expressly not native CAD evidence.
            payload=b'synthetic checksum fixture, not geometry'
            (root/'domain.brep').write_bytes(payload)
            record={'file':'domain.brep','sha256':hashlib.sha256(payload).hexdigest()}
            faces=[]
            for index,role in enumerate(('inlet','receiver_outlet','fixture_stem_seals','fixture_stem_seals','walls_seat'),1):
                matches=[{'role':role,'source':role+'_fixture','coincident_area':10.}]
                if role=='walls_seat':matches.append({'role':'walls_chamber','source':'chamber_tool_face_3','coincident_area':10.})
                faces.append({**record,'id':index,'role':role,'area':10.,'surface_type':'GeomAbs_Plane','source_match':matches})
            original={'exports':{'domain_brep':record},'boundary_faces':faces,
                'gates':{'brep_valid':True,'bop_no_faults':False,'positive_intake_curtain':False},
                'manufacturing_authorized':False,'CFD_executed':False}
            source=root/'source.json';source.write_text(json.dumps(original))
            before=source.read_bytes()
            enriched=gas.reclassify_report(source,root/'enriched.json')
            self.assertEqual(before,source.read_bytes())
            self.assertTrue(enriched['gates']['boundary_assignment_complete'])
            self.assertFalse(enriched['gates']['bop_no_faults'])
            self.assertFalse(enriched['gates']['positive_intake_curtain'])
            self.assertFalse(enriched['manufacturing_authorized'])
            self.assertFalse(enriched['CFD_executed'])
            self.assertEqual(enriched['status'],'rejected_native_domain_or_boundaries')
            (root/'domain.brep').write_bytes(b'tampered checksum fixture')
            with self.assertRaisesRegex(ValueError,'changed_native_artifact'):
                gas.reclassify_report(source,root/'changed.json')


if __name__=='__main__':unittest.main()
