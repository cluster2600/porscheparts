"""Prepared pure synthetic oracle checks; none is a native repair result."""
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest

HERE=Path(__file__).resolve().parent


def load(name):
    spec=importlib.util.spec_from_file_location('literal_'+name,HERE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


A=load('assess_003');P=load('prepare')
REF=json.loads((HERE/'expectations.json').read_text())


def success(name,directory):
    """One valid literal quotient triangulation, not an emulated native execution."""
    case=REF['cases'][name];points=case['input_points'];faces=case['input_oriented_faces']
    members=set(case['group_members']);keeper=case['expected_keeper'];origins=case['expected_output_origins']
    indices={v:i for i,v in enumerate(origins)};output=[];sources=[]
    fixed_cap=set(case['input_observations']['fixed_cap_face_ids'])
    for i,t in enumerate(faces):
        mapped=tuple(keeper if v in members else v for v in t)
        if len(set(mapped))!=3:continue
        output.append(tuple(indices[v] for v in mapped))
        sources.append(i if any(points[v][2]!=0. for v in t) or i in fixed_cap else A.MAX)
    (directory/'candidate.bin').write_bytes(P.surface_bytes([points[v] for v in origins],output))
    (directory/'vertex-coordinate-origins.u64').write_bytes(b''.join(struct.pack('<Q',v) for v in origins))
    (directory/'face-source-ids.u64').write_bytes(b''.join(struct.pack('<Q',i) for i in sources))
    score=case['native_score_six_order_bounds'][str(keeper)]
    star=[i for i,t in enumerate(faces) if set(t)&members and any(points[v][2]!=0. for v in t)]
    report=dict(status='local_candidate_only',manufacturing_authorized=False,head_surface_or_solver_admitted=False,
        before_poor_faces=len(case['input_observations']['poor_face_ids']),after_poor_faces=0,
        exported=True,candidate_file_present=True,guards={k:True for k in A.GUARDS},output_vertices=17,output_faces=34,
        group_choices=[dict(component_minimum=min(members),members=sorted(members),selected_keeper=keeper,
            side_star_minimum_quality=score['score_lower'],side_star_faces=star)],coupled_side_face_ids=[],
        global_Euler_before=0,global_Euler_after=0,fixed_cap_face_ids=sorted(fixed_cap),fixed_cap_faces=len(fixed_cap),
        original_cap_exact_area='12',mapped_cap_exact_area='12')
    report.update(input_vertices=len(points),input_faces=len(faces),target_edges=len(case['targets']),
        native_poor_face_ids=case['input_observations']['poor_face_ids'],native_reference_face_ids=case['input_observations']['incident_face_ids'],
        original_cap_cycles=[list(x) for x in A.cap_cycles([tuple(t) for t in faces if all(points[v][2]==0. for v in t)])],
        mapped_cap_cycles=[list(x) for x in A.cap_cycles([tuple(origins[v] for v in t) for t in output if all(points[origins[v]][2]==0. for v in t)])])
    (directory/'report.json').write_text(json.dumps(report))


class FixtureOracleTests(unittest.TestCase):
    def test_literal_patch_and_all_boundary_annulus_preconditions(self):
        path=A.ROOT/'work/962-engineering/atomic-cavity-plane-clip-patch-census-prep-001/patch_kernels.py'
        self.assertEqual(A.sha(path),'856a39e7772a6245e9750a1282756de6338983e3412bfcbc32e4c493eab81dc2')
        spec=importlib.util.spec_from_file_location('retained_tiny_patch_kernel',path)
        kernel=importlib.util.module_from_spec(spec);spec.loader.exec_module(kernel)
        for name in ('pair','triple'):
            case=REF['cases'][name];faces=case['input_oriented_faces'];observed=case['input_observations']
            patch=kernel.topology({i:tuple(faces[i]) for i in observed['incident_face_ids']})
            cap=kernel.topology({i:tuple(faces[i]) for i in observed['cap_face_ids']})
            self.assertTrue(patch['local_oriented_manifold_with_boundary'])
            self.assertTrue(cap['local_oriented_manifold_with_boundary'])
            self.assertEqual((cap['Euler'],cap['edge_connected_components'],len(cap['oriented_boundary_cycles'])),(0,1,2))
            self.assertEqual(cap['vertices'],len(cap['boundary_vertices']))

    def test_complete_literal_pair_and_triple(self):
        for name in ('pair','triple'):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as d:
                directory=Path(d);success(name,directory)
                result=A.assess(name,directory)
                self.assertEqual((result['vertices'],result['faces'],result['exact_volume_mm3']),(17,34,'12'))
                self.assertEqual(result['keeper'],17 if name=='pair' else 18)

    def test_changed_coordinate_is_not_a_source_subset(self):
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d);success('pair',directory);path=directory/'candidate.bin';raw=bytearray(path.read_bytes())
            raw[24]^=1;path.write_bytes(raw)
            with self.assertRaises(ValueError):A.assess('pair',directory)

    def test_fixed_cap_face_cannot_be_relabelled_retriangulated(self):
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d);success('pair',directory);path=directory/'face-source-ids.u64'
            values=[r[0] for r in struct.iter_unpack('<Q',path.read_bytes())]
            fixed=set(REF['cases']['pair']['input_observations']['fixed_cap_face_ids'])
            i=next(i for i,v in enumerate(values) if v in fixed);values[i]=A.MAX
            path.write_bytes(b''.join(struct.pack('<Q',v) for v in values))
            with self.assertRaises(ValueError):A.assess('pair',directory)

    def test_refusal_never_exports_candidate(self):
        for name in ('fixed-refusal','cross-loop-refusal'):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as d:
                directory=Path(d);report=dict(status='rejected_no_candidate',exported=False,candidate_file_present=False,
                    manufacturing_authorized=False,head_surface_or_solver_admitted=False,before_poor_faces=2)
                case=REF['cases'][name];points=case['input_points'];faces=case['input_oriented_faces']
                report.update(input_vertices=len(points),input_faces=len(faces),target_edges=len(case['targets']),
                    native_poor_face_ids=case['input_observations']['poor_face_ids'],native_reference_face_ids=case['input_observations']['incident_face_ids'],
                    original_cap_cycles=[list(x) for x in A.cap_cycles([tuple(t) for t in faces if all(points[v][2]==0. for v in t)])],mapped_cap_cycles=[])
                (directory/'report.json').write_text(json.dumps(report))
                self.assertEqual(A.assess(name,directory)['expected_native_returncode'],3)
                (directory/'candidate.bin').write_bytes(b'not-an-export')
                with self.assertRaises(ValueError):A.assess(name,directory)

    def test_native_ID_partitions_cannot_be_omitted_or_fractional(self):
        for key in ('native_poor_face_ids','native_reference_face_ids'):
            with self.subTest(key=key),tempfile.TemporaryDirectory() as d:
                directory=Path(d);success('pair',directory);path=directory/'report.json';r=json.loads(path.read_text())
                r[key][0]=float(r[key][0]);path.write_text(json.dumps(r))
                with self.assertRaises(ValueError):A.assess('pair',directory)

    def test_mapped_cap_cycle_must_match_actual_source_map(self):
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d);success('pair',directory);path=directory/'report.json';r=json.loads(path.read_text())
            r['mapped_cap_cycles'][0].reverse();path.write_text(json.dumps(r))
            with self.assertRaises(ValueError):A.assess('pair',directory)


if __name__=='__main__':unittest.main()
