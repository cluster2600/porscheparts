import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'twins/962-cylinder-head-f0/source/coolant_flow/prepare_kali_bound_case.py'
spec=importlib.util.spec_from_file_location('bound_kali_case',SOURCE)
case=importlib.util.module_from_spec(spec);spec.loader.exec_module(case)


class BoundKaliCaseTests(unittest.TestCase):
    def test_mismatched_surface_is_rejected_before_preparation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);mesh=root/'mesh';surface=root/'surface';mesh.mkdir();surface.mkdir()
            (mesh/'mesh-report.json').write_text(json.dumps(dict(surface_receipt_sha256='wrong')))
            (mesh/'saved-readback.json').write_text('{}')
            (surface/'surface-report.json').write_text('{}')
            with self.assertRaises(ValueError):case.prepare(mesh,surface,root/'budget',root/'out')
            self.assertFalse((root/'out').exists())


if __name__=='__main__':unittest.main()
