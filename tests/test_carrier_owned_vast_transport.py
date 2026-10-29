"""Regress endpoint parsing and short-lived, already-destroyed lease cleanup."""
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022'


def load(name,filename):
    spec=importlib.util.spec_from_file_location(name,SOURCE/filename)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


transport=load('owned_endpoints','owned_vast_ssh_endpoints.py')
guard=load('short_lease_guard','lease_guard_four_hour_live.py')


class OwnedVastTransportTests(unittest.TestCase):
    def test_actual_direct_proxy_response_is_parsed(self):
        response=dict(instance_id=123,direct=dict(host='192.0.2.1',port=40022),
                      proxy=dict(host='ssh.example.test',port=22022),ssh_connection_tested=False)
        endpoints=transport.owned_ssh_endpoints(response,123)
        self.assertEqual([x['port']for x in endpoints],[40022,22022])

    def test_wrong_instance_response_is_refused(self):
        with self.assertRaisesRegex(ValueError,'owned instance'):
            transport.owned_ssh_endpoints(dict(instance_id=456,direct=None,proxy=None),123)

    def test_pending_endpoint_metadata_does_not_claim_connectivity(self):
        self.assertEqual(transport.owned_ssh_endpoints(dict(instance_id=123,
                         direct=dict(host=None,port=None),proxy=None),123),[])

    def test_guard_finishes_after_matching_teardown_even_if_it_missed_the_live_window(self):
        with tempfile.TemporaryDirectory()as temp:
            base=Path(temp);now=time.time();manifest=base/'manifest.json'
            manifest.write_text(json.dumps(dict(created_epoch=now,deadline_epoch=now+3600,
                                               budget_usd=2,offer_id=7,image='image',label='owned')))
            (base/'launch-receipt.json').write_text(json.dumps(dict(instance_id=123,
                image='image',label='owned',selected_offer=dict(id=7))))
            (base/'teardown-verification.json').write_text(json.dumps(dict(instance_id=123,
                owned_instance_absent=True)))
            observations=[]
            def inventory(*args):
                observations.append(args)
                if len(observations)>3:raise AssertionError('Guard failed to terminate after three absent confirmations')
                return []
            with patch.object(guard,'call',side_effect=inventory),patch.object(guard.time,'sleep'),\
                 patch.object(guard.subprocess,'Popen'),patch('sys.argv',['guard','--manifest',str(manifest)]):
                guard.main()
            terminal=json.loads((base/'guard-terminal-live.json').read_text())
            self.assertEqual(terminal['consecutive_absent_confirmations'],3)
            self.assertEqual(len(observations),3)

    def test_guard_does_not_accept_another_leases_teardown(self):
        with tempfile.TemporaryDirectory()as temp:
            base=Path(temp)
            (base/'teardown-verification.json').write_text(json.dumps(dict(instance_id=456,
                owned_instance_absent=True)))
            self.assertFalse(guard.observed_teardown_matches(base,123))


if __name__=='__main__':unittest.main()
