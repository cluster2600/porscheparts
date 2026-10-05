import importlib.util
from pathlib import Path
import time
import unittest

path = Path(__file__).resolve().parents[1]/'deploy/vast/m64-cad-batch/deadline_guard.py'
spec = importlib.util.spec_from_file_location('m64_cad_guard', path)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class CADBatchGuardTest(unittest.TestCase):
    def test_budget_and_foreign_identity_are_not_bypassed(self):
        other = dict(id=12, label='unrelated', image='image@digest')
        own = dict(id=13, label='own', image=guard.IMAGE, dph_total=.86,
                   inet_up_cost_usd_per_gb=.001, inet_down_cost_usd_per_gb=.001)
        now = int(time.time())
        manifest = dict(profile='m64-cad-parallel-v1', image_ref=guard.IMAGE,
            attempt_label='3dprinting993-component-factory-f41-cad-'+'a'*20,
            created_epoch=now, deadline_epoch=now+10800, budget_usd=10,
            image_download_gb=20, max_input_gb=2, max_output_gb=2, background_instance=other)
        guard.validate(manifest)
        self.assertTrue(guard.cost_valid(own, manifest))
        self.assertFalse(guard.cost_valid({**own, 'dph_total':2}, manifest))
        self.assertFalse(guard.cost_valid(own, {**manifest, 'budget_usd':2}))
        self.assertTrue(guard.pending_metadata({'status':None}))
        self.assertFalse(guard.pending_metadata({'status':'stopped'}))
        self.assertFalse(guard.pending_metadata({'status':'running'}))
        self.assertTrue(guard.missing_cost({**own, 'inet_up_cost_usd_per_gb':None}, .86))
        self.assertFalse(guard.missing_cost({**own, 'inet_up_cost_usd_per_gb':None}, .85))
        self.assertEqual(guard.visible_inventory([other, own], other), [own])
        self.assertEqual(guard.visible_inventory([own], other), [own])
        with self.assertRaises(guard.engine.GuardError):
            guard.visible_inventory([{**other, 'image':'changed'}, own], other)
        for bad in ({'budget_usd':11}, {'deadline_epoch':now+10801}, {'image_ref':'other'}):
            with self.assertRaises(guard.engine.GuardError): guard.validate({**manifest, **bad})
