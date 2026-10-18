"""Regression guards for exact packaging rebinding and explicit case selection."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess

import numpy as np
from native_case_contract import PROFILES, arrays_identity, bind_repair, selected_inputs, sha, write, validate_terminal


class ContractTests(unittest.TestCase):
    def test_array_identity_ignores_zip_order_but_not_values_or_dtype(self):
        with tempfile.TemporaryDirectory() as name:
            p=Path(name); v=np.array([[1.,2.,3.]]); f=np.array([[0,0,0]],dtype=np.int64)
            np.savez(p/'a.npz',vertices=v,faces=f)
            np.savez_compressed(p/'b.npz',faces=f,vertices=v)
            self.assertEqual(arrays_identity(p/'a.npz'),arrays_identity(p/'b.npz'))
            np.savez(p/'c.npz',vertices=v,faces=f.astype(np.int32))
            self.assertNotEqual(arrays_identity(p/'a.npz'),arrays_identity(p/'c.npz'))
            np.savez(p/'d.npz',vertices=np.nextafter(v,np.inf),faces=f)
            self.assertNotEqual(arrays_identity(p/'a.npz'),arrays_identity(p/'d.npz'))

    def test_repair_binds_only_identical_all_arrays(self):
        with tempfile.TemporaryDirectory() as name:
            p=Path(name); np.savez(p/'raw.npz',vertices=np.zeros((3,3)),faces=np.array([[0,1,2]]))
            np.savez(p/'snap.npz',vertices=np.zeros((3,3)),faces=np.array([[0,1,2]]),source=np.array([1]))
            write(p/'template.json',dict(canonical_arrays_sha256={k:arrays_identity(p/(n+'.npz')) for k,n in [('first_snap','snap'),('original_raw','raw')]},plan={'vertex_maps':[{'source':2,'target':1}]}))
            plan=bind_repair(p/'template.json',p/'snap.npz',p/'raw.npz',p/'plan.json')
            self.assertEqual(plan['input_sha256'],sha(p/'snap.npz'))
            self.assertEqual(plan['vertex_maps'],[{'source':2,'target':1}])
            np.savez(p/'snap.npz',vertices=np.zeros((3,3)),faces=np.array([[0,1,2]]),source=np.array([2]))
            with self.assertRaises(ValueError):bind_repair(p/'template.json',p/'snap.npz',p/'raw.npz',p/'bad.json')

    def test_profiles_preserve_historical_orders_and_explicit_left(self):
        self.assertEqual(PROFILES[8]['order'],'mask-first')
        for i in [1,3,9,10]:self.assertEqual(PROFILES[i]['order'],'difference-first')
        self.assertEqual(PROFILES[2]['csg_seconds'],600)
        self.assertNotEqual(PROFILES[0]['backend'],PROFILES[8]['backend'])

    def test_input_selection_rejects_duplicates_and_tamper(self):
        with tempfile.TemporaryDirectory() as name:
            p=Path(name)
            for n in ['chain','mask','part']:np.savez(p/(n+'.npz'),vertices=np.zeros((3,3)),faces=np.array([[0,1,2]]))
            row=dict(source_index=8,chain='chain.npz',chain_sha256=sha(p/'chain.npz'),mask='mask.npz',mask_sha256=sha(p/'mask.npz'))
            report=dict(sources_and_input_unchanged=True,expected_regions=1,regions=[row],part='part.npz',part_sha256=sha(p/'part.npz'))
            write(p/'inputs.json',report);self.assertEqual(set(selected_inputs(p/'inputs.json',8)[2]),{'chain','mask','part'})
            report.update(expected_regions=2,regions=[row,row]);write(p/'inputs.json',report)
            with self.assertRaises(ValueError):selected_inputs(p/'inputs.json',8)
            report.update(expected_regions=1,regions=[row]);write(p/'inputs.json',report)
            (p/'mask.npz').write_bytes(b'changed')
            with self.assertRaises(ValueError):selected_inputs(p/'inputs.json',8)

    def test_terminal_binds_all_sources_runtime_manifest_and_stable_path(self):
        with tempfile.TemporaryDirectory() as name:
            p=Path(name);(p/'sealed').mkdir();write(p/'sealed/native_audit.json',{'test':'payload'})
            plan=dict(source_index=0,profile=PROFILES[0],input_manifest_sha256='input',sources_sha256={'worker':'source'})
            ref=dict(path='sealed/native_audit.json',sha256=sha(p/'sealed/native_audit.json'))
            terminal=dict(schema='native-envelope-case-v2',status='executed',source_index=0,backend=PROFILES[0]['backend'],
                profile=PROFILES[0],input_manifest_sha256='input',runtime_sha256='runtime',
                source_snapshot_sha256={'worker':'source'},all_owned_scopes_inactive=True,
                native_audit=ref,files_sha256={ref['path']:ref['sha256']})
            validate_terminal(terminal,plan,'runtime',p)
            for key,bad in [('runtime_sha256','changed'),('input_manifest_sha256','changed'),
                            ('source_snapshot_sha256',{}),('all_owned_scopes_inactive',False),
                            ('native_audit',dict(path='../native_audit.json',sha256=ref['sha256']))]:
                changed=dict(terminal);changed[key]=bad
                with self.assertRaises(ValueError):validate_terminal(changed,plan,'runtime',p)

    def test_stop_between_uploads_never_launches_or_uploads_next_payload(self):
        import run_native_envelope_case as frontend
        with tempfile.TemporaryDirectory() as name:
            p=Path(name).resolve()
            for n in ['chain','mask','part']:np.savez(p/(n+'.npz'),vertices=np.zeros((3,3)),faces=np.array([[0,1,2]]))
            write(p/'inputs.json',dict(input_sha256='software-witness',sources_and_input_unchanged=True,expected_regions=1,
                part='part.npz',part_sha256=sha(p/'part.npz'),regions=[dict(source_index=8,chain='chain.npz',chain_sha256=sha(p/'chain.npz'),mask='mask.npz',mask_sha256=sha(p/'mask.npz'))]))
            write(p/'runtime.json',dict(schema='carrier-native-case-runtime-v2',host='fixture-only',
                **{k:'/fixture-only/'+k for k in ['remote_parent','python','audit_python','pymesh_orders','prism_csg','snap','distance']}))
            commands=[]
            def fake(command,**_):
                commands.append(command)
                if command[0]=='scp' and str(p/'output/source') in command:
                    frontend.STOP=True
                return subprocess.CompletedProcess(command,0)
            previous=frontend.STOP
            try:
                frontend.STOP=False
                with patch.object(frontend.subprocess,'run',fake), patch.object(frontend.subprocess,'Popen',side_effect=AssertionError('Remote launch must not occur')):
                    with self.assertRaises(InterruptedError):frontend.run(p/'inputs.json',p/'output',8,p/'runtime.json')
            finally:frontend.STOP=previous
            uploads=[c for c in commands if c[0]=='scp' and str(p/'output/source') in c]
            self.assertEqual(len(uploads),1)
            self.assertFalse(any(str(p/'output/inputs') in c for c in commands))
            self.assertFalse((p/'output/case.json').exists())
            self.assertEqual(json.loads((p/'output/execution-receipt.json').read_text())['status'],'rejected_or_incomplete')


if __name__=='__main__':unittest.main()
