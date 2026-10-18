"""Small stdlib guards; no actual mesh, package, Gmsh or NumPy imports."""
import ast
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('unarmed_real_bridge', HERE / 'run.py')
r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)


class CampaignDouble:
    """Scheduling double only: frozen bridge maths are tested separately."""
    def __init__(self, stop=3, protected_failure=False):
        self.stop = stop; self.protected_failure = protected_failure; self.lifts = 0
    def compact_t10(self, nodes, elements, groups):
        self.nodes = nodes; self.elements = elements
        return dict(points=list(nodes), cells=list(elements))
    def mark_t4(self, compact, regions):
        return ([0] if len(compact['cells']) < self.stop else []), {'box': [0]}
    def refine_with_ledger(self, p, t, marked, api):
        return p + [len(p) + 1], t + [len(t) + 1], [{'vertex': len(p), 'parents': [0, 1]}]
    def lift_t10(self, compact, p, t, ledger):
        self.lifts += 1
        facet = (100, 101, 102)
        return dict(nodes={i: (0., 0., 0.) for i in p}, elements={i: () for i in t},
                    parent_elements={i: 1 for i in t}, closure_parent_elements=[1],
                    boundary_parent_faces={} if self.protected_failure else {facet: facet},
                    native_to_retained_midpoint_differences=[])
    def boundary(self, elements): return {(100, 101, 102): None}


def run_double(output, **kwargs):
    np = SimpleNamespace(asarray=lambda x, dtype: list(x), float64='float64', int32='int32')
    bridge = CampaignDouble(**kwargs)
    result = r.adaptive_refine(bridge, SimpleNamespace(np=np), {1: ()}, {1: ()},
                              {'bolt0': [100, 101, 102]}, [], output, 20, 20)
    return bridge, result


class Checks(unittest.TestCase):
    def test_protected_facet_unchanged(self):
        out = r.protected_facets({(1, 2, 3): None}, {(1, 2, 3): (1, 2, 3)}, {'bolt0': [1, 2, 3, 5]})
        self.assertEqual(out, {'1,2,3': ['bolt0']})

    def test_protected_facet_subdivision_refused(self):
        with self.assertRaisesRegex(ValueError, 'Protected'):
            r.protected_facets({(1, 2, 3): None}, {(1, 2, 4): (1, 2, 3), (2, 3, 4): (1, 2, 3)}, {'bolt0': [1, 2, 3]})

    def test_protected_facet_missing_refused(self):
        with self.assertRaises(ValueError): r.protected_facets({(1, 2, 3): None}, {}, {'end1': [1, 2, 3]})

    def test_partial_group_does_not_invent_protected_face(self):
        self.assertEqual(r.protected_facets({(1, 2, 3): None}, {}, {'bolt0': [1, 2]}), {})

    def test_multiple_group_labels_kept(self):
        out = r.protected_facets({(1, 2, 3): None}, {(1, 2, 3): (1, 2, 3)}, {'bolt0': [1, 2, 3], 'end1': [1, 2, 3]})
        self.assertEqual(out['1,2,3'], ['bolt0', 'end1'])

    def test_unarmed_before_real_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'plan.json'; p.write_text(json.dumps({'launch_ready': False}))
            with self.assertRaisesRegex(ValueError, 'unarmed'): r.main(p, r.sha(p))

    def test_plan_hash_refused_before_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'plan.json'; p.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'Plan drift'): r.main(p, '0' * 64)

    def test_original_NODE_lexemes_reader(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'mesh.inp'; p.write_text('*NODE\n1,0.100000000000,2e-03,0\n2,1,0,0\n*ELEMENT,TYPE=C3D10\n1,1,2\n')
            self.assertEqual(r.node_lines(p)[1], '1,0.100000000000,2e-03,0\n')
            p.write_text('*NODE\n1,0,0,0\n1,0,0,0\n')
            with self.assertRaises(ValueError): r.node_lines(p)

    def test_Gmsh_only_reads_and_measures(self):
        tree = ast.parse((HERE / 'run.py').read_text()); calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = ast.unparse(node.func)
                if name.startswith('gmsh.'): calls.append(name)
        self.assertEqual(set(calls), {'gmsh.initialize', 'gmsh.finalize', 'gmsh.option.setNumber', 'gmsh.model.addDiscreteEntity',
                                    'gmsh.model.mesh.addNodes', 'gmsh.model.mesh.addElementsByType',
                                    'gmsh.model.mesh.getElements', 'gmsh.model.mesh.getNodes', 'gmsh.model.mesh.getElementQualities',
                                    'gmsh.model.mesh.getElementProperties'})
        self.assertIn("'minDetJac'", ast.unparse(tree)); self.assertIn("'volume'", ast.unparse(tree))

    def test_old_prefix_with_gapped_IDs(self):
        self.assertEqual(r.ordered_tags([10, 30, 80], [82, 30, 10, 81, 80]), [10, 30, 80, 81, 82])
        self.assertEqual(r.ordered_tags([10, 30, 80], [80, 10, 30]), [10, 30, 80])

    def test_old_prefix_failures(self):
        for old, new in [([30, 10], [10, 30, 31]), ([10, 30, 80], [10, 30, 50, 80]),
                         ([10, 30], [10, 31]), ([10, 30], [10, 30, 30]), ([True, 30], [1, 30])]:
            with self.subTest(old=old, new=new), self.assertRaises(ValueError): r.ordered_tags(old, new)

    def test_current_metadata_does_not_inherit_Gmsh_sizing(self):
        reference = dict(nodes=123, gmsh_version='old', global_mesh_size_factor=.875, arbitrary_legacy='unchanged')
        original = dict(reference)
        meta = r.mesh_metadata(reference, {'minimum_Jacobian': .25}, 200, 80, 9., 10.,
                               {'bolt0': 12}, '4.15.2', 'mesh-7', 'a' * 64, 'b' * 64)
        self.assertEqual(reference, original)
        self.assertEqual(meta['historical_reference_mesh_metadata'], reference)
        self.assertNotIn('global_mesh_size_factor', meta)
        self.assertNotIn('gmsh_version', meta)
        self.assertNotIn('arbitrary_legacy', meta)
        self.assertEqual(meta['nodes'], 200)
        self.assertEqual(meta['quality_evaluator']['version'], '4.15.2')
        self.assertFalse(meta['quality_evaluator']['remeshing'])
        self.assertIn('scikit-fem12.0.2', meta['meshing_backend'])

    def test_parent_layout_exact_and_exclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / 'source'; source.mkdir(); output = root / 'output'; output.mkdir()
            names = ['carrier.step', 'study.json', 'geometry.json', 'protected-interfaces.json']
            sources = {}; expected = {}
            for i, name in enumerate(names):
                p = source / name; p.write_bytes((b'original-' + bytes([i])) * 10)
                sources[name] = p; expected[name] = r.sha(p)
            self.assertEqual(r.copy_parent_inputs(sources, output, expected), expected)
            self.assertEqual(sorted(p.name for p in output.iterdir()), sorted(names))
            self.assertTrue(all((output / n).read_bytes() == sources[n].read_bytes() for n in names))
            with self.assertRaises(FileExistsError): r.copy_parent_inputs(sources, output, expected)

    def test_adaptive_campaign_two_passes_and_ordered_journal(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp); bridge, result = run_double(output)
            records = result[1]; self.assertEqual(len(records), 2); self.assertEqual(bridge.lifts, 2)
            rows = [json.loads(x) for x in (output / 'passes.jsonl').read_text().splitlines()]
            self.assertEqual([x['event'] for x in rows], ['pass_start', 'pass_finish', 'pass_start', 'pass_finish', 'targets_reached'])
            first = json.loads((output / records[0]['proof']).read_text()); second = json.loads((output / records[1]['proof']).read_text())
            self.assertEqual(first['input_is'], 'original_mesh7')
            self.assertEqual(second['input_is'], 'previous_pass_output')
            self.assertEqual(second['previous_pass_proof_sha256'], records[0]['proof_sha256'])
            self.assertEqual([first['input_elements'], second['input_elements']], [1, 2])

    def test_adaptive_campaign_protected_failure_not_committed(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            with self.assertRaisesRegex(ValueError, 'Protected'): run_double(output, protected_failure=True)
            self.assertEqual(list(output.glob('pass-*.json')), [])
            self.assertEqual([json.loads(x)['event'] for x in (output / 'passes.jsonl').read_text().splitlines()], ['pass_start'])

    def test_adaptive_campaign_cap_keeps_completed_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp); np = SimpleNamespace(asarray=lambda x, dtype: list(x), float64='', int32='')
            with self.assertRaisesRegex(ValueError, 'output-size'):
                r.adaptive_refine(CampaignDouble(stop=4), SimpleNamespace(np=np), {1: ()}, {1: ()},
                                  {'bolt0': [100, 101, 102]}, [], output, 2, 2)
            proofs = list(output.glob('pass-*.json')); self.assertEqual(len(proofs), 1)
            self.assertEqual(json.loads(proofs[0].read_text())['pass_number'], 1)

    def test_no_scientific_import_at_module_load(self):
        tree = ast.parse((HERE / 'run.py').read_text())
        for n in tree.body:
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                self.assertFalse(any(x.name.startswith(('numpy', 'scipy', 'gmsh', 'skfem')) for x in n.names))


if __name__ == '__main__': unittest.main()
