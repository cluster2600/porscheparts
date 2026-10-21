"""Two focused historical-label tests; the unchanged twelve-test suite is separate."""
from pathlib import Path
import ast,json,unittest
H=Path(__file__).resolve().parent;R=H.parents[1]
class Checks(unittest.TestCase):
    def test_whole_source_inverse_and_unchanged_scientific_functions(self):
        changes=json.loads((H/'source-changes.json').read_bytes());new=(H/'figure.py').read_text();restored=new
        for e in reversed(changes['file_changes']['figure.py']['replacements']):self.assertEqual(restored.count(e['after']),1);restored=restored.replace(e['after'],e['before'],1)
        original=(R/changes['file_changes']['figure.py']['original_path']).read_text();self.assertEqual(restored,original)
        functions=lambda text:{n.name:ast.dump(n,include_attributes=False)for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
        a,b=functions(original),functions(new);self.assertEqual([k for k in a if a[k]!=b[k]],['render'])
    def test_snapshot_labels_and_values_preserved(self):
        source=(H/'figure.py').read_text();self.assertIn('At the law observation, geometry gates were pending',source);self.assertNotIn('all downstream geometry checks remain PENDING',source)
        p=json.loads((H/'pending-plan.json').read_bytes());self.assertEqual(p['downstream_geometry_gate_status_scope'],'historical_at_the_law_observation');self.assertEqual(p['downstream_geometry_gates'],'PENDING')
        old=H.with_name('carrier-seven-edge-law-figure-preparation-001');self.assertEqual((H/'law-data.json').read_bytes(),(old/'law-data.json').read_bytes());self.assertEqual(p['runtime_sha256'],json.loads((old/'pending-plan.json').read_bytes())['runtime_sha256'])
if __name__=='__main__':unittest.main()
