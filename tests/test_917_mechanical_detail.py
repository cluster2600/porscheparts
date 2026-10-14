"""Mechanical hypotheses must retain protected axes, pressure walls and explicit limits."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import unittest
import tempfile
import sys

ROOT=Path(__file__).resolve().parents[1];HERE=ROOT/'models/917-engine-reconstruction/mechanical-detail'
spec=importlib.util.spec_from_file_location('mechanical_detail_design',HERE/'design.py');design=importlib.util.module_from_spec(spec);spec.loader.exec_module(design)


class DetailTests(unittest.TestCase):
    def test_pressure_and_air_slots_are_separated_by_nominal_walls(self):
        for limit,gas_count,air_count in [(20,6,5),(32,9,8)]:
            gas=design.pressure_rows(limit);air=design.air_rows(limit)
            self.assertEqual(len(gas),gas_count);self.assertEqual(len(air),air_count)
            self.assertEqual(gas[0],-limit);self.assertEqual(gas[-1],limit)
            gap=min(abs(a-g)-.75-1.5 for a in air for g in gas)
            self.assertEqual(gap,1.75)

    def test_charge_paths_have_flat_nominal_ports_and_clear_drive_in_xz(self):
        for bank in (-1,1):
            p=design.charge_path(bank)
            self.assertEqual(p[0],[500,bank*382.25,-160-bank*49])
            self.assertEqual(p[1][::2],p[0][::2]);self.assertEqual(p[1][1]-p[0][1],bank*40)
            self.assertEqual(p[2][1]-p[1][1],bank*40)
            self.assertEqual(p[-1],[-100,bank*310,295])
            self.assertEqual(p[-2][1:],p[-1][1:])
            for a,b in zip(p,p[1:]):
                if min(a[0],b[0])<=448 and max(a[0],b[0])>=389:
                    self.assertGreater(min(a[2],b[2])-25,210)
            returns=design.return_path(bank)
            self.assertEqual(returns[0],[231,bank*310,295])
            self.assertEqual(returns[1][1:],returns[0][1:])
            self.assertGreaterEqual(math.dist(returns[0],returns[1]),25)
            self.assertLess(max(v[0] for v in returns)+25,389)
        with self.assertRaises(ValueError):design.charge_path(0)

    def test_nominal_cover_bolts_avoid_swept_gears_and_each_other(self):
        receipt=json.loads((HERE.parent/'cam-drive/execution-20261012.json').read_text())
        gears=[]
        for t in receipt['layout']['trains']:
            gears.extend([[t['plane_x_mm'],*p,1.5*n/2+1.5] for p,n in zip(t['centres_yz_mm'],t['teeth'])])
        bolts=design.cover_bolts(gears)
        self.assertGreaterEqual(len(bolts),12)
        for i,p in enumerate(bolts):
            self.assertGreaterEqual(min(math.dist(p,[y,z])-r for _,y,z,r in gears),4.9)
            for q in bolts[i+1:]:self.assertGreaterEqual(math.dist(p,q),18)

    @unittest.skipUnless(importlib.util.find_spec('trimesh'),'mesh runtime unavailable')
    def test_native_audit_rejects_changed_or_disconnected_mesh_without_erasing_small_faces(self):
        sys.path.insert(0,str(HERE))
        sys.path.insert(0,str(HERE.parent/'head-bionic'))
        from detail_audit import audit_native,verified_cache
        import trimesh
        def record(directory,mesh):
            mesh.export(directory/'fixture.stl');(directory/'fixture.vdb').write_bytes(b'synthetic fixture')
            row={ext+'_sha256':hashlib.sha256((directory/('fixture.'+ext)).read_bytes()).hexdigest() for ext in ('stl','vdb')}
            (directory/'receipt.json').write_text(json.dumps({'parts':{'fixture':row}}))
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary)
            tetra=trimesh.Trimesh([[0,0,0],[1e-6,0,0],[0,1e-6,0],[0,0,1]],[[0,2,1],[0,1,3],[1,2,3],[2,0,3]],process=False)
            record(directory,tetra);meshes,audits=audit_native(directory)
            self.assertTrue(audits['fixture']['passed']);self.assertEqual(len(meshes['fixture'].faces),4)
            cached,cached_audit=verified_cache(directory);self.assertEqual(len(cached['fixture'].faces),4)
            self.assertEqual(cached_audit['fixture']['source_sha256'],audits['fixture']['source_sha256'])
            self.assertEqual(audits['fixture']['witness']['vertex_displacement'],0)
            cube=trimesh.creation.box();other=cube.copy();other.apply_translation([3,0,0])
            record(directory,trimesh.util.concatenate([cube,other]));meshes,audits=audit_native(directory)
            self.assertFalse(audits['fixture']['passed']);self.assertNotIn('fixture',meshes)
            with self.assertRaises(ValueError):verified_cache(directory)
            (directory/'fixture.stl').write_bytes(b'changed')
            with self.assertRaises(ValueError):audit_native(directory)
        sys.path.remove(str(HERE))
        sys.path.remove(str(HERE.parent/'head-bionic'))

    def test_execution_receipt_and_images_are_bound_without_physical_promotion(self):
        r=json.loads((HERE/'execution-20261012.json').read_text())
        for name,digest in r['source_hashes'].items():self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest,name)
        for name,digest in r['previews'].items():self.assertEqual(hashlib.sha256((HERE/name).read_bytes()).hexdigest(),digest)
        self.assertTrue(r['verification']['passed'])
        self.assertTrue(r['verification']['drive_clearance_uses_native_full_rotation_disc_envelopes'])
        for field in ('manufacturing_authorized','engine_start_authorized','thermal_or_fatigue_validated','full_assembly_interference_checked'):self.assertIs(r[field],False)
        for field in ('actual_alloy','measured_interfaces','professional_review'):self.assertIsNone(r[field])
        self.assertEqual(r['protected_heads'],12);self.assertEqual(r['protected_valves'],48)
        self.assertTrue(r['turbo_prototypes_unchanged'])
        self.assertTrue(r['connection_checks']['passed'])
        self.assertEqual(len(r['connection_checks']['checks']),12)
        self.assertFalse(r['connection_checks']['pressure_sealing_qualified'])
        self.assertGreater(r['frame_control']['volume_reduction_fraction'],0)
        self.assertFalse(r['frame_control']['strength_or_fatigue_optimized'])
        for level in r['native_audits'].values():
            self.assertEqual(len(level),25)
            self.assertTrue(all(row['passed'] for row in level.values()))
        self.assertTrue(all(row['passed'] for row in r['intake_audits'].values()))
        self.assertTrue(all(row['passed'] for level in r['housing_clearance_audits'].values() for row in level.values()))
        contract=json.loads((HERE/'interface-contract.json').read_text())
        for interface in contract['interfaces']:
            self.assertIsNone(interface['measured_datums']);self.assertIsNone(interface['approved_tolerances'])


if __name__=='__main__':unittest.main()
