"""Stdlib/AST-only proof-bound input tests; no prepared/scientific module imports."""
import ast,hashlib,json
from pathlib import Path
import tempfile,unittest
from types import SimpleNamespace

PREP=Path(__file__).resolve().parent
SOURCE=PREP/'mesh_delaunay_postexport.py'
SOURCE_SHA='ebb1f1ba8e7c0b032a4eb0178bbf8c332c68070816e6626f4a3f4788ed638527'
if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SOURCE_SHA:raise ValueError('Frozen source changed before AST extraction')
TREE=ast.parse(SOURCE.read_text())
FUNCTIONS={n.name:n for n in TREE.body if isinstance(n,ast.FunctionDef)}

class FirstPassGuards(unittest.TestCase):
    def context(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);root=Path(temporary.name).resolve()
        q=((0.,0.,0.),(1.,0.,0.),(0.,1.,0.));nt=(1,2,3);et=(4,5);en=((1,2,3,1),(1,3,2,1));state=(q,nt,et,en)
        sha=lambda value:hashlib.sha256(repr(value).encode()).hexdigest()
        identity=dict(zip(('sorted_coordinates_sha256','sorted_node_tags_sha256','sorted_tetra_tags_sha256','tagged_tetra_connectivity_sha256'),map(sha,state)))
        classification={'complete_synthetic_classification':True};surface=object()
        core=SimpleNamespace(CANDIDATE_SHA='c'*64,array_sha=sha,tagged_volume=lambda gmsh:(q,None,nt,et,en),surface_roundtrip=lambda *a,**k:surface)
        audit=dict(tetrahedra=2,total_mesh_nodes=3,tetra_referenced_nodes=3,tetra_referenced_interior_nodes=1,unreferenced_mesh_nodes=0,summed_tetra_volume_mm3=1.,volume_relative_error=0.,actual_tetra_boundary={'observed':True},internal_tetra_face_orientation={'observed':True},classifications=classification,array_sha256s=identity,quality={'minimum_SICN':{'minimum':-1e-17}})
        report=dict(status='reading_saved_mesh',stage='reopening_saved_file_for_tagged_array_identity',direct_full_tetra_face_incidence_completed=True,direct_internal_face_orientation_completed=True,exact_source_boundary_coordinate_bits=True,mesh_sha256='d'*64,candidate_sha256='c'*64,audit=audit)
        path=root/'audit.json';path.write_text(json.dumps(report))
        ns=dict(ROOT=root,INPUT_READBACK='audit.json',INPUT=root/'saved.msh',INPUT_HASHES={'saved.msh':'d'*64,'audit.json':'a'*64},json=json,classifications=lambda *a:classification)
        exec(compile(ast.Module(body=[FUNCTIONS['array_identity'],FUNCTIONS['load_before']],type_ignores=[]),str(SOURCE),'exec'),ns)
        return SimpleNamespace(root=root,path=path,report=report,ns=ns,core=core,state=state,surface=surface,classification=classification)

    def write(self,c):c.path.write_text(json.dumps(c.report))

    def test_single_complete_first_pass_closes_identity_but_keeps_prior_timeout(self):
        c=self.context();state,report=c.ns['load_before'](c.core,object(),[0,1],[0])
        self.assertEqual(state,c.state);self.assertIs(report['current_surface'],c.surface)
        self.assertTrue(report['input_array_identity_freshly_closed_before_optimizer'])
        self.assertFalse(report['prior_optional_reopen_completed']);self.assertFalse(report['prior_reader_terminal_completion'])
        self.assertTrue(report['missing_worker_array_proof_not_claimed'])
        self.assertEqual(report['retained_not_recomputed']['quality']['minimum_SICN']['minimum'],-1e-17)
        self.assertNotIn('retained_independent_quality_path',report)

    def test_every_loaded_array_must_match_the_one_proof(self):
        for key in self.context().report['audit']['array_sha256s']:
            with self.subTest(key=key):
                c=self.context();c.report['audit']['array_sha256s'][key]='0'*64;self.write(c)
                with self.assertRaisesRegex(ValueError,'Loaded tagged arrays differ'):c.ns['load_before'](c.core,object(),[0,1],[0])

    def test_complete_first_pass_flags_identity_and_counts_are_required(self):
        cases=[('status','completed'),('stage','some_other_stage'),('direct_full_tetra_face_incidence_completed',False),('direct_internal_face_orientation_completed',1),('exact_source_boundary_coordinate_bits',False),('mesh_sha256','e'*64),('candidate_sha256','e'*64)]
        for key,value in cases:
            with self.subTest(key=key):
                c=self.context();c.report[key]=value;self.write(c)
                with self.assertRaisesRegex(ValueError,'Complete first-pass audit'):c.ns['load_before'](c.core,object(),[0,1],[0])
        for key,value in [('tetrahedra',3),('total_mesh_nodes',4)]:
            with self.subTest(key=key):
                c=self.context();c.report['audit'][key]=value;self.write(c)
                with self.assertRaisesRegex(ValueError,'Complete first-pass audit'):c.ns['load_before'](c.core,object(),[0,1],[0])

    def test_fresh_classification_must_match_the_same_proof(self):
        c=self.context();c.ns['classifications']=lambda *args:{'changed':True}
        with self.assertRaisesRegex(ValueError,'classifications differ'):c.ns['load_before'](c.core,object(),[0,1],[0])

    def test_optimizer_order_and_full_base_reverse_are_unchanged(self):
        record=json.loads((PREP/'source-delta.json').read_text());text=SOURCE.read_text()
        for row in reversed(record['replacements']):
            self.assertEqual(text.count(row['new']),1);text=text.replace(row['new'],row['old'],1)
        self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),'28746e14a041db464c3a41b732f1fc3e9ad9fd6ce96e886f728e5409d6ea0e36')
        calls=[n for n in ast.walk(FUNCTIONS['worker']) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
        self.assertLess(next(n.lineno for n in calls if n.func.id=='load_before'),next(n.lineno for n in calls if n.func.id=='optimize_and_refresh'))
        optimizer=FUNCTIONS['optimize_and_refresh'];native=[n for n in ast.walk(optimizer) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
        self.assertEqual([n.func.attr for n in native],['update','optimize','update','rebuildElementCache','update'])
        call=next(n for n in native if n.func.attr=='optimize');self.assertEqual({kw.arg:ast.literal_eval(kw.value) for kw in call.keywords},{'method':'','force':True})
        self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='generate' for n in ast.walk(TREE)))

if __name__=='__main__':unittest.main()
