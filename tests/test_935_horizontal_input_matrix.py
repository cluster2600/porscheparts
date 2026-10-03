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
        self.assertEqual(report['bounded_language_lanes'],40)
        self.assertEqual(report['explicit_null_gaps'],66)

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

    def mutate_research(self,name,change,message):
        with tempfile.TemporaryDirectory() as temp:
            copy=Path(temp)/'program';shutil.copytree(PROGRAM,copy)
            p=copy/'research'/name;data=json.loads(p.read_text());change(data)
            p.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,message):module.check(copy)

    def test_reported_replica_result_cannot_become_admitted(self):
        self.mutate_research('ENGINE_FAN_PARAMETER_LEDGER.json',
            lambda d:next(v for v in d['parameter_records'] if v['id']=='P040').update(automatic_model_admission=True),
            'cannot automatically admit')

    def test_missing_fan_geometry_cannot_become_numeric_zero(self):
        self.mutate_research('ENGINE_FAN_PARAMETER_LEDGER.json',
            lambda d:next(v for v in d['parameter_records'] if v['id']=='P078').update(reported_value=0),
            'must remain null')

    def test_claim_requires_original_artifact_lineage(self):
        self.mutate_research('ENGINE_FAN_PARAMETER_LEDGER.json',
            lambda d:d['original_claim_index'][0].update(original_artifact_sha256='0'*64),
            'Original artifact provenance')

    def test_public_source_view_rejects_excerpt_payload(self):
        self.mutate_research('SOURCE_FAMILIES.json',
            lambda d:d['families'][0]['members'][0].update(short_quote='private imported quotation'),
            'excerpt/cache payload prohibited')

    def test_navigation_cannot_fill_matrix_input(self):
        self.mutate_research('matrix-crosswalk.json',
            lambda d:d['rows'][0].update(accepted_input_value=2.85),
            'Navigation cannot admit')

    def test_unmodified_view_digest_is_verified(self):
        with tempfile.TemporaryDirectory() as temp:
            copy=Path(temp)/'program';shutil.copytree(PROGRAM,copy)
            with (copy/'research/CONSOLIDATED_REPORT.md').open('a') as stream:stream.write('\nSilent modification\n')
            with self.assertRaisesRegex(ValueError,'public view digest differs'):module.check(copy)


if __name__=='__main__':unittest.main()
