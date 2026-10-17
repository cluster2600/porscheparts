"""Compact routes must preserve ports; changed housings must not hide cold collisions."""
import importlib.util
import hashlib
import json
from pathlib import Path
import sys
import shutil
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1];HERE=ROOT/'models/917-engine-reconstruction/compact-packaging'
spec=importlib.util.spec_from_file_location('compact_test_design',HERE/'design.py');design=importlib.util.module_from_spec(spec);spec.loader.exec_module(design)


class CompactTests(unittest.TestCase):
    def test_lower_routes_preserve_both_flat_end_interfaces(self):
        for bank in (-1,1):
            before=design.prior.charge_path(bank);after=design.charge_path(bank)
            self.assertEqual(after[:3],before[:3]);self.assertEqual(after[-1],before[-1])
            self.assertEqual(after[-2][1:],after[-1][1:])
            self.assertEqual(max(p[2] for p in before)-max(p[2] for p in after),40)
            self.assertEqual(max(p[2] for p in after),295)
        with self.assertRaises(ValueError):design.charge_path(0)

    def test_bank_housing_coordinates_follow_six_protected_heads(self):
        rows=[]
        for bank in (-1,1):
            for local_x in (-322.5,-204.5,-86.5,86.5,204.5,322.5):
                rows.append({'family':'individual_head','bank':bank,'matrix_mm':[[1,0,0,local_x+bank*18.5],[0,1,0,0],[0,0,1,0],[0,0,0,1]]})
        banks=design.bank_config(rows,40.58830586754674,167.38283857597582)
        self.assertEqual([b['bank'] for b in banks],[-1,1])
        for b in banks:
            self.assertEqual(b['head_centres_local_x_mm'],[-322.5,-204.5,-86.5,86.5,204.5,322.5])
            self.assertEqual(b['pose'][0][3],b['bank']*18.5)
            self.assertAlmostEqual(b['lid_bottom_mm']-b['adapter_top_mm'],.5)
            self.assertIsNone(b['actual_alloy']);self.assertIsNone(b['measured_interfaces'])
        with self.assertRaises(ValueError):design.bank_config(rows[:-1],40,167)

    @unittest.skipUnless(importlib.util.find_spec('trimesh') and importlib.util.find_spec('manifold3d'),'triangle Boolean runtime unavailable')
    def test_transformed_family_collision_is_retained_and_rejected(self):
        import numpy as np
        import trimesh
        sys.path.insert(0,str(HERE.parent/'head-bionic'))
        import study
        from engine_layout import module
        verify=module('compact_fixture_verify',HERE/'verify.py')
        meshes={'bank_valve_cover_negative':trimesh.creation.box(extents=[2,2,2]),'probe':trimesh.creation.box(extents=[6,.2,.2])}
        for i,name in enumerate(('charge_pipe_negative','charge_pipe_positive','drive_housing','drive_cover','drive_bionic_frame')):
            m=trimesh.creation.box();m.apply_translation([(i+1)*1000,0,0]);meshes[name]=m
        rows=[{'family':n,'matrix_mm':np.eye(4).tolist(),'instance_id':n} for n in meshes]
        probe=next(r for r in rows if r['family']=='probe');matrix=trimesh.transformations.rotation_matrix(np.pi/4,[0,0,1]);matrix[0,3]=1.5;probe['matrix_mm']=matrix.tolist()
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)
            with self.assertRaises(ValueError):verify.run(output,meshes,rows,{})
            report=json.loads((output/'verification.json').read_text());self.assertFalse(report['passed'])
            failed=[r for r in report['checks'] if not r['passed']]
            self.assertEqual(failed[0]['group'],'bank_valve_cover_negative/probe');self.assertGreater(failed[0]['volume_mm3'],0)
            matrix[0,3]=10;probe['matrix_mm']=matrix.tolist();report=verify.run(output,meshes,rows,{})
            self.assertTrue(report['passed']);self.assertFalse(report['full_assembly_interference_checked']);self.assertFalse(report['manufacturing_authorized'])
        sys.path.remove(str(HERE.parent/'head-bionic'))

    @unittest.skipUnless(importlib.util.find_spec('trimesh'),'triangle runtime unavailable')
    def test_identical_native_cache_is_bound_and_changed_files_are_rejected(self):
        import trimesh
        sys.path.insert(0,str(HERE.parent/'head-bionic'))
        import study
        from engine_layout import module
        builder=module('compact_cache_fixture',HERE/'run.py')
        with tempfile.TemporaryDirectory() as temp:
            old=Path(temp)/'old';new=Path(temp)/'new';old.mkdir();new.mkdir()
            mesh=trimesh.Trimesh([[0,0,0],[1e-6,0,0],[0,1e-6,0],[0,0,1]],[[0,2,1],[0,1,3],[1,2,3],[2,0,3]],process=False)
            mesh.export(old/'fixture.stl');(old/'fixture.vdb').write_bytes(b'synthetic cache fixture')
            row={ext+'_sha256':hashlib.sha256((old/('fixture.'+ext)).read_bytes()).hexdigest() for ext in ('stl','vdb')}
            (old/'receipt.json').write_text(json.dumps({'parts':{'fixture':row}}));builder.audit.audit_native(old)
            prior_witness=(old/'independent-audit.json').read_bytes()
            for n in ('fixture.stl','fixture.vdb','receipt.json'):shutil.copy2(old/n,new/n)
            meshes,audits=builder.audit_level(new,old)
            self.assertTrue(audits['fixture']['passed']);self.assertIn('audit_reused_from',audits['fixture'])
            self.assertEqual(len(meshes['fixture'].faces),4);self.assertEqual((old/'independent-audit.json').read_bytes(),prior_witness)
            self.assertFalse((new/'_audit_cache').exists())
            (new/'fixture.vdb').write_bytes(b'new VDB serialization')
            current=json.loads((new/'receipt.json').read_text());current['parts']['fixture']['vdb_sha256']=hashlib.sha256((new/'fixture.vdb').read_bytes()).hexdigest()
            (new/'receipt.json').write_text(json.dumps(current));meshes,audits=builder.audit_level(new,old)
            self.assertIn('STL_topology_only',audits['fixture']['audit_reused_from']['scope'])
            (new/'fixture.vdb').write_bytes(b'tampered')
            with self.assertRaises(ValueError):builder.audit_level(new,old)
            (new/'fixture.vdb').write_bytes(b'new VDB serialization')
            (new/'fixture.stl').write_bytes(b'changed')
            with self.assertRaises(ValueError):builder.audit_level(new,old)
        sys.path.remove(str(HERE.parent/'head-bionic'))


    def test_published_execution_preserves_inheritance_and_physical_limits(self):
        r=json.loads((HERE/'execution-20261013.json').read_text())
        for n,digest in r['source_hashes'].items():self.assertEqual(hashlib.sha256((ROOT/n).read_bytes()).hexdigest(),digest,n)
        for n,digest in r['previews'].items():self.assertEqual(hashlib.sha256((HERE/n).read_bytes()).hexdigest(),digest,n)
        self.assertTrue(r['verification']['passed']);self.assertTrue(r['verification']['cam_rotation_envelopes_checked'])
        self.assertTrue(r['connection_checks']['passed']);self.assertTrue(r['glb_roundtrip']['triangles_retained'])
        self.assertEqual((r['definitions'],r['assembly_occurrences']),(157,1419))
        self.assertEqual((r['protected_heads'],r['protected_valves'],r['protected_turbo_prototypes']),(12,48,39))
        self.assertTrue(r['all_inherited_instances_except_removed_covers_unchanged'])
        for level in r['native_audits'].values():
            self.assertEqual(len(level['bank']),8);self.assertEqual(len(level['pipes']),2)
            self.assertTrue(all(a['passed'] for kind in level.values() for a in kind.values()))
        self.assertTrue(all(a['passed'] for a in r['dense_audits'].values()))
        self.assertTrue(all(0<a['volume_reduction_fraction']<1 for a in r['wall_control'].values()))
        for flag in ('manufacturing_authorized','engine_start_authorized','thermal_or_fatigue_validated','full_assembly_interference_checked'):self.assertIs(r[flag],False)
        for flag in ('actual_alloy','measured_interfaces','professional_review'):self.assertIsNone(r[flag])
        self.assertFalse(r['front_enclosure_inspection']['negative_front_adapter_seal_loop_closed'])
        self.assertEqual(r['front_enclosure_inspection']['intersection_mm3'],0)
        contract=HERE/'interface-contract.json';self.assertEqual(hashlib.sha256(contract.read_bytes()).hexdigest(),r['interface_contract_sha256'])
        c=json.loads(contract.read_text());self.assertFalse(c['functional_enclosure_complete'])
        for interface in c['interfaces']:self.assertIsNone(interface['measured_datums']);self.assertIsNone(interface['approved_tolerances'])


if __name__=='__main__':unittest.main()
