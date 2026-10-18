"""Small stdlib checks for the saved-stock provenance and local-gate boundary."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

H=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('_stock_local_source_only',H/'admit.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
records=module.RECORDS

class Checks(unittest.TestCase):
    def test_actual_closed_stock_not_union(self):
        row=records.closed_stock()
        self.assertEqual(row['candidate_BREP']['sha256'],'42da92ccbcf08783e69edba68bbeb56d3963746538d48682a3e495310a88e776')
        self.assertFalse(row['failed_union_used_as_candidate']);self.assertFalse(row['old_complete7_law_inherited'])

    def test_no_scientific_import(self):
        self.assertFalse(set(sys.modules).intersection({'OCP','build123d','numpy','gmsh'}))

    def test_parent_success_relabel_refused(self):
        actual=records.read
        def changed(path):
            data=actual(path)
            if Path(path).name=='root-terminal-review-001.json':data['status']='PASSED'
            return data
        with patch.object(records,'read',changed),self.assertRaisesRegex(ValueError,'Parent refusal scope'):records.closed_stock()

    def test_union_artifact_substitution_refused(self):
        actual=records.read
        def changed(path):
            data=actual(path)
            if Path(path).name=='terminal-collection.json':
                data['all_outputs'][str((records.STOCK/'native-body.brep').relative_to(records.R))]['sha256']='9bea2115dda827aef3f01ec560c2bad6d93d8a09c5c7b0cb5135a239d4ee0770'
            return data
        with patch.object(records,'read',changed),self.assertRaisesRegex(ValueError,'stock artifact differs'):records.closed_stock()

    def test_changed_readback_gate_refused(self):
        actual=records.read
        def changed(path):
            data=actual(path)
            if Path(path).name=='volume-integration.json':data['adaptive_relative_difference']=.5
            return data
        with patch.object(records,'read',changed),self.assertRaisesRegex(ValueError,'readback gate'):records.closed_stock()

    def test_changed_effective_ledger_refused(self):
        actual=records.read
        def changed(path):
            data=actual(path)
            if Path(path)==records.PARENT/'output-001/assessment.json':data['actual_window_branch_ledgers']['base-without-ribs']['rows'][0]['inset_mm']=1.5
            return data
        with patch.object(records,'read',changed),self.assertRaisesRegex(ValueError,'ledger crossed'):records.closed_stock()

    def test_pending_refuses_before_native(self):
        with tempfile.TemporaryDirectory()as folder:
            path=Path(folder)/'pending.json';path.write_text(json.dumps(dict(schema='first-window-stock-native-local-plan-1',bounds=dict(outer=600,inner=560,CPU=[520,540],threads=1,workers=0),launch_ready=False,root_GO_sha256=None)))
            with self.assertRaisesRegex(ValueError,'NON-ARMED'):module.verify(path,module.sha(path),True)

    def test_strict_empty_retains_dimensional_requirement(self):
        row=dict(native_topologically_empty=True,native_valid=True,counts=dict(solids=0,faces=0,edges=0,vertices=0),highest_topological_dimension=None)
        module.strict_empty(row);row['counts']['edges']=1
        with self.assertRaises(ValueError):module.strict_empty(row)

    def test_original_gate_function_is_not_rewritten(self):
        self.assertEqual(module.GATE.local_gate_flags.__code__.co_filename,str(H.with_name('bounded-webs-C1-endfillet-preparation-002')/'close_end.py'))
        self.assertEqual(module.GATE.BASELINE,'de0e55a3150dacc5428bbc301d18d2e43477f038c3f4df295d9373af8e906b63')

    def test_same_solid_three_original_overloads(self):
        basis=module.load('_original_volume_fixture',records.R/'work/carrier-process-20261017/bounded-webs-BREP-volume-method-diagnostic-preparation-001/compare.py')
        solid=object();seen=[]
        class Props:
            def Mass(self):return 2.
        class Methods:
            @staticmethod
            def VolumeProperties_s(value,props,*args):seen.append((value,args));return .0 if type(args[0])is float else None
        rows=basis.evaluate(solid,Methods,Props)
        self.assertEqual([args for value,args in seen],[(False,False,False),(True,False,False),(1e-10,True,False)])
        self.assertTrue(all(value is solid for value,args in seen));self.assertEqual(len(rows),3)

    def test_measurements_and_Cut_raws_before_gates(self):
        source=(H/'admit.py').read_text()
        self.assertLess(source.index("write(out/'native-volume-overloads.json'"),source.index("strict_empty(summaries['baseline-minus-stock'])"))
        self.assertLess(source.index("write(out/'local-measurements-before-gates.json'"),source.index("strict_empty(summaries['baseline-minus-stock'])"))
        self.assertLess(source.index("write(out/(name+'-raw-preservation.json')"),source.index('summaries[name]=summary(raw)'))

    def test_no_rebuild_or_union_or_current_subset_gate(self):
        source=(H/'admit.py').read_text();tree=ast.parse(source)
        self.assertNotIn('old + stock',source);self.assertNotIn('current07b-minus',source)
        calls=[ast.unparse(n.func)for n in ast.walk(tree)if isinstance(n,ast.Call)]
        self.assertNotIn('builder.build',calls);self.assertNotIn('candidate.fuse',calls)
        self.assertIn("for name in ('baseline-minus-stock','stock-minus-baseline')",source)

if __name__=='__main__':unittest.main()
