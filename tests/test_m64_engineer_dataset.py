"""Offline provenance and family-splitting checks; no CUDA training is implied."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / 'training/m64-engineer/dataset.py'
SPEC = importlib.util.spec_from_file_location('m64_engineer_dataset',PATH)
data = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(data)


class EngineerDatasetTests(unittest.TestCase):
    def test_candidate_gates_and_group_split(self):
        rows=data.candidates()
        self.assertEqual(len(rows),120)
        self.assertEqual(rows,data.candidates())
        with self.assertRaises(ValueError): data.split(rows)
        self.assertEqual(data.topology(3,[(0,1),(1,2)]),data.topology(3,[(2,0),(0,1)]))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'work').mkdir()
            reviewed=copy.deepcopy(rows[:80])
            for r in reviewed:
                checksum=data.sha(r['messages'][-1]['content'])
                receipt=root/'work'/(r['id']+'.json')
                receipt.write_text(json.dumps({'answer_sha256':checksum}))
                r['validation']={'status':'verified','answer_sha256':checksum,
                    'evidence':[{'path':str(receipt),'sha256':hashlib.sha256(receipt.read_bytes()).hexdigest()}]}
            with patch.object(data,'ROOT',root):
                split=data.split(reviewed)
                groups=[{r['family_id'] for r in split[s]} for s in ('train','valid','test')]
                self.assertTrue(all(split.values()))
                self.assertFalse(groups[0]&groups[1] or groups[1]&groups[2] or groups[0]&groups[2])
                self.assertEqual(sum(map(len,split.values())),80)
                changed=copy.deepcopy(reviewed); changed[0]['messages'][-1]['content']+=' invalid'
                with self.assertRaises(ValueError): data.check(changed)
                changed=copy.deepcopy(reviewed); changed[0]['sources'][0]['training_allowed']=False
                with self.assertRaises(ValueError): data.check(changed)
                receipt.write_text('{}')
                with self.assertRaises(ValueError): data.check(reviewed)
