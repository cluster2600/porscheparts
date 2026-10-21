"""Actual generator validation and exclusive-output tests; stdlib only."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('head_binding_generator',Path(__file__).with_name('generate_head_binding_002.py'))
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)


class BindingTests(unittest.TestCase):
    def test_header_contains_exact_pinned_complete_partition(self):
        raw=M.SOURCE.read_bytes(); expected=M.validated_ids(json.loads(raw))
        text=M.render(raw).decode(); actual=[int(v) for v in text.split('{{',1)[1].split('}}',1)[0].split(',') if v.strip()]
        self.assertEqual(actual,expected);self.assertEqual(len(actual),3112)
        self.assertEqual(M.render(raw),Path(__file__).with_name('head_binding.hpp').read_bytes())

    def test_invalid_ID_partition_and_frozen_byte_drift_refused(self):
        raw=M.SOURCE.read_bytes()
        for invalid in [True,-1,1739126,1.0]:
            changed=json.loads(raw);changed['candidate']['plane_classes']['cap_all_z0']['poor_face_ids'][0]=invalid
            with self.assertRaises(ValueError):M.validated_ids(changed)
        changed=json.loads(raw);ids=changed['candidate']['plane_classes']['cap_all_z0']['poor_face_ids'];ids[0]=ids[1]
        with self.assertRaises(ValueError):M.validated_ids(changed)
        with self.assertRaises(ValueError):M.render(raw+b' ')

    def test_previous_header_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'head.hpp';path.write_bytes(b'preserved')
            with self.assertRaises(FileExistsError):M.write_header(M.SOURCE.read_bytes(),path)
            self.assertEqual(path.read_bytes(),b'preserved')


if __name__=='__main__':
    unittest.main()
