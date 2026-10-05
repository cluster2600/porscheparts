#!/usr/bin/env python3
"""Reject incomplete native restart state and changes to the fixed20 protocol."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from prepare_d2_restart1000 import validate_checkpoint, changed_control

ROOT = Path(__file__).resolve().parents[1]


class NativeRestart(unittest.TestCase):
    def setUp(self):
        self.audit = json.loads((ROOT/'results/runtime/D2-restart-checkpoint-audit.json').read_text())
        self.plan = json.loads((ROOT/'parameters/D2-restart1000-protocol.json').read_text())

    def test_actual_native1000_admissible_for_restart_only(self):
        validate_checkpoint(self.audit, self.plan)

    def test_missing_surface_field_and_nonfinite_state_refused(self):
        for action in ('missing_Uf', 'nonfinite_pressure'):
            audit = copy.deepcopy(self.audit)
            row = audit['checkpoints']['1000']['processors'][2]
            if action == 'missing_Uf':
                del row['fields']['Uf']
            else:
                row['fields']['p']['finite'] = False
            with self.assertRaises(ValueError):
                validate_checkpoint(audit, self.plan)

    def test_partial_or_mixed_native_time_refused(self):
        self.audit['checkpoints']['1000']['processors'][3]['uniform_time']['index'] = '1001'
        with self.assertRaises(ValueError):
            validate_checkpoint(self.audit, self.plan)

    def test_extra_iterations_or_control_replay_refused(self):
        for key, value in [('target_iteration',1040), ('new_iterations',40), ('new_cases',['current','extended']), ('current_control_replayed',True)]:
            plan = copy.deepcopy(self.plan)
            plan[key] = value
            with self.assertRaises(ValueError):
                validate_checkpoint(self.audit, plan)

    def test_actual_control_change_preserves_all_other_bytes(self):
        expected = (ROOT/'parameters/D2-restart1000-controlDict').read_text()
        old = expected.replace('startFrom startTime; startTime 1000;', 'startFrom latestTime; startTime 0;')
        self.assertEqual(hashlib.sha256(old.encode()).hexdigest(),self.audit['files']['system/controlDict']['sha256'])
        self.assertEqual(changed_control(old), expected)
        with self.assertRaises(ValueError):
            changed_control(old.replace('endTime 1020;', 'endTime 1040;'))


if __name__ == '__main__':
    unittest.main()
