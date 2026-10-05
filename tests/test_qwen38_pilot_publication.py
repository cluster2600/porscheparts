"""Public offline response regrading and meaningful tampering refusals."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

PACKAGE = Path(__file__).resolve().parents[1]/'training/qwen38-natural-language-pilot-20261004'
spec=importlib.util.spec_from_file_location('qwen38_publication_check',PACKAGE/'check_publication.py')
CHECK=importlib.util.module_from_spec(spec);spec.loader.exec_module(CHECK)


class Qwen38PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='qwen38-publication-mutation-')
        self.directory=Path(self.temp.name)
        for name in ('cases.json','results.json','README.md'):
            (self.directory/name).write_bytes((PACKAGE/name).read_bytes())
        self.cases=json.loads((self.directory/'cases.json').read_bytes())
        self.results=json.loads((self.directory/'results.json').read_bytes())

    def tearDown(self):self.temp.cleanup()

    def write(self):
        for name,value in (('cases.json',self.cases),('results.json',self.results)):
            (self.directory/name).write_text(json.dumps(value,ensure_ascii=False,allow_nan=False)+'\n')

    def change_raw(self,index,raw):
        row=self.cases['cases'][index];row['raw_response']=raw
        data=raw.encode('utf-8');row['raw_response_sha256']=hashlib.sha256(data).hexdigest()
        row['raw_response_utf8_bytes']=len(data)

    def test_published_responses_regrade_without_runtime(self):
        result=CHECK.check(self.directory)
        self.assertEqual((result['model_correct'],result['baseline_metadata_correct'],result['paired_wins']),(8,6,2))
        self.assertFalse(result['model_or_baseline_rerun'])
        self.assertFalse(result['historical_runtime_execution_proved_by_this_check'])

    def test_allowed_tuple_for_wrong_request_is_rejected(self):
        candidate=json.loads(self.cases['cases'][0]['raw_response'])
        candidate['parameters']['outer_diameter_mm']=40
        raw=json.dumps(candidate);CHECK.V.validate_json(raw)  # Geometric/schema validity alone passes.
        self.change_raw(0,raw);self.write()
        with self.assertRaisesRegex(ValueError,'do not match this request'):CHECK.check(self.directory)

    def test_duplicate_raw_key_rejected_even_with_updated_hash(self):
        raw=self.cases['cases'][0]['raw_response'].replace('{','{"schema_version":1,',1)
        json.loads(raw)  # Default json silently accepts the duplicate.
        self.change_raw(0,raw);self.write()
        with self.assertRaisesRegex(ValueError,'Duplicate JSON key'):CHECK.check(self.directory)

    def test_falsified_aggregate_count_is_rejected(self):
        self.results['scores']['model_correct']=7;self.write()
        with self.assertRaisesRegex(ValueError,'Aggregate score differs'):CHECK.check(self.directory)

    def test_private_path_leak_is_rejected(self):
        self.results['provenance']['leaked_source']='/Users/private-owner/gold.json';self.write()
        with self.assertRaisesRegex(ValueError,'Private path'):CHECK.check(self.directory)

    def test_credential_leak_is_rejected(self):
        self.results['provenance']['leaked_token']='hf_'+'a'*40;self.write()
        with self.assertRaisesRegex(ValueError,'credential material'):CHECK.check(self.directory)

    def test_nonfinite_raw_json_rejected_even_with_updated_hash(self):
        raw=self.cases['cases'][0]['raw_response'].replace('"outer_diameter_mm": 45','"outer_diameter_mm": NaN')
        self.assertIn('NaN',raw);self.change_raw(0,raw);self.write()
        with self.assertRaisesRegex(ValueError,'Nonstandard JSON number'):CHECK.check(self.directory)

    def test_cpu_target_cannot_be_relabelled_as_ceiling(self):
        self.results['resources']['authorized_rolling_cpu_ceiling_core_equivalents']=2;self.write()
        with self.assertRaisesRegex(ValueError,'Resource metadata differs'):CHECK.check(self.directory)
