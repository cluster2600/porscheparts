"""UNRUN focused stdlib cooling/release guards; root alone may invoke after review."""
from pathlib import Path
from itertools import product
from tempfile import TemporaryDirectory
from unittest.mock import patch
import ast
import hashlib
import importlib.util
import json
import unittest
SOURCE = Path(__file__).with_name('assess.py')
SOURCE_SHA = 'aa7ee403a0a3078df58410815f2b613aaeb9634bd14bc9c90517ce00cec7f2d5'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA
spec = importlib.util.spec_from_file_location('cooling_release_assessor_guard', SOURCE)
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)  # Only stdlib top level; this file remains UNRUN by author.
POLICY = dict(temperature_K=1e-10, displacement_m=1e-12, QP_coordinate_m=2e-13,
              strain=1e-10, stress_Pa=.1, force_N=1e-7, moment_Nm=1e-7)


def geometry_fixture():
    special = {(0., 0., 0.): 0, (1., 0., 0.): 32, (0., 1., 0.): 137}
    return {special.get(p, 1000+i): p for i, p in enumerate(product(tuple(i/8 for i in range(17)), tuple(i/4 for i in range(5)), tuple(i/4 for i in range(5))))}


def release_fixture(energy_before=2., energy_after=0.):
    nodes = {10: dict(disp_x=0., disp_y=0., disp_z=0.), 20: dict(disp_x=0., disp_y=0., disp_z=0.)}
    before = dict(nodes=nodes, forces={10: [-4., 0., 0.], 20: [0., 0., 0.]}, energy_J=energy_before, energy_product_error_bound_J=1e-9)
    after = dict(nodes={10: dict(disp_x=1., disp_y=0., disp_z=0.), 20: dict(nodes[20])},
                 forces={10: [0., 0., 0.], 20: [0., 0., 0.]}, energy_J=energy_after, energy_product_error_bound_J=1e-9)
    return before, after


class Guards(unittest.TestCase):
    def test_phase_masks_clamp_birth_release_and_no_overlap(self):
        geometry = geometry_fixture(); old = {t for t,p in geometry.items() if p[0] <= 1.}
        for step, phase, active, expected, exempt in [(0,'begin',old,135,0),(79,'end',old,135,0),
                (80,'begin',set(geometry),255,0),(180,'end',set(geometry),255,0),
                (181,'begin',set(geometry),6,249),(181,'end',set(geometry),6,0),(182,'end',set(geometry),6,0)]:
            constrained, free, released = a.support_masks(geometry, active, step, phase)
            self.assertEqual((len(constrained),len(released)),(expected,exempt)); self.assertFalse(constrained & free)
            self.assertEqual(constrained | free,{(t,k) for t in active for k in range(3)})
        with self.assertRaises(ValueError): a.support_masks({**geometry,0:(0.,0.,.25)},old,0,'begin')
        for step,phase in [(-1,'begin'),(183,'end'),(181,'middle')]:
            with self.assertRaises(ValueError): a.support_masks(geometry,set(geometry),step,phase)

    def test_declared_cooling_keeps_BEGIN_previous_END_and_exact300_release(self):
        tokens = {7:'400.12345678901234',8:'350'}
        self.assertEqual(a.cooling_values(tokens,161,'begin'),{k:float(v) for k,v in tokens.items()})
        self.assertGreater(a.cooling_values(tokens,180,'begin')[7],300.)
        for step,phase in [(180,'end'),(181,'begin'),(181,'end'),(182,'begin'),(182,'end')]:
            self.assertEqual(a.cooling_values(tokens,step,phase),{7:300.,8:300.})
        self.assertEqual(a.cooling_values(tokens,162,'begin'),a.cooling_values(tokens,161,'end'))
        for step,phase in [(160,'end'),(183,'end'),(181,'other')]:
            with self.assertRaises(ValueError): a.cooling_values(tokens,step,phase)

    def test_release_nonincrease_and_secant_work_refusals(self):
        before,after=release_fixture(); result=a.release_energy_check(before,after,{(20,0)},POLICY)
        self.assertEqual(result['change_J'],-2.);self.assertEqual(result['trapezoidal_internal_work_J'],-2.)
        self.assertIsNone(result['new_independent_Joule_tolerance']);self.assertFalse(result['work_equals_2U_used'])
        bad=dict(after,energy_J=3.)
        with self.assertRaises(ValueError): a.release_energy_check(before,bad,{(20,0)},POLICY)
        bad=dict(before,forces={10:[-3.,0.,0.],20:[0.,0.,0.]})
        with self.assertRaises(ValueError): a.release_energy_check(bad,after,{(20,0)},POLICY)
        with self.assertRaises(ValueError): a.release_energy_check(before,after,{(999,0)},POLICY)

    def test_fixed300_hold_checks_displacements_reactions_tensors_and_energy(self):
        fields={n:[[0.]*3 for _ in range(3)] for n in a.TENSORS}
        nodes={7:dict(disp_x=0.,disp_y=0.,disp_z=0.,temperature=300.,rx=0.,ry=0.,rz=0.)}
        before=dict(nodes=nodes,qp={(3,0):(0,fields)},energy_J=0.,energy_product_error_bound_J=1e-9)
        self.assertTrue(a.hold_state_check(a.Audit(POLICY),before,before)['END181_to_END182_individual_SI_gates_passed'])
        for name,value in [('temperature',300.+2e-10),('disp_x',2e-12),('rx',2e-7)]:
            bad=dict(before,nodes={7:{**nodes[7],name:value}})
            with self.assertRaises(ValueError): a.hold_state_check(a.Audit(POLICY),before,bad)
        with self.assertRaises(ValueError): a.hold_state_check(a.Audit(POLICY),before,{**before,'energy_J':1.})

    def test_energy_product_uses_all_nine_tensor_entries_and_existing_bounds(self):
        points=list(product((0.,.125),(0.,.25),(0.,.25))); geometry=dict(enumerate(points));cells={3:list(geometry)}
        stress=[[2.,3.,0.],[3.,4.,0.],[0.,0.,5.]];strain=[[.001,.002,0.],[.002,.003,0.],[0.,0.,.004]]
        state=dict(stress=stress,elastic_strain=strain);qp={(3,q):(q,state) for q in range(8)}
        energy,bound=a.energy_products(geometry,cells,qp,POLICY)
        volume=.125*.25*.25
        self.assertAlmostEqual(energy,.5*volume*sum(stress[i][j]*strain[i][j] for i in range(3) for j in range(3)))
        self.assertAlmostEqual(bound,.5*volume*sum(POLICY['stress_Pa']*abs(strain[i][j])+POLICY['strain']*abs(stress[i][j])+POLICY['stress_Pa']*POLICY['strain'] for i in range(3) for j in range(3)))
        self.assertGreater(bound,0.)

    def test_completed_storage_data_registry_gates_fail_closed(self):
        keys=('data_result_peer','data_root_acceptance','native_capture_peer','native_capture_root_acceptance',
              'native_storage_audit','native_storage_root_acceptance','TimePeriod24_presence','TimePeriod24_root_closed')
        c={k:'work/962-engineering/fake/'+k+'.json' for k in keys};pins={v:'a'*64 for v in c.values()}
        c.update(continuation_data_peer_and_root_accepted=True,complete_native_storage_audit_and_root_review_complete=True,TimePeriod24_registry_peer_and_root_review_complete=True)
        with patch.object(a,'sha',return_value='a'*64):a.completed_evidence(c,pins)
        for k in keys:
            with patch.object(a,'sha',return_value='a'*64),self.assertRaises(ValueError):a.completed_evidence({**c,k:None},pins)
        with patch.object(a,'sha',return_value='b'*64),self.assertRaises(ValueError):a.completed_evidence(c,pins)
        with self.assertRaises(ValueError):a.completed_evidence({**c,'complete_native_storage_audit_and_root_review_complete':False},pins)

    def test_all183_native_frames_required_without_decoder_or_numbering_guess(self):
        geometry=geometry_fixture();inverse={p:t for t,p in geometry.items()}
        corners=((0.,0.,0.),(.125,0.,0.),(.125,.25,0.),(0.,.25,0.),(0.,0.,.25),(.125,0.,.25),(.125,.25,.25),(0.,.25,.25))
        cells={11*i+3:[inverse[(x+dx,y+dy,z+dz)] for dx,dy,dz in corners] for i,(x,y,z) in enumerate(product(tuple(i/8 for i in range(16)),tuple(i/4 for i in range(4)),tuple(i/4 for i in range(4))))}
        def member(first,last):
            times=[i/400 for i in range(first,last+1)]
            return dict(nodes=geometry,cells=cells,blocks={t:2 if max(geometry[n][0] for n in conn)<=1. else 1 if first<80 else 3 for t,conn in cells.items()},times=times,node_map=[t+1 for t in geometry],element_map=[t+1 for t in cells],fields={},block_ids=[1,2] if first<80 else [2,3],block_status=[1,1])
        with TemporaryDirectory() as name:
            directory=Path(name);names=['thermoelastic.e','thermoelastic.e-s002']
            for fn in names:(directory/fn).write_bytes(b'CDF\x02')
            transfer={'node_rows':[dict(source_node_id=t,coordinates_m=list(p)) for t,p in geometry.items()]}
            with patch.object(a,'read_exodus',side_effect=[member(0,79),member(80,182)]):self.assertEqual(len(a.geometry_family(directory,names,transfer)[2]),183)
            with patch.object(a,'read_exodus',side_effect=[member(0,79),member(80,181)]),self.assertRaises(ValueError):a.geometry_family(directory,names,transfer)

    def test_unchanged_math_readers_policy_and_own_birth_reference_source(self):
        donor=a.ROOT/'work/962-engineering/cp1-oneway-thermoelastic-assessor-prep-003/assess.py'
        def defs(path):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(path.read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        old,new=defs(donor),defs(SOURCE)
        for name in ('need','sha','bits','number','integer','rows','tensor','symgrad','hooke','hex_rule','ordered_hex','mechanical_state','accumulate','Audit','node_sample','cdf_magic','read_exodus','quadrature_sample','field_phase'):self.assertEqual(old[name],new[name])
        policy=json.loads(SOURCE.with_name('POLICY.json').read_text())
        self.assertEqual(policy['absolute_SI_limits'],POLICY)
        text=SOURCE.read_text();self.assertIn("born_u = {tag: [nodal[tag][k] for k in DISP] for tag in born_nodes}",text)
        self.assertNotIn('cp1-oneway-thermoelastic-transfer-002',text)
        self.assertIn("if step >= 181 or (step == 180 and phase == 'end'):",text)
        self.assertFalse(policy['qualification']['material_qualified'])


if __name__=='__main__':unittest.main()
