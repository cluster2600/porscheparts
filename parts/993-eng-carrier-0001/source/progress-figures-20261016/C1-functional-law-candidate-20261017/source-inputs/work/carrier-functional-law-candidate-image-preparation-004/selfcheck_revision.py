"""Narrow stdlib checks for runtime completion and diagnostic-before-refusal; no graphics imports."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

H = Path(__file__).resolve().parent
R = H.parents[1]
O = R / 'work/carrier-functional-law-candidate-image-preparation-003'
spec = importlib.util.spec_from_file_location('_candidate_runtime_revision', H/'figure.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
changes = m.read(H/'source-changes.json')

def node(source, name):
    return next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == name)

def diagnostic_fragment():
    body = node((H/'figure.py').read_text(), 'render').body
    start = next(i for i,n in enumerate(body) if isinstance(n, ast.Assign) and any(isinstance(t,ast.Name) and t.id=='diagnostic' for t in n.targets))
    fragment = body[start:start+3]
    assert len(fragment)==3 and isinstance(fragment[1],ast.Expr) and ast.unparse(fragment[1].value.func)=='write' and ast.unparse(fragment[2].value.func)=='require'
    return ast.Module(body=fragment,type_ignores=[])

class Checks(unittest.TestCase):
    def test_whole_source_preparer_and_doc_inverse(self):
        for name,key in [('figure.py','figure_substitutions'),('prepare.py','preparer_substitutions'),('PREPARATION.md','documentation_substitutions')]:
            s=(H/name).read_text()
            for row in reversed(changes[key]):
                self.assertEqual(s.count(row['after']),1); s=s.replace(row['after'],row['before'],1)
            self.assertEqual(s.encode(),(O/name).read_bytes())
        for name,digest in changes['copied_bytes_equal'].items():self.assertEqual(m.sha(H/name),m.sha(O/name),digest)
    def test_no_render_math_or_other_function_changed(self):
        old=(O/'figure.py').read_text();new=(H/'figure.py').read_text()
        names=[n.name for n in ast.parse(old).body if isinstance(n,ast.FunctionDef)]
        for name in names:
            a,b=copy.deepcopy(node(old,name)),copy.deepcopy(node(new,name))
            if name=='verify':
                q=changes['figure_substitutions'][0];b=node(new.replace(q['after'],q['before'],1),name)
            self.assertEqual(ast.dump(a),ast.dump(b),name)
    def test_original_guard_literal_and_diagnostic_order(self):
        source=(H/'figure.py').read_text()
        guard="require(loaded <= set(runtime), 'Plot package imported outside the retained runtime')"
        self.assertEqual(source.count(guard),1);self.assertEqual((O/'figure.py').read_text().count(guard),1)
        self.assertIn("write(output / 'runtime-origin-diagnostic.json', diagnostic)",source)
        diagnostic_fragment()
    def test_outside_origin_is_saved_before_same_refusal(self):
        saved=[];runtime={'/pinned/site-packages/a.py':'digest'};loaded=set(runtime)|{'/outside/site-packages/b.py'}
        scope=dict(runtime=runtime,loaded=loaded,output=Path('/fresh'),write=lambda p,v:saved.append((p,copy.deepcopy(v))),require=m.require)
        with self.assertRaisesRegex(ValueError,'Plot package imported outside'):exec(compile(diagnostic_fragment(),'<actual diagnostic AST>','exec'),scope)
        self.assertEqual(saved[0][1]['outside_runtime_imported_files'],['/outside/site-packages/b.py'])
        self.assertEqual(saved[0][1]['runtime_imported_files'],sorted(loaded))
    def test_success_still_saves_empty_outside_list(self):
        saved=[];runtime={'/pinned/site-packages/a.py':'digest'}
        exec(compile(diagnostic_fragment(),'<actual diagnostic AST>','exec'),dict(runtime=runtime,loaded=set(runtime),output=Path('/fresh'),write=lambda p,v:saved.append(v),require=m.require))
        self.assertEqual(saved[0]['outside_runtime_imported_files'],[])
    def test_diagnostic_write_is_exclusive(self):
        with tempfile.TemporaryDirectory()as folder:
            p=Path(folder)/'diagnostic.json';m.write(p,{'outside':['retained']});before=p.read_bytes()
            with self.assertRaises(FileExistsError):m.write(p,{'outside':[]})
            self.assertEqual(p.read_bytes(),before)
    def test_completed_map_preserves_old_and_declares_direct_dependencies(self):
        completion=m.read(H/'runtime-completion.json');original=m.read(O/'pending-plan.json')['runtime_sha256'];added=completion['additional_runtime_sha256']
        self.assertEqual(len(original),5249);self.assertEqual(len(added),54)
        self.assertEqual(len(set(added)-set(original)),10)
        self.assertEqual(len(dict(original,**added)),5259)
        for name,digest in original.items():self.assertEqual(dict(original,**added)[name],digest)
        self.assertEqual(completion['runtime_origin_evidence']['whole_imported_files'],598)
        self.assertEqual(len(completion['runtime_origin_evidence']['new_exact_package_rows']),10)
        for name,digest in added.items():self.assertEqual(m.sha(R/name),digest)
        byname={r['name'].lower().replace('_','-'):r for r in completion['distribution_metadata']}
        self.assertIn('pyparsing',byname);self.assertIn('hsluv',byname)
        self.assertIn('pyparsing>=3',byname['matplotlib']['unconditional_requirements'])
        self.assertIn('hsluv',byname['vispy']['unconditional_requirements'])
        self.assertFalse({'numpy','matplotlib','vispy','OCP','gmsh'}&set(sys.modules))

if __name__ == '__main__':unittest.main()
