"""Owner-authorized parallel leases: no network, credentials or paid calls."""
from contextlib import ExitStack, redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest import mock
import test_openbao_vastai_picogk as baseline

ROOT=Path(__file__).resolve().parents[1]

class ParallelLeaseTests(unittest.TestCase):
    def setUp(self):
        fixture=baseline.PicoGKTests('test_offer_limits_and_budget')
        fixture.setUp();self.addCleanup(fixture.doCleanups)
        self.root=fixture.root;self.manifest=fixture.manifest;self.path=fixture.path;self.raw=fixture.raw
        variant=self.root/'deploy/openbao/openbao-vastai';variant.parent.mkdir(parents=True)
        shutil.copyfile(ROOT/'deploy/openbao/openbao-vastai',variant)
        subprocess.run(['git','apply',str(ROOT/'deploy/vast/picogk-parallel/wrapper-parallel.patch'),
                        str(ROOT/'deploy/vast/picogk-parallel/wrapper-ssh-propagation.patch')],
                       cwd=self.root,check=True,capture_output=True,timeout=10)
        self.w=baseline.load(variant,'parallel_wrapper_fixture')
        self.g=baseline.load('deploy/vast/picogk-parallel/deadline_guard.py','parallel_guard_fixture')
        self.offer=fixture.offer

    def test_foreign_instances_are_ignored_but_owned_identity_is_exact(self):
        foreign={**self.raw,'id':1000,'label':'another-authorized-job'}
        with mock.patch.object(self.w,'strict_instance_inventory',return_value=[foreign]):
            self.w.picogk_singleton('synthetic',None,self.manifest)
        with mock.patch.object(self.w,'strict_instance_inventory',return_value=[foreign,self.raw]):
            self.w.picogk_singleton('synthetic',999,self.manifest)
            with self.assertRaises(self.w.SafeError):self.w.picogk_singleton('synthetic',None,self.manifest)
            with self.assertRaises(self.w.SafeError):self.w.picogk_singleton('synthetic',1000,self.manifest)
        for owned in ([self.raw,{**self.raw,'id':1001}],[{**self.raw,'image_uuid':'different'}]):
            with mock.patch.object(self.w,'strict_instance_inventory',return_value=[foreign,*owned]):
                with self.assertRaises(self.w.SafeError):self.w.picogk_singleton('synthetic',999,self.manifest)

    def test_guard_arms_with_foreign_job_and_only_cleans_owned_absence(self):
        fake=self.root/'approved-wrapper';fake.write_text('# never executed\n')
        own=self.w.safe_instance(self.raw);foreign={**own,'id':1000,'label':'another-authorized-job'}
        proof=dict(instance_id=999,destroyed=True,verified_absent=True)
        with mock.patch.object(self.g,'WRAPPER',fake), \
             mock.patch.object(self.g,'wrapper_call',side_effect=[[foreign],[foreign,own],[foreign]]) as calls, \
             mock.patch.object(self.g.time,'monotonic',return_value=0), \
             mock.patch.object(self.g.time,'sleep'), \
             mock.patch.object(self.g,'cleanup_until_absent',return_value=proof) as cleanup, \
             redirect_stdout(io.StringIO()):
            result=self.g.guard(self.path)
        self.assertEqual(result['reason'],'already_destroyed')
        cleanup.assert_called_once_with(999,self.manifest)
        self.assertEqual(calls.call_args_list,[mock.call('instances')]*3)

    def test_unrelated_job_does_not_hide_owned_cost_violation(self):
        fake=self.root/'approved-wrapper';fake.write_text('# never executed\n')
        own=self.w.safe_instance({**self.raw,'dph_total':.9})
        foreign={**own,'id':1000,'label':'another-authorized-job','dph_total':.5}
        proof=dict(instance_id=999,destroyed=True,verified_absent=True)
        with mock.patch.object(self.g,'WRAPPER',fake), \
             mock.patch.object(self.g,'wrapper_call',side_effect=[[foreign],[foreign,own]]), \
             mock.patch.object(self.g.time,'monotonic',return_value=0), \
             mock.patch.object(self.g,'cleanup_until_absent',return_value=proof) as cleanup, \
             redirect_stdout(io.StringIO()):
            result=self.g.guard(self.path)
        self.assertEqual(result['reason'],'contract_or_cost_guard')
        cleanup.assert_called_once_with(999,self.manifest)

    def test_existing_attempt_is_refused_before_readiness(self):
        fake=self.root/'approved-wrapper';fake.write_text('# never executed\n')
        own=self.w.safe_instance(self.raw)
        with mock.patch.object(self.g,'WRAPPER',fake), \
             mock.patch.object(self.g,'wrapper_call',return_value=[own]), \
             mock.patch.object(self.g,'cleanup_until_absent') as cleanup:
            with self.assertRaises(self.g.GuardError):self.g.guard(self.path)
        cleanup.assert_not_called()
        self.assertFalse(Path(self.manifest['guard_ready_path']).exists())

    def ssh_fixture(self,stack,responses):
        stack.enter_context(redirect_stderr(io.StringIO()))
        stack.enter_context(mock.patch.object(self.w,'read_local_ssh_public_key',return_value='synthetic-public-key'))
        stack.enter_context(mock.patch.object(self.w,'instance_lists_approved_ssh_key',return_value=True))
        stack.enter_context(mock.patch.object(self.w,'prepare_component_factory_f41_known_hosts',return_value=self.root/'known-hosts'))
        stack.enter_context(mock.patch.object(self.w,'vast_request',return_value={'instances':self.raw}))
        stack.enter_context(mock.patch.object(self.w,'validate_component_factory_f41_known_hosts'))
        stack.enter_context(mock.patch.object(self.w,'picogk_singleton'))
        sleep=stack.enter_context(mock.patch.object(self.w.time,'sleep'))
        probe=stack.enter_context(mock.patch.object(self.w,'run_component_factory_f41_ssh_probe',side_effect=responses))
        return probe,sleep

    def test_delayed_key_attachment_can_pass_on_third_identical_probe(self):
        witness=json.dumps(dict(status='PASS',architecture='X64',scope='software_geometry_witness_only',
            triangles=100,stl_roundtrip_triangles=100,relative_volume_error=.03,
            manufacturing_validated=False,engine_validated=False))
        denied=mock.Mock(returncode=255,stdout='',stderr='Permission denied')
        success=mock.Mock(returncode=0,stdout=witness,stderr='')
        with ExitStack() as stack:
            probe,sleep=self.ssh_fixture(stack,[denied,denied,success])
            self.w.picogk_ssh_ready('synthetic',999,self.manifest,self.offer)
        self.assertEqual(probe.call_count,3)
        self.assertEqual(sleep.call_args_list,[mock.call(5),mock.call(5)])
        self.assertEqual(probe.call_args_list[0],probe.call_args_list[1])
        self.assertEqual(probe.call_args_list[1],probe.call_args_list[2])

    def test_persistent_authentication_denial_stops_after_three_probes(self):
        denied=mock.Mock(returncode=255,stdout='',stderr='Permission denied')
        with ExitStack() as stack:
            probe,sleep=self.ssh_fixture(stack,[denied]*3)
            with self.assertRaisesRegex(self.w.SafeError,'authentication_denied'):
                self.w.picogk_ssh_ready('synthetic',999,self.manifest,self.offer)
        self.assertEqual(probe.call_count,3);self.assertEqual(sleep.call_count,2)

    def test_changed_host_key_is_never_retried(self):
        failure=mock.Mock(returncode=255,stdout='',stderr='REMOTE HOST IDENTIFICATION HAS CHANGED')
        with ExitStack() as stack:
            probe,sleep=self.ssh_fixture(stack,[failure])
            with self.assertRaisesRegex(self.w.SafeError,'host_key_changed'):
                self.w.picogk_ssh_ready('synthetic',999,self.manifest,self.offer)
        self.assertEqual(probe.call_count,1);sleep.assert_not_called()

if __name__=='__main__':unittest.main()
