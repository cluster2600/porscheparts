"""AST/builtins-only checks; never import the held worker or scientific code."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import unittest

PREP=Path(__file__).resolve().parent
SOURCE=PREP/'mesh_atomic_postexport_002.py'
BASE=PREP.parents[2]/'twins/962-cylinder-head-f0/source/mesh_quality_head_postexport.py'


class SourceTests(unittest.TestCase):
    def test_every_one_of_four_metric_counts_is_required(self):
        tree=ast.parse(SOURCE.read_text())
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='audit_after')
        guard=next(n for n in function.body if isinstance(n,ast.If) and
            any(isinstance(x,ast.Constant) and x.value=='Every metric distribution must cover every actual tetrahedron' for x in ast.walk(n)))
        check=ast.FunctionDef(name='check_counts',args=ast.arguments(posonlyargs=[],args=[ast.arg(arg='report'),ast.arg(arg='cells')],kwonlyargs=[],kw_defaults=[],defaults=[]),body=[copy.deepcopy(guard)],decorator_list=[])
        namespace={};exec(compile(ast.fix_missing_locations(ast.Module(body=[check],type_ignores=[])),'<extracted_count_guard>','exec'),namespace)
        names=['minimum_jacobian','native_volume_mm3','minimum_SICN','independent_signed_volume_mm3']
        valid={'quality':{name:{'count':3} for name in names}}
        namespace['check_counts'](valid,[0,1,2])
        for name in names:
            for bad in [2,4,True,3.0,None]:
                with self.subTest(metric=name,count=bad):
                    changed=copy.deepcopy(valid);changed['quality'][name]['count']=bad
                    with self.assertRaises(ValueError):namespace['check_counts'](changed,[0,1,2])

    def test_exact_reverse_proof_restores_all_public_base_bytes(self):
        record=json.loads((PREP/'source-replacements-002.json').read_text())
        text=SOURCE.read_text()
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),record['adapted_sha256'])
        for row in reversed(record['replacements']):
            self.assertEqual(text.count(row['new']),1)
            text=text.replace(row['new'],row['old'],1)
        self.assertEqual(text.encode(),BASE.read_bytes())
        self.assertEqual(hashlib.sha256(BASE.read_bytes()).hexdigest(),'3e76e32426177ecf68300fce826ef6beccbbfc76ea4dded9e0aae4ae7eb1df86')

    def test_new_core_deadline_inputs_and_single_optimizer_cache_sequence(self):
        tree=ast.parse(SOURCE.read_text());assignments={}
        for n in tree.body:
            if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):
                try:assignments[n.targets[0].id]=ast.literal_eval(n.value)
                except (ValueError,TypeError):pass
        self.assertEqual(assignments['CORE_SHA256'],'61542a339b03cfab600ac869d12a0ae4d72768bcc5db5838efa3bb72a0ccfada')
        self.assertEqual(assignments['DEADLINE'],1200)
        self.assertEqual(assignments['OPTIONS']['Mesh.OptimizeThreshold'],.3)
        self.assertEqual(assignments['OPTIONS']['Mesh.Optimize'],0)
        self.assertEqual(assignments['INPUT_HASHES']['work/962-engineering/atomic-cavity-volume-readback-peer-result-001/review.json'],'cc00c64f53f5fdfc6fef8a76aa7fe31d205b49db95e0b28db110331bf95d9bb7')
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='optimize_and_refresh')
        calls=[n for n in ast.walk(function) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
        optimize=[n for n in calls if n.func.attr=='optimize'];refresh=[n for n in calls if n.func.attr=='rebuildElementCache']
        self.assertEqual(len(optimize),1);self.assertEqual(len(refresh),1)
        self.assertLess(optimize[0].lineno,refresh[0].lineno)
        self.assertEqual({n.arg:ast.literal_eval(n.value) for n in optimize[0].keywords},{'method':'','force':True})
        self.assertIs(ast.literal_eval(refresh[0].args[0]),False)
        self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='generate' for n in ast.walk(tree)))


if __name__=='__main__':unittest.main()
