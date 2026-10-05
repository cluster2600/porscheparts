"""Check source holdouts and corruption rejection, not metallurgical expertise."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT/'training/qwen-metal-additive-20261002'
SPEC = importlib.util.spec_from_file_location('metal_data', PACKAGE/'prepare.py')
DATA = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DATA)

class MetalDataTest(unittest.TestCase):
    def test_frozen_data_and_whole_publication_holdouts(self):
        result = DATA.audit(PACKAGE)
        self.assertEqual(result['status'], 'pass')
        records = DATA.read_rows(PACKAGE/'data/sft-records.jsonl')
        chunks = DATA.read_rows(PACKAGE/'data/cpt-provenance.jsonl')
        seen = {}
        for row in records + chunks:
            ids = row.get('source_ids', [row.get('source_id')])
            for source in ids:
                seen.setdefault(source, set()).add(row['split'])
        self.assertTrue(all(len(splits) == 1 for splits in seen.values()))
        self.assertEqual(seen['MET003'], {'valid'})
        self.assertEqual(seen['MET004'], {'test'})
        self.assertEqual(sum(result['counts']['sft'].values()), 58)
        self.assertEqual(sum(result['counts']['cpt'].values()), 116)

    def test_multi_source_example_cannot_cross_partitions(self):
        with self.assertRaisesRegex(ValueError, 'Cross-partition'):
            DATA.split_for(['MET001', 'MET003'])

    def test_missing_material_property_is_not_invented(self):
        rows = DATA.read_rows(PACKAGE/'data/sft-records.jsonl')
        missing = [r for r in rows if r['id'].endswith('validated_powder_conductivity_at_1400C')]
        self.assertEqual(len(missing), 7)
        for row in missing:
            self.assertIsNone(row['expected']['value'])
            self.assertEqual(row['expected']['status'], 'not_in_record')

    def test_changed_source_rejected_before_data_is_rebuilt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/'package'
            shutil.copytree(PACKAGE, root)
            source = json.loads((root/'input/documents.json').read_text())[0]
            body = root/source['path']
            body.write_text(body.read_text() + '\nUnverified replacement property')
            with self.assertRaisesRegex(ValueError, 'Changed document'):
                DATA.prepare(root)
            with self.assertRaisesRegex(ValueError, 'Frozen input changed'):
                DATA.audit(root)

if __name__ == '__main__':
    unittest.main()
