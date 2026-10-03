"""Admission, applicability and dependency safeguards for the public matrix."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
PROGRAM=ROOT/'twins/935-horizontal-cooling-system'
spec=importlib.util.spec_from_file_location('horizontal_matrix',PROGRAM/'source/check_input_matrix.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class HorizontalMatrixTests(unittest.TestCase):
    def test_publication_preserves_unknown_variants_and_partial_coverage(self):
        report=module.check()
        self.assertEqual(report['separate_variants'],6)
        self.assertEqual(report['accepted_935_numeric_physical_claims'],0)

    def mutate(self,change,message):
        with tempfile.TemporaryDirectory() as temp:
            copy=Path(temp)/'program';shutil.copytree(PROGRAM,copy)
            file=copy/'data/input-matrix.json';data=json.loads(file.read_text());change(data)
            file.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,message):module.check(copy)

    def test_unreviewed_engine_speed_cannot_be_admitted(self):
        self.mutate(lambda a:next(r for r in a['rows'] if r['id']=='D01').update(accepted_value=8000),'reviewed provenance')

    def test_factory_cooling_claim_cannot_silently_become_k3_architecture(self):
        self.mutate(lambda a:next(v for v in a['variants'] if v['id']=='kremer_k3').update(cooling_architecture='borrowed_935_78'),'cooling architecture')

    def test_dependency_cycles_are_rejected(self):
        self.mutate(lambda a:a['rows'][0].update(depends_on=['A01']),'Dependency cycle')

    def test_unreceived_language_reports_do_not_count_as_imported(self):
        with tempfile.TemporaryDirectory() as temp:
            copy=Path(temp)/'program';shutil.copytree(PROGRAM,copy)
            p=copy/'research/coverage.json';a=json.loads(p.read_text());a['received_original_report_files']=22;p.write_text(json.dumps(a))
            with self.assertRaisesRegex(ValueError,'cannot be claimed imported'):module.check(copy)


if __name__=='__main__':unittest.main()
